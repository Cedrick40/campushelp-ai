"""
python manage.py run_evaluation

Runs the team's evaluation questions (tests/evaluation/questions.json) through
the real pipeline and prints PASS or FAIL for each one (FR-09).

By default every question goes through POST /api/ask/ exactly as the web page
would send it. That needs the AI key in backend/.env. Use --retrieval-only to
test just the search step with no key and no model call.
"""

import json
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.test.utils import override_settings

from retrieval.search import retrieve_evidence

DEFAULT_FILE = settings.BASE_DIR.parent / "tests" / "evaluation" / "questions.json"
STATUSES = {"answered", "insufficient_evidence", "conflicting_sources"}


def _titles_match(expected, found):
    found_lower = [t.lower() for t in found]
    return all(any(e.lower() in t for t in found_lower) for e in expected)


def _expected_statuses(item):
    expected = item["expected_status"]
    return expected if isinstance(expected, list) else [expected]


class Command(BaseCommand):
    help = "Run the evaluation questions and print pass/fail for each."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to the questions JSON file.")
        parser.add_argument("--retrieval-only", action="store_true",
                            help="Test the search step only (no AI key, no model call).")
        parser.add_argument("--delay", type=float, default=0.0,
                            help="Seconds to wait between questions (helps with provider rate limits).")

    def handle(self, *args, **options):
        questions = self._load(options["file"])
        client = Client(raise_request_exception=False)  # talks to the app in-process, no server needed
        results = []

        # The built-in test client identifies itself as "testserver", so allow that host here.
        with override_settings(ALLOWED_HOSTS=[*settings.ALLOWED_HOSTS, "testserver"]):
            for index, item in enumerate(questions):
                if index and options["delay"]:
                    time.sleep(options["delay"])
                if options["retrieval_only"]:
                    ok, detail = self._check_retrieval(item)
                else:
                    ok, detail = self._check_endpoint(client, item)
                results.append(ok)
                label = self.style.SUCCESS("PASS") if ok else self.style.ERROR("FAIL")
                self.stdout.write(f"{label}  {item.get('id', '?'):<6} {item['category']:<22} {item['question']}")
                if not ok:
                    self.stdout.write(f"        -> {detail}")

        passed = sum(results)
        self.stdout.write(f"\n{passed}/{len(results)} passed")
        if passed != len(results):
            raise CommandError(f"{len(results) - passed} question(s) failed.")

    def _load(self, path):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            raise CommandError(f"Question file not found: {path}")
        except json.JSONDecodeError as error:
            raise CommandError(f"Question file is not valid JSON: {error}")

        questions = data.get("questions") if isinstance(data, dict) else None
        if not questions:
            raise CommandError("No questions found. Add entries to the 'questions' list (see the file's _format note).")

        for item in questions:
            for key in ("category", "question", "expected_status"):
                if key not in item:
                    raise CommandError(f"A question is missing '{key}': {item}")

            for expected_status in _expected_statuses(item):
                if expected_status not in STATUSES:
                    raise CommandError(
                        f"Unknown expected_status '{expected_status}' in "
                        f"{item.get('id', item['question'])}"
                    )
        return questions

    def _check_endpoint(self, client, item):
        response = client.post("/api/ask/", data=json.dumps({"question": item["question"]}),
                               content_type="application/json")
        try:
            body = response.json()
        except ValueError:
            return False, f"the server answered HTTP {response.status_code}, not JSON (did you run 'python manage.py migrate'?)"
        status = body.get("status")
        expected_statuses = _expected_statuses(item)

        if status not in expected_statuses:
            return False, (
                f"expected status {expected_statuses} but got '{status}' "
                f"({body.get('message')})"
            )
        expected = item.get("expected_sources", [])
        if expected:
            titles = [s.get("title", "") for s in body.get("sources", [])]
            if not _titles_match(expected, titles):
                return False, f"expected sources {expected} but the answer cited {titles}"

        answer_text = f"{body.get('answer') or ''} {body.get('message') or ''}".lower()
        required = item.get("expected_answer_contains", [])

        if required and not all(term.lower() in answer_text for term in required):
            return False, f"answer did not contain all of {required}: {answer_text[:300]}"

        forbidden = item.get("expected_answer_not_contains", [])

        if forbidden:
            found = [term for term in forbidden if term.lower() in answer_text]
            if found:
                return False, f"answer contained forbidden text {found}: {answer_text[:300]}"

        return True, ""

    def _check_retrieval(self, item):
        status, evidence = retrieve_evidence(item["question"])
        wants_evidence = any(
            expected in {"answered", "conflicting_sources"}
            for expected in _expected_statuses(item)
        )
        # Abstention is layer 2's job; retrieval-only mode cannot check it.
        if not wants_evidence:
            return True, ""

        if status != "retrieved":
            return False, "retrieval found no usable evidence"

        expected = item.get("expected_sources", [])
        if expected:
            titles = [p.get("title", "") for p in evidence]
            if not _titles_match(expected, titles):
                return False, f"expected sources {expected} but retrieval returned {titles}"
        return True, ""