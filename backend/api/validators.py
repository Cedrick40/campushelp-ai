"""
Final safety check on answer results before they reach the client, plus the
FakeProvider that lets the whole /api/ask/ path be tested without an API key.

Spec: devpost/spec.md > Response Validation.
"""

import re

ALLOWED_STATUSES = {"answered", "insufficient_evidence", "conflicting_sources", "error"}

NOT_VERIFIED_MESSAGE = "I could not verify this from the available documents."
CONFLICT_MESSAGE = "These sources disagree."
ERROR_MESSAGE = "Something went wrong. Please try again."


def first_sentences(text, count=2, limit=400):
    """The first few sentences of a passage, used for quoted excerpts."""
    if not isinstance(text, str):
        return ""
    text = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+", text)
    excerpt = " ".join(parts[:count]).strip()
    if len(excerpt) > limit:
        excerpt = excerpt[: limit - 1].rstrip() + "…"
    return excerpt


def _document_key(passage):
    for key in ("document_id", "source_id"):
        value = passage.get(key)
        if value is not None:
            return str(value)
    return None


def _error(message=ERROR_MESSAGE):
    return {"status": "error", "answer": None, "cited_source_ids": [], "message": message}


def _insufficient(message=NOT_VERIFIED_MESSAGE):
    return {"status": "insufficient_evidence", "answer": None, "cited_source_ids": [], "message": message}


def validate_generation(result, evidence):
    """
    Return a safe {status, answer, cited_source_ids, message}. Never raises.

    - unknown structure or status        -> error
    - citations not in the evidence      -> dropped
    - an answer left with no citations   -> insufficient_evidence
    - conflict without 2+ distinct docs  -> insufficient_evidence
    """
    if not isinstance(result, dict) or not isinstance(evidence, list):
        return _error()

    status = result.get("status")
    if status not in ALLOWED_STATUSES:
        return _error()

    answer = result.get("answer")
    answer = answer.strip() if isinstance(answer, str) and answer.strip() else None
    message = result.get("message")
    message = message.strip() if isinstance(message, str) and message.strip() else None

    by_id = {
        str(p["source_id"]): p
        for p in evidence
        if isinstance(p, dict) and p.get("source_id") is not None
    }

    raw = result.get("cited_source_ids")
    citations = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, str) and item in by_id and item not in citations:
            citations.append(item)

    if status == "error":
        return _error(message or ERROR_MESSAGE)

    if status == "insufficient_evidence":
        return _insufficient(message or NOT_VERIFIED_MESSAGE)

    if not answer or not citations:
        return _insufficient()

    if status == "conflicting_sources":
        documents = {_document_key(by_id[c]) for c in citations}
        if len(documents) < 2:
            return _insufficient()
        message = message or CONFLICT_MESSAGE
    else:
        message = None

    return {"status": status, "answer": answer, "cited_source_ids": citations, "message": message}


class FakeProvider:
    """
    A stand-in for the AI provider: callable as provider(question, evidence).

    modes: "answer" (quotes the first evidence sentence), "abstain",
    "conflict", "bad_citation", "error".
    """

    def __init__(self, mode="answer"):
        self.mode = mode

    def __call__(self, question, evidence):
        if self.mode == "error":
            raise RuntimeError("fake provider failure")

        if self.mode == "abstain":
            return _insufficient()

        if self.mode == "bad_citation":
            return {"status": "answered", "answer": "Invented answer.",
                    "cited_source_ids": ["does-not-exist"], "message": None}

        first = evidence[0]

        if self.mode == "conflict":
            other = next((p for p in evidence if _document_key(p) != _document_key(first)), first)
            return {"status": "conflicting_sources",
                    "answer": "The two sources give different information.",
                    "cited_source_ids": [first["source_id"], other["source_id"]],
                    "message": CONFLICT_MESSAGE}

        return {"status": "answered",
                "answer": first_sentences(first.get("text", ""), count=1),
                "cited_source_ids": [first["source_id"]], "message": None}