
import unittest

from retrieval.evidence_validation import validate_answer_result


class AnswerQualityTests(unittest.TestCase):
    def setUp(self):
        self.evidence = [
            {
                "source_id": "REG-001",
                "text": "Registration closes on the published deadline.",
            },
            {
                "source_id": "REG-002",
                "text": "The registration schedule lists the relevant dates.",
            },
        ]

    def test_supported_answer_requires_valid_citation(self):
        result = {
            "answer": "Registration closes on the published deadline.",
            "status": "supported",
            "citations": ["REG-001"],
        }

        self.assertEqual(
            validate_answer_result(result, self.evidence),
            result,
        )

    def test_unsupported_result_must_not_invent_answer(self):
        result = {
            "answer": "",
            "status": "unsupported",
            "citations": [],
        }

        self.assertEqual(
            validate_answer_result(result, self.evidence),
            result,
        )

    def test_unknown_citation_is_rejected(self):
        result = {
            "answer": "Registration closes on the deadline.",
            "status": "supported",
            "citations": ["UNKNOWN-999"],
        }

        with self.assertRaises(ValueError):
            validate_answer_result(result, self.evidence)

    def test_supported_answer_requires_citation(self):
        result = {
            "answer": "Registration closes on the deadline.",
            "status": "supported",
            "citations": [],
        }

        with self.assertRaises(ValueError):
            validate_answer_result(result, self.evidence)

    def test_ambiguous_result_explains_clarification_needed(self):
        result = {
            "answer": "Do you mean registration or fee payment?",
            "status": "ambiguous",
            "citations": [],
        }

        self.assertEqual(
            validate_answer_result(result, self.evidence),
            result,
        )

    def test_conflicting_result_requires_two_sources(self):
        result = {
            "answer": "The supplied sources disagree about the deadline.",
            "status": "conflicting",
            "citations": ["REG-001", "REG-002"],
        }

        self.assertEqual(
            validate_answer_result(result, self.evidence),
            result,
        )

    def test_conflict_with_one_source_is_rejected(self):
        result = {
            "answer": "The sources disagree.",
            "status": "conflicting",
            "citations": ["REG-001"],
        }

        with self.assertRaises(ValueError):
            validate_answer_result(result, self.evidence)

    def test_duplicate_citations_are_rejected(self):
        result = {
            "answer": "Registration closes on the deadline.",
            "status": "supported",
            "citations": ["REG-001", "REG-001"],
        }

        with self.assertRaises(ValueError):
            validate_answer_result(result, self.evidence)


if __name__ == "__main__":
    unittest.main()
