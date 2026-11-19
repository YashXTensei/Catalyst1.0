import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.repositories import process_discussion_for_decisions
from app.database import Base
from app.models.discussion import Discussion
from app.models.repository import Repository


def run_immediately(coroutine):
    """Run indexing coroutines whose mocked dependencies do not suspend."""
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    raise RuntimeError("Test coroutine unexpectedly suspended")


class IncrementalIndexingTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.db = sessionmaker(bind=engine)()
        self.repo = Repository(
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            url="https://example.invalid/test-owner/test-repo",
        )
        self.db.add(self.repo)
        self.db.commit()
        self.db.refresh(self.repo)

    def tearDown(self):
        self.db.close()

    @staticmethod
    def discussion(body="Choose SQLite for local storage"):
        return {
            "source_id": "source-1",
            "discussion_type": "issue",
            "number": 1,
            "title": "Storage decision",
            "body": body,
            "author": "architect",
            "url": "https://example.invalid/issues/1",
            "state": "closed",
        }

    def get_discussion(self):
        return self.db.query(Discussion).filter(Discussion.repo_id == self.repo.id).one()

    def test_already_processed_unchanged_discussion_skips_extraction(self):
        with patch(
            "app.api.repositories.decision_extractor.extract_from_discussion",
            new=AsyncMock(return_value=[]),
        ) as extract:
            run_immediately(process_discussion_for_decisions(self.db, self.repo, self.discussion()))
            run_immediately(process_discussion_for_decisions(self.db, self.repo, self.discussion()))

        self.assertEqual(extract.await_count, 1)
        self.assertTrue(self.get_discussion().indexed_for_decisions)

    def test_new_discussion_is_extracted_and_marked_processed_after_persistence(self):
        extracted = [{"decision": "Use SQLite", "context": "Embedded deployment", "source_url": "https://example.invalid/issues/1"}]
        with patch(
            "app.api.repositories.decision_extractor.extract_from_discussion",
            new=AsyncMock(return_value=extracted),
        ) as extract, patch(
            "app.api.repositories.memory_service.store_decision",
            new=AsyncMock(return_value=MagicMock()),
        ) as store:
            saved = run_immediately(process_discussion_for_decisions(self.db, self.repo, self.discussion()))

        self.assertEqual(saved, 1)
        self.assertEqual(extract.await_count, 1)
        self.assertEqual(store.await_count, 1)
        self.assertTrue(self.get_discussion().indexed_for_decisions)
        self.assertIsNotNone(self.get_discussion().decision_content_hash)

    def test_failed_extraction_remains_retryable(self):
        with patch(
            "app.api.repositories.decision_extractor.extract_from_discussion",
            new=AsyncMock(side_effect=RuntimeError("Gemini unavailable")),
        ):
            saved = run_immediately(process_discussion_for_decisions(self.db, self.repo, self.discussion()))

        self.assertEqual(saved, 0)
        self.assertFalse(self.get_discussion().indexed_for_decisions)

        with patch(
            "app.api.repositories.decision_extractor.extract_from_discussion",
            new=AsyncMock(return_value=[]),
        ) as retry:
            run_immediately(process_discussion_for_decisions(self.db, self.repo, self.discussion()))

        self.assertEqual(retry.await_count, 1)
        self.assertTrue(self.get_discussion().indexed_for_decisions)

    def test_failed_decision_persistence_does_not_mark_discussion_processed(self):
        extracted = [{"decision": "Use SQLite", "context": "Embedded deployment", "source_url": "https://example.invalid/issues/1"}]
        with patch(
            "app.api.repositories.decision_extractor.extract_from_discussion",
            new=AsyncMock(return_value=extracted),
        ), patch(
            "app.api.repositories.memory_service.store_decision",
            new=AsyncMock(return_value=None),
        ):
            run_immediately(process_discussion_for_decisions(self.db, self.repo, self.discussion()))

        self.assertFalse(self.get_discussion().indexed_for_decisions)

    def test_updated_discussion_is_reprocessed_and_can_store_new_information(self):
        initial = self.discussion()
        updated = self.discussion("Choose SQLite for local storage; reject PostgreSQL for this deployment.")
        first_result = []
        updated_result = [{"decision": "Reject PostgreSQL", "context": "Operational overhead", "source_url": updated["url"]}]

        with patch(
            "app.api.repositories.decision_extractor.extract_from_discussion",
            new=AsyncMock(side_effect=[first_result, updated_result]),
        ) as extract, patch(
            "app.api.repositories.memory_service.store_decision",
            new=AsyncMock(return_value=MagicMock()),
        ) as store:
            run_immediately(process_discussion_for_decisions(self.db, self.repo, initial))
            saved = run_immediately(process_discussion_for_decisions(self.db, self.repo, updated))

        self.assertEqual(extract.await_count, 2)
        self.assertEqual(store.await_count, 1)
        self.assertEqual(saved, 1)
        self.assertTrue(self.get_discussion().indexed_for_decisions)


if __name__ == "__main__":
    unittest.main()
