
import json
import os
import unittest
from unittest.mock import patch

from retrieval.gemini_provider import (
    DEFAULT_MODEL,
    _generate_with_retry,
    _retry_delay,
    build_contents,
    configured_api_key,
    gemini_provider,
    model_name,
    parse_output,
)
from retrieval.generation import clear_provider, generate_answer


EVIDENCE = [
    {
        "source_id": "REG-001",
        "title": "Registration Policy",
        "section": "Registration",
        "page": 3,
        "document_date": "2026-01-10",
        "text": "Students must complete registration before the advertised deadline.",
    },
    {
        "source_id": "REG-002",
        "title": "Registration Notice",
        "text": "The earlier notice set the deadline at 15 January 2026.",
    },
]


class ProviderConfigTests(unittest.TestCase):
    @patch.dict(os.environ, {"AI_API_KEY": "real-key-123"})
    def test_api_key_is_read_from_the_environment(self):
        self.assertEqual(configured_api_key(), "real-key-123")

    @patch.dict(os.environ, {"AI_API_KEY": "your-key-here"})
    def test_placeholder_key_counts_as_missing(self):
        self.assertIsNone(configured_api_key())

    @patch.dict(os.environ, {"AI_API_KEY": ""})
    def test_empty_key_counts_as_missing(self):
        self.assertIsNone(configured_api_key())

    def test_blank_ai_model_is_ignored(self):
        with patch.dict(os.environ, {"AI_MODEL": "   "}):
            self.assertEqual(model_name(), DEFAULT_MODEL)

    def test_ai_model_override_is_used(self):
        with patch.dict(os.environ, {"AI_MODEL": "gemini-3.6-flash"}):
            self.assertEqual(model_name(), "gemini-3.6-flash")


class PromptTests(unittest.TestCase):
    def setUp(self):
        self.contents = build_contents("When must students register?", EVIDENCE)

    def test_every_evidence_source_is_labelled(self):
        for passage in EVIDENCE:
            self.assertIn(f"source_id={passage['source_id']}", self.contents)

    def test_evidence_text_and_metadata_are_included(self):
        self.assertIn("Students must complete registration", self.contents)
        self.assertIn("title=Registration Policy", self.contents)
        self.assertIn("page=3", self.contents)
        self.assertIn("section=Registration", self.contents)

    def test_question_is_included(self):
        self.assertIn("When must students register?", self.contents)

    def test_malformed_passages_do_not_crash(self):
        contents = build_contents("Q", [None, {}, {"source_id": "X"}])
        self.assertIn("source_id=X", contents)


class OutputParsingTests(unittest.TestCase):
    def test_plain_json_is_parsed(self):
        raw = json.dumps(
            {
                "status": "answered",
                "answer": "Before the deadline.",
                "cited_source_ids": ["REG-001"],
                "message": None,
            }
        )
        self.assertEqual(
            parse_output(raw),
            {
                "status": "answered",
                "answer": "Before the deadline.",
                "cited_source_ids": ["REG-001"],
                "message": None,
            },
        )

    def test_json_wrapped_in_code_fences_is_parsed(self):
        raw = '```json\n{"status": "insufficient_evidence", "answer": null, "cited_source_ids": [], "message": "No."}\n```'
        self.assertEqual(parse_output(raw)["status"], "insufficient_evidence")

    def test_missing_citation_list_defaults_to_empty(self):
        raw = '{"status": "answered", "answer": "Yes."}'
        self.assertEqual(parse_output(raw)["cited_source_ids"], [])

    def test_non_json_output_raises(self):
        with self.assertRaises(ValueError):
            parse_output("I could not find that.")

    def test_empty_output_raises(self):
        with self.assertRaises(ValueError):
            parse_output("   ")

    def test_json_array_output_raises(self):
        with self.assertRaises(ValueError):
            parse_output("[]")


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return self.response


class FakeClient:
    def __init__(self, response):
        self.models = FakeModels(response)


class ProviderCallTests(unittest.TestCase):
    def setUp(self):
        clear_provider()

    def tearDown(self):
        clear_provider()

    def run_provider(self, text, key="real-key-123"):
        client = FakeClient(FakeResponse(text))
        with patch.dict(os.environ, {"AI_API_KEY": key}):
            with patch(
                "retrieval.gemini_provider._client",
                return_value=client,
            ):
                result = gemini_provider("When must students register?", EVIDENCE)
        return result, client

    def test_valid_model_output_becomes_the_contract(self):
        raw = json.dumps(
            {
                "status": "answered",
                "answer": "Students must complete registration.",
                "cited_source_ids": ["REG-001"],
                "message": None,
            }
        )
        result, client = self.run_provider(raw)
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["cited_source_ids"], ["REG-001"])
        self.assertEqual(client.models.calls[0]["model"], DEFAULT_MODEL)

    def test_missing_key_raises_before_any_call(self):
        with patch.dict(os.environ, {"AI_API_KEY": ""}):
            with self.assertRaises(ValueError):
                gemini_provider("Q", EVIDENCE)

    def test_provider_failure_becomes_a_friendly_error(self):
        def boom(*args, **kwargs):
            raise RuntimeError("AI_API_KEY=sk-secret https://internal")

        with patch.dict(os.environ, {"AI_API_KEY": "real-key-123"}):
            with patch("retrieval.gemini_provider._client", side_effect=boom):
                result = generate_answer(EVIDENCE, "When must students register?")

        self.assertEqual(result["status"], "error")
        self.assertNotIn("secret", result["message"].lower())
        self.assertNotIn("AI_API_KEY", result["message"])

    def test_hallucinated_citation_is_dropped_end_to_end(self):
        raw = json.dumps(
            {
                "status": "answered",
                "answer": "The deadline is 15 January.",
                "cited_source_ids": ["MADE-UP-999"],
                "message": None,
            }
        )
        client = FakeClient(FakeResponse(raw))
        with patch.dict(os.environ, {"AI_API_KEY": "real-key-123"}):
            with patch("retrieval.gemini_provider._client", return_value=client):
                result = generate_answer(EVIDENCE, "What is the deadline?")

        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["cited_source_ids"], [])
        self.assertIsNone(result["answer"])


class ApiError(Exception):
    def __init__(self, code, retry_after=None):
        super().__init__(f"{code}")
        self.code = code
        if retry_after is not None:
            self.response = type(
                "Response",
                (),
                {"headers": {"retry-after": str(retry_after)}},
            )()


class RetryPolicyTests(unittest.TestCase):
    def test_rate_limit_is_retryable(self):
        self.assertIsNotNone(_retry_delay(ApiError(429), attempt=1))

    def test_daily_quota_is_not_retried(self):
        class DailyQuotaError(ApiError):
            def __str__(self):
                return "429 per day limit exceeded"

        self.assertIsNone(_retry_delay(DailyQuotaError(429), attempt=1))

    def test_server_error_is_retryable(self):
        self.assertIsNotNone(_retry_delay(ApiError(503), attempt=1))

    def test_bad_key_is_not_retryable(self):
        self.assertIsNone(_retry_delay(ApiError(401), attempt=1))

    def test_not_found_is_not_retryable(self):
        self.assertIsNone(_retry_delay(ApiError(404), attempt=1))

    def test_backoff_grows_with_attempts(self):
        first = _retry_delay(ApiError(429), attempt=1)
        third = _retry_delay(ApiError(429), attempt=3)
        self.assertLess(first, third)

    def test_retry_after_header_is_honoured(self):
        delay = _retry_delay(ApiError(429, retry_after=7), attempt=1)
        self.assertEqual(delay, 7.0)


class RetryExecutionTests(unittest.TestCase):
    def _client_raising_then_succeeding(self, errors, result="{}"):
        calls = {"n": 0, "result": result}

        class Models:
            def generate_content(self, **kwargs):
                calls["n"] += 1
                if calls["n"] <= len(errors):
                    raise errors[calls["n"] - 1]
                return type("R", (), {"text": calls["result"]})()

        class Client:
            models = Models()

        return Client(), calls

    def test_transient_error_retries_then_succeeds(self):
        client, calls = self._client_raising_then_succeeding([ApiError(429)])
        with patch("retrieval.gemini_provider._client", return_value=client):
            with patch("retrieval.gemini_provider.time.sleep"):
                text = _generate_with_retry("k", "prompt")
        self.assertEqual(text, "{}")
        self.assertEqual(calls["n"], 2)

    def test_non_retryable_error_raises_immediately(self):
        client, calls = self._client_raising_then_succeeding([ApiError(401)])
        with patch("retrieval.gemini_provider._client", return_value=client):
            with patch("retrieval.gemini_provider.time.sleep"):
                with self.assertRaises(ApiError):
                    _generate_with_retry("k", "prompt")
        self.assertEqual(calls["n"], 1)

    def test_gives_up_after_max_attempts(self):
        errors = [ApiError(429) for _ in range(10)]
        client, calls = self._client_raising_then_succeeding(errors)
        with patch.dict(os.environ, {"AI_MODEL": "pinned-model"}):
            with patch("retrieval.gemini_provider._client", return_value=client):
                with patch("retrieval.gemini_provider.time.sleep"):
                    with self.assertRaises(ApiError):
                        _generate_with_retry("k", "prompt")
        self.assertEqual(calls["n"], 5)

    def test_daily_quota_falls_back_to_the_next_model(self):
        class DailyQuotaError(ApiError):
            def __str__(self):
                return "429 per day limit exceeded"

        client, calls = self._client_raising_then_succeeding([DailyQuotaError(429)])
        with patch("retrieval.gemini_provider._client", return_value=client):
            with patch("retrieval.gemini_provider.time.sleep"):
                text = _generate_with_retry("k", "prompt")
        self.assertEqual(text, "{}")
        self.assertEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main()
