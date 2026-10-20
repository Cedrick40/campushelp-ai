
import json
from pathlib import Path

from retrieval.search import MIN_COVERAGE, MIN_SCORE, retrieve


BASE_DIR = Path(__file__).resolve().parent
PASSAGES_FILE = BASE_DIR / "data" / "sample_passages.json"
QUESTIONS_FILE = BASE_DIR / "data" / "retrieval_eval.json"


def load_json(path: Path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def evaluate(threshold: float | None = None) -> dict:
    passages = load_json(PASSAGES_FILE)
    questions = load_json(QUESTIONS_FILE)

    options = {"top_k": 3}
    if threshold is not None:
        options["min_score"] = threshold

    total = len(questions)
    answerable_hits = 0
    reciprocal_ranks = []
    precision_scores = []
    unsupported = 0
    layer_one_abstentions = 0
    layer_two_deferrals = 0
    failures = []
    known_limitations = []
    per_question = []

    for item in questions:
        expected = set(item["expected_source_ids"])
        results = retrieve(item["question"], passages, **options)
        retrieved_ids = [passage.get("source_id") for passage in results]

        if expected:
            relevant = sum(1 for sid in retrieved_ids if sid in expected)
            precision_scores.append(
                relevant / len(retrieved_ids) if retrieved_ids else 0.0
            )

            matching_ranks = [
                rank
                for rank, sid in enumerate(retrieved_ids, start=1)
                if sid in expected
            ]

            if matching_ranks:
                answerable_hits += 1
                reciprocal_ranks.append(1 / matching_ranks[0])
                verdict = "PASS"
            elif item.get("known_limitation"):
                verdict = "KNOWN LIMITATION"
                reciprocal_ranks.append(0)
                known_limitations.append(item["id"])
            else:
                verdict = "FAIL"
                reciprocal_ranks.append(0)
                failures.append(item["id"])
        else:
            unsupported += 1

            if not retrieved_ids:
                verdict = "PASS (layer 1 abstain)"
                layer_one_abstentions += 1
            else:
                verdict = "DEFERRED to layer 2 (generation)"
                layer_two_deferrals += 1

        per_question.append((item, retrieved_ids, verdict))

    answerable_total = sum(1 for q in questions if q["expected_source_ids"])

    return {
        "total": total,
        "per_question": per_question,
        "recall_at_3": answerable_hits / answerable_total if answerable_total else 0,
        "mrr": sum(reciprocal_ranks) / answerable_total if answerable_total else 0,
        "precision_at_3": (
            sum(precision_scores) / len(precision_scores)
            if precision_scores
            else 0
        ),
        "unsupported": unsupported,
        "layer_one_abstentions": layer_one_abstentions,
        "layer_two_deferrals": layer_two_deferrals,
        "failures": failures,
        "known_limitations": known_limitations,
    }


def main():
    report = evaluate()

    for item, retrieved_ids, verdict in report["per_question"]:
        print(f"\nQuestion: {item['id']} ({item['type']})")
        print(f"Text: {item['question']}")
        print(f"Expected sources: {sorted(item['expected_source_ids'])}")
        print(f"Expected status: {item['expected_status']}")
        print(f"Retrieved: {retrieved_ids}")
        print(f"Result: {verdict}")

    print("\n--- Evaluation Summary ---")
    print(f"Questions evaluated: {report['total']}")
    print(f"Recall@3: {report['recall_at_3']:.2%}")
    print(f"Mean Reciprocal Rank: {report['mrr']:.2f}")
    print(f"Precision@3 (mean over answerable): {report['precision_at_3']:.2%}")
    print(
        "Unsupported questions abstaining at layer 1: "
        f"{report['layer_one_abstentions']}/{report['unsupported']}"
    )
    print(
        "Unsupported questions deferred to layer 2 (generation): "
        f"{report['layer_two_deferrals']}/{report['unsupported']}"
    )
    print(f"Failed questions: {report['failures']}")
    print(f"Known keyword limitations: {report['known_limitations']}")
    print(
        "Calibrated constants: "
        f"MIN_SCORE={MIN_SCORE}, MIN_COVERAGE={MIN_COVERAGE} "
        "(chosen from the evaluate_thresholds sweep; MIN_COVERAGE is the "
        "lowest query coverage among answerable questions in this set)"
    )


if __name__ == "__main__":
    main()
