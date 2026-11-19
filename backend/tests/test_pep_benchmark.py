import unittest
from app.services.pep_dataset_service import pep_dataset_service
from app.integrations.discourse_connector import clean_html, discourse_connector
from app.services.pep_benchmark_service import pep_benchmark_service


class TestPEPBenchmark(unittest.IsolatedAsyncioTestCase):
    def test_clean_html(self):
        raw = "<p>Hello <b>World</b>!<br>This is a <i>test</i>.</p>"
        cleaned = clean_html(raw)
        self.assertIn("Hello World!", cleaned)
        self.assertNotIn("<p>", cleaned)
        self.assertNotIn("<br>", cleaned)

    def test_candidate_list(self):
        candidates = pep_dataset_service.list_candidate_peps()
        self.assertTrue(len(candidates) >= 4)
        self.assertIn(695, candidates)
        self.assertIn(654, candidates)

    async def test_pep_metadata_parsing(self):
        content, ext = await pep_dataset_service.fetch_pep_raw(695)
        self.assertIsNotNone(content)
        meta = pep_dataset_service.parse_pep_metadata(content, 695)
        self.assertEqual(meta["pep_number"], 695)
        self.assertIn("Type Parameter Syntax", meta["title"])
        self.assertTrue(len(meta["discuss_urls"]) > 0)
        self.assertIn("discuss.python.org", meta["primary_discussion_url"])

    async def test_pep_rejected_ideas_parsing(self):
        content, _ = await pep_dataset_service.fetch_pep_raw(695)
        rejected = pep_dataset_service.parse_rejected_ideas(content)
        self.assertTrue(len(rejected) >= 3)
        ideas_titles = [r["idea"] for r in rejected]
        self.assertTrue(any("Prefix" in t or "Angle" in t for t in ideas_titles))

    async def test_explainable_comparison(self):
        ground_truth = [
            {"idea": "Angle Brackets", "reason": "Angle brackets <> create lexical scanning ambiguity in Python grammar."}
        ]
        recovered = [
            {
                "decision": "Use square brackets for generics",
                "status": "accepted",
                "rejected_alternatives": ["Angle brackets syntax <T>"],
                "reasoning": ["Avoids scanner grammar ambiguity with comparisons"],
                "evidence": ["'Angle brackets cause ambiguity'"],
            }
        ]
        comparisons, tp, fp, fn = await pep_benchmark_service.compare_ideas(
            ground_truth, recovered, "https://discuss.python.org/t/test/123"
        )
        self.assertEqual(len(comparisons), 1)
        self.assertIn(comparisons[0]["status"], ["matched", "partial"])
        self.assertGreater(comparisons[0]["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
