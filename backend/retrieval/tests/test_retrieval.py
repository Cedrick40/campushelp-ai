
import unittest

from retrieval.retrieval import retrieve_evidence


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.passages = [
            {
                "source_id": "HANDBOOK-001",
                "title": "Student Handbook",
                "page": 3,
                "section": "Registration",
                "text": (
                    "Students must complete registration "
                    "before the published deadline."
                ),
            },
            {
                "source_id": "FEES-001",
                "title": "Fees Guide",
                "page": 2,
                "section": "Tuition",
                "text": (
                    "Students should consult the approved "
                    "fees schedule for their programme."
                ),
            },
        ]

    def test_retrieves_relevant_passage(self):
        results = retrieve_evidence(
            "When must students complete registration?",
            self.passages,
        )
        self.assertTrue(results)
        self.assertEqual(results[0]["source_id"], "HANDBOOK-001")

    def test_preserves_source_metadata(self):
        results = retrieve_evidence(
            "When must students complete registration?",
            self.passages,
        )
        self.assertEqual(results[0]["page"], 3)
        self.assertEqual(results[0]["section"], "Registration")

    def test_unrelated_question_returns_no_evidence(self):
        results = retrieve_evidence("xyzqv blorpt", self.passages)
        self.assertEqual(results, [])

    def test_nonpositive_top_k_returns_no_results(self):
        results = retrieve_evidence(
            "registration",
            self.passages,
            top_k=0,
        )
        self.assertEqual(results, [])

    def test_best_matching_passage_ranks_first(self):
        passages = [
            {
                "source_id": "UNRELATED-001",
                "text": "The library provides books and computers.",
            },
            {
                "source_id": "REGISTRATION-001",
                "text": (
                    "Students must complete registration "
                    "before the deadline."
                ),
            },
        ]
        results = retrieve_evidence(
            "When must students complete registration?",
            passages,
        )
        self.assertTrue(results)
        self.assertEqual(
            results[0]["source_id"],
            "REGISTRATION-001",
        )

    def test_empty_question_returns_no_evidence(self):
        results = retrieve_evidence("   ", self.passages)
        self.assertEqual(results, [])

    def test_empty_passage_list_returns_no_evidence(self):
        results = retrieve_evidence("When is registration?", [])
        self.assertEqual(results, [])

    def test_top_k_limits_result_count(self):
        results = retrieve_evidence(
            "students registration fees programme",
            self.passages,
            top_k=1,
        )
        self.assertLessEqual(len(results), 1)

    
    def test_missing_metadata_does_not_crash(self):
        passages = [
            {"text": "Students must complete registration."}
        ]

        results = retrieve_evidence(
            "When must students complete registration?",
            passages,
        )

        self.assertEqual(len(results), 1)
        self.assertIn("text", results[0])

    def test_top_k_never_exceeds_available_matches(self):
        passages = [
            {
                "source_id": "REG-001",
                "text": "Students must complete registration."
            }
        ]

        results = retrieve_evidence(
            "When must students complete registration?",
            passages,
            top_k=5,
        )

        self.assertLessEqual(len(results), 5)
        self.assertEqual(len(results), 1)

    def test_original_passage_metadata_is_preserved(self):
        passage = {
            "source_id": "REG-001",
            "title": "Registration Guide",
            "page": 4,
            "section": "Deadlines",
            "text": "Students must complete registration.",
        }

        results = retrieve_evidence(
            "When must students complete registration?",
            [passage],
        )

        self.assertEqual(results[0]["source_id"], "REG-001")
        self.assertEqual(results[0]["title"], "Registration Guide")
        self.assertEqual(results[0]["page"], 4)

    def test_empty_passage_text_is_ignored(self):
        passages = [
            {"source_id": "EMPTY-001", "text": ""},
            {
                "source_id": "REG-001",
                "text": "Students must complete registration."
            },
        ]

        results = retrieve_evidence(
            "When must students complete registration?",
            passages,
        )

        self.assertTrue(results)
        self.assertEqual(results[0]["source_id"], "REG-001")
    


if __name__ == "__main__":
    unittest.main()
