# CampusHelp AI

**Demo video:** [add the public YouTube/Vimeo link before submitting] · **Runs locally** (no hosted page; see "Run it locally")

## About

CampusHelp AI answers students' questions about university rules, fees and dates using only a fixed set of approved documents. Every answer shows the source it came from, with a short quoted excerpt, so a student can check it. If the documents do not support an answer, it says "I could not verify this from the available documents" instead of guessing. Students can ask as guests, or register to keep a private history of their questions across sessions. This is an unofficial student project, not affiliated with any university.

## Objective

Show that an AI assistant can be trusted on rules that cost students money or deadlines: it retrieves evidence first, answers only from that evidence, and is honest when the evidence is missing or conflicting.

## Tools

- Python 3.14, Django 5.2 LTS, Django REST Framework, drf-spectacular (Swagger)
- SQLite with FTS5 full-text search
- Google Gemini API (through one swappable function)
- React 19 and Vite, Node.js 24 LTS
- Browser Web Speech API for voice typing (Chrome, Edge and Safari)
- Built with the Devpost Learn "Build With AI: Basics" Skill Pack (see `devpost/`)

## My approach

1. **Retrieve first.** The question is cleaned into search words and matched against stored document passages with SQLite FTS5.
2. **Two-layer honesty.** If retrieval finds no convincing evidence, the system answers "could not verify" without calling the AI at all. If evidence is found but does not answer the question, the model is told to abstain.
3. **Quote, don't paraphrase.** An answered response returns the complete cited paragraph verbatim, so the student gets the exact rule.
4. **Cite or drop.** Every source the model cites must be one of the retrieved passages; invented citations are removed.
5. **Conflicts are shown, not hidden.** If two documents disagree, both are shown side by side.
6. **Safe failures.** Provider or network errors give a friendly retry message and never expose keys or internal details.

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

## Deploy it

Deploy the backend and frontend separately, then point the frontend at the
backend. The frontend must **not** be built with `VITE_API_BASE_URL`
pointing at `localhost`, or the deployed page will show "Could not reach the
CampusHelp AI service".

**Backend (Django, gunicorn)**

Set these environment variables on the host:

| Variable | Example |
|---|---|
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | a long random value |
| `DJANGO_ALLOWED_HOSTS` | `campushelp-ai.onrender.com` |
| `AI_API_KEY` | your Gemini key |
| `FRONTEND_ORIGINS` | `https://campushelp-ai.vercel.app` (comma-separated; setting it locks CORS to those origins) |
| `FRONTEND_ORIGIN_REGEXES` | `^https://campushelp[a-z0-9-]*\.vercel\.app$` (optional, for Vercel preview URLs) |
| `CORS_ALLOW_ALL_ORIGINS` | optional override; production defaults to open only when `FRONTEND_ORIGINS` is empty |

Vercel gives every deployment a unique preview URL, but the production domain
(e.g. `campushelp-ai.vercel.app`) does not change. Use the production domain
in `FRONTEND_ORIGINS`, or add the preview regex above.

The Vercel deployment calls the API on its own origin: `frontend/vercel.json`
rewrites `/proxy-api/*` to the backend's `/api/*` on the stable backend domain.
Vercel reserves `/api` for serverless functions, so the frontend uses
`/proxy-api` as the public prefix. The frontend build therefore sets
`VITE_API_SAME_ORIGIN=true` and does not expose the backend URL to the browser.
This avoids CORS and works when a student's network can reach Vercel but not
the backend host directly. If you deploy the frontend somewhere without that
rewrite, set `VITE_API_BASE_URL` to the deployed backend origin instead.

Build/start commands (run from `backend/`):

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py ingest          # loads documents/ + metadata/documents.json
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

`python manage.py ingest` must run on the deployed machine, because the
SQLite database is not committed. If the host uses an ephemeral filesystem,
run it on every deploy (it is idempotent). Health check: `GET /api/health/`.

If the host deploys only `backend/`, either copy `documents/` and
`metadata/` into the deployment or point `DOCUMENTS_DIR` at their location.
The included `render.yaml` keeps Render rooted at the repository root so
`documents/` and `metadata/` are available; do not set Render's Root
Directory to `backend/` unless you move those folders too.

**Frontend (static build)**

Build normally:

```bash
cd frontend
npm run build
```

The committed `frontend/.env.production` makes the app call `/proxy-api` on
its own origin, and `frontend/vercel.json` proxies `/proxy-api/*` to
`https://campushelp-ai.onrender.com/api/*`. It also raises the timeout for
Render's free-tier cold starts. If the backend URL changes, update the rewrite
target in `frontend/vercel.json`. Alternatively edit `apiBaseUrl` in the
deployed `config.js` (copied from `frontend/public/config.js`) to bypass the
proxy without rebuilding.

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

Status on 26 October 2026: the API, search table, answer validation, token accounts, saved history and automated tests are in place; the documents and the full demo are in place also.

## Credits

- Document collection and ingestion: [Samson Kwizera]
- Search and AI answers: [Ezra Muhizi]
- Backend API and integration: Cedrick Niyibikora
- Student interface: [Person 4 name]
- Planning method: Devpost Learn Skill Pack

## Author

Cedrick Niyibikora, backend and integration lead and team leader. GitHub: [Cedrick40](https://github.com/Cedrick40)

Released under the MIT licence (see `LICENSE`).