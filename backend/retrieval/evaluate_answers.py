
"""
Pipeline evaluation for the typed questions (spec §Evaluation).

Retrieval → generation → validation, per question, with pass/fail printed.
Skipped with a clear message when no provider key is configured, because
the generation half cannot run offline (FR-04: retrieval stays testable
without it — use `evaluate_retrieval` for that).

    python -m retrieval.evaluate_answers
"""

import json
from pathlib import Path

from retrieval.evidence_validation import ALLOWED_STATUSES, NOT_VERIFIED_MESSAGE
from retrieval.gemini_provider import configured_api_key, model_name
from retrieval.generation import generate_answer
from retrieval.search import retrieve_with_status


BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_FILE = BASE_DIR / "test_questions.json"
PASSAGES_FILE = BASE_DIR / "data" / "sample_passages.json"


def main():
    if not configured_api_key():
        print(
            "No AI_API_KEY configured in backend/.env — skipping the "
            "generation half of the pipeline.\n"
            "Retrieval-only evaluation: python -m retrieval.evaluate_retrieval"
        )
        return

    with PASSAGES_FILE.open(encoding="utf-8") as file:
        passages = json.load(file)

    with QUESTIONS_FILE.open(encoding="utf-8") as file:
        questions = json.load(file)

    print(f"Provider: gemini | model: {model_name()}\n")

    passed = 0
    failures = []

    for item in questions:
        status, evidence = retrieve_with_status(item["question"], passages)

        if status == "insufficient_evidence":
            result = {
                "status": "insufficient_evidence",
                "answer": None,
                "cited_source_ids": [],
                "message": NOT_VERIFIED_MESSAGE,
            }
            note = "layer 1: no model call"
        else:
            result = generate_answer(evidence, item["question"])
            note = ""

        retrieved_ids = [p["source_id"] for p in evidence]
        citations = result["cited_source_ids"]
        valid_status = result["status"] in ALLOWED_STATUSES
        status_match = result["status"] == item["expected_status"]
        citations_supported = set(citations) <= set(retrieved_ids)
        ok = valid_status and status_match and citations_supported

        print(f"Question: {item['id']} ({item['type']})")
        print(f"Text: {item['question']}")
        print(f"Expected status: {item['expected_status']}")
        print(f"Retrieved: {retrieved_ids}")
        print(f"Status: {result['status']}")
        print(f"Answer: {result['answer']}")
        print(f"Citations: {citations}")
        print(f"Message: {result['message']}")
        if note:
            print(f"Note: {note}")

        if not (status_match and citations_supported):
            print("Result: FAIL")
            failures.append(item["id"])
        elif not valid_status:
            print("Result: FAIL (status outside the contract)")
            failures.append(item["id"])
        else:
            print("Result: PASS")
            passed += 1

        print()

    total = len(questions)
    print("--- Pipeline Summary ---")
    print(f"Questions evaluated: {total}")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {failures}")


if __name__ == "__main__":
    main()
