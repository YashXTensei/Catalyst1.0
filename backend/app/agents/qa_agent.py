import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.repository import Repository
from app.models.decision import Decision
from app.schemas.qa import QuestionResponse, Citation
from app.schemas.decision import DecisionResponse
from app.services.memory_service import memory_service
from app.services.github_service import github_service
from app.agents.decision_extractor import decision_extractor
from app.utils.llm import generate_text

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = """You are DecisionTrail's Engineering Decision Intelligence Assistant.
Your job is to answer the user's technical question based STRICTLY and ONLY on the historical decisions, discussion excerpts, and evidence provided in the context.

STRICT RULES:
1. If the provided context DOES NOT contain evidence to answer the question, explicitly state:
   "No relevant historical engineering decision or discussion was found in this repository regarding this topic."
   Do NOT speculate or fabricate reasons.
2. When answering, cite the specific decision, reasons, trade-offs, and rejected alternatives explicitly.
3. Keep the answer professional, concise, structured, and developer-oriented.
4. Quote the exact evidence excerpts when relevant.
"""


class QuestionAnsweringAgent:
    @staticmethod
    async def answer_question(
        db: Session,
        repo: Repository,
        question: str,
    ) -> QuestionResponse:
        """
        Executes Question-First retrieval & answering pipeline:
        1. Hybrid search on stored repository memory.
        2. If memory is sparse or lacking high-confidence matches, performs targeted GitHub search on-demand.
        3. Extracts and persists on-demand decisions to project memory.
        4. Synthesizes a factual, citation-backed response.
        """
        search_strategy = "cached_memory"
        top_decisions: List[Decision] = []

        # Step 1: Hybrid search from existing database
        scored_decisions = await memory_service.search_decisions(db, repo.id, question, top_k=5)
        top_decisions = [d for d, score in scored_decisions]

        # Step 2: Question-First On-Demand Search if memory has few or low-confidence results
        if len(top_decisions) < 2:
            try:
                search_strategy = "hybrid_on_demand"
                logger.info(f"Triggering on-demand search for question: '{question}' in {repo.full_name}")
                # Extract main search terms from question
                terms = " ".join([w for w in question.replace("?", "").replace("why", "").replace("was", "").split() if len(w) > 2])
                discussions = await github_service.search_discussions(repo.owner, repo.name, terms, limit=4)

                for disc in discussions:
                    # Fetch comments for deeper context
                    comments = await github_service.fetch_comments(repo.owner, repo.name, disc.get("number", 0), limit=5)
                    extracted = await decision_extractor.extract_from_discussion(
                        title=disc.get("title", ""),
                        body=disc.get("body", ""),
                        source_url=disc.get("url", ""),
                        comments=comments,
                        source_type="github",
                    )
                    for ed in extracted:
                        new_dec = await memory_service.store_decision(
                            db=db,
                            repo_id=repo.id,
                            decision_data=ed,
                            source_id=f"search_{disc.get('source_id')}_{ed.get('decision')[:30]}",
                        )
                        if new_dec and new_dec not in top_decisions:
                            top_decisions.append(new_dec)
            except Exception as e:
                logger.warning(f"On-demand targeted search error: {e}")

        # If no decisions found at all, call Gemini for intelligent architectural perspective
        if not top_decisions:
            logger.info(f"No direct decisions found for '{question}'. Calling Gemini for architectural context.")
            total_repo_decisions = db.query(Decision).filter(Decision.repo_id == repo.id).count()

            fallback_prompt = f"""You are DecisionTrail's Senior Technical Architect.
The user is asking a question in the context of the repository '{repo.full_name}' (Description: {repo.description or 'Open source software'}).
Total decisions indexed in this repository's vector memory: {total_repo_decisions}.

User question: "{question}"

Our repository project memory search found NO specific internal decision or discussion thread matching this query.

YOUR MISSION:
1. If the question is a conversational, status, or health-check question (e.g. "working properly?", "is this working?", "hello", "status", "test"):
   - Confirm clearly that DecisionTrail's memory and retrieval engine is online and fully operational for '{repo.full_name}'.
   - State that currently {total_repo_decisions} decision(s) are indexed in memory for this repository.
   - If this repo has only 1 decision (e.g., 'Add python-dotenv dependency'), mention it, and remind the user that they can switch to the 'vlabs-iiit-sonepat' repository in the top navigation dropdown to explore 80+ architectural decisions (like Op-Amp LM741 IC, 3D room scenes, FEE lab circuits).
2. If the question asks about a specific technology, library, or engineering design:
   - State clearly: "No specific historical engineering decision was recorded in **{repo.full_name}** regarding '{question}'."
   - Provide an intelligent, helpful architectural perspective based on modern software engineering practices.
   - Suggest relevant topics that are actually present in this project's memory.

Keep the response concise, helpful, and developer-friendly.
"""
            llm_fallback_answer = await generate_text(fallback_prompt)

            if llm_fallback_answer and llm_fallback_answer.strip():
                return QuestionResponse(
                    question=question,
                    answer=llm_fallback_answer.strip(),
                    confidence="general_knowledge",
                    evidence_found=False,
                    decisions_used=[],
                    citations=[],
                    search_strategy="ai_general_knowledge",
                )

            # Rule-based fallback if LLM is unavailable
            existing_sample = db.query(Decision).filter(Decision.repo_id == repo.id).limit(4).all()
            if existing_sample:
                topics = set()
                for ed in existing_sample:
                    for comp in (ed.affected_components or []):
                        topics.add(comp)
                topics_str = ", ".join(list(topics)[:3]) or "Frontend UI, Components, and Core Architecture"
                sample_list = "\n".join([f"• \"{ed.decision}\"" for ed in existing_sample])
                answer_text = (
                    f"No historical decision was found in **{repo.full_name}** regarding '{question}'.\n\n"
                    f"💡 **Context**: This repository's recorded decisions primarily focus on **{topics_str}**.\n\n"
                    f"**Topics and decisions you can ask about in this repository:**\n{sample_list}\n\n"
                    f"*(Try asking a question about one of the above!)*"
                )
            else:
                answer_text = (
                    f"No relevant historical engineering decision or discussion was found in repository "
                    f"'{repo.full_name}' regarding '{question}'."
                )

            return QuestionResponse(
                question=question,
                answer=answer_text,
                confidence="insufficient_evidence",
                evidence_found=False,
                decisions_used=[],
                citations=[],
                search_strategy=search_strategy,
            )

        # Step 3: Construct context for LLM synthesis
        context_blocks = []
        citations: List[Citation] = []
        decisions_used_schemas: List[DecisionResponse] = []

        for d in top_decisions[:5]:
            evidence_str = "; ".join(d.evidence) if d.evidence else "No quote available"
            reasoning_str = "; ".join(d.reasoning) if d.reasoning else "Not specified"
            rejected_str = "; ".join(d.rejected_alternatives) if d.rejected_alternatives else "None recorded"
            code_str = ", ".join(d.code_references) if d.code_references else "None"

            block = (
                f"- Decision: {d.decision} (Status: {d.status})\n"
                f"  Context: {d.context}\n"
                f"  Reasoning: {reasoning_str}\n"
                f"  Rejected Alternatives: {rejected_str}\n"
                f"  Affected Code Files: {code_str}\n"
                f"  Evidence: {evidence_str}\n"
                f"  Source URL: {d.source_url}\n"
            )
            context_blocks.append(block)

            citations.append(
                Citation(
                    decision_id=d.id,
                    decision_title=d.decision,
                    source_url=d.source_url,
                    evidence_snippet=evidence_str[:250],
                    source_type=d.source_type or "github",
                )
            )
            decisions_used_schemas.append(DecisionResponse.model_validate(d))

        prompt = f"""Question: {question}

Historical Engineering Context from {repo.full_name}:
{"".join(context_blocks)}

Synthesize a direct, clear, and well-structured answer explaining the decision, rationale, rejected alternatives, and trade-offs. Cite the evidence directly. If evidence is insufficient, state so clearly.
"""

        llm_answer = await generate_text(prompt, system_instruction=QA_SYSTEM_PROMPT)

        if not llm_answer or not llm_answer.strip():
            # Fallback deterministic answer synthesis
            primary = top_decisions[0]
            reasons = "; ".join(primary.reasoning) if primary.reasoning else "General consensus"
            rejected = f" Alternatives rejected: {', '.join(primary.rejected_alternatives)}." if primary.rejected_alternatives else ""
            llm_answer = (
                f"Based on historical records, the decision was to **{primary.decision}** (Status: {primary.status}).\n\n"
                f"**Context**: {primary.context}\n"
                f"**Key Rationale**: {reasons}.{rejected}\n\n"
                f"**Evidence**: \"{'; '.join(primary.evidence[:2]) if primary.evidence else primary.context}\""
            )

        return QuestionResponse(
            question=question,
            answer=llm_answer.strip(),
            confidence="high" if len(top_decisions) >= 1 else "medium",
            evidence_found=True,
            decisions_used=decisions_used_schemas,
            citations=citations,
            search_strategy=search_strategy,
        )


qa_agent = QuestionAnsweringAgent()
