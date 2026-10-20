# CampusHelp AI --- Project Requirements

**Project:** CampusHelp AI\
**Hackathon:** Build With AI: Basics\
**Document:** Requirements, delivery plan, and acceptance criteria\
**Team size:** 4 people\
**Planning date:** 12 October 2026\
**Submission deadline:** 26 October 2026, 5:00 p.m. EDT (11:00 p.m.
Zambia time)\
**Status:** Draft for team review

------------------------------------------------------------------------

## 1. Purpose of this document

This document defines what CampusHelp AI must do, what the team must
deliver, the steps required to complete the project, and how we will
decide whether each part is finished.

It is intentionally **technology- and programming-language-neutral**.
Team members use different tools and languages, so the project
requirements describe behaviour, interfaces, data, and outcomes rather
than prescribing one implementation stack.

This is the shared agreement for the whole team. After reviewing it, the
team can decide how to divide ownership based on skills and
availability.

## 2. Product summary

CampusHelp AI is a student-facing university information assistant. A
student asks a question in ordinary language. The system searches a
collection of approved university information, generates an answer based
on the relevant evidence, and shows the source so the student can verify
it.

If reliable evidence is not available, CampusHelp AI must clearly say
that it cannot verify the answer instead of inventing university rules.

### Product promise

> Get a clear answer to a university-information question, see the
> official source behind it, or be told honestly when the available
> information is insufficient.

### Problem to address

University information may be spread across handbooks, academic
calendars, regulations, notices, websites, and service pages. Students
may struggle to find the right information quickly. A general-purpose AI
chatbot may also produce confident but unsupported answers about
university policy.

CampusHelp AI will make a defined collection of university information
easier to search and understand while preserving source traceability.

### Intended users

-   **Primary user:** A student seeking university information.
-   **Information source/maintainer:** The team initially curates the
    documents used in the demonstration. A full staff
    document-management portal is outside the initial scope.
-   **Institution:** The university whose public or explicitly
    authorized information is represented in the knowledge base.

### Target institution

**Decision pending:** The team must choose one target university or use
a clearly labelled demonstration dataset if suitable official
information cannot be obtained in time. The product must not present
invented rules as official university policy.

## 3. Goals and success criteria

The initial version is successful when a user can ask a question, the
system can retrieve relevant evidence, and the user receives a useful
answer with verifiable source information---or an honest fallback if
evidence is inadequate.

### Must achieve

1.  Deliver one complete end-to-end question-and-answer workflow.
2.  Use a defined collection of university documents with recorded
    provenance.
3.  Retrieve relevant passages before generating an answer.
4.  Show source references for answers, with page or section details
    when available.
5.  Avoid making up answers when the knowledge base cannot support them.
6.  Handle common user errors and service failures with understandable
    messages.
7.  Be runnable by another developer using the repository instructions.
8.  Meet the official hackathon's Skill Pack, planning-file, repository,
    license, and demo requirements.

### Not a success criterion

-   Building a complete university management system.
-   Supporting every university from the first release.
-   Having the largest feature list.
-   Using the most complicated AI architecture.
-   Claiming perfect accuracy without evaluation.

## 4. Scope

### 4.1 In scope for the minimum viable product (MVP)

-   A simple student-facing interface.
-   A way to submit a question.
-   A curated knowledge base of university information.
-   Text extraction from supported documents.
-   Storage of document metadata and extracted passages.
-   Retrieval of relevant passages for a question.
-   Answer generation grounded in retrieved evidence.
-   Source citations or references shown with the answer.
-   A clear "I could not verify this" response when evidence is missing
    or insufficient.
-   Loading, empty-input, unsupported-document, and service-error
    handling.
-   A small, repeatable set of evaluation questions and expected
    sources.
-   Setup instructions, configuration documentation, and a working
    demonstration.

### 4.2 Could add if the MVP is reliable

-   Suggested questions or topic categories.
-   Feedback on whether an answer was helpful or incorrect.
-   A basic conversation history for the current session.
-   A small document-update procedure.
-   Basic usage metrics that do not expose unnecessary personal
    information.

These features must not delay the core workflow or weaken testing.

### 4.3 Out of scope for the hackathon MVP

-   A complete student information system.
-   Student registration, fee payment, grades, or official account
    integrations.
-   Access to private student records.
-   Automatic changes to university records.
-   A full multi-university tenancy and administration platform.
-   A complex staff portal with many roles.
-   Voice calling, mobile applications, and messaging-platform
    integrations.
-   Training a foundation model from scratch.
-   A promise that every answer is always correct.
-   Unverified claims presented as official policy.

## 5. Functional requirements

Priority definitions:

-   **P0 --- Must:** Required for the core demonstration.
-   **P1 --- Should:** Valuable if the P0 workflow is stable.
-   **P2 --- Could:** Consider only if time remains.

### FR-01 --- Ask a question (P0)

The user must be able to enter and submit a university-information
question.

**Acceptance criteria** - A non-empty question can be submitted. - Empty
or whitespace-only input is rejected with a clear message. - The user
can distinguish a loading state from a completed response. - The
interface displays either a useful answer or a clear error/fallback.

### FR-02 --- Maintain a curated knowledge base (P0)

The system must use a defined collection of university documents or
official information pages.

**Acceptance criteria** - Each source has a recorded title and origin. -
Where available, the source records issuing institution/department,
publication or update date, and source URL. - The team records whether a
document's current status has been checked. - Sample or fictional
information is explicitly labelled as such. - Only documents appropriate
for the public demonstration are included.

### FR-03 --- Extract document text (P0)

The system must turn supported documents into text that can be searched.

**Acceptance criteria** - The supported file types are documented. -
Extraction failures are handled visibly and do not silently create a
false impression that the document was processed. - Source metadata and
page/section information are preserved when available. - The team
manually checks extraction quality on representative documents.

### FR-04 --- Retrieve relevant evidence (P0)

Before generating an answer, the system must search the knowledge base
for passages relevant to the question.

**Acceptance criteria** - A test question about one topic retrieves
relevant passages for that topic. - Retrieved passages retain references
to their original source. - If no sufficiently relevant evidence is
found, the system follows the unsupported-question policy. - Retrieval
behaviour can be tested separately from answer generation.

### FR-05 --- Generate an evidence-grounded answer (P0)

The system must generate an understandable answer based on retrieved
evidence.

**Acceptance criteria** - The answer is based on the evidence supplied
to the model. - The answer does not knowingly add unsupported dates,
amounts, requirements, or policy details. - The response uses clear
language and avoids unnecessary verbosity. - Contradictory or ambiguous
evidence is not silently treated as certain.

### FR-06 --- Show source references (P0)

The user must be able to identify the source behind an answer.

**Acceptance criteria** - An answer's references point to real sources
in the knowledge base. - The interface shows a useful source title and a
link where available. - Page, heading, or section details are displayed
when available. - The system does not display invented source names or
references. - A citation is not treated as proof of correctness unless
its passage actually supports the associated claim.

### FR-07 --- Handle unsupported questions (P0)

The system must not invent an answer when the evidence is missing or
insufficient.

**Acceptance criteria** - Questions outside the knowledge base produce
an honest fallback. - The fallback makes clear that the information
could not be verified from available sources. - Where appropriate and
known, the user is directed to an official source or relevant office. -
The fallback does not invent office names, contact details, or
university procedures.

### FR-08 --- Handle errors safely (P0)

The system must handle predictable errors.

**Acceptance criteria** - Empty questions receive a clear validation
message. - Unsupported or unreadable files receive a clear error. -
AI-provider or network failures do not expose credentials, stack traces,
or sensitive configuration. - Timeouts and failed requests produce a
useful retry or failure message. - One failed request does not corrupt
stored documents or other records.

### FR-09 --- Record evaluation examples (P0)

The team must create a small evaluation set of realistic questions and
expected supporting sources.

**Acceptance criteria** - Each evaluation question has an expected
source or is deliberately marked as unanswerable from the available
documents. - The team tests relevant, ambiguous, unsupported, and
out-of-scope questions. - Failures are recorded and corrected where time
permits. - The final demo uses questions that the system has actually
been tested against.

### FR-10 --- Provide a usable student experience (P0)

The interface must make the main workflow understandable.

**Acceptance criteria** - A first-time user can tell where to enter a
question. - The answer, uncertainty message, and sources are visually
distinguishable. - Loading and failure states are visible. - Text is
readable on common desktop and mobile-sized screens. - The interface
does not imply that the assistant is an official decision-maker.

### FR-11 --- Collect answer feedback (P1)

The user may mark an answer as helpful or unhelpful and optionally
describe a problem.

**Acceptance criteria** - Feedback is associated with the relevant
answer or request. - Feedback does not require unnecessary personal
information. - Feedback submission failures do not break question
answering.

### FR-12 --- Support a basic document-update process (P1)

The team should document how the curated information can be refreshed.

**Acceptance criteria** - The update procedure is described in the
README or supporting documentation. - Replacing a document does not
silently leave stale passages presented as current. - The team can
identify the source and status of each included document.

## 6. Non-functional requirements

### NFR-01 --- Trustworthiness

The system must prefer an honest uncertainty response over an
unsupported policy answer.

### NFR-02 --- Traceability

Answers must retain links to the evidence used to generate them so
failures can be investigated.

### NFR-03 --- Security

-   Secrets and API keys must be stored in environment configuration or
    an equivalent secret-management mechanism.
-   Secrets must never be committed to the public repository.
-   Any administrative or document-modification action must be
    restricted appropriately.
-   Public endpoints must validate input and handle unexpected requests
    safely.

### NFR-04 --- Privacy

-   Do not collect student IDs, passwords, grades, financial details, or
    other personal information unless genuinely required; the MVP does
    not require them.
-   Do not put private student records into the demo knowledge base.
-   Document any third-party AI processing that affects the information
    users submit.
-   Avoid logging full user content unless needed for testing and
    explicitly handled appropriately.

### NFR-05 --- Reliability and error handling

Common errors must produce controlled responses. The application must
not rely on every external API call succeeding.

### NFR-06 --- Maintainability

Components should have clear responsibilities and documented interfaces.
The implementation may use different languages and frameworks across
team members, provided the agreed interfaces work together.

### NFR-07 --- Performance

The system should respond within a reasonable wait for a small
demonstration knowledge base. The team must measure actual response
times rather than claim a speed target it has not tested.

### NFR-08 --- Accessibility and usability

Use readable contrast, clear labels, keyboard-operable controls, and
understandable error messages. Avoid relying on colour alone to
communicate status.

### NFR-09 --- Reproducibility

A new developer must be able to follow the documented setup process,
configure required services, start the project, and test the main
workflow.

### NFR-10 --- Legal and source integrity

Respect document copyright, site terms, and third-party service terms.
Prefer public official sources or documents the team is authorized to
use. Clearly identify sample data and do not imply institutional
endorsement without permission.

## 7. Data and answer rules

### 7.1 Source record

For each document, preserve as many of these fields as are available:

-   Unique document identifier.
-   Title.
-   Issuing institution or department.
-   Source URL or acquisition origin.
-   Publication/effective date.
-   Date checked by the team.
-   Status, such as current, superseded, or unknown.
-   Extracted text and page/section information.
-   Notes about extraction quality.

### 7.2 Evidence policy

1.  Search the approved knowledge base.
2.  Retrieve relevant passages.
3.  Generate an answer using those passages.
4.  Return references that correspond to the actual retrieved sources.
5.  Check the response structure and source identifiers before returning
    it.
6.  Abstain when the evidence is insufficient, contradictory, or not
    current enough for the question.
7.  Never fabricate official policies, deadlines, fees, contacts, or
    citations.

A language model's confidence is not evidence. A source reference must
be relevant to the claim it supports.

### 7.3 Current and conflicting information

If two documents conflict, the system should not silently choose one
unless an explicit and defensible precedence rule exists. It should
explain that the available sources conflict or ask the user to verify
the information with the relevant official office.

For time-sensitive questions, the source's effective date and current
status matter. If currency cannot be established, the system should say
so.

## 8. Suggested logical components

This section describes responsibilities, not mandatory technologies.

1.  **User interface:** Accept questions and display answers, source
    references, loading states, and errors.
2.  **Question/API interface:** Validate requests and return a
    consistent response format.
3.  **Document ingestion:** Extract text and metadata from approved
    sources.
4.  **Knowledge store:** Preserve documents, passages, and source
    metadata.
5.  **Retrieval service:** Find and rank passages relevant to the user's
    question.
6.  **Answer generation:** Produce an answer using retrieved evidence
    and explicit uncertainty rules.
7.  **Response validation:** Ensure returned references are valid and
    the response follows the expected structure.
8.  **Evaluation and logging:** Support repeatable tests and safe
    debugging without exposing secrets or unnecessary personal
    information.

The team may combine these components within one application or
distribute them across services. Keep the architecture as simple as
possible for the deadline.

## 9. Interface contract between components

Because team members use different technologies, agree on the interface
before implementing separate parts.

### Example question request

``` json
{
  "question": "What documents are required for registration?"
}
```

### Example successful response

``` json
{
  "status": "answered",
  "answer": "The required documents are listed in the registration guidance.",
  "sources": [
    {
      "title": "Registration Guidance",
      "url": "https://example.edu/registration",
      "section": "Required documents",
      "page": 2
    }
  ],
  "message": null
}
```

### Example insufficient-evidence response

``` json
{
  "status": "insufficient_evidence",
  "answer": null,
  "sources": [],
  "message": "I could not verify this from the university information available to me."
}
```

These are illustrative contracts. The team must finalize field names,
status values, error format, source fields, and any session identifiers
before parallel integration. Example URLs and policy text are
placeholders, not real university information.

## 10. Testing and quality plan

Testing must cover the full system and the most important failure cases,
not just whether the happy path works.

### Test categories

-   **Input validation:** Empty, whitespace-only, unusually long, and
    malformed requests.
-   **Document processing:** Valid files, unsupported formats,
    scanned/image-only files if not supported, and extraction failures.
-   **Retrieval:** Relevant questions, similar wording, ambiguous
    questions, and topics absent from the corpus.
-   **Grounding:** Answers that are fully supported, partially
    supported, and unsupported.
-   **Citations:** Correct source, relevant passage, valid URL, correct
    page/section when available.
-   **Conflicting sources:** Two documents with inconsistent
    requirements or dates.
-   **Service failures:** AI provider timeout, rate limit, invalid
    configuration, and network failure.
-   **Security and privacy:** No exposed API keys, no unnecessary
    personal data, and no unauthorized document modifications.
-   **Integration:** The interface can submit a question and render both
    an answer and its sources.
-   **Reproducibility:** Another team member can run the project from
    the documented setup instructions.

### Minimum evaluation set

Aim for 15--30 realistic questions if the source material allows.
Include:

-   Answerable questions from different topics.
-   Questions that require finding a date or specific requirement.
-   Questions that use wording different from the source document.
-   Questions with no supporting source.
-   Ambiguous questions.
-   Questions involving outdated or conflicting information.

For each test, record the question, expected outcome, expected source,
actual result, and whether it passed. Do not claim an accuracy
percentage unless it has been measured against a defined evaluation set.

## 11. Required project and hackathon deliverables

The team must verify the current official rules and submission form
before submitting. Based on the published Build With AI: Basics
requirements, prepare the following:

-   [ ] A new project created during the eligible submission period.
-   [ ] Required Devpost Learn Skill Pack installed and used.
-   [ ] `scope.md` generated through the required workflow.
-   [ ] `prd.md` generated through the required workflow.
-   [ ] `spec.md` generated through the required workflow.
-   [ ] Working end-to-end proof of concept.
-   [ ] Public source-code repository.
-   [ ] Open-source license in the repository.
-   [ ] README with setup, configuration, run, test, and demo
    instructions.
-   [ ] Clear project description explaining the problem, users,
    solution, and impact.
-   [ ] Public demo video under three minutes, hosted on an accepted
    platform.
-   [ ] Required screenshots or other submission materials.
-   [ ] All required submission fields completed before the deadline.
-   [ ] Final check that the repository and demo links are accessible.
-   [ ] No secrets, private student records, or unauthorized documents
    in public materials.

The official rules take precedence over this checklist if they change or
contain more specific requirements.

## 12. Project steps and timeline

**Planning date: 12 October 2026. Deadline: 26 October 2026 at 5:00 p.m.
EDT (11:00 p.m. Zambia time).** This plan is intentionally compressed.
The team should aim to submit well before the final hour.

### Phase 1 --- Confirm the project and rules (12 October)

-   Read the official rules together.
-   Confirm team eligibility and the submission account/representative.
-   Choose the target university or decide on a clearly labelled sample
    corpus.
-   Confirm that the team can access suitable official documents.
-   Confirm available AI service access, cost limits, and account
    ownership.
-   Create the new project repository and agree on a single shared
    requirements document.
-   Install and run the required Skill Pack workflow.
-   Generate and review `scope.md`, `prd.md`, and `spec.md`.

**Exit condition:** The team agrees on the exact MVP, has usable source
material, has a tested path to an AI API, and has the required planning
artifacts.

### Phase 2 --- Collect and validate knowledge sources (13 October)

-   Collect a small, relevant set of official documents.
-   Record source URLs, titles, dates, and status.
-   Check whether the text is extractable.
-   Create the initial evaluation questions and expected sources.
-   Remove sensitive or unauthorized information.

**Exit condition:** The team has a usable knowledge corpus and can
identify the source expected for each test question.

### Phase 3 --- Agree on contracts and architecture (13 October)

-   Define the request and response formats.
-   Define source-reference fields and error formats.
-   Decide where the knowledge base is stored.
-   Decide how document processing and retrieval will be invoked.
-   Define how the frontend calls the backend.
-   Create a minimal integration example before building all features
    separately.

**Exit condition:** All team members understand the interfaces and can
build compatible components independently.

### Phase 4 --- Build the vertical slice (14--17 October)

-   Implement the question submission path.
-   Process and store documents and passages.
-   Retrieve relevant evidence.
-   Generate an answer from the evidence.
-   Return valid source references.
-   Implement the insufficient-evidence response.
-   Connect the user interface to the working path.

**Exit condition:** At least one real question travels from the
interface through retrieval and answer generation and back with a
verifiable source.

### Phase 5 --- Complete and integrate the MVP (18--20 October)

-   Complete required error states.
-   Integrate all components.
-   Verify the public source references.
-   Add a small amount of usability polish.
-   Ensure the system does not expose secrets or sensitive information.

**Exit condition:** The core requirements work together in one runnable
version.

### Phase 6 --- Evaluate and fix (21--22 October)

-   Run the evaluation set.
-   Test unsupported and ambiguous questions.
-   Test citation correctness and source freshness.
-   Test AI service failures and malformed inputs.
-   Fix high-impact issues first.
-   Record known limitations honestly.

**Exit condition:** The core demonstration is repeatable and the team
understands its remaining failure modes.

### Phase 7 --- Documentation and release candidate (23 October)

-   Complete the README and configuration instructions.
-   Add the license.
-   Confirm the planning documents are in the repository.
-   Verify the clean setup procedure.
-   Prepare screenshots and a concise project description.
-   Create a release candidate and stop adding non-essential features.

**Exit condition:** A team member who did not implement the main
workflow can run it using the documentation.

### Phase 8 --- Demo and submission checks (24--25 October)

-   Record a demo shorter than three minutes.
-   Show a successful answer with its source.
-   Show an unsupported question receiving an honest fallback.
-   Explain the real user problem and what the team built.
-   Verify repository/video links and every required submission field.
-   Rehearse the demo and keep a backup recording.

**Exit condition:** The complete submission is ready and verified before
deadline day.

### Phase 9 --- Final submission buffer (26 October)

-   Make only necessary fixes.
-   Verify all links and access permissions.
-   Submit before 5:00 p.m. EDT / 11:00 p.m. Zambia time.
-   Confirm the submission was received.

**Rule:** Do not plan essential development for the final hours.

## 13. Main risks and responses

  -----------------------------------------------------------------------
  Risk                                Response
  ----------------------------------- -----------------------------------
  Target university has too few       Decide quickly; use a clearly
  accessible documents                labelled sample corpus if needed.

  Documents are outdated or           Track dates/status and abstain when
  contradictory                       information cannot be reconciled.

  AI API access or cost becomes a     Test access early, set a budget,
  blocker                             and keep the provider integration
                                      replaceable.

  Answers sound convincing but are    Use source-grounded prompts,
  wrong                               citation validation, evaluation
                                      questions, and abstention.

  Different technologies do not       Finalize the API contract early and
  integrate                           integrate a small vertical slice
                                      before expanding.

  The team builds too many features   Protect the P0 scope; defer P1/P2
                                      work until the core passes tests.

  Public repository leaks secrets or  Use environment configuration,
  private data                        review the repository, and remove
                                      sensitive content before
                                      publishing.

  Deployment takes too long           Keep a reproducible local
                                      demonstration and choose the
                                      simplest viable deployment path.

  Demo fails or exceeds three minutes Rehearse, use a backup recording,
                                      and show only the strongest tested
                                      workflow.

  Required hackathon steps are missed Use the official rules and Skill
                                      Pack checklist as release gates.
  -----------------------------------------------------------------------

## 14. Definition of done

CampusHelp AI is ready for submission when all of the following are
true:

-   [ ] A user can submit a question through the interface.
-   [ ] The system retrieves relevant passages from the approved
    knowledge base.
-   [ ] A supported question receives an answer that matches the
    evidence.
-   [ ] The answer shows valid and relevant source references.
-   [ ] An unsupported question receives an honest fallback.
-   [ ] Empty input and common service failures are handled clearly.
-   [ ] The core evaluation set has been run and failures recorded.
-   [ ] The project can be run using the documented instructions.
-   [ ] The repository contains the required planning documents and an
    open-source license.
-   [ ] The public repository contains no secrets or
    unauthorized/private data.
-   [ ] The demo is public, under three minutes, and shows the real
    working system.
-   [ ] All official hackathon requirements and submission fields have
    been checked.

## 15. Decisions still to be made by the team

These are deliberate open questions; they should be resolved early
rather than silently assumed.

1.  Which university or clearly labelled sample corpus will be used?
2.  Which official documents are available and current?
3.  Which AI provider can the team access within its budget and terms?
4.  What is the final request/response contract between the interface
    and backend?
5.  What deployment option is realistic for the team's time and
    resources?
6.  Who will own each project area? **Team division is intentionally not
    assigned in this document.**
7.  Who will act as the submission representative?
8.  What project name, repository name, and public demo URL will be
    used?

## 16. Team agreement

Before implementation begins, all four team members should review this
document and agree that:

-   The MVP is small enough to complete before the deadline.
-   The source of university information will be transparent.
-   The system will not invent policy answers to appear intelligent.
-   Integration and testing are part of the work, not optional final
    tasks.
-   Any scope changes must be agreed by the team and must not jeopardize
    the P0 requirements or submission.

**End of requirements document.**
