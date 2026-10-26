
"""
`generate_answer(evidence, question)` — the single swappable provider
boundary (spec §Generation).

The team's provider is the Gemini API (Google AI Studio key, Flash tier),
reached only through `retrieval/gemini_provider.py`. Swapping providers
touches that one file; everything else keeps the same contract:

    input:  evidence = retrieved passage dicts (each with `source_id`)
    output: {status, answer, cited_source_ids, message}

The key comes from `AI_API_KEY` in `backend/.env` and never leaves the
provider module (FR-08).
"""

import re
from collections.abc import Callable

from retrieval.evidence_validation import (
    ALLOWED_STATUSES,
    CONFLICT_MESSAGE,
    ERROR_MESSAGE,
    NOT_VERIFIED_MESSAGE,
    validate_answer_result,
)
from retrieval.gemini_provider import (
    configured_api_key,
    gemini_provider,
    load_backend_env,
)


Provider = Callable[[str, list[dict]], dict]

NOT_CONFIGURED_MESSAGE = (
    "The answer service is not available right now. Please try again later."
)

_provider: Provider | None = None


def set_provider(provider: Provider) -> None:
    """Register a provider behind this boundary (tests / future swaps)."""
    global _provider
    _provider = provider


def clear_provider() -> None:
    global _provider
    _provider = None


def _default_provider() -> Provider | None:
    """Gemini, but only once a real key exists."""
    return gemini_provider if configured_api_key() else None


def _error(message: str = ERROR_MESSAGE) -> dict:
    return {
        "status": "error",
        "answer": None,
        "cited_source_ids": [],
        "message": message,
    }


def _normalize_text(text: str) -> str:
    return " ".join(str(text).split())


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", str(text).lower()))


def _exact_answer(answer: str, citations: list[str], evidence: list[dict]) -> str:
    """
    Return the complete cited paragraph, verbatim.

    The provider is asked to quote the source, but a paraphrase or a partial
    sentence would still be grounded while missing the rest of the rule. Pick
    the cited passage that best matches the provider's answer and return its
    full text, preserving the document's wording.
    """
    by_id = {
        str(passage.get("source_id")): passage
        for passage in evidence
        if isinstance(passage, dict)
        and passage.get("source_id") is not None
        and isinstance(passage.get("text"), str)
        and passage["text"].strip()
    }
    cited = [by_id[source_id] for source_id in citations if source_id in by_id]

    if not cited:
        return answer

    normalized_answer = _normalize_text(answer)

    if any(normalized_answer == _normalize_text(p["text"]) for p in cited):
        return answer

    answer_terms = _tokens(answer)
    best = cited[0]
    best_score = -1.0

    for passage in cited:
        passage_terms = _tokens(passage["text"])
        overlap = len(answer_terms & passage_terms)
        score = overlap / max(len(answer_terms), 1)
        if score > best_score:
            best = passage
            best_score = score

    return _normalize_text(best["text"])


def _normalize(raw: dict, evidence: list[dict]) -> dict:
    """Drop unknown citations and enforce the layer-2 fallback rules."""
    if not isinstance(raw, dict):
        raise ValueError("Provider output must be a dictionary.")

    status = raw.get("status")

    if status not in ALLOWED_STATUSES:
        raise ValueError("Provider returned an unknown status.")

    answer = raw.get("answer") if isinstance(raw.get("answer"), str) else None
    citations = raw.get("cited_source_ids")
    message = raw.get("message") if isinstance(raw.get("message"), str) else None

    if not isinstance(citations, list):
        citations = []

    known_ids = {
        passage.get("source_id")
        for passage in evidence
        if isinstance(passage, dict)
        and isinstance(passage.get("source_id"), str)
    }
    citations = [c for c in citations if isinstance(c, str) and c in known_ids]

    if status == "answered" and not (answer and answer.strip()):
        status = "insufficient_evidence"
        answer = None
        citations = []
        message = NOT_VERIFIED_MESSAGE

    if status == "answered" and not citations:
        status = "insufficient_evidence"
        answer = None
        message = NOT_VERIFIED_MESSAGE

    if status == "answered" and answer and citations:
        answer = _exact_answer(answer, citations, evidence)

    if status == "insufficient_evidence":
        answer = None
        citations = []
        message = message if message and message.strip() else NOT_VERIFIED_MESSAGE

    if status == "conflicting_sources":
        documents = {
            passage.get("document_id") or passage.get("source_id")
            for passage in evidence
            if isinstance(passage, dict)
        }
        documents.discard(None)
        cited_documents = {c for c in citations if c in documents}

        if len(cited_documents) < 2:
            status = "insufficient_evidence"
            answer = None
            citations = []
            message = NOT_VERIFIED_MESSAGE
        elif not message or not message.strip():
            message = CONFLICT_MESSAGE

    if status == "error":
        answer = None
        citations = []
        message = message if message and message.strip() else ERROR_MESSAGE

    return {
        "status": status,
        "answer": answer,
        "cited_source_ids": citations,
        "message": message,
    }


def generate_answer(
    evidence: list[dict],
    question: str,
    provider: Provider | None = None,
) -> dict:
    """
    Ask the provider for an answer using only the supplied passages.

    Every failure — no provider, bad key, timeout, malformed output — is
    returned as `status: error` with a friendly message. Credentials,
    configuration and tracebacks never reach the caller (FR-08).
    """
    if not isinstance(evidence, list):
        return _error()
    if not isinstance(question, str) or not question.strip():
        return _error()

    load_backend_env()
    provider = provider or _provider or _default_provider()

    if provider is None:
        return _error(NOT_CONFIGURED_MESSAGE)

    if not configured_api_key():
        return _error(NOT_CONFIGURED_MESSAGE)

    try:
        raw = provider(question, evidence)
    except Exception:
        return _error(NOT_CONFIGURED_MESSAGE)

    try:
        result = _normalize(raw, evidence)
        return validate_answer_result(result, evidence)
    except ValueError:
        return _error()
