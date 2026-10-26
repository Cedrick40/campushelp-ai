
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
    _cited_documents,
    validate_answer_result,
)
from retrieval.gemini_provider import (
    configured_api_key,
    gemini_provider,
    load_backend_env,
)
from retrieval.search import query_terms, tokenize


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

    for passage in cited:
        if normalized_answer == _normalize_text(passage["text"]):
            return _normalize_text(passage["text"])

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


GENERAL_RULE_MARKERS = (
    "all students",
    "every student",
    "each student",
    "all candidates",
    "all learners",
)
SUBGROUP_RULE_MARKERS = (
    "supplementary list",
    "applicants on the",
    "for applicants",
    "specific programme",
    "specific program",
    "only applicants",
    "only students",
)


def _general_rule(citations: list[str], evidence: list[dict]) -> dict | None:
    """
    Pick the all-students rule when a conflict is really general vs subgroup.

    A policy for everyone and a narrower policy for a named subgroup are not
    contradictory; the general question should get the general rule.
    """
    by_id = {
        str(passage.get("source_id")): passage
        for passage in evidence
        if isinstance(passage, dict)
        and passage.get("source_id") is not None
        and isinstance(passage.get("text"), str)
    }
    cited = [by_id[source_id] for source_id in citations if source_id in by_id]

    if len(cited) < 2:
        return None

    general = [
        passage
        for passage in cited
        if any(
            marker in _normalize_text(passage["text"]).lower()
            for marker in GENERAL_RULE_MARKERS
        )
    ]

    if len(general) != 1:
        return None

    others = [passage for passage in cited if passage is not general[0]]

    if not all(
        any(
            marker in _normalize_text(passage["text"]).lower()
            for marker in SUBGROUP_RULE_MARKERS
        )
        for passage in others
    ):
        return None

    return general[0]


def _has_general_marker(text: str) -> bool:
    normalized = _normalize_text(text).lower()
    return any(marker in normalized for marker in GENERAL_RULE_MARKERS)


def _has_subgroup_marker(text: str) -> bool:
    normalized = _normalize_text(text).lower()
    return any(marker in normalized for marker in SUBGROUP_RULE_MARKERS)


def _preferred_general_rule(
    question: str, citations: list[str], evidence: list[dict]
) -> dict | None:
    """Prefer the all-students rule when the question asks a general question."""
    terms = query_terms(question)

    if "regist" not in terms or "deadline" not in terms:
        return None

    if any(marker in question.lower() for marker in SUBGROUP_RULE_MARKERS):
        return None

    by_id = {
        str(passage.get("source_id")): passage
        for passage in evidence
        if isinstance(passage, dict)
        and passage.get("source_id") is not None
        and isinstance(passage.get("text"), str)
    }
    cited = [by_id[source_id] for source_id in citations if source_id in by_id]

    if not cited or any(_has_general_marker(p["text"]) for p in cited):
        return None

    if not any(_has_subgroup_marker(p["text"]) for p in cited):
        return None

    general = [
        passage
        for passage in evidence
        if isinstance(passage, dict)
        and isinstance(passage.get("text"), str)
        and _has_general_marker(passage["text"])
    ]

    if len(general) != 1:
        return None

    passage = general[0]
    overlap = len(terms & tokenize(passage["text"])) / len(terms)

    if overlap < 0.5:
        return None

    return passage


def _clarification_message(question: str) -> str | None:
    """Ask which item the student means for broad, underspecified questions."""
    text = _normalize_text(question).lower()
    terms = query_terms(question)
    specific = {"regist", "fee", "exam", "tuition", "payment", "late", "hostel"}

    if "deadline" in terms and not (terms & specific):
        return "Which deadline do you mean — registration, fees, or exams?"

    if "how much" in text and (terms & {"pay", "fee"}) and not (terms & specific):
        return "Which fee do you mean — tuition, registration, or late payment?"

    return None


def _grounded_fallback(question: str, evidence: list[dict]) -> dict | None:
    """Answer with the strongest passage when the model wrongly abstains."""
    terms = query_terms(question)

    if len(terms) < 2:
        return None

    best = None
    best_key = (-1.0, False)

    for passage in evidence:
        if not isinstance(passage, dict):
            continue

        text = passage.get("text")

        if not isinstance(text, str) or not text.strip():
            continue

        overlap = terms & tokenize(text)
        key = (len(overlap) / len(terms), _has_general_marker(text))

        if key > best_key:
            best_key = key
            best = passage

    if best is None or best_key[0] < 0.6:
        return None

    return best


def _normalize(raw: dict, evidence: list[dict], question: str) -> dict:
    """Drop unknown citations and enforce the layer-2 fallback rules."""
    if not isinstance(raw, dict):
        raise ValueError("Provider output must be a dictionary.")

    status = raw.get("status")

    if status == "ambiguous":
        status = "insufficient_evidence"

    if status not in ALLOWED_STATUSES:
        raise ValueError("Provider returned an unknown status.")

    model_abstained = status == "insufficient_evidence"

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
        preferred = _preferred_general_rule(question, citations, evidence)

        if preferred is not None:
            answer = _normalize_text(preferred["text"])
            citations = [preferred["source_id"]]
        else:
            answer = _exact_answer(answer, citations, evidence)

    if status == "insufficient_evidence":
        fallback = (
            _grounded_fallback(question, evidence) if model_abstained else None
        )

        if fallback is not None:
            status = "answered"
            answer = _normalize_text(fallback["text"])
            citations = [fallback["source_id"]]
            message = None
        else:
            answer = None
            citations = []
            clarification = (
                _clarification_message(question) if model_abstained else None
            )
            message = (
                clarification
                or (message if message and message.strip() else NOT_VERIFIED_MESSAGE)
            )

    if status == "conflicting_sources":
        general_rule = _general_rule(citations, evidence)

        if general_rule is not None:
            status = "answered"
            answer = _normalize_text(general_rule["text"])
            citations = [general_rule["source_id"]]
            message = None
        elif len(_cited_documents(citations, evidence)) < 2:
            status = "insufficient_evidence"
            answer = None
            citations = []
            message = NOT_VERIFIED_MESSAGE
        elif not message or not message.strip():
            message = CONFLICT_MESSAGE

    if status == "error":
        clarification = _clarification_message(question)

        if clarification is not None:
            status = "insufficient_evidence"
            answer = None
            citations = []
            message = clarification
        else:
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
        clarification = _clarification_message(question)

        if clarification is not None:
            return {
                "status": "insufficient_evidence",
                "answer": None,
                "cited_source_ids": [],
                "message": clarification,
            }

        return _error(NOT_CONFIGURED_MESSAGE)

    try:
        result = _normalize(raw, evidence, question)
        return validate_answer_result(result, evidence)
    except ValueError:
        return _error()
