---
doc: spec
status: approved
---

# CampusHelp AI — Technical Spec

## How This Works, In Plain Language

The app is three parts: a web page (React), a Django server behind it, and a folder of documents.

You type a question on the page. The page sends it to Django's `/api/ask/` endpoint. Django first **cleans the question into search words** (drops "when", "is", "the", etc.), then **searches the stored passages** with SQLite's built-in search — this is `retrieve()`. It gets back the matching passages with a relevance score, each still tagged with its document, section, page, and date.

If nothing scored well enough, we stop right there: the response is "I could not verify this from the available documents" — the fallback has two layers. Layer one is the search step: not enough of the question's terms matched anything, or the best score was too low, and we never call the model at all. Layer two catches the rest: the passages *were* retrieved but still don't answer this question, so the prompt tells the model to say `insufficient_evidence` rather than stretch, and the response check accepts that. Either way the fallback can also carry an office line (`contact_line`), which Person 1 puts in the metadata file from the official contacts page — we never ask the model for an office, so it can't invent one.

If passages did score well, they're handed to **one swappable function**, `generate_answer(evidence, question)`, which asks the AI provider (Person 2's choice) to write a short answer *using only those passages* — like being handed open-book notes and told "answer from these pages only, cite which one." The result is checked: every cited source must be one of the passages we actually retrieved, or it's dropped. The page then shows the answer plus source cards, so the student can verify without leaving the page.

Documents get into the system by running one command, `python manage.py ingest`, which reads files from `documents/` plus a metadata file beside them (title, url, date, corpus type, optional `contact_line`), extracts the text into passages, and rewrites the search index each time. No upload screen — the corpus changes only when the team runs the command.

Why this shape: it's the smallest system where retrieval-before-generation (the kernel) is real and testable. The search index lives inside the SQLite database we already have, so there's no second service, no vector store, and the critical path works even before the AI provider is wired up.

## The Core Journey Through the System

PRD ref: `prd.md > The Core Journey`.

1. Student opens the page → React renders banner (from `GET /api/corpus/`), title, question box, three example questions, empty answer area.
2. They type a question (or click an example, which fills and submits immediately) → React validates non-empty, then `POST /api/ask/ {question}`.
3. Django: question → keyword cleaning → `retrieve()` → passages with scores.
4. **Query-term coverage too low, or best score below `MIN_SCORE` →** response `status: insufficient_evidence` directly from retrieval, no model call — page shows the neutral fallback notice, plus `contact_line` (office name + its source) when Person 1 supplied one in the metadata.
5. **Passages found →** `generate_answer(passages, question)` → provider returns a draft (it may itself return `insufficient_evidence` when the passages don't answer the question — layer two of the fallback) → response validator checks every cited source id exists in the retrieved set (drops/abstains otherwise; flags conflict if ≥2 distinct documents disagree) → `status: answered`, `status: insufficient_evidence`, or `status: conflicting_sources`.
6. Page renders loading state while waiting, then the answer (≤3 sentences) + source cards (title, section, date, quoted excerpt, page when present, "Open document" link) — official docs open their public URL in a new tab, sample docs open the file served by Django at `GET /api/documents/<id>/file/`.
7. Student opens a source, asks the next question — loop repeats on the same page. Nothing persists between sessions (`prd.md > States and Boundaries > Persistence`).

## Stack

| Choice | Why / tradeoff accepted |
|---|---|
| **React 19 + Vite** (frontend, scaffolded with `npm create vite@latest`) | Team's versions. Vite gives a fast dev server and standard tooling. Doc: https://react.dev, https://vitejs.dev |
| **Python 3.14, Django 5.2 LTS + Django REST Framework** (backend) | Team's versions; the learner already has Django experience. LTS means security fixes through the project's life. Doc: https://docs.djangoproject.com/en/5.2/, https://www.django-rest-framework.org |
| **Node 24 LTS** | Team's version for the frontend toolchain. Doc: https://nodejs.org |
| **SQLite** (database) | Decided by the team. Zero setup, ships with Python. Its FTS5 extension provides the search index — same file, no extra service. Doc: https://www.sqlite.org/fts5.html |
| **SQLite FTS5 keyword search** for retrieval | Agreed this spec: no new account or dependency, keeps the critical path independent of the AI provider. Tradeoff: weaker on heavily reworded questions — accepted, mitigated by question-word dropping and checked against the evaluation set. Swappable later behind `retrieve()`. |
| **`generate_answer()` single swappable function** | AI provider is Person 2's decision. Everything else in the system talks to this one function with a fixed input (passages + question) and fixed output (status, answer, cited source ids, message). Changing providers touches one file. |
| **drf-spectacular** for Swagger UI at `/api/docs/` | Already in the repo's plan; gives the team a live contract page. Doc: https://drf-spectacular.readthedocs.io |
| **pdfminer.six** (PDF), **python-docx** (.docx, only if Person 1's files need it), built-in readers for .md/.txt | Plain-text extraction without a service. Tradeoff: scanned/image PDFs won't extract — they error visibly instead of silently succeeding (FR-03). Doc: https://pypi.org/project/pdfminer.six/ |
| **`django-cors-headers`** (via `FRONTEND_ORIGIN` in `.env`) | Vite runs on :5173, Django on :8000; the browser needs permission to cross. Doc: https://github.com/adamchainz/django-cors-headers |

Unverified to check early in the build: FTS5 is compiled into Python's bundled SQLite on most platforms — verify on the build machine on day one; if missing, fall back to a simple `LIKE`-based `retrieve()` with the same signature (same rule, weaker ranking).

## Where It Runs and How Someone Tries It

Local, on one machine. **Python 3.14, Node 24 LTS.** One `.env` file at `backend/.env`, laid out exactly as the README shows it:

```
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
FRONTEND_ORIGIN=http://localhost:5173
AI_API_KEY=your-key-here        # Person 2's provider key; the only secret
```

```bash
# Backend (terminal 1)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env            # then paste AI_API_KEY
python manage.py migrate
python manage.py ingest            # loads ../documents/ into SQLite
python manage.py runserver         # http://localhost:8000  (Swagger: /api/docs/)

# Frontend (terminal 2)
cd frontend
npm create vite@latest . -- --template react   # first time only (Person 4 scaffolds once)
npm install
npm run dev                        # http://localhost:5173
```

Open **http://localhost:5173** — that's the demo recording surface. Submission needs the demo video + public repo; deployment is optional and decided in `6-ship`. The README must reproduce exactly this sequence (clone → install → `.env` → migrate → ingest → run), with the `.env` block above as the one authoritative layout, per NFR-09.

## Look and Feel

Carried forward unchanged from `prd.md > Look and Feel` and `scope.md > Inspiration & Identity`: calm reference page — white/light grey with one deep blue (button, links, focus outlines), readable sans-serif, generous spacing, small rounded corners, mobile-first. Explicitly no crest/logo, no sparkle icons, no chat bubbles, no gradients, no typing animation. Sample-data banner is visible on load. Plain CSS (no UI framework) keeps this enforceable and matches the "nothing decorative" rule. Banner/footer wording comes from `GET /api/corpus/`, with placeholder university name until Person 1 decides (`prd.md > Open Questions`).

## Components

### Frontend — Question Box
Input + submit button; client-side rejection of empty/whitespace input with a visible message before any request; **500-character limit** enforced on both client and server (over-limit → validation message, no request sent); three clickable examples that fill and submit immediately (one triggers the fallback); loading state distinguishable from answer and error.
PRD ref: `prd.md > Asking a question`, `States and Boundaries > Empty input / Loading`.

### Frontend — Answer Area
Renders one of: answer + source cards, fallback notice, conflict display, or failure message with retry. Answer ≤3 sentences, direct answer first.
PRD ref: `prd.md > Answer with sources`, `Honest fallback`, `Conflicting sources`, `Error handling`.

### Frontend — Source Card
Shows document title, section, date, 1–3 sentence quoted excerpt, "Open document" link; page number only when present. Official → public URL in new tab; sample → backend file endpoint `GET /api/documents/<id>/file/`. Conflict state: two cards side by side (wide) / stacked (phones) with "These sources disagree."
PRD ref: `prd.md > Answer with sources`, `Conflicting sources`.

### Frontend — Banner & Footer
Banner text from `GET /api/corpus/` (sample vs official wording, university, last-checked date); footer "Unofficial student project, not affiliated with [university]."
PRD ref: `prd.md > Screens and Layout`, `States and Boundaries > Banner state`.

### API — `POST /api/ask/` (Person 3)
Validates input (400 on empty/whitespace input or over 500 characters), orchestrates retrieve → generate → validate, returns the contract below. No credentials or stack traces ever in a response (FR-08).
PRD ref: `prd.md > Asking a question`, `Error handling`.

**Contract (finalized per `docs/requirements.md` §9):**

```json
// Request
{ "question": "When is the deadline to register for exams?" }

// 200 responses (one of)
{ "status": "answered",
  "answer": "…≤3 sentences…",
  "sources": [ { "title": "…", "url": "…", "section": "…", "page": 2,
                 "date": "2026-01-15", "excerpt": "…" } ],
  "message": null }

{ "status": "insufficient_evidence", "answer": null, "sources": [],
  "message": "I could not verify this from the available documents.",
  "contact_line": { "office": "…", "source": "…" } }   // contact_line only when Person 1 supplied one; otherwise null

{ "status": "conflicting_sources", "answer": "…",
  "sources": [ …two or more from different documents… ],
  "message": "These sources disagree." }

// 400 validation, 502 provider/network failure:
{ "status": "error", "answer": null, "sources": [],
  "message": "friendly retry message" }   // never: keys, config, traces
```

`page` omitted when the document has none. `conflicting_sources` is only permitted when ≥2 distinct documents were retrieved.

### API — `GET /api/corpus/` (Person 3)
Returns `{ "type": "sample" | "official", "university": "…", "last_checked": "YYYY-MM-DD" }` from the single corpus-config record written by ingest.
PRD ref: `prd.md > Screens and Layout > Banner`, `States and Boundaries > Banner state`.

### API — `GET /api/documents/<id>/file/` (Person 3)
Streams the stored file for a Document row **only if that id exists in the Document table** — no path input from the client, no serving of anything outside recorded `file_path`s. This address is what a sample document's `url` field holds in source cards; official documents keep their original public URLs.
PRD ref: `prd.md > Answer with sources` ("sample documents open a file served by our backend").

### API — Swagger (Person 3)
`/api/docs/` via drf-spectacular; the team's live view of the contract.

### Ingestion — `backend/ingestion/` (Person 1)
`management/commands/ingest.py`: reads `documents/` + a machine-readable metadata file beside them — title, url, date, corpus type, plus optional **`contact_line`** (office name and its source, taken from the official contacts page by Person 1) and issuer/checked-date/status where available (FR-02 fields). `contact_line` is stored on the corpus config and returned as-is on fallback responses; it is never model-generated. Extracts text (PDF, Markdown, txt, + .docx if needed), splits into passages preserving section/page, rebuilds document/passage/FTS records — **re-running replaces, never duplicates**. Unreadable/unsupported files → clear per-file error, exit non-zero, never a silent partial success (FR-03). Writes the corpus-config record (banner data + contact line).
PRD ref: `prd.md > Answer with sources` (link targets), `Honest fallback` (office contacts from sourced content only), `Error handling`.

### Retrieval — `backend/retrieval/` (Person 2)
- `retrieve(question) -> [{passage_id, document_id, score, …}]` — drops common question words (stopword list), runs SQLite FTS5 `MATCH`, returns passages ranked by relevance score.
- **Insufficient-evidence rule, layer 1 (retrieval):** the search fails when there are no hits, **too few of the question's meaningful terms are covered** by the matched passages, or the best score is below `MIN_SCORE`. Any of these → `insufficient_evidence` immediately, no model call at all. Coverage and `MIN_SCORE` are two constants calibrated against the evaluation set during the build (see Open Issues).
- Retrieval is testable without generation (FR-04).
PRD ref: `prd.md > Honest fallback`; `docs/requirements.md` §7.2 rules 1–2, 6.

### Generation — `generate_answer(evidence, question)` (Person 2)
The single swappable provider boundary. Input: ordered passages + question. Output: `{status, answer, cited_source_ids, message}`. Prompt instructs: answer only from supplied passages, ≤3 sentences, direct answer first, no new dates/amounts/policy, mark disagreement between passages rather than picking one, **and — layer 2 of the fallback — return `status: insufficient_evidence` when the supplied passages do not actually answer the question, instead of stretching them**. Never generates office names or contacts. Provider, model, and key all live behind this function; `.env` supplies `AI_API_KEY`.
PRD ref: `prd.md > Answer with sources`, `Honest fallback`, `Conflicting sources`; `docs/requirements.md` §7.2 rules 3, 7.

### Response Validation — `backend/api/validators.py` (Person 3)
Checks model output before it reaches the client: structure, status value (including accepting a model-returned `insufficient_evidence` from layer 2), every cited id ∈ retrieved set (drop invalid citations; if the answer loses all support → `insufficient_evidence`), conflict status only with ≥2 distinct documents. Implemented with a `FakeProvider` so the whole path is testable without a key.
PRD ref: `prd.md > Answer with sources` ("no invented source names"), `Conflicting sources`; `docs/requirements.md` §7.2 rule 5.

### Evaluation — `python manage.py run_evaluation` (team)
Runs `tests/evaluation/questions.json` (15–30 questions: answerable, reworded, ambiguous, unsupported, conflicting; each with expected source or marked unanswerable) and prints pass/fail per question. Demo questions come from this set (FR-09).
PRD ref: `prd.md > What We're Building`; `docs/requirements.md` §10.

## Data Model

SQLite, written only by ingest (and nothing else — questions are never stored).

- **Document** — id, title, issuer, source_url, publication_date, checked_date, status (current/superseded/unknown), corpus_type (sample/official), file_path, extraction_notes. One row per source file; replaced wholesale on re-ingest.
- **Passage** — id, document (FK), section, page (nullable), position, text. The unit of retrieval and the thing a source card quotes.
- **PassageFTS** — FTS5 virtual table over `text`, keyed to passage ids; rebuilt by ingest. This *is* the knowledge index.
- **CorpusConfig** — single row: type, university, last_checked, optional contact_line (office name + its source); feeds `GET /api/corpus/` and the fallback response.

Persistence: corpus persists across restarts. Answers, questions, and sessions do not — every page load starts fresh (`prd.md > States and Boundaries > Persistence`).

## File Structure

```
campushelp-ai/
├── backend/
│   ├── manage.py
│   ├── requirements.txt          # django, djangorestframework, drf-spectacular,
│   │                             # cors-headers, pdfminer.six, python-docx?, python-dotenv
│   ├── .env                      # AI_API_KEY, DJANGO_SECRET_KEY, FRONTEND_ORIGIN (gitignored)
│   ├── config/                   # Django project: settings.py, urls.py (wires /api/, /api/docs/)
│   ├── api/                      # Person 3 — API + data models
│   │   ├── models.py             # Document, Passage, CorpusConfig
│   │   ├── serializers.py
│   │   ├── views.py              # AskView, CorpusView, DocumentFileView (/api/documents/<id>/file/)
│   │   ├── validators.py         # response validation + FakeProvider
│   │   ├── urls.py
│   │   └── management/commands/run_evaluation.py
│   ├── ingestion/                # Person 1
│   │   └── management/commands/ingest.py
│   ├── retrieval/                # Person 2
│   │   ├── search.py             # retrieve() + coverage & MIN_SCORE rules (FTS5)
│   │   └── generation.py         # generate_answer() — the swappable provider boundary
│   └── app.py                    # Person 1's starter file — DO NOT OVERWRITE
├── documents/                    # source files + corpus.json metadata
│   │                            # (title, url, date, corpus type, optional contact_line)
├── frontend/                     # Person 4 — React + Vite
│   │   └── index.html            # Person 1's starter file — DO NOT OVERWRITE (until Person 4's build)
│   └── src/
│       ├── App.jsx               # page layout: banner, title, box, examples, answer area, footer
│       ├── api.js                # fetch wrappers for /api/ask/, /api/corpus/
│       ├── components/
│       │   ├── QuestionBox.jsx   # input, submit, examples, validation, loading
│       │   ├── AnswerArea.jsx    # answer | fallback | conflict | error states
│       │   ├── SourceCard.jsx    # + conflict side-by-side/stacked layout
│       │   └── Banner.jsx
│       └── styles.css            # calm reference-page styling (no UI framework)
├── devpost/                      # planning docs (scope, prd, spec, checklist…)
├── docs/requirements.md
├── tests/                        # existing team test folder
│   └── evaluation/
│       └── questions.json        # FR-09 evaluation set
├── README.md                     # clone → install → .env (one layout) → migrate → ingest → run
└── LICENSE
```

Boundaries that matter: frontend never talks to retrieval or the provider — only to the three endpoints. Generation touches nothing but its own function file. Ingest is the only writer of corpus data.

## External Services and Dependencies

- **AI provider (Person 2's choice)** — reached only through `generate_answer()`. Needs `AI_API_KEY` in `backend/.env`. Exact model/endpoint/pricing to be confirmed by Person 2; the contract above is provider-independent. Verify cost + key access on day one (risk in `docs/requirements.md` §13).
- **Everything else runs offline** — SQLite, FTS5, local extraction. No hosting, no third-party APIs.

## Important Failure Modes

- **AI provider down / timeout / bad key** → caught inside `generate_answer()`, returns `status: error` with a friendly retry message; no key, config, or traceback in the response (FR-08). Retrieval and ingest still work, so the pipeline is debuggable without the provider.
- **Retrieval finds nothing convincing** → layer 1 of the fallback: coverage/`MIN_SCORE` rule returns `insufficient_evidence` with no model call, plus Person 1's `contact_line` when present — the honest fallback can't be broken by provider trouble. If retrieval passes but the passages still don't answer, layer 2 (model abstains, validator accepts).
- **File won't extract (scanned PDF, corrupt file)** → ingest prints a clear per-file error and exits non-zero; that document simply isn't in the corpus rather than sitting there looking processed.

## What Was Simplified and Why

- **Keyword FTS5 instead of embeddings** — avoids a second API dependency before the provider is chosen; relevance at 5–10 documents is demonstrable. Embeddings can be added later behind the same `retrieve()`.
- **Management command instead of an upload UI** — the team curates the corpus, not the student; saves a whole authenticated surface.
- **Conflict flagged by the model but gated by the validator** — detecting "disagreement" robustly is genuinely hard; the gate (≥2 distinct retrieved documents) keeps the display honest without a rules engine.
- **No session history, no accounts, no feedback buttons** — deferred in `prd.md > Deferred From the POC`.
- **Local-only demo** — recording is sufficient for submission; hosting decided in `6-ship`.

## Decisions and Open Issues

**Learner/team decisions made in this spec:**
- **FTS5 keyword retrieval behind a single `retrieve()`**, returning scored passages — chosen over embeddings to keep the critical path provider-independent; tradeoff accepted: weaker on reworded questions, checked against the evaluation set.
- **Two-layer honest fallback.** Layer 1: retrieval short-circuits to `insufficient_evidence` (no hits, insufficient query-term coverage, or best score < `MIN_SCORE`) with no model call. Layer 2: the generation prompt instructs the model to return `insufficient_evidence` when the retrieved passages don't answer the question, and the validator accepts that status. Office guidance comes only from Person 1's `contact_line` metadata, never from the model.
- **Ingest command inside Person 1's app**, machine-readable metadata file beside documents (including optional `contact_line`), re-run replaces records, clear errors on unreadable files, types PDF/MD/txt (+ .docx if needed).
- **`GET /api/documents/<id>/file/`** (Person 3) serves sample-document files, gated on the Document table; a sample source card's `url` is that address.
- **Local-only for the demo**; hosting deferred to `6-ship`. README must be reproducible end-to-end, with **one authoritative `.env` layout** (the four keys in *Where It Runs*) and versions **Python 3.14 / Node 24 LTS / React 19 / Django 5.2 LTS**, frontend scaffolded via `npm create vite@latest`.
- **500-character question limit**, enforced client-side and by `POST /api/ask/` validation.
- **API contract as written above**, Swagger at `/api/docs/`, folder ownership: Person 1 `backend/ingestion`, Person 2 `backend/retrieval`, Person 3 (learner) API + data models, Person 4 frontend.
- **Evaluation set lives at `tests/evaluation/questions.json`**, run by `python manage.py run_evaluation`.
- **Corpus legality note:** only documents the team is allowed to redistribute may be committed; otherwise a clearly labelled sample set (NFR-10, `scope.md > Who It's For`).

**Learner uncertainty explored (learning goal: retrieval-before-generation):** *embeddings vs. keyword search* — explained as "match by meaning" vs "match by words." Resolved by choosing FTS5; the agreed check is running the reworded questions in the evaluation set (`docs/requirements.md` §10) and inspecting whether `retrieve()` still surfaces the right passage. If reworded questions systematically fail, that's the evidence for adding embeddings behind the same function.

**Open issues:**
- **`MIN_SCORE` and query-coverage threshold values** — two constants; calibrate together during the evaluation phase (Phase 6), record the values and how they were set.
- **AI provider/model/cost** — Person 2's call; block only `generate_answer()`, nothing else.
- **Target university name, document set, sample-vs-official** — Person 1's; placeholder wording in banner/footer until then (`prd.md > Open Questions`).
- **Whether .docx support is actually needed** — depends on Person 1's files; add `python-docx` only if so.
- **FTS5 availability on the build machine** — verify first day; fallback is a `LIKE`-based `retrieve()` with the identical signature.


## Build Notes (Person 3, 24 October 2026)

Changes made while building, so this spec matches the code:

- Source cards also carry `checked_date` (always present, may be null): the Cavendish documents have no publication dates, so `date` may be null.
- The search table is `api_passage_fts` (FTS5, external content over `api_passage.text`), kept in step by database triggers, so writers never need to rebuild it. `rebuild_search_index()` remains for manual repair.
- `Document` has an `external_id` field holding the team's readable id (for example `cuz-001`).
- Identifiers: `source_id = str(Passage.id)` and `document_id = str(Document.id)`. They are always strings in the evidence passed between retrieval, generation and validation.
- `contact_line` is returned only on `insufficient_evidence` responses, and is null when no office was supplied.
- Document source records live in `metadata/` (Person 1's `documents.json`); the banner data and `contact_line` are planned for `metadata/corpus.json`, to be confirmed with Person 1.
- The evaluation set is `tests/evaluation/questions.json`, run by `python manage.py run_evaluation` (`--retrieval-only` needs no AI key).