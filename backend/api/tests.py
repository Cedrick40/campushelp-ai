import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from .models import CorpusConfig, Document
from .validators import FakeProvider, validate_generation

EVIDENCE = [
    {"source_id": "1", "document_id": "10", "title": "Fee Schedule",
     "url": "https://example.edu/fees", "section": "Payment", "page": 2,
     "date": "2026-01-15", "checked_date": "2026-10-20",
     "text": "Tuition fees are due before registration closes. Late payment attracts a penalty. A third sentence. A fourth."},
    {"source_id": "2", "document_id": "11", "title": "Registration Page",
     "url": "/api/documents/11/file/", "section": "Dates", "page": None,
     "date": None, "checked_date": "2026-10-20",
     "text": "Registration closes on 15 March."},
]
SAME_DOC = [dict(EVIDENCE[0]), dict(EVIDENCE[1], document_id="10")]


def ask(client, question="When does registration close?", status="retrieved", evidence=None, mode="answer"):
    evidence = EVIDENCE if evidence is None else evidence
    with patch("api.views.retrieve_evidence", return_value=(status, evidence)), \
         patch("api.views.generate_answer",
               side_effect=lambda ev, q: FakeProvider(mode)(q, ev)):
        return client.post("/api/ask/", {"question": question}, content_type="application/json")


class AskEndpointTests(TestCase):
    def test_empty_question_is_rejected(self):
        for body in ["", "   "]:
            r = ask(self.client, question=body)
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.json()["status"], "error")
            self.assertEqual(r.json()["message"], "Please enter a question.")

    def test_question_over_500_characters_is_rejected(self):
        r = ask(self.client, question="x" * 501)
        self.assertEqual(r.status_code, 400)
        self.assertIn("500", r.json()["message"])

    def test_answered_has_sources_with_excerpt_and_no_page_when_missing(self):
        r = ask(self.client)
        body = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(body["status"], "answered")
        card = body["sources"][0]
        self.assertEqual(card["title"], "Fee Schedule")
        self.assertEqual(card["page"], 2)
        self.assertIn("Tuition fees are due", card["excerpt"])
        self.assertNotIn("A third sentence", card["excerpt"])

    def test_page_is_omitted_when_the_document_has_none(self):
        ev = [EVIDENCE[1]]
        card = ask(self.client, evidence=ev).json()["sources"][0]
        self.assertNotIn("page", card)

    def test_retrieval_fallback_returns_contact_line_without_calling_the_model(self):
        CorpusConfig.objects.create(contact_office="Registrar's Office", contact_source="Contacts page")
        with patch("api.views.generate_answer") as model:
            with patch("api.views.retrieve_evidence", return_value=("insufficient_evidence", [])):
                r = self.client.post("/api/ask/", {"question": "Can I get a refund?"}, content_type="application/json")
            model.assert_not_called()
        body = r.json()
        self.assertEqual(body["status"], "insufficient_evidence")
        self.assertEqual(body["message"], "I could not verify this from the available documents.")
        self.assertEqual(body["contact_line"], {"office": "Registrar's Office", "source": "Contacts page"})
        self.assertEqual(body["sources"], [])

    def test_fallback_without_contact_line_is_null(self):
        r = ask(self.client, status="insufficient_evidence", evidence=[])
        self.assertIsNone(r.json()["contact_line"])

    def test_model_abstaining_gives_the_fallback(self):
        body = ask(self.client, mode="abstain").json()
        self.assertEqual(body["status"], "insufficient_evidence")

    def test_invented_citation_is_dropped_and_becomes_fallback(self):
        body = ask(self.client, mode="bad_citation").json()
        self.assertEqual(body["status"], "insufficient_evidence")
        self.assertIsNone(body["answer"])

    def test_conflicting_sources_need_two_distinct_documents(self):
        ok = ask(self.client, mode="conflict").json()
        self.assertEqual(ok["status"], "conflicting_sources")
        self.assertEqual(len(ok["sources"]), 2)
        self.assertEqual(ok["message"], "These sources disagree.")
        one_doc = ask(self.client, mode="conflict", evidence=SAME_DOC).json()
        self.assertEqual(one_doc["status"], "insufficient_evidence")

    def test_provider_failure_is_a_friendly_502_with_no_internals(self):
        with patch("api.views.retrieve_evidence", return_value=("retrieved", EVIDENCE)), \
             patch("api.views.generate_answer", side_effect=RuntimeError("secret-key-123 traceback")):
            r = self.client.post("/api/ask/", {"question": "Hello there?"}, content_type="application/json")
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json()["status"], "error")
        self.assertNotIn("secret", r.content.decode())

    def test_retrieval_failure_is_a_friendly_502(self):
        with patch("api.views.retrieve_evidence", side_effect=RuntimeError("db exploded")):
            r = self.client.post("/api/ask/", {"question": "Hello there?"}, content_type="application/json")
        self.assertEqual(r.status_code, 502)
        self.assertNotIn("exploded", r.content.decode())


class ValidatorTests(TestCase):
    def test_malformed_results_become_errors(self):
        for bad in [None, "text", [], {"status": "nonsense"}]:
            self.assertEqual(validate_generation(bad, EVIDENCE)["status"], "error")

    def test_answer_needs_a_valid_citation(self):
        result = {"status": "answered", "answer": "Yes.", "cited_source_ids": ["99"], "message": None}
        self.assertEqual(validate_generation(result, EVIDENCE)["status"], "insufficient_evidence")

    def test_valid_answer_passes_and_citations_are_deduplicated(self):
        result = {"status": "answered", "answer": "Yes.", "cited_source_ids": ["1", "1", "99"], "message": None}
        out = validate_generation(result, EVIDENCE)
        self.assertEqual(out["status"], "answered")
        self.assertEqual(out["cited_source_ids"], ["1"])


class CorpusEndpointTests(TestCase):
    def test_defaults_when_nothing_is_configured(self):
        body = self.client.get("/api/corpus/").json()
        self.assertEqual(body["type"], "sample")
        self.assertIsNone(body["last_checked"])

    def test_returns_the_configured_banner_data(self):
        CorpusConfig.objects.create(corpus_type="official", university="Cavendish University Zambia",
                                    last_checked=date(2026, 10, 20))
        body = self.client.get("/api/corpus/").json()
        self.assertEqual(body, {"type": "official", "university": "Cavendish University Zambia",
                                "last_checked": "2026-10-20"})


class DocumentFileTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "documents"
        self.root.mkdir()
        (self.root / "policy.md").write_text("# Policy\nFees are due.", encoding="utf-8")
        (Path(self.tmp.name) / "secret.txt").write_text("private", encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)

    def test_serves_a_recorded_file(self):
        doc = Document.objects.create(title="P", file_path="documents/policy.md")
        with override_settings(DOCUMENTS_DIR=self.root):
            r = self.client.get(f"/api/documents/{doc.id}/file/")
            body = b"".join(r.streaming_content).decode()
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/plain", r["Content-Type"])
        self.assertIn("Fees are due", body)

    def test_unknown_id_is_404(self):
        with override_settings(DOCUMENTS_DIR=self.root):
            self.assertEqual(self.client.get("/api/documents/999/file/").status_code, 404)

    def test_paths_outside_documents_are_refused(self):
        doc = Document.objects.create(title="Bad", file_path="../secret.txt")
        with override_settings(DOCUMENTS_DIR=self.root):
            self.assertEqual(self.client.get(f"/api/documents/{doc.id}/file/").status_code, 404)