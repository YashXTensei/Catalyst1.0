import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.decision import Decision
from app.models.repository import Repository
from app.services.memory_service import ProjectMemoryService
from app.utils.embeddings import EMBEDDING_DIMENSION, cosine_similarity, is_valid_embedding
from scripts import regenerate_legacy_embeddings as migration


def unit_vector(index: int):
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[index] = 1.0
    return vector


class EmbeddingMigrationTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.db = sessionmaker(bind=engine)()
        self.repo = Repository(
            owner="test",
            name="embeddings",
            full_name="test/embeddings",
            url="https://example.invalid/test/embeddings",
        )
        self.db.add(self.repo)
        self.db.commit()
        self.db.refresh(self.repo)

    def tearDown(self):
        self.db.close()

    def add_decision(self, title, embedding):
        decision = Decision(
            repo_id=self.repo.id,
            decision=title,
            context="Embedding migration test context",
            source_url="https://example.invalid/source",
            embedding=embedding,
        )
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)
        return decision

    def test_dimension_validation_and_cosine_for_current_model_vectors(self):
        query = unit_vector(0)
        self.assertTrue(is_valid_embedding(query))
        self.assertFalse(is_valid_embedding([0.1] * 768))
        self.assertAlmostEqual(cosine_similarity(query, unit_vector(0)), 1.0)
        self.assertAlmostEqual(cosine_similarity(query, unit_vector(1)), 0.0)

    def test_store_decision_persists_only_a_valid_current_dimension_embedding(self):
        data = {
            "decision": "New current-model decision",
            "context": "A new decision should have the configured dimension.",
            "source_url": "https://example.invalid/new",
        }
        with patch("app.services.memory_service.generate_embedding", return_value=unit_vector(3)):
            saved = migration.run_synchronously(ProjectMemoryService.store_decision(self.db, self.repo.id, data))
        self.db.expire_all()
        persisted = self.db.get(Decision, saved.id)
        self.assertTrue(is_valid_embedding(persisted.embedding))
        self.assertEqual(len(persisted.embedding), EMBEDDING_DIMENSION)

    def test_migration_preserves_legacy_on_failure_and_replaces_only_after_validation(self):
        legacy = self.add_decision("Legacy decision", [0.1] * 768)
        original = list(legacy.embedding)
        with patch("scripts.regenerate_legacy_embeddings.generate_embedding", return_value=None):
            failed = migration.run_synchronously(migration.migrate_embeddings(self.db, apply=True))
        self.db.refresh(legacy)
        self.assertEqual(failed["failed"], 1)
        self.assertEqual(legacy.embedding, original)

        with patch("scripts.regenerate_legacy_embeddings.generate_embedding", return_value=unit_vector(0)):
            completed = migration.run_synchronously(migration.migrate_embeddings(self.db, apply=True))
        self.db.expire_all()
        migrated = self.db.get(Decision, legacy.id)
        self.assertEqual(completed["migrated"], 1)
        self.assertTrue(is_valid_embedding(migrated.embedding))
        self.assertEqual(len(migrated.embedding), EMBEDDING_DIMENSION)

    def test_search_retrieves_new_and_migrated_decisions_with_current_dimension_query(self):
        migrated = self.add_decision("Migrated decision", [0.1] * 768)
        new = self.add_decision("New decision", unit_vector(1))
        with patch("scripts.regenerate_legacy_embeddings.generate_embedding", return_value=unit_vector(0)):
            migration.run_synchronously(migration.migrate_embeddings(self.db, apply=True))

        with patch("app.services.memory_service.generate_embedding", return_value=unit_vector(0)):
            results = migration.run_synchronously(
                ProjectMemoryService.search_decisions(self.db, self.repo.id, "migration decision", top_k=5)
            )
        result_ids = {decision.id for decision, _ in results}
        self.assertIn(migrated.id, result_ids)
        self.assertIn(new.id, result_ids)
        self.assertAlmostEqual(cosine_similarity(unit_vector(0), self.db.get(Decision, migrated.id).embedding), 1.0)


if __name__ == "__main__":
    unittest.main()
