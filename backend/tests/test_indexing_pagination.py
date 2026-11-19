import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.repositories import run_background_indexing
from app.database import Base
from app.models.repository import Repository
from app.services.github_service import DiscussionPage, next_page_from_links


def run_immediately(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    raise RuntimeError("Test coroutine unexpectedly suspended")


def issue(source_id: str):
    return {
        "source_id": source_id,
        "number": 1,
        "title": f"Issue {source_id}",
        "body": "No extraction needed for pagination tests.",
        "url": f"https://example.invalid/issues/{source_id}",
        "author": "test",
        "state": "open",
        "discussion_type": "issue",
    }


class IndexingPaginationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        session = self.sessions()
        repo = Repository(
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            url="https://example.invalid/test-owner/test-repo",
            indexing_status="idle",
        )
        session.add(repo)
        session.commit()
        self.repo_id = repo.id
        session.close()

    def tearDown(self):
        self.engine.dispose()

    def run_index(self, pages, max_pages=10):
        with patch("app.api.repositories.SessionLocal", side_effect=self.sessions), patch(
            "app.api.repositories.github_service.fetch_issues_and_prs_page",
            new=AsyncMock(side_effect=pages),
        ) as fetch, patch(
            "app.api.repositories.github_service.fetch_comments", new=AsyncMock(return_value=[])
        ), patch(
            "app.api.repositories.github_service.fetch_pure_issues", new=AsyncMock(return_value=[])
        ), patch(
            "app.api.repositories.process_discussion_for_decisions", new=AsyncMock(return_value=0)
        ):
            run_immediately(run_background_indexing(self.repo_id, max_pages=max_pages))
        session = self.sessions()
        repo = session.get(Repository, self.repo_id)
        session.expunge(repo)
        session.close()
        return repo, fetch

    def test_indexes_more_than_two_linked_pages(self):
        repo, fetch = self.run_index(
            [
                DiscussionPage(discussions=[issue("1")], next_page=2),
                DiscussionPage(discussions=[issue("2")], next_page=3),
                DiscussionPage(discussions=[issue("3")], next_page=None),
            ]
        )

        self.assertEqual(fetch.await_count, 3)
        self.assertEqual(repo.indexing_status, "completed")
        self.assertEqual(repo.total_pages_fetched, 3)
        self.assertEqual(repo.total_records_fetched, 3)

    def test_reads_next_page_from_github_link_header(self):
        self.assertEqual(
            next_page_from_links({"next": {"url": "https://api.github.com/repos/a/b/issues?page=3&per_page=50"}}),
            3,
        )
        self.assertIsNone(next_page_from_links({}))

    def test_failure_after_progress_is_partial_not_completed(self):
        repo, _ = self.run_index(
            [
                DiscussionPage(discussions=[issue("1")], next_page=2),
                DiscussionPage(error="GitHub issues request failed (500)"),
            ]
        )

        self.assertEqual(repo.indexing_status, "partial")
        self.assertEqual(repo.total_pages_fetched, 1)
        self.assertEqual(repo.total_records_fetched, 1)
        self.assertIn("failed", repo.indexing_progress.lower())

    def test_rate_limit_before_first_page_is_failed_not_completed(self):
        repo, _ = self.run_index([DiscussionPage(error="GitHub rate limit reached", rate_limited=True)])

        self.assertEqual(repo.indexing_status, "failed")
        self.assertEqual(repo.total_pages_fetched, 0)
        self.assertEqual(repo.total_records_fetched, 0)
        self.assertIn("rate limit", repo.indexing_progress.lower())

    def test_empty_successful_page_completes(self):
        repo, fetch = self.run_index([DiscussionPage(discussions=[], next_page=None)])

        self.assertEqual(fetch.await_count, 1)
        self.assertEqual(repo.indexing_status, "completed")
        self.assertEqual(repo.total_pages_fetched, 1)
        self.assertEqual(repo.total_records_fetched, 0)

    def test_safe_page_limit_marks_run_partial(self):
        repo, fetch = self.run_index([DiscussionPage(discussions=[issue("1")], next_page=2)], max_pages=1)

        self.assertEqual(fetch.await_count, 1)
        self.assertEqual(repo.indexing_status, "partial")
        self.assertEqual(repo.total_pages_fetched, 1)
        self.assertEqual(repo.indexing_next_page, 2)

    def test_partial_run_resumes_from_persisted_next_page(self):
        self.run_index([DiscussionPage(discussions=[issue("1")], next_page=2)], max_pages=1)

        repo, fetch = self.run_index([DiscussionPage(discussions=[issue("2")], next_page=None)], max_pages=1)

        self.assertEqual(fetch.await_count, 1)
        self.assertEqual(fetch.await_args.kwargs["page"], 2)
        self.assertEqual(repo.indexing_status, "completed")
        self.assertEqual(repo.indexing_next_page, None)
        self.assertEqual(repo.total_pages_fetched, 2)
        self.assertEqual(repo.total_records_fetched, 2)


if __name__ == "__main__":
    unittest.main()
