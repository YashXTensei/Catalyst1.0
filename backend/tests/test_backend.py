import os
import sys
import unittest

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.services.github_service import GitHubService
from app.services.code_mapping import CodeMappingService
from app.utils.embeddings import get_fallback_embedding, cosine_similarity
from app.database import Base, engine, SessionLocal
from app.models.repository import Repository
from app.models.decision import Decision
from app.services.memory_service import ProjectMemoryService


class DecisionTrailBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("database", data)
        self.assertEqual(data["database"]["status"], "connected")

    def test_02_parse_repo_urls(self):
        cases = [
            ("https://github.com/fastapi/fastapi", ("fastapi", "fastapi")),
            ("https://github.com/facebook/react/", ("facebook", "react")),
            ("http://github.com/torvalds/linux.git", ("torvalds", "linux")),
            ("pallets/flask", ("pallets", "flask")),
        ]
        for url, expected in cases:
            owner, repo = GitHubService.parse_repo_url(url)
            self.assertEqual((owner, repo), expected)

    def test_03_code_mapping_extraction(self):
        text = "We should update database.py and src/models/user.ts to migrate from PostgreSQL to SQLite."
        extracted = CodeMappingService.extract_file_references(text)
        self.assertIn("database.py", extracted)
        self.assertIn("src/models/user.ts", extracted)

    def test_04_code_mapping_pr_overlap(self):
        decision_refs = ["database.py", "config.py"]
        pr_files = ["backend/database.py", "frontend/src/App.jsx"]
        matched = CodeMappingService.map_decision_to_pr_files(decision_refs, pr_files)
        self.assertEqual(matched, ["backend/database.py"])

    def test_05_embeddings_and_cosine_similarity(self):
        vec1 = get_fallback_embedding("PostgreSQL database migration")
        vec2 = get_fallback_embedding("PostgreSQL database setup")
        vec3 = get_fallback_embedding("Frontend CSS styling components")

        sim_1_2 = cosine_similarity(vec1, vec2)
        sim_1_3 = cosine_similarity(vec1, vec3)

        self.assertGreater(sim_1_2, sim_1_3)
        self.assertEqual(len(vec1), 768)

    def test_06_store_and_search_decision(self):
        import asyncio

        # Create test repository
        repo = self.db.query(Repository).filter(Repository.full_name == "test-owner/test-repo").first()
        if not repo:
            repo = Repository(
                owner="test-owner",
                name="test-repo",
                full_name="test-owner/test-repo",
                url="https://github.com/test-owner/test-repo",
                description="Test repository for decisions",
                indexing_status="completed",
                total_discussions=1,
                total_decisions=1
            )
            self.db.add(repo)
            self.db.commit()
            self.db.refresh(repo)

        decision_data = {
            "decision": "Retain SQLite over PostgreSQL",
            "status": "accepted",
            "context": "Discussion regarding embedded vs client-server DB",
            "rejected_alternatives": ["PostgreSQL", "MySQL"],
            "reasoning": ["Zero deployment complexity", "Low memory footprint"],
            "affected_components": ["Database", "Storage"],
            "code_references": ["database.py"],
            "evidence": ["Benchmark tests showed SQLite fulfills all query performance targets."],
            "source_url": "https://github.com/test-owner/test-repo/issues/42",
            "source_type": "github",
        }

        async def run_store():
            return await ProjectMemoryService.store_decision(
                db=self.db,
                repo_id=repo.id,
                decision_data=decision_data,
                source_id="test_issue_42"
            )

        saved = asyncio.run(run_store())
        self.assertIsNotNone(saved)
        self.assertEqual(saved.decision, "Retain SQLite over PostgreSQL")

        # Test search
        async def run_search():
            return await ProjectMemoryService.search_decisions(
                db=self.db,
                repo_id=repo.id,
                query="Why was PostgreSQL rejected?",
                top_k=3
            )

        results = asyncio.run(run_search())
        self.assertTrue(len(results) > 0)
        top_decision, score = results[0]
        self.assertEqual(top_decision.decision, "Retain SQLite over PostgreSQL")
        self.assertIn("PostgreSQL", top_decision.rejected_alternatives)

    def test_07_api_get_decisions(self):
        repo = self.db.query(Repository).filter(Repository.full_name == "test-owner/test-repo").first()
        self.assertIsNotNone(repo)

        response = self.client.get(f"/api/repositories/{repo.id}/decisions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("decisions", data)
        self.assertGreaterEqual(data["total"], 1)

    def test_08_api_status(self):
        repo = self.db.query(Repository).filter(Repository.full_name == "test-owner/test-repo").first()
        response = self.client.get(f"/api/repositories/{repo.id}/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["repo_id"], repo.id)
        self.assertEqual(data["full_name"], "test-owner/test-repo")

    def test_09_api_ask_project_memory(self):
        repo = self.db.query(Repository).filter(Repository.full_name == "test-owner/test-repo").first()
        response = self.client.post(
            f"/api/repositories/{repo.id}/ask",
            json={"question": "Why did we choose SQLite instead of PostgreSQL?"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("answer", data)
        self.assertTrue(data["evidence_found"])
        self.assertGreaterEqual(len(data["citations"]), 1)
        self.assertIn("SQLite", data["answer"])


if __name__ == "__main__":
    unittest.main()
