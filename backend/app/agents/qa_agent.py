import logging
import re
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
    def _has_technical_keywords(query: str) -> bool:
        """Determines if query contains technical terminology suitable for GitHub on-demand search."""
        q = query.lower()
        technical_terms = [
            "why", "decide", "decision", "alternative", "rejected", "architecture", 
            "library", "framework", "database", "storage", "api", "backend", "frontend",
            "component", "standardize", "migrate", "upgrade", "auth", "token", "diff",
            "fastapi", "react", "redux", "sqlite", "postgres", "docker", "redis", "celery", 
            "zustand", "vue", "ic", "circuit", "breadboard", "scene", "3d", "trainer", 
            "op-amp", "fee", "starlight", "lunaria", "dotenv", "yolo", "detection"
        ]
        return any(term in q for term in technical_terms)

    @staticmethod
    async def answer_question(
        db: Session,
        repo: Repository,
        question: str,
    ) -> QuestionResponse:
        """
        Executes Question-First retrieval & answering pipeline:
        1. Hybrid search on stored repository memory.
        2. If memory is sparse and query has technical keywords, performs targeted GitHub search on-demand.
        3. Synthesizes a factual, citation-backed response if evidence exists.
        4. If no specific repo decisions exist, naturally and intelligently converses with the user.
        """
        total_repo_decisions = db.query(Decision).filter(Decision.repo_id == repo.id).count()
        search_strategy = "cached_memory"
        top_decisions: List[Decision] = []

        # Step 1: Hybrid search from existing database
        scored_decisions = await memory_service.search_decisions(db, repo.id, question, top_k=5)
        top_decisions = [d for d, score in scored_decisions]

        # Step 2: Question-First On-Demand Search only if technical keywords exist
        if len(top_decisions) < 2 and QuestionAnsweringAgent._has_technical_keywords(question):
            try:
                search_strategy = "hybrid_on_demand"
                logger.info(f"Triggering on-demand search for question: '{question}' in {repo.full_name}")
                terms = " ".join([w for w in question.replace("?", "").replace("why", "").replace("was", "").split() if len(w) > 2])
                discussions = await github_service.search_discussions(repo.owner, repo.name, terms, limit=4)

                for disc in discussions:
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

        # Step 3: If no relevant repository decisions matched, use Gemini for natural, intelligent response
        if not top_decisions:
            logger.info(f"No direct decisions found for '{question}'. Calling Gemini with generic conversational prompt.")

            fallback_prompt = f"""You are DecisionTrail Intelligence, an AI assistant integrated with the repository '{repo.full_name}'.
Repository description: {repo.description or 'Open source project'}.
Total decisions currently recorded in memory for this repo: {total_repo_decisions}.

User input: "{question}"

Repository search result: No specific historical engineering decisions or ADRs in this repo matched this query.

INSTRUCTIONS:
1. Casual chat, greetings, jokes, or everyday conversation (e.g. "Whats your name?", "Jus chill have a break bro", "How are you?", "Tell me a joke", "Hello", "Working properly?"):
   - Reply naturally, warmly, and conversationally in the same language and friendly vibe as the user.
   - Feel free to be playful, supportive, and human.
   - NEVER use robotic boilerplate like "No historical ADR was found" or "Mujhe is topic se related koi decision nahi mila" for casual chat!
2. Questions specifically about this project or software engineering (e.g. "What database does this use?", "Why React?", "How do I deploy?"):
   - If it's about a specific decision not recorded here, simply say naturally that there's no recorded decision about this in the repo's history yet.
   - Provide an intelligent, helpful architectural perspective based on modern software engineering practices.
   - If relevant, mention what topics developers can ask about in this repository.
"""
            llm_fallback_answer = await generate_text(fallback_prompt, subsystem="qa")

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

            # Simple fallback if LLM is offline
            return QuestionResponse(
                question=question,
                answer="I'm online and ready to assist you! Feel free to ask about this project's architecture, past decisions, or any engineering questions.",
                confidence="general_knowledge",
                evidence_found=False,
                decisions_used=[],
                citations=[],
                search_strategy="cached_memory",
            )

        # Step 4: Construct context for LLM synthesis from genuine matching decisions
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

Synthesize a direct, clear, and well-structured answer explaining the decision, rationale, rejected alternatives, and trade-offs. Cite the evidence directly.
CRITICAL: If the retrieved context does not actually answer what the user asked, answer naturally and clarify that no specific decision was found for that topic.
"""
        raw_answer = await generate_text(prompt, system_instruction=QA_SYSTEM_PROMPT, subsystem="qa")
        answer = raw_answer.strip() if raw_answer else ""

        if not answer:
            primary = top_decisions[0]
            reasons = "; ".join(primary.reasoning) if primary.reasoning else "General consensus"
            rejected = f" Alternatives rejected: {', '.join(primary.rejected_alternatives)}." if primary.rejected_alternatives else ""
            answer = (
                f"Based on historical records, the decision was to **{primary.decision}** (Status: {primary.status}).\n\n"
                f"**Context**: {primary.context}\n"
                f"**Key Rationale**: {reasons}.{rejected}\n\n"
                f"**Evidence**: \"{'; '.join(primary.evidence[:2]) if primary.evidence else primary.context}\""
            )

        # If answer states nothing was found, suppress citations
        if "No relevant historical engineering decision" in answer or "koi specific engineering decision nahi mili" in answer or "nahi mili" in answer:
            citations = []
            decisions_used_schemas = []

        return QuestionResponse(
            question=question,
            answer=answer,
            confidence="high" if len(top_decisions) >= 2 else "medium",
            evidence_found=True if citations else False,
            decisions_used=decisions_used_schemas,
            citations=citations,
            search_strategy=search_strategy,
        )


qa_agent = QuestionAnsweringAgent()
