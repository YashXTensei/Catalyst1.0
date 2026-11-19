import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.decision import Decision
from app.models.repository import Repository
from app.utils.embeddings import generate_embedding, cosine_similarity, is_valid_embedding
from app.services.code_mapping import code_mapping_service

logger = logging.getLogger(__name__)


class ProjectMemoryService:
    @staticmethod
    async def store_decision(
        db: Session,
        repo_id: int,
        decision_data: Dict[str, Any],
        discussion_id: Optional[int] = None,
        source_id: Optional[str] = None,
    ) -> Optional[Decision]:
        """
        Stores structured decision in database with vector embedding, avoiding duplicates.
        """
        decision_title = decision_data.get("decision", "").strip()
        if not decision_title:
            return None

        # Check for deduplication by source_id or decision title within this repo
        existing = db.query(Decision).filter(
            Decision.repo_id == repo_id,
            or_(
                Decision.source_id == source_id if source_id else False,
                Decision.decision == decision_title,
            )
        ).first()

        if existing:
            # Update evidence if richer
            if len(decision_data.get("evidence", [])) > len(existing.evidence or []):
                existing.evidence = decision_data.get("evidence", [])
                db.commit()
            return existing

        # Generate embedding for the decision summary & reasoning
        text_to_embed = (
            f"Decision: {decision_title}. "
            f"Context: {decision_data.get('context', '')}. "
            f"Reasoning: {' '.join(decision_data.get('reasoning', []))}. "
            f"Rejected alternatives: {' '.join(decision_data.get('rejected_alternatives', []))}. "
            f"Components: {' '.join(decision_data.get('affected_components', []))}."
        )
        embedding_vec = await generate_embedding(text_to_embed)
        # A failed or invalid provider response must never introduce a vector
        # that is incompatible with the configured embedding model.
        if embedding_vec is not None and not is_valid_embedding(embedding_vec):
            logger.error("Refusing to save an invalid embedding for decision '%s'.", decision_title)
            embedding_vec = None

        new_decision = Decision(
            repo_id=repo_id,
            discussion_id=discussion_id,
            decision=decision_title,
            status=decision_data.get("status", "accepted"),
            context=decision_data.get("context", ""),
            rejected_alternatives=decision_data.get("rejected_alternatives", []),
            reasoning=decision_data.get("reasoning", []),
            affected_components=decision_data.get("affected_components", []),
            code_references=decision_data.get("code_references", []),
            evidence=decision_data.get("evidence", []),
            source_url=decision_data.get("source_url", ""),
            source_type=decision_data.get("source_type", "github"),
            source_id=source_id,
            confidence=float(decision_data.get("confidence", 1.0)),
            embedding=embedding_vec,
        )

        db.add(new_decision)
        db.commit()
        db.refresh(new_decision)

        # Update repository total_decisions counter
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            repo.total_decisions = db.query(Decision).filter(Decision.repo_id == repo_id).count()
            db.commit()

        return new_decision

    @staticmethod
    async def search_decisions(
        db: Session,
        repo_id: int,
        query: str,
        top_k: int = 5,
        min_score: float = 0.05,
    ) -> List[Tuple[Decision, float]]:
        """
        Hybrid search combining semantic vector similarity + keyword relevance.
        """
        decisions = db.query(Decision).filter(Decision.repo_id == repo_id).all()
        if not decisions:
            return []

        query_vec = await generate_embedding(query)
        # Extract clean words without punctuation
        raw_words = re.findall(r"\w+", query.lower())
        stop_words = {
            "why", "what", "how", "when", "where", "which", "who", "was", "is", "are", 
            "were", "been", "the", "a", "an", "in", "of", "to", "for", "with", "on", 
            "at", "by", "from", "up", "about", "into", "over", "after", "it", "its", 
            "this", "that", "these", "those", "can", "could", "would", "should", 
            "working", "work", "works", "properly", "hello", "hi", "hey", "tell", 
            "show", "give", "please", "you", "your", "project", "repo", "system"
        }
        query_words = set(w for w in raw_words if len(w) > 2 and w not in stop_words)

        scored: List[Tuple[Decision, float]] = []

        for d in decisions:
            # 1. Semantic score
            sem_score = 0.0
            if is_valid_embedding(d.embedding) and is_valid_embedding(query_vec):
                sem_score = max(0.0, cosine_similarity(query_vec, d.embedding))

            # 2. Keyword score
            corpus = (
                f"{d.decision} {d.context} "
                f"{' '.join(d.rejected_alternatives or [])} "
                f"{' '.join(d.reasoning or [])} "
                f"{' '.join(d.affected_components or [])} "
                f"{' '.join(d.code_references or [])}"
            ).lower()

            kw_matches = sum(1 for w in query_words if w in corpus)
            kw_score = min(1.0, kw_matches * 0.35)

            # Hybrid blended score
            final_score = (0.55 * sem_score) + (0.45 * kw_score)

            # High-signal relevance gate:
            # - If 2+ keywords match: high confidence
            # - If 1 keyword matches: must also have reasonable semantic alignment (>= 0.40)
            # - If 0 keywords match: must have strong semantic similarity (>= 0.55)
            is_relevant = False
            if kw_matches >= 2:
                is_relevant = True
            elif kw_matches == 1 and sem_score >= 0.40:
                is_relevant = True
            elif kw_matches == 0 and sem_score >= 0.55:
                is_relevant = True

            if is_relevant:
                scored.append((d, final_score))

        # Sort descending by score
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    @staticmethod
    def get_decisions_by_code_references(
        db: Session,
        repo_id: int,
        changed_files: List[str]
    ) -> List[Decision]:
        """
        Finds decisions whose code references match any of the changed files in a PR.
        """
        if not changed_files:
            return []

        all_decisions = db.query(Decision).filter(Decision.repo_id == repo_id).all()
        matching = []

        for d in all_decisions:
            if not d.code_references:
                continue
            matched_files = code_mapping_service.map_decision_to_pr_files(d.code_references, changed_files)
            if matched_files:
                matching.append(d)

        return matching


memory_service = ProjectMemoryService()
