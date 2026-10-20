
import re


def tokenize(text: str) -> set[str]:
    """Convert text into lowercase word tokens."""
    return set(re.findall(r"\b\w+\b", text.lower()))


def retrieve_evidence(
    question: str,
    passages: list[dict],
    top_k: int = 5,
    min_score: float = 0.3,
) -> list[dict]:
    """
    Rank passages by keyword overlap.

    Only return passages meeting the minimum relevance score.
    Preserve complete passage dictionaries for citations.
    """
    if top_k <= 0 or not 0 <= min_score <= 1:
        return []

    question_words = tokenize(question)

    if not question_words:
        return []

    ranked = []

    for passage in passages:
        if not isinstance(passage, dict):
            continue

        text = passage.get("text", "")

        if not isinstance(text, str) or not text.strip():
            continue

        passage_words = tokenize(text)
        overlap = question_words & passage_words

        if overlap:
            score = len(overlap) / len(question_words)

            if score >= min_score:
                ranked.append((score, passage))

    ranked.sort(key=lambda item: item[0], reverse=True)

    return [
        passage
        for score, passage in ranked[:top_k]
    ]
