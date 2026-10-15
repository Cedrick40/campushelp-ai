
ALLOWED_STATUSES = {
    "supported",
    "unsupported",
    "ambiguous",
    "conflicting",
}


def validate_answer_result(result: dict, evidence: list[dict]) -> dict:
    """
    Validate the structure and citations of an answer result.

    This checks consistency, not whether the answer is factually true.
    """
    if not isinstance(result, dict):
        raise ValueError("Answer result must be a dictionary.")

    if not isinstance(evidence, list):
        raise ValueError("Evidence must be a list.")

    status = result.get("status")
    answer = result.get("answer")
    citations = result.get("citations")

    if status not in ALLOWED_STATUSES:
        raise ValueError("Invalid answer status.")

    if not isinstance(answer, str):
        raise ValueError("Answer must be a string.")

    if not isinstance(citations, list):
        raise ValueError("Citations must be a list.")

    if any(not isinstance(source_id, str) for source_id in citations):
        raise ValueError("Every citation must be a source ID string.")

    if len(citations) != len(set(citations)):
        raise ValueError("Duplicate citations are not allowed.")

    available_ids = {
        passage.get("source_id")
        for passage in evidence
        if isinstance(passage, dict)
        and isinstance(passage.get("source_id"), str)
    }

    if any(source_id not in available_ids for source_id in citations):
        raise ValueError("A citation refers to a source not supplied as evidence.")

    if status == "supported":
        if not answer.strip():
            raise ValueError("Supported answers must contain an answer.")

        if not citations:
            raise ValueError("Supported answers must cite evidence.")

    if status == "unsupported":
        if answer.strip():
            raise ValueError(
                "Unsupported results must not contain an unsupported answer."
            )

        if citations:
            raise ValueError(
                "Unsupported results must not contain citations."
            )

    if status == "ambiguous" and not answer.strip():
        raise ValueError(
            "Ambiguous results should explain what needs clarification."
        )

    if status == "conflicting":
        if not answer.strip():
            raise ValueError(
                "Conflicting results must explain the disagreement."
            )

        if len(set(citations)) < 2:
            raise ValueError(
                "Conflicting results must cite at least two distinct sources."
            )

    return result
