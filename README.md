# CampusHelp AI

**Demo video:** [add the public YouTube/Vimeo link before submitting] · **Runs locally** (no hosted page; see "Run it locally")

## About

CampusHelp AI answers students' questions about university rules, fees and dates using only a fixed set of approved documents. Every answer shows the source it came from, with a short quoted excerpt, so a student can check it. If the documents do not support an answer, it says "I could not verify this from the available documents" instead of guessing. This is an unofficial student project, not affiliated with any university.

## Objective

Show that an AI assistant can be trusted on rules that cost students money or deadlines: it retrieves evidence first, answers only from that evidence, and is honest when the evidence is missing or conflicting.

## Tools

- Python 3.14, Django 5.2 LTS, Django REST Framework, drf-spectacular (Swagger)
- SQLite with FTS5 full-text search
- Google Gemini API (through one swappable function)
- React 19 and Vite, Node.js 24 LTS
- Built with the Devpost Learn "Build With AI: Basics" Skill Pack (see `devpost/`)

## My approach

1. **Retrieve first.** The question is cleaned into search words and matched against stored document passages with SQLite FTS5.
2. **Two-layer honesty.** If retrieval finds no convincing evidence, the system answers "could not verify" without calling the AI at all. If evidence is found but does not answer the question, the model is told to abstain.
3. **Cite or drop.** Every source the model cites must be one of the retrieved passages; invented citations are removed.
4. **Conflicts are shown, not hidden.** If two documents disagree, both are shown side by side.
5. **Safe failures.** Provider or network errors give a friendly retry message and never expose keys or internal details.

## Run it locally

Requires Python 3.14 and Node.js 24 LTS.

```bash
git clone https://github.com/Cedrick40/campushelp-ai.git
cd campushelp-ai/backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env            # then add your own AI_API_KEY
python manage.py migrate
python manage.py ingest            # loads the documents into the database
python manage.py runserver         # http://localhost:8000  (API docs: /api/docs/)
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

Tests: `python manage.py test api` (backend) and `python manage.py run_evaluation` (the evaluation questions; add `--retrieval-only` to run without an AI key).

## Project structure

```
backend/        Django REST API: api/ (endpoints, models, validation), retrieval/ (search and answers), ingestion/ (document loading)
frontend/       React + Vite student page
documents/      the source documents
metadata/       document source records
tests/          evaluation questions (tests/evaluation/questions.json)
devpost/        scope.md, prd.md and spec.md from the Skill Pack
docs/           the team's requirements document
```

## Outcome

Status on 24 October 2026: the API, search table, answer validation and automated tests are in place; document and the full demo are in place also.

## Credits

- Document collection and ingestion: [Samson Kwizera]
- Search and AI answers: [Ezra Muhizi]
- Backend API and integration: Cedrick Niyibikora
- Student interface: [Person 4 name]
- Planning method: Devpost Learn Skill Pack

## Author

Cedrick Niyibikora, backend and integration lead and team leader. GitHub: [Cedrick40](https://github.com/Cedrick40)

Released under the MIT licence (see `LICENSE`).