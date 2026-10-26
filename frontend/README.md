# CampusHelp AI — Frontend

The student-facing page: ask a question, get an answer with the document it
came from, or an honest notice when it cannot be verified.

Stack: React 19 + Vite, plain JavaScript, plain CSS, `fetch()`. Accounts and
saved history use Django token authentication: the token is kept in
`localStorage` and sent as `Authorization: Token <key>`.

Contract, look and feel, and component responsibilities are defined in
`../devpost/spec.md` and `../devpost/prd.md`.

## Setup

```bash
cd frontend
npm install
cp .env.example .env      # then set VITE_API_BASE_URL
npm run dev               # http://localhost:5173
```

Other commands: `npm run build` (production build into `dist/`), `npm run lint`,
`npm run preview` (serve the built output), `npm run verify` (see below).

## Checking that it works

```bash
cd frontend
npm run verify
```

`npm run verify` runs the linter, the production build, and then a set of
checks that exercise the real code in `src/`:

- **Contract checks** — `src/api.js` is loaded and asked for answers in mock
  mode, against a running backend, and against a backend that is not there.
  This covers all four response types, the empty-question and 500-character
  rules, relative source links and malformed responses.
- **Browser checks** — the page is opened in headless Chrome and driven the
  way a student would drive it: submit a question, click the examples, read
  the answer, break the input. Every state is checked, including that no
  uncaught error reaches the page.

Every check is reported as PASS, FAIL or SKIP, and the command exits non-zero
if anything failed. A check is only skipped when it cannot apply (no Chrome
installed, or the backend is not running) and the reason is printed.

The live browser checks run on the origin the backend allows
(`FRONTEND_ORIGIN` in `backend/.env`, by default `http://localhost:5173`),
because the browser blocks calls from any other origin. If a dev server is
already running on that port in mock mode, those checks are skipped with a
message rather than failing.

Browser checks need Chrome or Chromium. They are skipped when no browser is
found; everything else still runs. In a headless container where Chrome cannot
start, set `VERIFY_NO_BROWSER=1 npm run verify` to skip those checks explicitly.

## Configuration

All configuration is environment based, so nothing machine-specific is
committed. `.env` is gitignored; `.env.example` is the template.

| Variable | Meaning | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Backend origin, e.g. `http://localhost:8000` | `""` (same origin) |
| `VITE_API_SAME_ORIGIN` | `true` = call `/api` on the page's own origin and ignore `VITE_API_BASE_URL` | `false` |
| `VITE_USE_MOCK` | `true` = answer from the local mock, `false` = call the backend | `false` |
| `VITE_REQUEST_TIMEOUT_MS` | Request timeout in milliseconds | `30000` |

The backend address lives in `VITE_API_BASE_URL` rather than in the source so
that the same build can point at a laptop, a teammate's machine or a deployed
host without a code change.

Production builds set `VITE_API_SAME_ORIGIN=true`. Vercel rewrites
`/proxy-api/*` to the Django backend using `vercel.json`, so the browser only
talks to the Vercel origin. This avoids CORS and works even if the student's
network cannot reach the backend host directly. Vercel reserves `/api` for
serverless functions, so the public proxy prefix is `/proxy-api`:

```json
{
  "rewrites": [
    {
      "source": "/proxy-api/(.*)",
      "destination": "https://campushelp-ai.onrender.com/api/$1"
    }
  ]
}
```

The `(.*)` capture keeps trailing slashes, which Django's `/api/health/` and
`/api/ask/` routes require.

For deployments there is also a runtime file, `public/config.js`, copied to
`dist/config.js`. Editing `apiBaseUrl` there changes the backend address
without rebuilding:

```js
window.CAMPUSHELP_CONFIG = { apiBaseUrl: 'https://campushelp-api.onrender.com' }
```

A production build made with `VITE_API_BASE_URL=http://localhost:8000` cannot
work online: the browser on the student's machine tries its own localhost.
Set the deployed backend origin at build time or in `config.js`.

## Mock first, real API second

The interface was built against a mock before the backend existed, and the
mock is still available for working on the UI without the server running.

**1. Mock mode (no backend needed)**

```bash
# frontend/.env
VITE_USE_MOCK=true
```

`src/mockApi.js` answers with exactly the payload shapes the real API
returns, so every screen and state can be built and reviewed on its own. The
mock covers all four responses: answered, insufficient evidence, conflicting
sources, and a service failure. The footer shows "Mock data — the backend is
not connected." so mock content can never be mistaken for a real answer.

Mock mode only replaces the Q&A and banner endpoints. Register, log in,
logout and saved history always use the real backend, because they rely on
real accounts and server-side storage.

**3. Accounts and history**

Registration creates a Django user, hashes the password on the server, and
returns a token. Saved questions are stored in the `ChatEntry` table per
user, so history survives a refresh, a restart and another device. Logging
out deletes the token on the server and clears it locally; it also clears the
conversation on screen. Guests can ask questions but nothing is saved.

**2. Real API mode**

```bash
# frontend/.env
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://localhost:8000
```

Nothing else changes: `src/api.js` picks the transport, the components stay
the same. The backend must be running and must allow this origin —
`FRONTEND_ORIGIN=http://localhost:5173` in `backend/.env`.

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/ask/` | Ask a question, get an answer with sources |
| `GET /api/corpus/` | Banner data: corpus type, university, last checked |
| `GET /api/documents/<id>/file/` | Serves a sample document; used as the `url` of sample sources |
| `POST /api/auth/register/` | Create an account; returns `{ token, user }` |
| `POST /api/auth/login/` | Exchange email and password for a token |
| `POST /api/auth/logout/` | Revoke the caller's token |
| `GET /api/auth/me/` | The signed-in user; restores a session on load |
| `GET /api/history/` | The caller's saved answers, newest first |
| `POST /api/history/` | Save one question and its answer |
| `DELETE /api/history/` | Clear the caller's saved history |
| `GET /api/history/<id>/` | Read one saved answer |
| `DELETE /api/history/<id>/` | Delete one saved answer |

The auth and history endpoints require `Authorization: Token <key>`.
Unknown or revoked tokens return 401 and the client clears the saved token.

Request and response shapes are in `../devpost/spec.md` under
*API — `POST /api/ask/`*. `src/api.js` normalises every response into one
internal shape, so the components never have to deal with missing optional
fields (a source without a date, an excerpt or a link still renders).

## Layout

```
src/
├── App.jsx                 page layout, conversation, auth and history state
├── api.js                  fetch wrappers, token auth, history, normalisation
├── mockApi.js              mock Q&A backend used when VITE_USE_MOCK=true
├── format.js               date and history timestamp formatting
├── styles.css              all styling, no UI framework
└── components/
    ├── Banner.jsx          sample-data vs official-documents notice
    ├── QuestionBox.jsx     input, submit, examples, validation, loading
    ├── AnswerArea.jsx      answer | fallback | conflict | failure
    ├── ChatMessage.jsx     user bubble and assistant reply wrapper
    ├── Sidebar.jsx         saved history, open/delete/clear, account footer
    ├── AuthModal.jsx       log in / register with server errors and focus trap
    └── SourceCard.jsx      title, section, date, page, excerpt, link
```

## Behaviour notes

- Empty or whitespace-only questions are rejected before any request is sent.
- Questions are limited to 500 characters, checked on the client and again by
  the backend.
- Example questions fill the box and submit immediately; the third one is the
  question the documents do not cover, so the honest fallback is one click.
- Every state carries a written label ("Answer", "Not verified", "Sources
  disagree", "Request failed"), so the states never depend on colour alone.
- Source links that come back as paths (for example
  `/api/documents/12/file/`) get the backend origin prepended so they stay
  clickable.
- Requests time out after `VITE_REQUEST_TIMEOUT_MS` and turn into a retry
  message instead of hanging.
- A guest can ask questions; only a signed-in user's answers are saved. The
  sidebar lists saved answers newest first, and clicking one reopens it.
- The signed-in session is restored from `localStorage` on load. An invalid
  token is discarded, and the page falls back to guest mode without an error.
- Logging out revokes the token on the server, clears it locally, and clears
  the visible conversation while leaving the account's history intact for the
  next login.
- The auth dialog closes on Escape or a backdrop click, traps Tab focus, locks
  page scrolling while open, and shows the server's validation message.
