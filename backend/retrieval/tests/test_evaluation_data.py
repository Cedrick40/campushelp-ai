
import json
import unittest
from pathlib import Path

from retrieval.evidence_validation import ALLOWED_STATUSES
from retrieval.search import MIN_COVERAGE, MIN_SCORE


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
QUESTIONS_FILE = DATA_DIR / "retrieval_eval.json"
PASSAGES_FILE = DATA_DIR / "sample_passages.json"
TYPED_QUESTIONS_FILE = DATA_DIR.parent / "test_questions.json"


def load(path: Path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


class EvaluationDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.passages = load(PASSAGES_FILE)
        cls.eval_questions = load(QUESTIONS_FILE)
        cls.typed_questions = load(TYPED_QUESTIONS_FILE)
        cls.source_ids = {p["source_id"] for p in cls.passages}

    def test_sample_passages_carry_source_ids_and_text(self):
        self.assertTrue(self.passages)
        for passage in self.passages:
            self.assertIn("source_id", passage)
            self.assertTrue(passage["text"].strip())

    def test_evaluation_set_meets_the_minimum_size(self):
        self.assertGreaterEqual(len(self.eval_questions), 15)
        self.assertLessEqual(len(self.eval_questions), 30)

    def test_evaluation_set_covers_the_required_categories(self):
        types = {q["type"] for q in self.eval_questions}
        self.assertTrue(
            {
                "answerable",
                "unsupported",
                "reworded",
                "ambiguous",
                "conflicting",
            } <= types,
            f"missing categories: {types}",
        )

    def test_evaluation_statuses_are_contract_statuses(self):
        for item in self.eval_questions:
            self.assertIn(item["expected_status"], ALLOWED_STATUSES, item["id"])

    def test_evaluation_source_ids_exist_in_the_corpus(self):
        for item in self.eval_questions:
            for source_id in item["expected_source_ids"]:
                self.assertIn(source_id, self.source_ids, item["id"])

    def test_typed_questions_cover_the_four_answer_outcomes(self):
        types = {q["type"] for q in self.typed_questions}
        self.assertEqual(
            types, {"supported", "unsupported", "ambiguous", "conflicting"}
        )

    def test_typed_questions_use_the_contract_status(self):
        for item in self.typed_questions:
            self.assertIn(item["expected_status"], ALLOWED_STATUSES, item["id"])
            self.assertTrue(item["expected_behavior"].strip())
            for source_id in item["expected_source_ids"]:
                self.assertIn(source_id, self.source_ids, item["id"])

    def test_conflicting_question_expects_two_documents(self):
        conflict = [
            q
            for q in self.typed_questions
            if q["type"] == "conflicting"
        ][0]
        self.assertGreaterEqual(len(conflict["expected_source_ids"]), 2)

    def test_calibrated_constants_are_recorded(self):
        self.assertEqual(MIN_SCORE, 0.3)
        self.assertEqual(MIN_COVERAGE, 0.33)


if __name__ == "__main__":
    unittest.main()
