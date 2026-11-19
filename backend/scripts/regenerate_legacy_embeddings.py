"""Safely regenerate non-current DecisionTrail embeddings.

Run from ``backend``:
    python scripts/regenerate_legacy_embeddings.py --dry-run
    python scripts/regenerate_legacy_embeddings.py --apply

The script generates and validates a replacement before assigning it to a
Decision. Failed records are rolled back individually, retaining their prior
embedding unchanged.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models.decision import Decision
from app.services.memory_service import ProjectMemoryService
from app.utils.embeddings import EMBEDDING_DIMENSION, generate_embedding, is_valid_embedding

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def decision_embedding_text(decision: Decision) -> str:
    """Reconstruct exactly the text used when a decision is initially stored."""
    return (
        f"Decision: {decision.decision}. "
        f"Context: {decision.context}. "
        f"Reasoning: {' '.join(decision.reasoning or [])}. "
        f"Rejected alternatives: {' '.join(decision.rejected_alternatives or [])}. "
        f"Components: {' '.join(decision.affected_components or [])}."
    )


async def migrate_embeddings(db, apply: bool, limit: int | None = None) -> Dict[str, int]:
    """Regenerate every persisted vector that is not the configured dimension."""
    decisions = db.query(Decision).order_by(Decision.id).all()
    legacy = [d for d in decisions if not is_valid_embedding(d.embedding)]
    if limit is not None:
        legacy = legacy[:limit]

    summary = {"candidates": len(legacy), "migrated": 0, "failed": 0, "unchanged": 0}
    for decision in legacy:
        original_embedding = decision.embedding
        try:
            replacement = await generate_embedding(decision_embedding_text(decision))
            if not is_valid_embedding(replacement):
                raise ValueError("provider did not return a valid current-model embedding")

            if not apply:
                summary["unchanged"] += 1
                continue

            # Assignment and commit happen only after successful generation and
            # validation. A rollback restores the original JSON vector on any
            # database error.
            decision.embedding = replacement
            db.commit()
            db.refresh(decision)
            if not is_valid_embedding(decision.embedding):
                raise ValueError("database did not persist a valid replacement")
            summary["migrated"] += 1
        except Exception as exc:
            db.rollback()
            # Confirm the transaction leaves the previous embedding intact.
            db.refresh(decision)
            retained = decision.embedding == original_embedding
            logger.warning(
                "Decision %s was not migrated (%s; original retained=%s).",
                decision.id,
                exc,
                retained,
            )
            summary["failed"] += 1

    return summary


async def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate legacy DecisionTrail embeddings safely.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate candidates without writing (default).")
    mode.add_argument("--apply", action="store_true", help="Persist only valid regenerated embeddings.")
    parser.add_argument("--limit", type=int, help="Maximum legacy records to process.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = await migrate_embeddings(db, apply=args.apply, limit=args.limit)
        logger.info(
            "Target dimension=%s; candidates=%s, migrated=%s, failed=%s, unchanged=%s",
            EMBEDDING_DIMENSION,
            summary["candidates"],
            summary["migrated"],
            summary["failed"],
            summary["unchanged"],
        )
        return 1 if summary["failed"] else 0
    finally:
        db.close()


def run_synchronously(coroutine):
    """Run this maintenance coroutine without an event loop.

    The current embedding implementation calls the synchronous Gemini SDK and
    has no suspension points. Avoiding ``asyncio.run`` also makes this script
    work in Windows shells where creating an asyncio self-pipe is blocked.
    Fail loudly if that implementation changes in the future.
    """
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    raise RuntimeError("Migration coroutine unexpectedly suspended; use an async runner.")


if __name__ == "__main__":
    raise SystemExit(run_synchronously(main()))
