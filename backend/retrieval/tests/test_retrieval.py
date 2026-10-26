
import unittest

from retrieval.search import (
    MIN_COVERAGE,
    MIN_SCORE,
    coverage,
    query_terms,
    retrieve,
    retrieve_with_status,
)


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
        results = retrieve(
            "When must students complete registration?",
            self.passages,
        )
        self.assertTrue(results)
        self.assertEqual(results[0]["source_id"], "HANDBOOK-001")

    def test_results_carry_a_score(self):
        results = retrieve(
            "When must students complete registration?",
            self.passages,
        )
        self.assertIn("score", results[0])
        self.assertGreaterEqual(results[0]["score"], MIN_SCORE)
        self.assertLessEqual(results[0]["score"], 1)

    def test_preserves_source_metadata(self):
        results = retrieve(
            "When must students complete registration?",
            self.passages,
        )
        self.assertEqual(results[0]["page"], 3)
        self.assertEqual(results[0]["section"], "Registration")

    def test_unrelated_question_returns_no_evidence(self):
        results = retrieve("xyzqv blorpt", self.passages)
        self.assertEqual(results, [])

    def test_nonpositive_top_k_returns_no_results(self):
        results = retrieve("registration", self.passages, top_k=0)
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
        results = retrieve(
            "When must students complete registration?",
            passages,
        )
        self.assertTrue(results)
        self.assertEqual(results[0]["source_id"], "REGISTRATION-001")

    def test_empty_question_returns_no_evidence(self):
        results = retrieve("   ", self.passages)
        self.assertEqual(results, [])

    def test_stopword_only_question_returns_no_evidence(self):
        results = retrieve("what is it that must be", self.passages)
        self.assertEqual(results, [])

    def test_stopwords_are_dropped_from_the_query(self):
        terms = query_terms("What is the registration deadline?")
        self.assertEqual(terms, {"registration", "deadline"})
        self.assertEqual(query_terms("the deadline"), {"deadline"})
        self.assertNotIn("the", terms)

    def test_temporal_registration_question_also_searches_for_deadline(self):
        self.assertEqual(
            query_terms("When is registration?"),
            {"registration", "deadline"},
        )
        self.assertEqual(
            query_terms("When do I register?"),
            {"register", "deadline"},
        )
        self.assertEqual(
            query_terms("registration fees"),
            {"registration", "fees"},
        )

    def test_empty_passage_list_returns_no_evidence(self):
        results = retrieve("When is registration?", [])
        self.assertEqual(results, [])

    def test_top_k_limits_result_count(self):
        results = retrieve(
            "students registration fees programme",
            self.passages,
            top_k=1,
        )
        self.assertLessEqual(len(results), 1)

    def test_missing_metadata_does_not_crash(self):
        passages = [
            {"text": "Students must complete registration."}
        ]

        results = retrieve(
            "When must students complete registration?",
            passages,
        )

        self.assertEqual(len(results), 1)
        self.assertIn("text", results[0])

    def test_top_k_never_exceeds_available_matches(self):
        passages = [
            {
                "source_id": "REG-001",
                "text": "Students must complete registration.",
            }
        ]

        results = retrieve(
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

        results = retrieve(
            "When must students complete registration?",
            [passage],
        )

        self.assertEqual(results[0]["source_id"], "REG-001")
        self.assertEqual(results[0]["title"], "Registration Guide")
        self.assertEqual(results[0]["page"], 4)
        self.assertNotIn("score", passage)

    def test_empty_passage_text_is_ignored(self):
        passages = [
            {"source_id": "EMPTY-001", "text": ""},
            {
                "source_id": "REG-001",
                "text": "Students must complete registration.",
            },
        ]

        results = retrieve(
            "When must students complete registration?",
            passages,
        )

        self.assertTrue(results)
        self.assertEqual(results[0]["source_id"], "REG-001")


class LayerOneFallbackTests(unittest.TestCase):
    def setUp(self):
        self.passages = [
            {
                "source_id": "REG-001",
                "text": "Students must complete registration before the deadline.",
            },
            {
                "source_id": "LIB-001",
                "text": "Students may borrow books from the library.",
            },
        ]

    def test_no_hits_abstains_without_a_model_call(self):
        status, results = retrieve_with_status("xyzqv blorpt", self.passages)
        self.assertEqual(status, "insufficient_evidence")
        self.assertEqual(results, [])

    def test_hits_return_retrieved_status_with_scored_passages(self):
        status, results = retrieve_with_status(
            "When must students complete registration?",
            self.passages,
        )
        self.assertEqual(status, "retrieved")
        self.assertEqual(results[0]["source_id"], "REG-001")

    def test_low_query_coverage_triggers_insufficient_evidence(self):
        question = "students complete registration deadline fees"

        status, _ = retrieve_with_status(question, self.passages)
        self.assertEqual(status, "retrieved")

        status, results = retrieve_with_status(
            question,
            self.passages,
            min_coverage=0.99,
        )
        self.assertEqual(status, "insufficient_evidence")
        self.assertEqual(results, [])

    def test_below_min_score_triggers_insufficient_evidence(self):
        status, results = retrieve_with_status(
            "registration deadline fees",
            self.passages,
            min_score=0.99,
        )
        self.assertEqual(status, "insufficient_evidence")
        self.assertEqual(results, [])

    def test_coverage_is_the_share_of_query_terms_covered(self):
        question = "registration deadline"
        results = retrieve(question, self.passages)
        self.assertEqual(coverage(question, results), 1.0)
        self.assertEqual(coverage(question, []), 0.0)

    def test_calibrated_constants_are_exported(self):
        self.assertGreater(MIN_COVERAGE, MIN_SCORE)
        self.assertGreater(MIN_SCORE, 0)
        self.assertLessEqual(MIN_COVERAGE, 1)


if __name__ == "__main__":
    unittest.main()
