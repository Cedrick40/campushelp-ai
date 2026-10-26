
"""
Gemini behind `generate_answer()` — spec §Generation.

Provider, model and key all live in this file:
- key: `AI_API_KEY` from `backend/.env` (the spec's one authoritative layout);
  never logged, never returned, never sent anywhere but Google.
- model: `AI_MODEL` env var, defaulting to `DEFAULT_MODEL`.
- SDK: `google-genai`, imported lazily so the rest of the branch keeps
  working if it is not installed.
"""

import json
import os
import random
import re
import time
from pathlib import Path


DEFAULT_MODEL = "gemini-3.5-flash-lite"
# Free-tier daily quotas are per model, so a fallback keeps the demo usable
# when the primary model's quota is exhausted or the model is overloaded.
FALLBACK_MODELS = ("gemini-3.1-flash-lite", "gemini-3.8-flash")
REQUEST_TIMEOUT_MS = int(os.environ.get("AI_TIMEOUT_MS") or 120_000)

# The Gemini Developer API free tier returns 429 (and occasionally 5xx) under
# load. Retrying with exponential backoff keeps a valid request from becoming
# a user-facing failure. Total added wait stays well under a request timeout.
MAX_ATTEMPTS = int(os.environ.get("AI_MAX_ATTEMPTS") or 5)
BASE_BACKOFF_S = float(os.environ.get("AI_BACKOFF_S") or 2.0)
MAX_BACKOFF_S = 30.0
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
PLACEHOLDER_KEYS = {"", "your-key-here", "change-me"}

SYSTEM_INSTRUCTIONS = """
You answer student questions using only the evidence passages supplied
with the question.

Rules:
- Use ONLY the evidence passages. Never use outside knowledge.
- Every source id you cite must appear in the evidence passages.
- If the passages answer the question: status "answered", copy one complete
  paragraph verbatim from the single cited passage that answers it. Do not
  paraphrase, summarize, shorten, or merge disconnected passages. Put the
  source id used in cited_source_ids and set message null.
- Answer the question's intent from the closest relevant passage even when
  the passage does not repeat the question's wording. Do not abstain merely
  because a rule is worded differently from the question.
- If the question is genuinely ambiguous and the evidence contains several
  possible answers, use status "insufficient_evidence" and ask which one the
  student means instead of guessing or claiming the documents are missing.
- If the passages do not contain the answer: status "insufficient_evidence",
  answer null, cited_source_ids [], and a message explaining that the
  available documents do not contain it.
- If the passages disagree with each other for the same group of students:
  status "conflicting_sources", an answer that explains the disagreement
  without choosing a side, cited_source_ids listing at least two of the
  disagreeing passages, and message "These sources disagree."
- A rule for all students and a narrower rule explicitly limited to a named
  subgroup (for example, applicants on the supplementary list) are not a
  conflict. For a general question, answer with the general rule and cite
  only that passage.
- If the question asserts a false premise, do not repeat it as fact; state
  that the documents do not support it.
- Never invent dates, fees, amounts, policies, office names or contacts
  that are not in the passages.
- Output JSON only, with exactly these keys: status, answer,
  cited_source_ids, message. status must be one of answered,
  insufficient_evidence, conflicting_sources.
""".strip()

_loaded = False


def load_backend_env() -> None:
    """Load `backend/.env` once, without overriding the real environment."""
    global _loaded

    if _loaded or not ENV_FILE.exists():
        _loaded = True
        return

    from dotenv import load_dotenv

    load_dotenv(ENV_FILE, override=False)
    _loaded = True


def configured_api_key() -> str | None:
    """The Gemini API key, or None when it is missing or a placeholder."""
    load_backend_env()
    key = (os.environ.get("AI_API_KEY") or "").strip()
    return None if key in PLACEHOLDER_KEYS else key


def model_name() -> str:
    return (os.environ.get("AI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def model_candidates() -> list[str]:
    """Primary model plus fallbacks, unless AI_MODEL pins a specific model."""
    primary = model_name()
    if os.environ.get("AI_MODEL"):
        return [primary]
    return [primary, *[model for model in FALLBACK_MODELS if model != primary]]


def build_contents(question: str, evidence: list[dict]) -> str:
    """Evidence passages as numbered blocks, then the question."""
    blocks = []

    for number, passage in enumerate(evidence, start=1):
        if not isinstance(passage, dict):
            continue

        meta = [f"source_id={passage.get('source_id', '?')}"]

        for key in ("title", "section", "page", "document_date", "status", "url"):
            value = passage.get(key)
            if value is not None and value != "":
                meta.append(f"{key}={value}")

        text = passage.get("text", "")
        blocks.append(
            f"[{number}] " + " | ".join(meta) + f"\n    {text}"
        )

    return (
        "Evidence passages:\n\n"
        + "\n\n".join(blocks)
        + f"\n\nQuestion: {question}"
    )


def parse_output(text: str) -> dict:
    """Model output → the contract dict, or ValueError if it is unusable."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("The model returned no text.")

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    data = json.loads(cleaned)

    if not isinstance(data, dict):
        raise ValueError("The model output was not a JSON object.")

    return {
        "status": data.get("status"),
        "answer": data.get("answer"),
        "cited_source_ids": data.get("cited_source_ids") or [],
        "message": data.get("message"),
    }


_client_instance = None
_client_key = None


def _client(api_key: str):
    """
    One reusable client, kept alive at module scope.

    The SDK closes a client (and its HTTP transport) as soon as it is
    garbage-collected, so a throwaway client can die mid-request. Reusing a
    single instance also avoids rebuilding the transport on every question.
    """
    global _client_instance, _client_key

    if _client_instance is None or _client_key != api_key:
        from google import genai
        from google.genai import types

        _client_instance = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        )
        _client_key = api_key

    return _client_instance


def _retry_delay(error: Exception, attempt: int) -> float | None:
    """
    Seconds to wait before retrying, or None when the error is not
    retryable (bad key, invalid model, malformed request).

    Retries 429 (rate limit) and 5xx (transient server) only. Honours a
    server `Retry-After` when present, otherwise exponential backoff with
    jitter.
    """
    status = getattr(error, "code", None) or getattr(error, "status_code", None)

    if status is None:
        return None

    if status != 429 and not (500 <= status < 600):
        return None

    message = str(error).lower()

    # A daily quota cannot recover in a few seconds; move to the next model.
    if status == 429 and ("per day" in message or "perday" in message):
        return None

    retry_after = None

    response = getattr(error, "response", None)

    if response is not None:
        try:
            header = response.headers.get("retry-after")
            if header:
                retry_after = float(header)
        except (AttributeError, TypeError, ValueError):
            retry_after = None

    if retry_after is not None:
        return min(retry_after, MAX_BACKOFF_S)

    delay = min(BASE_BACKOFF_S * (2 ** (attempt - 1)), MAX_BACKOFF_S)
    return delay + random.uniform(0, delay / 4)


def _should_try_next_model(error: Exception) -> bool:
    status = getattr(error, "code", None) or getattr(error, "status_code", None)
    return status == 404 or status == 429 or (
        isinstance(status, int) and 500 <= status < 600
    )


def _generate_with_retry(api_key: str, prompt: str) -> str:
    from google.genai import types

    client = _client(api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTIONS,
        response_mime_type="application/json",
    )

    last_error = None

    for model in model_candidates():
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                return response.text
            except Exception as error:
                last_error = error
                delay = _retry_delay(error, attempt)

                if delay is not None and attempt < MAX_ATTEMPTS:
                    time.sleep(delay)
                    continue

                if _should_try_next_model(error):
                    break

                raise

    raise last_error or RuntimeError("unreachable")


def gemini_provider(question: str, evidence: list[dict]) -> dict:
    """
    Ask Gemini for an answer grounded in the supplied passages.

    Rate limits and transient server errors are retried with backoff before
    giving up. Raises on any terminal failure — `generate_answer()` turns
    that into a friendly `status: error` with no key or traceback in it
    (FR-08).
    """
    api_key = configured_api_key()

    if not api_key:
        raise ValueError("AI_API_KEY is not configured.")

    text = _generate_with_retry(
        api_key, build_contents(question, evidence)
    )

    return parse_output(text)
