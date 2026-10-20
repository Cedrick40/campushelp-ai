
import json
from pathlib import Path

from retrieval.retrieval import retrieve_evidence


BASE_DIR = Path(__file__).resolve().parent
PASSAGES_FILE = BASE_DIR / "data" / "sample_passages.json"
QUESTIONS_FILE = BASE_DIR / "data" / "retrieval_eval.json"


def main():
    with PASSAGES_FILE.open(encoding="utf-8") as file:
        passages = json.load(file)

    with QUESTIONS_FILE.open(encoding="utf-8") as file:
        questions = json.load(file)

    total = len(questions)
    answerable_total = 0
    answerable_hits = 0
    reciprocal_ranks = []
    unsupported_false_positives = 0
    failures = []
    precision_scores = []

    for item in questions:
        expected = set(item["expected_source_ids"])
        results = retrieve_evidence(
            item["question"],
            passages,
            top_k=3,
        )

        retrieved_ids = [
            passage.get("source_id")
            for passage in results
        ]
        if expected:
            relevant_count = sum(
                1 for source_id in retrieved_ids
                if source_id in expected
            )

            precision_scores.append(
                relevant_count / len(retrieved_ids)
                if retrieved_ids else 0
            )

        if expected:
            answerable_total += 1
            matching_ranks = [
                rank
                for rank, source_id in enumerate(retrieved_ids, start=1)
                if source_id in expected
            ]

            if matching_ranks:
                answerable_hits += 1
                reciprocal_ranks.append(1 / matching_ranks[0])
            else:
                reciprocal_ranks.append(0)

        elif retrieved_ids:
            unsupported_false_positives += 1

        passed = (
            bool(expected.intersection(retrieved_ids))
            if expected
            else not retrieved_ids
        )

        print(f"\nQuestion: {item['id']}")
        print(f"Text: {item['question']}")
        print(f"Expected: {sorted(expected)}")
        print(f"Retrieved: {retrieved_ids}")
        print(f"Result: {'PASS' if passed else 'FAIL'}")

        if not passed:
            failures.append(item["id"])

    recall_at_3 = (
        answerable_hits / answerable_total
        if answerable_total else 0
    )
    mrr = (
        sum(reciprocal_ranks) / answerable_total
        if answerable_total else 0
    )
    false_positive_rate = (
        unsupported_false_positives
        / sum(not item["expected_source_ids"] for item in questions)
        if any(not item["expected_source_ids"] for item in questions)
        else 0
    )
    precision_at_3 = (
        sum(precision_scores) / len(precision_scores)
        if precision_scores else 0
    )

    print("\n--- Evaluation Summary ---")
    print(f"Questions evaluated: {total}")
    print(f"Recall@3: {recall_at_3:.2%}")
    print(f"Mean Reciprocal Rank: {mrr:.2f}")
    print(f"Unsupported false-positive rate: {false_positive_rate:.2%}")
    print(f"Failed questions: {failures}")
    print(f"Precision@3: {precision_at_3:.2%}")


if __name__ == "__main__":
    main()
