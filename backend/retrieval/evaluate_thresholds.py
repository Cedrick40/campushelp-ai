
import json
from pathlib import Path

from retrieval.retrieval import retrieve_evidence


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def main():
    with (DATA_DIR / "sample_passages.json").open(
        encoding="utf-8"
    ) as file:
        passages = json.load(file)

    with (DATA_DIR / "retrieval_eval.json").open(
        encoding="utf-8"
    ) as file:
        questions = json.load(file)

    thresholds = [0.0, 0.1, 0.2, 0.3, 0.5]

    for threshold in thresholds:
        hits = 0
        answerable = 0
        relevant_retrieved = 0
        total_retrieved = 0
        reciprocal_rank_sum = 0
        unsupported_questions = 0
        unsupported_false_positives = 0

        for item in questions:
            expected = set(item["expected_source_ids"])

            results = retrieve_evidence(
                item["question"],
                passages,
                top_k=3,
                min_score=threshold,
            )

            retrieved_ids = [
                passage.get("source_id")
                for passage in results
            ]

            total_retrieved += len(retrieved_ids)

            if expected:
                answerable += 1

                matching_ranks = [
                    rank
                    for rank, source_id in enumerate(
                        retrieved_ids, start=1
                    )
                    if source_id in expected
                ]

                if matching_ranks:
                    hits += 1
                    reciprocal_rank_sum += (
                        1 / matching_ranks[0]
                    )

                relevant_retrieved += sum(
                    source_id in expected
                    for source_id in retrieved_ids
                )
            else:
                unsupported_questions += 1

                if retrieved_ids:
                    unsupported_false_positives += 1

        recall = hits / answerable if answerable else 0
        precision = (
            relevant_retrieved / total_retrieved
            if total_retrieved else 0
        )
        mrr = (
            reciprocal_rank_sum / answerable
            if answerable else 0
        )
        false_positive_rate = (
            unsupported_false_positives / unsupported_questions
            if unsupported_questions else 0
        )

        print(
            f"Threshold={threshold:.1f} | "
            f"Precision@3={precision:.2%} | "
            f"Recall@3={recall:.2%} | "
            f"MRR={mrr:.2f} | "
            f"Unsupported FPR={false_positive_rate:.2%}"
        )


if __name__ == "__main__":
    main()
