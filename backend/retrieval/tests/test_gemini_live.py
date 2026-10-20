
"""
Live check against the Gemini API. Skipped unless a real AI_API_KEY is set.

    AI_API_KEY=... python -m unittest retrieval.tests.test_gemini_live

Runs the four typed questions in `test_questions.json` end to end:
retrieve → generate → validate, asserting each one's expected status and
that citations stay inside the retrieved evidence.
"""

import json
import os
import time
import unittest
from pathlib import Path

from retrieval.evidence_validation import ALLOWED_STATUSES
from retrieval.gemini_provider import configured_api_key
from retrieval.generation import clear_provider, generate_answer
from retrieval.search import retrieve_with_status


BASE_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = BASE_DIR / "test_questions.json"
PASSAGES_FILE = BASE_DIR / "data" / "sample_passages.json"

# Space calls out so the free tier's per-minute limit isn't self-inflicted.
LIVE_DELAY_S = float(os.environ.get("AI_LIVE_DELAY_S") or 12)


def load(path: Path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


@unittest.skipUnless(
    configured_api_key(),
    "AI_API_KEY not set — live Gemini check skipped",
)
class LiveGeminiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.passages = load(PASSAGES_FILE)
        cls.questions = load(QUESTIONS_FILE)

    def setUp(self):
        clear_provider()

    def run_pipeline(self, question):
        status, evidence = retrieve_with_status(question, self.passages)

        if status == "insufficient_evidence":
            return evidence, {
                "status": "insufficient_evidence",
                "answer": None,
                "cited_source_ids": [],
                "message": "layer 1 abstain",
                "_layer": 1,
            }

        time.sleep(LIVE_DELAY_S)
        result = generate_answer(evidence, question)
        result["_layer"] = 2
        return evidence, result

    def test_every_typed_question_matches_its_expected_status(self):
        failures = []

        for item in self.questions:
            evidence, result = self.run_pipeline(item["question"])
            retrieved_ids = {p["source_id"] for p in evidence}

            ok = (
                result["status"] in ALLOWED_STATUSES
                and result["status"] == item["expected_status"]
                and set(result["cited_source_ids"]) <= retrieved_ids
            )

            status = "PASS" if ok else "FAIL"
            print(
                f"\n[{status}] {item['id']} ({item['type']}) "
                f"expected={item['expected_status']} "
                f"got={result['status']} layer={result['_layer']}"
            )
            print(f"    answer: {result['answer']}")
            print(f"    citations: {result['cited_source_ids']}")
            print(f"    message: {result['message']}")

            if not ok:
                failures.append(
                    f"{item['id']}: expected {item['expected_status']}, "
                    f"got {result['status']}"
                )

        self.assertEqual(failures, [], "\n".join(failures))

    def test_conflicting_pair_is_flagged_not_resolved_silently(self):
        item = [q for q in self.questions if q["type"] == "conflicting"][0]
        _, result = self.run_pipeline(item["question"])

        self.assertEqual(result["status"], "conflicting_sources")
        self.assertGreaterEqual(len(set(result["cited_source_ids"])), 2)

    def test_no_response_contains_the_api_key(self):
        key = os.environ["AI_API_KEY"]
        _, result = self.run_pipeline("When must students complete registration?")

        self.assertNotIn(key, json.dumps(result))


if __name__ == "__main__":
    unittest.main()
