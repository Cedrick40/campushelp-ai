---
doc: prd
status: approved
---

# CampusHelp AI — Product Requirements

A one-page student assistant that answers university-information questions only from a curated set of documents, shows the source — excerpt included — or honestly says it could not verify. Source: `scope.md > The Unique Kernel`, `The Core Loop`, `What "Working" Looks Like`.

## The Core Journey

1. A student opens the single page and sees the banner (sample-data or official-documents notice), the title, and the question box with three clickable example questions.
2. They type a real question (or click an example) and press submit.
3. A loading state appears so waiting is distinguishable from the result.
4. The answer area fills with a short paragraph (≤3 sentences, direct answer first) plus one or more source cards — each showing document title, section, date, a 1–3 sentence quoted excerpt, and an "Open document" link (plus the page number when the document has one) — so they can verify without leaving the page.
5. The student opens a source to confirm, then asks the next question — the loop repeats on the same page.
6. If the question isn't covered, the same area shows the neutral notice "I could not verify this from the available documents" plus which office to contact (only when a curated, sourced office reference exists — never invented).
7. If two sources disagree, both cards appear side by side on wide screens (stacked on phones) with "These sources disagree."

Success = both demo beats work: the sourced deadline answer, then the honest refusal. Source: `scope.md > What "Working" Looks Like`.

## Screens and Layout

One page, one column, top to bottom:

1. **Banner (thin, top):** "Sample data, not official university documents" when using sample data; otherwise "Based on official documents from [university], last checked [date]." The backend provides this banner data: corpus type (sample or official), university name, and last-checked date.
2. **Title:** "CampusHelp AI" with the line "Ask a question about university rules and get an answer with its source."
3. **Question box + submit button.** Under it, three clickable example questions, at least one of which triggers the fallback.
4. **Answer area** (below the box) — holds answer, source cards, fallback notice, or conflict display.
5. **Footer:** "Unofficial student project, not affiliated with [university]."

No other screens. Source: `scope.md > The Core Loop` ("on one screen").

## Look and Feel

Calm, plain, trustworthy — like a clean reference page. Mostly white and light grey with one deep blue for the button, links, and focus outlines. Readable sans-serif at a comfortable size, generous spacing, small rounded corners, nothing decorative. Mobile-first: it must work well on a phone.

Explicitly not: an official university portal (no crest, no logo, no official-looking header) and not a generic AI chat app (no sparkle icons, no robot avatar, no chat bubbles, no gradients, no typing animation). Source: `scope.md > Inspiration & Identity`.

## Features and Behavior

### Asking a question
- Non-empty questions can be submitted; empty or whitespace-only input is rejected with a clear validation message before any request is sent.
- Loading state is visible and distinguishable from a completed response.
- Clicking an example question fills the box and submits it immediately.

### Answer with sources
- Answer is a short paragraph of at most three sentences, direct answer in the first sentence; bullets only when the source itself lists steps.
- The answer is built only from retrieved passages; it adds no unsupported dates, amounts, requirements, or policy details.
- Each source card always shows document title, section, date, a 1–3 sentence quoted excerpt from the document, and an "Open document" link; the page number is shown only when the document has one.
- "Open document": official documents open their original public URL in a new tab; sample documents open a file served by our backend.
- The excerpt lets the student verify the answer without leaving the page.
- Cards point to real sources in the knowledge base; no invented source names or links.
- Ambiguous or partially supported evidence is not presented as certain.

### Honest fallback (the demo's centerpiece)
- Questions the documents don't cover produce: "I could not verify this from the available documents."
- Where a curated, sourced office reference exists, the notice adds which office to contact; otherwise the message alone. Office contacts come only from sourced reference content — Person 1 will include an official contacts page in the corpus.
- Styled as a neutral notice, not an error — refusing is correct behaviour, not a failure.
- Never invents office names, contact details, or procedures.

### Conflicting sources
- When retrieved sources disagree, both cards are shown side by side on wide screens and stacked on phones, with the line "These sources disagree." — the system never silently picks one.
- For time-sensitive questions where currency can't be established, the answer says so.

### Error handling
- Empty questions → clear validation message.
- Unsupported or unreadable files → clear error (ingestion side).
- AI-provider or network failure, timeout → useful retry/failure message; no credentials, stack traces, or configuration details exposed.
- A failed request never corrupts stored documents or other records.

## States and Boundaries

- **First use** — page loads with example questions visible and an empty answer area; no onboarding, no accounts.
- **Loading** — visible indicator while waiting; distinguishable from both answer and error.
- **Empty input** — rejected with a message; no request sent.
- **Unsupported question** — neutral fallback notice (see above).
- **Conflict** — two cards (side by side on wide screens, stacked on phones) plus the disagreement line.
- **Service failure** — friendly failure message with a way to retry.
- **Banner state** — switches between the sample-data wording and the official-documents wording, driven by backend-provided banner data (corpus type, university name, last-checked date).
- **Persistence** — nothing persists between sessions; each visit starts fresh (session history is deferred).

## Product Decisions

- **Refusal is a neutral notice, not an error** — "refusing is correct behaviour," and it's the demo's "oh, that's cool" beat.
- **Show a quoted excerpt in every source card** — so a student can verify on the page instead of trusting a link.
- **Answer ≤3 sentences with the direct answer first** — plain reference-page tone, not chat prose.
- **Three clickable example questions, one triggering the fallback** — makes the refusal demoable in one click.
- **Mobile-first, no crest and no chat-app styling** — must look like neither an official portal nor a generic AI app.
- **Dual-state banner** — honest about whether the corpus is official or sample data, with a "last checked" date; banner data comes from the backend (corpus type, university name, last-checked date).
- **Side-by-side conflict display** — matches the requirements doc's rule against silently choosing between disagreeing sources (`docs/requirements.md` §7.3); side by side on wide screens, stacked on phones.
- **Example questions submit immediately** — clicking one fills the box and submits, so the fallback demo is one click.
- **Page number only when it exists** — cards always show title, section, date, excerpt, and link; the page field appears only for documents that have one.
- **Link targets by corpus type** — official documents open their original public URL in a new tab; sample documents open a backend-served file, so the source is always openable.
- **Office contacts only from sourced content** — Person 1 will include an official contacts page in the corpus; with no sourced reference, the fallback notice stands alone.

## What We're Building

The POC boundary from `scope.md > The POC Boundary`, sequenced by `scope.md > Minimum Demo Path`:

**Must work for the demo:** question submission with empty-input rejection and loading state (FR-01); retrieval before generation (FR-04); grounded answer with source cards including excerpt (FR-05, FR-06); honest fallback (FR-07); basic error handling (FR-08). Plus the screen, banner, footer, and look-and-feel above.

**Then, if time allows (still P0 for submission per `requirements.md` §14):** full source-record provenance fields (FR-02), extraction-failure edge handling (FR-03), the 15–30 question evaluation set (FR-09), cross-screen-size UX checks (FR-10).

**Deliverables:** README with setup/run/test instructions, public repo, license, demo video under three minutes, planning docs.

## Deferred From the POC

- Feedback (helpful/unhelpful) — FR-11, P1.
- Document-update procedure write-up — FR-12, P1, only if core is solid.
- Session conversation history — `scope.md > Later`.
- Persisted question history between visits.

## Possible Later Enhancements

Topic categories, usage metrics, a richer update procedure — the `scope.md > Later` list, unchanged.

## Non-Goals

From `scope.md > Explicitly Cut`: student records/registration/fee payment/grades; multi-university platform; mobile apps, voice, messaging integrations; training a model; perfect-accuracy claims. Also: no accounts or login (nothing in the MVP needs them).

## Open Questions

- **Target university and its exact name for the banner/footer** — Person 1's decision; placeholder wording works until then. Needed before the final demo, not before `4-spec`.

All other interview open questions are resolved and recorded under `Product Decisions`: example-question click behaviour (fills and submits), source-card page field (only when the document has one), banner data (backend-provided corpus type, university name, last-checked date), "Open document" targets (public URL in new tab for official, backend-served file for sample), conflict layout (side by side wide, stacked on phones), office contacts (sourced reference content only; Person 1 adds an official contacts page to the corpus).
