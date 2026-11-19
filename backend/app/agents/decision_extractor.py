import logging
from typing import Dict, Any, List, Optional
from app.utils.llm import generate_json
from app.services.code_mapping import code_mapping_service

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_INSTRUCTION = """You are DecisionTrail's Senior Engineering Decision Extraction Agent.
Your mission is to extract factual, evidence-backed engineering and architectural decisions from software discussions (issues, pull requests, reviews, comments).

CRITICAL RULES:
1. NEVER invent or hallucinate decisions, reasoning, or alternatives not grounded in the text.
2. If the discussion text or PR title clearly states a concrete technical change or integration (such as adding a dependency, connecting frontend to deployed backend, integrating maps, standardizing detection interfaces, or adopting a library), extract it as an accepted engineering decision.
3. Every item in 'reasoning' and 'rejected_alternatives' must be grounded in direct statements from the discussion or PR title.
4. 'evidence' MUST be exact or near-verbatim quotes/excerpts from the text supporting the decision.
5. 'code_references' must only include real file names or paths mentioned in the text. If none are mentioned, return an empty array [].
6. If the discussion does NOT reach a clear decision, or evidence is ambiguous/insufficient, mark "status": "uncertain" or return an empty list [] only if the PR is purely trivial maintenance with zero technical meaning (e.g. whitespace cleanup).
7. Possible statuses: "accepted", "rejected", "proposed", "deprecated", "uncertain".

Output a JSON array of decision objects adhering to this schema:
[
  {
    "decision": "Brief concise decision title (e.g., Retain SQLite for local storage)",
    "status": "accepted",
    "context": "Context describing why this discussion took place",
    "rejected_alternatives": ["PostgreSQL", "MySQL"],
    "reasoning": ["Deployment complexity", "Embedded zero-config requirement"],
    "affected_components": ["Storage", "Database"],
    "code_references": ["app/database.py"],
    "evidence": ["Excerpt: 'After benchmarking, SQLite fulfills our single-node latency goals without adding server ops.'"],
    "confidence": 0.95
  }
]
If there are no engineering decisions in the text, return [].
"""


class DecisionExtractorAgent:
    @staticmethod
    async def extract_from_discussion(
        title: str,
        body: str,
        source_url: str,
        comments: Optional[List[Dict[str, Any]]] = None,
        source_type: str = "github"
    ) -> List[Dict[str, Any]]:
        """
        Extracts structured engineering decisions from a discussion.
        Uses Gemini LLM with structured output, backed by code mapping and heuristic fallback.
        """
        full_text = f"Title: {title}\n\nBody:\n{body}\n\n"
        if comments:
            full_text += "Comments:\n"
            for idx, c in enumerate(comments[:8]):
                author = c.get("author", "User")
                c_body = c.get("body", "")
                full_text += f"[{author}]: {c_body}\n"

        prompt = f"""Analyze the following engineering discussion and extract any architectural/technical decisions:

{full_text[:7000]}

Extract all distinct decisions as a JSON array matching the required format.
"""
        decisions: List[Dict[str, Any]] = []

        # 1. Attempt LLM extraction
        llm_output = await generate_json(prompt, system_instruction=EXTRACTION_SYSTEM_INSTRUCTION)
        if isinstance(llm_output, list):
            for d in llm_output:
                if isinstance(d, dict) and "decision" in d and "context" in d:
                    # Validate and enrich
                    code_refs = d.get("code_references") or []
                    # Verify with code mapping service
                    extracted_refs = code_mapping_service.extract_file_references(full_text)
                    merged_refs = sorted(list(set(code_refs + [r for r in extracted_refs if r in full_text])))

                    decision_obj = {
                        "decision": str(d.get("decision", "")).strip(),
                        "status": str(d.get("status", "accepted")).lower(),
                        "context": str(d.get("context", "")).strip(),
                        "rejected_alternatives": d.get("rejected_alternatives") or [],
                        "reasoning": d.get("reasoning") or [],
                        "affected_components": d.get("affected_components") or [],
                        "code_references": merged_refs,
                        "evidence": d.get("evidence") or [title],
                        "source_url": source_url,
                        "source_type": source_type,
                        "confidence": float(d.get("confidence", 0.9)),
                    }
                    if decision_obj["decision"]:
                        decisions.append(decision_obj)

        # 2. Heuristic fallback when LLM is unavailable or key not configured
        if not decisions:
            heuristic_decision = DecisionExtractorAgent._heuristic_extract(title, body, source_url, source_type)
            if heuristic_decision:
                decisions.append(heuristic_decision)

        return decisions

    @staticmethod
    def _heuristic_extract(title: str, body: str, source_url: str, source_type: str) -> Optional[Dict[str, Any]]:
        """
        Rule-based decision detection for offline or non-API key operation.
        Detects ADR-like or decision keywords, conventions (feat, bump, refactor, use, redesign).
        """
        combined = f"{title}\n{body}".lower()
        title_lower = title.lower().strip()

        # Decision indicators in software PRs/issues
        decision_patterns = [
            "decide", "decision", "adopt", "migrate", "switch to", "replace",
            "deprecate", "reject", "in favor of", "instead of", "rather than",
            "use ", "add ", "added", "feat:", "feat(", "bump ", "upgrade ", "redesign ",
            "refactor ", "standardize ", "implement ", "integrate ", "remove ",
            "connect", "connected", "improve", "improved", "link ", "deploy",
            "setup", "configure", "pipeline", "model"
        ]

        has_decision = any(kw in combined for kw in decision_patterns)
        if not has_decision:
            return None

        code_refs = code_mapping_service.extract_file_references(f"{title}\n{body}")

        # Extract status
        status = "accepted"
        if "reject" in combined or "won't fix" in combined:
            status = "rejected"
        elif "deprecat" in combined:
            status = "deprecated"
        elif "propos" in combined or "rfc" in combined:
            status = "proposed"

        # Extract rejected alternatives if "instead of", "over", "rather than", "leave ... as" is present
        rejected_alts = []
        if "instead of" in combined:
            parts = combined.split("instead of")
            if len(parts) > 1:
                rejected_alts.append(parts[1].split()[0].strip(",.;"))
        elif "over " in combined and ("sqlite" in combined or "postgres" in combined):
            parts = combined.split("over ")
            if len(parts) > 1:
                rejected_alts.append(parts[1].split()[0].strip(",.;"))
        elif "and leave " in combined:
            parts = combined.split("and leave ")
            if len(parts) > 1:
                rejected_alts.append(f"Leaving {parts[1][:40].strip(',.;')}")

        # Determine affected component
        component = "Core Architecture"
        if any(w in combined for w in ["ui", "card", "font", "css", "styling", "page", "hero", "layout", "landing", "frontend"]):
            component = "Frontend UI"
        elif any(w in combined for w in ["backend", "api", "endpoint", "server", "deploy", "connect"]):
            component = "Backend & API"
        elif any(w in combined for w in ["detection", "model", "map", "safety", "analytics"]):
            component = "Safety Analytics"
        elif any(w in combined for w in ["database", "db", "sql", "storage", "sqlite", "postgres"]):
            component = "Storage & Database"
        elif any(w in combined for w in ["lab", "3d", "trainer", "circuit", "breadboard", "simulator"]):
            component = "Lab Simulations"
        elif any(w in combined for w in ["deps", "dependency", "dotenv", "bump", "next", "react"]):
            component = "Dependencies"

        # Clean decision title
        clean_title = title.strip()
        if clean_title.startswith("feat:") or clean_title.startswith("fix:"):
            clean_title = clean_title.split(":", 1)[1].strip()

        # Evidence excerpt
        evidence_snippet = body[:300].strip() if body and len(body.strip()) > 10 else title

        return {
            "decision": clean_title,
            "status": status,
            "context": f"Extracted from discussion: {title}",
            "rejected_alternatives": rejected_alts,
            "reasoning": [f"Implemented in {source_type} #{clean_title[:30]}"],
            "affected_components": [component],
            "code_references": code_refs,
            "evidence": [evidence_snippet],
            "source_url": source_url,
            "source_type": source_type,
            "confidence": 0.8,
        }


decision_extractor = DecisionExtractorAgent()
