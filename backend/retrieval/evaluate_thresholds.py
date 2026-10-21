
from retrieval.evaluate_retrieval import evaluate


THRESHOLDS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]


def main():
    print("Threshold | Precision@3 | Recall@3 | MRR  | Layer-1 abstain | Deferred")
    print("-" * 76)

    for threshold in THRESHOLDS:
        report = evaluate(threshold=threshold)
        print(
            f"{threshold:>9.1f} | "
            f"{report['precision_at_3']:>11.2%} | "
            f"{report['recall_at_3']:>8.2%} | "
            f"{report['mrr']:>4.2f} | "
            f"{report['layer_one_abstentions']:>15}/{report['unsupported']} | "
            f"{report['layer_two_deferrals']:>8}"
        )


if __name__ == "__main__":
    main()
