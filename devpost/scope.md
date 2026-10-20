---
doc: scope
status: approved
---

# CampusHelp AI

A student-facing assistant that answers university-information questions only from a curated set of official documents — showing the exact source — or honestly says it cannot verify.

## The Unique Kernel
Answers come only from retrieved passages, and every claim traces to a specific document, page and section a student can open. If the evidence is missing, weak or conflicting, the system says so instead of picking silently, and it flags when a document may be out of date. Without that, it's just a confident chatbot — and a wrong answer about a deadline or fee could cost a student real money or a missed exam.

## Who It's For
A student who needs one concrete fact — when exam registration closes, what a regulation says — and today either digs through handbooks and scattered pages or asks a general AI chatbot that answers confidently anyway.

Target university: **not decided yet — update this section when Person 1's information is ready.** The knowledge base will be roughly 5–10 public official documents (handbook, academic calendar, regulations). If enough official documents can't be obtained in time, the team uses a clearly labelled sample set and says on screen that it's sample data.

## The Core Loop
Open the page → type a real question ("When is the deadline to register for exams?") → get a short answer with a source card naming the exact document, section and page, with a link → open the source to verify → ask the next question. The loop includes its honest dead end: a question outside the corpus (e.g. "Can I get a refund on accommodation fees?") returns "I could not verify this from the available documents" plus which office to contact — never a guess.

## Inspiration & Identity
Plain-spoken and trustworthy. The memorable beat is the refusal, not flashiness: the system that won't invent things. Nothing on screen may look more official than it is; sample data is visibly labelled.

## Why This Matters to the Learner
In their words: learn "how to make an AI answer only from verified sources (retrieving evidence before generating)" and "how to lead a four-person team using one shared spec." The stakes are real too — students acting on a wrong deadline or fee.

## What "Working" Looks Like
On one screen: type "When is the deadline to register for exams?" and get a short answer with a source card showing the exact document, section and page, with a working link. Then type the unanswerable refund question and get the honest fallback naming a contact office instead of an invented policy. Both beats are the demo — the second one is the "oh, that's cool" moment.

## The POC Boundary
In: a simple student page; question input; ~5–10 official (or clearly labelled sample) documents with recorded provenance; text extraction; retrieval before generation; grounded answers with source cards; the honest fallback; empty-input and service-error states; a small evaluation set; README and demo video. This is the requirements doc's P0/MVP list, unchanged.

## Minimum Demo Path
**Must work for the two-beat demo:**
- Ask: submit a question, reject empty input, show a loading state (FR-01)
- Retrieve: find relevant passages before answering (FR-04)
- Grounded answer with source: short answer + source card with document, section, page, link (FR-05, FR-06)
- Honest fallback: "I could not verify this" + office to contact, no invented policy (FR-07)
- Basic error handling: clear messages for empty input and service failures, no leaked credentials or stack traces (FR-08)

**P0 items only if time allows after the demo path is solid:**
- Full source-record provenance fields beyond what the source card needs (FR-02)
- Extraction-failure edge handling beyond supported documents (FR-03)
- The full 15–30 question evaluation set (FR-09)
- UX polish and responsiveness across screen sizes (FR-10)

Note: the requirements doc marks all of these P0, and its Definition of Done (§14) expects them before submission — treat the second list as sequencing, not permanently deferred, if time reaches 23 October.

## Later
Feedback (helpful/not), session conversation history, document-update procedure, suggested questions — all P1 in the requirements doc, only if the core is solid.

## Explicitly Cut
- **Student records, registration, fee payment, grades** — a different product; the requirements doc puts it out of scope.
- **Multi-university platform** — one university or one labelled sample corpus for the demo.
- **Mobile apps, voice, messaging integrations** — the demo is a web page.
- **Training a model from scratch** — use an accessible AI provider's API.
- **"Always correct" claims** — a measured evaluation set instead of a promise.
