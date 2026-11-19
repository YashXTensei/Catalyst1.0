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
    def _is_conversational_or_greeting(query: str) -> bool:
        """Detects if query is a greeting, status check, or casual conversation rather than an engineering question."""
        q = query.strip().lower()
        words = re.findall(r"\w+", q)
        if not words:
            return True

        greetings = {"hello", "hi", "hey", "hola", "namaste", "good morning", "good afternoon", "good evening", "howdy", "sup", "yo"}
        if len(words) <= 3 and any(w in greetings for w in words):
            return True

        status_phrases = [
            "working properly", "is it working", "is this working", "are you working", 
            "working fine", "all good", "status", "health check", "ping", "test",
            "kaise ho", "kya chal raha", "works properly"
        ]
        if any(sp in q for sp in status_phrases):
            # Only treat as status check if no specific technical entity is named
            technical_nouns = ["pr", "issue", "database", "api", "model", "scene", "docker", "redux", "circuit", "breadboard"]
            if not any(tn in q for tn in technical_nouns):
                return True

        meta_phrases = [
            "who are you", "what can you do", "what do you do", "how do you work", 
            "help me", "help", "thank you", "thanks", "dhanyawad", "bye", "goodbye"
        ]
        if any(mp in q for mp in meta_phrases):
            return True

        return False

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
        1. Checks for conversational / greeting intent.
        2. Hybrid search on stored repository memory.
        3. If memory is sparse or lacking high-confidence matches, performs targeted GitHub search on-demand.
        4. Synthesizes a factual, citation-backed response.
        """
        total_repo_decisions = db.query(Decision).filter(Decision.repo_id == repo.id).count()

        # Step 0: Handle conversational greetings and health-check queries directly
        if QuestionAnsweringAgent._is_conversational_or_greeting(question):
            sample_decisions = db.query(Decision).filter(Decision.repo_id == repo.id).order_by(Decision.created_at.desc()).limit(3).all()
            sample_queries = []
            for d in sample_decisions:
                sample_queries.append(f"• *\"What was decided regarding: {d.decision}?\"*")
            sample_text = "\n".join(sample_queries) if sample_queries else "• *\"What were the key architectural decisions made?\"*"

            answer = (
                f"👋 **Hello! DecisionTrail Intelligence is active and working properly for `{repo.full_name}`.**\n\n"
                f"Currently, **{total_repo_decisions} architectural decision(s)** are indexed in this repository's vector memory.\n\n"
                f"You can ask me technical questions about why specific libraries were chosen, what alternatives were rejected, or how components were designed.\n\n"
                f"💡 **Example questions you can ask right now:**\n{sample_text}"
            )

            return QuestionResponse(
                question=question,
                answer=answer,
                confidence="high",
                evidence_found=True,
                decisions_used=[],
                citations=[],
                search_strategy="conversational_greeting",
            )

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

        # Step 3: If no relevant decisions found at all, call Gemini for honest, helpful architectural context
        if not top_decisions:
            logger.info(f"No direct decisions found for '{question}'. Calling Gemini for architectural context.")

            fallback_prompt = f"""You are DecisionTrail's Senior Technical Architect for '{repo.full_name}'.
The user asked: "{question}"

No historical engineering decision, issue discussion, or pull request in this repository matches this question.

YOUR MISSION:
1. Clearly state upfront:
   "Mujhe **{repo.full_name}** me is topic ('{question}') se related koi historical engineering decision ya discussion nahi mili."
2. Provide a helpful, concise standard engineering perspective or explanation based on general software architecture.
3. If this repository focuses on specific topics, mention what developers can ask about instead.

Keep it direct, professional, and friendly. Do NOT invent fake decisions.
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
                sample_list = "\n".join([f"• \"{ed.decision}\"" for ed in existing_sample])
                answer_text = (
                    f"Mujhe **{repo.full_name}** repository me '{question}' se related koi historical engineering decision nahi mili.\n\n"
                    f"**Is repository me aap in decisions ke baare me pooch sakte hain:**\n{sample_list}"
                )
            else:
                answer_text = (
                    f"Mujhe **{repo.full_name}** repository me '{question}' se related koi historical engineering decision nahi mili."
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
CRITICAL: If the provided decisions do not actually address the user's question, clearly state:
"Mujhe is repository me is topic se related koi specific engineering decision nahi mili."
"""
        raw_answer = await generate_text(prompt, system_instruction=QA_SYSTEM_PROMPT)
        answer = raw_answer.strip() if raw_answer else "Unable to synthesize answer from retrieved context."

        # If answer states nothing was found, suppress citations
        if "nahi mili" in answer or "No relevant historical engineering decision" in answer:
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
