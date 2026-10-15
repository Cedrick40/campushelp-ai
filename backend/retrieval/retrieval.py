
import re


def tokenize(text: str) -> set[str]:
    """Convert text into lowercase word tokens."""
    return set(re.findall(r"\b\w+\b", text.lower()))


def retrieve_evidence(
    question: str,
    passages: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """
    Rank passages by keyword overlap.

    Return complete passage dictionaries so source metadata
    remains available for citations.
    """
    if top_k <= 0:
        return []

    question_words = tokenize(question)

    if not question_words:
        return []

    ranked = []

    for passage in passages:
        text = passage.get("text", "")
        passage_words = tokenize(text)
        overlap = question_words & passage_words

        if overlap:
            score = len(overlap) / len(question_words)
            ranked.append((score, passage))

    ranked.sort(key=lambda item: item[0], reverse=True)

    return [
        passage
        for score, passage in ranked[:top_k]
    ]
