
import unittest

from retrieval.evidence_validation import validate_answer_result


class AnswerQualityTests(unittest.TestCase):
    def setUp(self):
        self.evidence = [
            {
                "source_id": "REG-001",
                "title": "Registration Policy",
                "text": "Registration closes on the published deadline.",
            },
            {
                "source_id": "REG-002",
                "title": "Registration Notice",
                "text": "The earlier notice set the deadline at 15 January 2026.",
            },
        ]

    def answered(self, **overrides):
        result = {
            "status": "answered",
            "answer": "Registration closes on the published deadline.",
            "cited_source_ids": ["REG-001"],
            "message": None,
        }
        result.update(overrides)
        return result

    def test_supported_answer_with_valid_citation_passes(self):
        result = self.answered()
        self.assertEqual(
            validate_answer_result(result, self.evidence),
            result,
        )

    def test_answered_with_no_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(self.answered(), [])

    def test_unknown_citation_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(
                self.answered(cited_source_ids=["UNKNOWN-999"]),
                self.evidence,
            )

    def test_answered_without_citation_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(
                self.answered(cited_source_ids=[]),
                self.evidence,
            )

    def test_answered_with_blank_answer_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(
                self.answered(answer="   "),
                self.evidence,
            )

    def test_answered_with_fallback_message_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(
                self.answered(message="I could not verify this."),
                self.evidence,
            )

    def test_unsupported_result_never_carries_an_answer(self):
        result = {
            "status": "insufficient_evidence",
            "answer": None,
            "cited_source_ids": [],
            "message": "I could not verify this from the available documents.",
        }
        self.assertEqual(
            validate_answer_result(result, self.evidence),
            result,
        )

    def test_unsupported_result_with_answer_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(
                {
                    "status": "insufficient_evidence",
                    "answer": "The deadline is 15 January.",
                    "cited_source_ids": [],
                    "message": "I could not verify this.",
                },
                self.evidence,
            )

    def test_unsupported_result_without_message_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(
                {
                    "status": "insufficient_evidence",
                    "answer": None,
                    "cited_source_ids": [],
                    "message": None,
                },
                self.evidence,
            )

    def test_ambiguous_question_abstains_with_a_clarifying_message(self):
        result = {
            "status": "insufficient_evidence",
            "answer": None,
            "cited_source_ids": [],
            "message": "Which deadline do you mean — registration or fees?",
        }
        self.assertEqual(
            validate_answer_result(result, self.evidence),
            result,
        )

    def test_conflicting_result_requires_two_documents(self):
        result = {
            "status": "conflicting_sources",
            "answer": "The sources disagree about the deadline.",
            "cited_source_ids": ["REG-001", "REG-002"],
            "message": "These sources disagree.",
        }
        self.assertEqual(
            validate_answer_result(result, self.evidence),
            result,
        )

    def test_conflict_with_one_source_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(
                {
                    "status": "conflicting_sources",
                    "answer": "The sources disagree.",
                    "cited_source_ids": ["REG-001"],
                    "message": "These sources disagree.",
                },
                self.evidence,
            )

    def test_conflict_requires_two_retrieved_documents(self):
        single_evidence = [self.evidence[0]]
        with self.assertRaises(ValueError):
            validate_answer_result(
                {
                    "status": "conflicting_sources",
                    "answer": "The sources disagree.",
                    "cited_source_ids": ["REG-001"],
                    "message": "These sources disagree.",
                },
                single_evidence,
            )

    def test_duplicate_citations_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(
                self.answered(cited_source_ids=["REG-001", "REG-001"]),
                self.evidence,
            )

    def test_error_result_carries_only_a_message(self):
        result = {
            "status": "error",
            "answer": None,
            "cited_source_ids": [],
            "message": "Something went wrong. Please try again.",
        }
        self.assertEqual(
            validate_answer_result(result, self.evidence),
            result,
        )

    def test_error_result_with_answer_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(
                {
                    "status": "error",
                    "answer": "Registration closes in January.",
                    "cited_source_ids": [],
                    "message": "Something went wrong.",
                },
                self.evidence,
            )

    def test_unknown_status_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result(
                self.answered(status="supported"),
                self.evidence,
            )

    def test_malformed_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_answer_result("not a dict", self.evidence)
        with self.assertRaises(ValueError):
            validate_answer_result(self.answered(), "not a list")


if __name__ == "__main__":
    unittest.main()
