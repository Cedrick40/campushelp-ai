
import os
import unittest
from unittest.mock import patch

from retrieval.generation import (
    NOT_CONFIGURED_MESSAGE,
    clear_provider,
    generate_answer,
    set_provider,
)


def answered_provider(question, evidence):
    return {
        "status": "answered",
        "answer": "Students must complete registration before the deadline.",
        "cited_source_ids": ["REG-001"],
        "message": None,
    }


class GenerationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.evidence = [
            {
                "source_id": "REG-001",
                "title": "Registration Policy",
                "text": "Students must complete registration before the deadline.",
            },
            {
                "source_id": "REG-002",
                "title": "Registration Notice",
                "text": "The earlier notice set the deadline at 15 January 2026.",
            },
        ]
        clear_provider()

    def tearDown(self):
        clear_provider()

    @patch.dict(os.environ, {"AI_API_KEY": ""})
    def test_without_a_provider_returns_a_friendly_error(self):
        result = generate_answer(self.evidence, "When is registration?")
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["answer"])
        self.assertEqual(result["cited_source_ids"], [])
        self.assertEqual(result["message"], NOT_CONFIGURED_MESSAGE)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_provider_key_returns_a_friendly_error(self):
        result = generate_answer(
            self.evidence, "When is registration?", provider=answered_provider
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], NOT_CONFIGURED_MESSAGE)

    @patch.dict(os.environ, {"AI_API_KEY": "test-key"})
    def test_provider_result_passes_the_contract(self):
        result = generate_answer(
            self.evidence,
            "When must students complete registration?",
            provider=answered_provider,
        )
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["cited_source_ids"], ["REG-001"])
        self.assertIsNone(result["message"])

    @patch.dict(os.environ, {"AI_API_KEY": "test-key"})
    def test_answered_result_uses_the_complete_cited_paragraph(self):
        def paraphrasing_provider(question, evidence):
            return {
                "status": "answered",
                "answer": "Students must complete registration.",
                "cited_source_ids": ["REG-001"],
                "message": None,
            }

        result = generate_answer(
            self.evidence,
            "When must students complete registration?",
            provider=paraphrasing_provider,
        )
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["answer"], self.evidence[0]["text"])

    @patch.dict(os.environ, {"AI_API_KEY": "test-key"})
    def test_citation_outside_the_evidence_is_dropped_and_abstained(self):
        def hallucinating_provider(question, evidence):
            return {
                "status": "answered",
                "answer": "Registration closes in January.",
                "cited_source_ids": ["MADE-UP-001"],
                "message": None,
            }

        result = generate_answer(
            self.evidence, "When is registration?", provider=hallucinating_provider
        )
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["cited_source_ids"], [])
        self.assertIsNone(result["answer"])
        self.assertTrue(result["message"])

    @patch.dict(os.environ, {"AI_API_KEY": "test-key"})
    def test_conflict_needs_two_distinct_documents(self):
        def one_document_provider(question, evidence):
            return {
                "status": "conflicting_sources",
                "answer": "The sources disagree.",
                "cited_source_ids": ["REG-001"],
                "message": "These sources disagree.",
            }

        result = generate_answer(
            self.evidence,
            "What is the registration deadline?",
            provider=one_document_provider,
        )
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["cited_source_ids"], [])

    @patch.dict(os.environ, {"AI_API_KEY": "test-key"})
    def test_valid_conflict_is_returned(self):
        def conflict_provider(question, evidence):
            return {
                "status": "conflicting_sources",
                "answer": "The two registration documents give different dates.",
                "cited_source_ids": ["REG-001", "REG-002"],
                "message": None,
            }

        result = generate_answer(
            self.evidence,
            "What is the registration deadline?",
            provider=conflict_provider,
        )
        self.assertEqual(result["status"], "conflicting_sources")
        self.assertEqual(result["cited_source_ids"], ["REG-001", "REG-002"])
        self.assertTrue(result["message"])

    @patch.dict(os.environ, {"AI_API_KEY": "test-key"})
    def test_conflict_matches_citations_to_document_ids(self):
        evidence = [
            {**self.evidence[0], "document_id": "DOC-1"},
            {**self.evidence[1], "document_id": "DOC-2"},
        ]

        def conflict_provider(question, evidence):
            return {
                "status": "conflicting_sources",
                "answer": "The two registration documents give different dates.",
                "cited_source_ids": ["REG-001", "REG-002"],
                "message": None,
            }

        result = generate_answer(
            evidence,
            "What is the registration deadline?",
            provider=conflict_provider,
        )
        self.assertEqual(result["status"], "conflicting_sources")
        self.assertEqual(result["cited_source_ids"], ["REG-001", "REG-002"])

    @patch.dict(os.environ, {"AI_API_KEY": "test-key"})
    def test_general_rule_wins_over_a_subgroup_rule(self):
        evidence = [
            {
                "source_id": "REG-ALL",
                "document_id": "DOC-ALL",
                "text": (
                    "The registration deadline ends after the fourth week. "
                    "This is the requirement for all students, new and continuing."
                ),
            },
            {
                "source_id": "REG-SUPP",
                "document_id": "DOC-SUPP",
                "text": (
                    "Registration shall be done two weeks before commencement "
                    "for applicants on the supplementary list."
                ),
            },
        ]

        def conflict_provider(question, evidence):
            return {
                "status": "conflicting_sources",
                "answer": "The sources give different registration dates.",
                "cited_source_ids": ["REG-ALL", "REG-SUPP"],
                "message": None,
            }

        result = generate_answer(
            evidence,
            "When is registration?",
            provider=conflict_provider,
        )
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["answer"], evidence[0]["text"])
        self.assertEqual(result["cited_source_ids"], ["REG-ALL"])
        self.assertIsNone(result["message"])

    @patch.dict(os.environ, {"AI_API_KEY": "test-key"})
    def test_provider_failure_never_leaks_details(self):
        def broken_provider(question, evidence):
            raise RuntimeError("AI_API_KEY=sk-secret https://provider.internal")

        result = generate_answer(
            self.evidence, "When is registration?", provider=broken_provider
        )
        self.assertEqual(result["status"], "error")
        self.assertNotIn("secret", result["message"].lower())
        self.assertNotIn("traceback", result["message"].lower())
        self.assertNotIn("AI_API_KEY", result["message"])

    @patch.dict(os.environ, {"AI_API_KEY": "test-key"})
    def test_malformed_provider_output_is_an_error(self):
        result = generate_answer(
            self.evidence,
            "When is registration?",
            provider=lambda question, evidence: "not a dict",
        )
        self.assertEqual(result["status"], "error")

    @patch.dict(os.environ, {"AI_API_KEY": "test-key"})
    def test_registered_provider_is_used_by_default(self):
        set_provider(answered_provider)
        result = generate_answer(
            self.evidence, "When must students complete registration?"
        )
        self.assertEqual(result["status"], "answered")


if __name__ == "__main__":
    unittest.main()
