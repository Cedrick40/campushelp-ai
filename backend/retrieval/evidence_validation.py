
"""
Response validation for answer results (spec §Response Validation).

Contract fixed by `devpost/spec.md` (generation output):
    {status, answer, cited_source_ids, message}

Evidence is passed in as the retrieved passage list — every passage carries
a `source_id` (plus title/section/page when available), and every cited id
must exist in that list.
"""

ALLOWED_STATUSES = {
    "answered",
    "insufficient_evidence",
    "conflicting_sources",
    "error",
}

NOT_VERIFIED_MESSAGE = (
    "I could not verify this from the available documents."
)
CONFLICT_MESSAGE = "These sources disagree."
ERROR_MESSAGE = "Something went wrong. Please try again."


def _document_key(passage: dict) -> str | None:
    for key in ("document_id", "source_id"):
        value = passage.get(key)
        if isinstance(value, str):
            return value
    return None


def _cited_documents(citations: list[str], evidence: list[dict]) -> set[str]:
    keys = {
        _document_key(passage)
        for passage in evidence
        if isinstance(passage, dict)
    }
    keys.discard(None)
    return {c for c in citations if c in keys}


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
    citations = result.get("cited_source_ids")
    message = result.get("message")

    if status not in ALLOWED_STATUSES:
        raise ValueError("Invalid answer status.")

    if answer is not None and not isinstance(answer, str):
        raise ValueError("Answer must be a string or null.")

    if not isinstance(citations, list):
        raise ValueError("Cited source IDs must be a list.")

    if any(not isinstance(source_id, str) for source_id in citations):
        raise ValueError("Every cited source ID must be a string.")

    if message is not None and not isinstance(message, str):
        raise ValueError("Message must be a string or null.")

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

    has_answer = bool(answer and answer.strip())
    has_message = bool(message and message.strip())

    if status == "answered":
        if not has_answer:
            raise ValueError("Answered results must contain an answer.")

        if not citations:
            raise ValueError("Answered results must cite evidence.")

        if has_message:
            raise ValueError("Answered results must not carry a fallback message.")

    if status == "insufficient_evidence":
        if has_answer:
            raise ValueError(
                "Insufficient-evidence results must not contain an answer."
            )

        if citations:
            raise ValueError(
                "Insufficient-evidence results must not contain citations."
            )

        if not has_message:
            raise ValueError(
                "Insufficient-evidence results must explain why."
            )

    if status == "conflicting_sources":
        if not has_answer:
            raise ValueError(
                "Conflicting-source results must explain the disagreement."
            )

        if not has_message:
            raise ValueError(
                "Conflicting-source results must carry a message."
            )

        evidence_documents = {
            key
            for key in (_document_key(p) for p in evidence if isinstance(p, dict))
            if key is not None
        }

        if len(evidence_documents) < 2:
            raise ValueError(
                "Conflict requires at least two distinct retrieved documents."
            )

        if len(_cited_documents(citations, evidence)) < 2:
            raise ValueError(
                "Conflicting-source results must cite at least two distinct documents."
            )

    if status == "error":
        if has_answer:
            raise ValueError("Error results must not contain an answer.")

        if citations:
            raise ValueError("Error results must not contain citations.")

        if not has_message:
            raise ValueError("Error results must carry a friendly message.")

    return result
