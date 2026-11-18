import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.repository import Repository
from app.models.decision import Decision
from app.schemas.pr import PRAnalyzeResponse, PotentialConflict
from app.schemas.decision import DecisionResponse
from app.services.github_service import github_service
from app.services.memory_service import memory_service
from app.utils.llm import generate_json

logger = logging.getLogger(__name__)

PR_ANALYSIS_SYSTEM_INSTRUCTION = """You are DecisionTrail's PR Intelligence & Architectural Drift Agent.
Your job is to compare a Pull Request's title, description, and changed files against historical engineering decisions from this repository.

STRICT CRITERIA:
1. Identify any conflicts where the PR might violate, revert, or run counter to a previously accepted architectural or technical decision (e.g., re-introducing a rejected library, changing a locked database choice, bypassing agreed architecture patterns).
2. Never hallucinate historical decisions; only compare against the provided historical decisions.
3. Assess conflict_risk accurately: "high" (direct contradiction/reversal), "medium" (potential drift or overlapping concern), "low" (minor touchpoint), or "none" (aligned or no conflict).
4. Provide constructive recommendations for the PR author and reviewers.
5. Never automatically approve or reject the PR.

Output a valid JSON object matching:
{
  "summary": "Concise summary of the PR and its architectural footprint",
  "potential_conflicts": [
    {
      "decision_id": 1,
      "conflict_risk": "high",
      "explanation": "PR re-introduces PostgreSQL while Decision #1 explicitly rejected it in favor of SQLite.",
      "affected_files": ["backend/database.py"],
      "evidence_snippet": "Decision excerpt quote",
      "recommendation": "Review whether requirements have changed since Issue #45 before proceeding."
    }
  ],
  "overall_risk": "high",
  "recommendations": [
    "Verify compatibility with existing SQLite schema.",
    "Tag architectural reviewer @lead."
  ]
}
"""


class PRIntelligenceAgent:
    @staticmethod
    async def analyze_pull_request(
        db: Session,
        repo: Repository,
        pr_number: int,
    ) -> PRAnalyzeResponse:
        """
        Analyzes a pull request against historical project decisions.
        """
        # Step 1: Fetch PR info & changed files
        pr_info = await github_service.fetch_pr_details_and_files(repo.owner, repo.name, pr_number)
        changed_files = pr_info.get("changed_files", [])
        pr_title = pr_info.get("title", f"PR #{pr_number}")
        pr_body = pr_info.get("body", "")

        # Step 2: Retrieve historical decisions via code mapping and semantic search
        related_decisions_map: Dict[int, Decision] = {}

        # 2a. Match by changed files
        file_matched_decisions = memory_service.get_decisions_by_code_references(db, repo.id, changed_files)
        for d in file_matched_decisions:
            related_decisions_map[d.id] = d

        # 2b. Match by PR title & description keywords/semantics
        search_query = f"{pr_title} {' '.join(changed_files[:5])}"
        scored_decisions = await memory_service.search_decisions(db, repo.id, search_query, top_k=6, min_score=0.1)
        for d, score in scored_decisions:
            related_decisions_map[d.id] = d

        related_decisions = list(related_decisions_map.values())

        # Step 3: LLM Conflict & Drift Analysis
        conflicts: List[PotentialConflict] = []
        overall_risk = "none"
        recommendations: List[str] = []
        summary = f"Pull Request #{pr_number} touches {len(changed_files)} file(s)."

        if related_decisions:
            decisions_context = []
            for d in related_decisions:
                decisions_context.append({
                    "id": d.id,
                    "decision": d.decision,
                    "status": d.status,
                    "rejected_alternatives": d.rejected_alternatives,
                    "reasoning": d.reasoning,
                    "code_references": d.code_references,
                    "evidence": d.evidence,
                    "source_url": d.source_url,
                })

            prompt = f"""Pull Request #{pr_number}:
Title: {pr_title}
Author: {pr_info.get('author')}
State: {pr_info.get('state')}
Description:
{pr_body[:2000]}

Changed Files:
{', '.join(changed_files[:30])}

Diff Samples:
{pr_info.get('patches_sample', 'No diff snippet')}

Historical Decisions to compare against:
{decisions_context}

Analyze and return JSON according to instructions.
"""
            llm_result = await generate_json(prompt, system_instruction=PR_ANALYSIS_SYSTEM_INSTRUCTION)
            if isinstance(llm_result, dict):
                summary = llm_result.get("summary", summary)
                overall_risk = llm_result.get("overall_risk", "none").lower()
                recommendations = llm_result.get("recommendations", [])

                for c in llm_result.get("potential_conflicts", []):
                    dec_id = c.get("decision_id")
                    matching_dec = next((d for d in related_decisions if d.id == dec_id), None)
                    if matching_dec:
                        conflicts.append(
                            PotentialConflict(
                                decision_id=matching_dec.id,
                                decision_title=matching_dec.decision,
                                status=matching_dec.status,
                                conflict_risk=c.get("conflict_risk", "medium").lower(),
                                explanation=c.get("explanation", "Potential architectural overlap."),
                                affected_files=c.get("affected_files") or [f for f in changed_files if any(cr in f for cr in matching_dec.code_references or [])],
                                evidence_snippet=c.get("evidence_snippet") or "; ".join(matching_dec.evidence[:1]),
                                recommendation=c.get("recommendation", "Review against historical decision."),
                                source_url=matching_dec.source_url,
                            )
                        )
        else:
            summary = f"PR #{pr_number} proposes changes across {len(changed_files)} file(s). No conflicting historical engineering decisions were detected."
            recommendations.append("Standard code review recommended. No historical architectural conflicts found.")

        # Fallback conflict checking if LLM did not generate or was unavailable
        if not conflicts and related_decisions:
            for d in related_decisions[:2]:
                # Check if PR body or title mentions a rejected alternative
                body_lower = f"{pr_title} {pr_body}".lower()
                for rejected in d.rejected_alternatives or []:
                    if rejected.lower() in body_lower:
                        conflicts.append(
                            PotentialConflict(
                                decision_id=d.id,
                                decision_title=d.decision,
                                status=d.status,
                                conflict_risk="high",
                                explanation=f"PR mentions '{rejected}', which was previously evaluated and rejected in decision: '{d.decision}'.",
                                affected_files=changed_files[:3],
                                evidence_snippet="; ".join(d.evidence[:1]) if d.evidence else d.context,
                                recommendation=f"Check previous decision '{d.decision}' ({d.source_url}) to ensure valid justification for reconsidering {rejected}.",
                                source_url=d.source_url,
                            )
                        )
                        overall_risk = "high"

        return PRAnalyzeResponse(
            pr_number=pr_number,
            pr_title=pr_title,
            pr_url=pr_info.get("url", ""),
            author=pr_info.get("author"),
            state=pr_info.get("state", "open"),
            changed_files=changed_files,
            summary=summary,
            related_decisions=[DecisionResponse.model_validate(d) for d in related_decisions],
            potential_conflicts=conflicts,
            overall_risk=overall_risk,
            recommendations=recommendations or ["Review changes against architecture guidelines."],
        )


pr_agent = PRIntelligenceAgent()
