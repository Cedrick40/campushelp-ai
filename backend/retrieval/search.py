
import re
from typing import Iterable


STOPWORDS = frozenset(
    """
    a about after again all also am an and any are as at be because been before
    being between both but by can could did do does doing down during each few
    for from further had has have having he her here hers herself him himself
    his how i if in into is it its itself just me may might more most my myself
    must no nor not of off on once only or other our ours ourselves out over own
    same she shall should so some such than that the their theirs them themselves
    then there these they this those through to too under until up very was we
    were what when where which while who whom why will with would you your yours
    yourself yourselves
    """.split()
)

MIN_SCORE = 0.3
MIN_COVERAGE = 0.33
DEFAULT_TOP_K = 8

INSUFFICIENT_EVIDENCE = "insufficient_evidence"
RETRIEVED = "retrieved"

TEMPORAL_HINTS = frozenset(
    {"when", "deadline", "date", "time", "period", "start", "end", "until"}
)
REGISTRATION_FORMS = frozenset(
    {"registration", "register", "registers", "registering", "registered"}
)
QUERY_NOISE = frozenset(
    """
    according available cut document documents explain explains find finish
    information know leave need needs off okay provide provided required say
    tell university
    """.split()
)

GENERAL_RULE_MARKERS = (
    "all students",
    "every student",
    "each student",
    "all candidates",
    "all learners",
)
STEMS = {
    "registration": "regist",
    "register": "regist",
    "registers": "regist",
    "registering": "regist",
    "registered": "regist",
}


def _stem(token: str) -> str:
    """Small prefix-preserving stem so "fees"/"fee" and "registering"/"registration" meet."""
    if token in STEMS:
        return STEMS[token]

    if token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    elif token.endswith("ed") and len(token) > 4:
        token = token[:-2]

    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        token = token[:-1]

    return token


STOPWORD_STEMS = frozenset(_stem(word) for word in STOPWORDS)
REGISTRATION_STEMS = frozenset(_stem(word) for word in REGISTRATION_FORMS)
QUERY_NOISE_STEMS = frozenset(_stem(word) for word in QUERY_NOISE)


def tokenize(text: str) -> set[str]:
    """Convert text into lowercase word tokens (single-character noise dropped)."""
    return {
        _stem(token)
        for token in re.findall(r"\b\w+\b", text.lower())
        if len(token) > 1
    }


def query_terms(question: str) -> set[str]:
    """Meaningful question terms: stopwords dropped, per spec."""
    tokens = tokenize(question)
    terms = tokens - STOPWORD_STEMS - QUERY_NOISE_STEMS

    # "When is registration?" otherwise matches only the word "registration",
    # so short section headings outrank the passage containing the deadline.
    if (tokens & REGISTRATION_STEMS) and (tokens & TEMPORAL_HINTS):
        terms.add("deadline")

    return terms


def _is_general_rule(text: str) -> bool:
    normalized = " ".join(str(text or "").split()).lower()
    return any(marker in normalized for marker in GENERAL_RULE_MARKERS)


def _is_heading(passage: dict) -> bool:
    """True for section/title stubs such as "Registration" or "3.1 Registration"."""
    text = " ".join(str(passage.get("text") or "").split())

    if not text:
        return True

    normalized = text.casefold()
    section = " ".join(str(passage.get("section") or "").split()).casefold()
    title = " ".join(str(passage.get("title") or "").split()).casefold()

    if normalized in {section, title}:
        return True

    without_section_number = re.sub(r"^\s*\d+(?:\.\d+)*\s*", "", text)
    return (
        len(without_section_number.split()) <= 12
        and not re.search(r"[.!?]", without_section_number)
    )


def retrieve(
    question: str,
    passages: list[dict],
    top_k: int = DEFAULT_TOP_K,
    min_score: float = MIN_SCORE,
) -> list[dict]:
    """
    Rank passages by keyword overlap and return them with a `score`.

    This is the offline / unit-test backend and the fallback when the
    database isn't available. When Person 1's ingest has written the
    corpus, `retrieve_from_db()` runs the spec's SQLite FTS5 path with the
    same contract. `source_id` plays the role of document id until the
    Passage model exists.

    Reference: `devpost/spec.md` §Retrieval.
    """
    if top_k <= 0 or not 0 <= min_score <= 1:
        return []

    terms = query_terms(question)

    if not terms:
        return []

    ranked = []

    for passage in passages:
        if not isinstance(passage, dict):
            continue

        text = passage.get("text", "")

        if not isinstance(text, str) or not text.strip() or _is_heading(passage):
            continue

        overlap = terms & tokenize(text)

        if overlap:
            score = len(overlap) / len(terms)

            if score >= min_score:
                ranked.append((score, _is_general_rule(text), passage))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)

    return [
        {**passage, "score": round(score, 4)}
        for score, _, passage in ranked[:top_k]
    ]


def coverage(question: str, retrieved: Iterable[dict]) -> float:
    """Share of meaningful question terms covered by the retrieved set."""
    terms = query_terms(question)

    if not terms:
        return 0.0

    covered: set[str] = set()

    for passage in retrieved:
        if isinstance(passage, dict) and isinstance(passage.get("text"), str):
            covered |= terms & tokenize(passage["text"])

    return len(covered) / len(terms)


# --- FTS5 backend (spec §Retrieval) ----------------------------------------
#
# Active once ingest writes the corpus. Falls back to `retrieve()` when the
# Django models/tables are not present, so this file is testable standalone.
#
# Expected columns (Person 3's models, see docs/requirements.md §7.1):
#   passage: id, text, section, page, source_id, document_id,
#            title, url, date, status
#   passage_fts: an FTS5 virtual table over passage.text keyed by rowid


PASSAGE_TABLE = "api_passage"
DOCUMENT_TABLE = "api_document"
FTS_TABLE = "api_passage_fts"

_FTS_COLUMNS = [
    "source_id", "document_id", "title", "url",
    "section", "page", "date", "status", "text",
]


def _fts_query(terms: set[str]) -> str:
    """AND-of-ORs so a shorthand term can match any full word (prefix)."""
    return " OR ".join(f'"{term}"*' for term in sorted(terms))


def retrieve_from_db(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = MIN_SCORE,
    min_coverage: float = MIN_COVERAGE,
) -> list[dict]:
    """
    Retrieve from the ingested corpus.

    SQLite uses the FTS5 `MATCH` path. Other databases (PostgreSQL in
    production) use the same ranking function over the Passage model, so
    accounts and history can live in a durable hosted database even though
    FTS5 is SQLite-only. Returns [] on any missing-DB condition.
    """
    from django.db import connection

    if connection.vendor != "sqlite":
        return _retrieve_from_models(
            question, top_k=top_k, min_score=min_score
        )

    return retrieve_from_connection(
        connection, question, top_k=top_k, min_score=min_score
    )


def _retrieve_from_models(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = MIN_SCORE,
) -> list[dict]:
    """Build passage records from the ORM and reuse the offline ranking."""
    from api.models import Passage

    passages = []
    rows = (
        Passage.objects.select_related("document")
        .order_by("document_id", "position")
        .iterator()
    )
    for passage in rows:
        document = passage.document
        passages.append(
            {
                "source_id": passage.source_id or str(passage.pk),
                "document_id": str(document.pk),
                "title": document.title,
                "url": document.source_url or None,
                "section": passage.section,
                "page": passage.page,
                "date": (
                    document.date_checked.isoformat()
                    if document.date_checked
                    else None
                ),
                "status": document.status,
                "text": passage.text,
            }
        )

    return retrieve(question, passages, top_k=top_k, min_score=min_score)


def _table_exists(cursor, name: str) -> bool:
    """Works with both Django (`%s`) and raw sqlite3 (`?`) placeholders."""
    marker = "?" if cursor.__class__.__module__.startswith("sqlite3") else "%s"

    cursor.execute(
        f"SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name = {marker}",
        [name],
    )
    return cursor.fetchone() is not None


def retrieve_from_connection(
    connection,
    question: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = MIN_SCORE,
) -> list[dict]:
    """
    FTS5 retrieval against an explicit DB-API connection.

    `retrieve_from_db` uses Django's connection; this variant exists so the
    FTS5 path can be unit-tested with a plain sqlite3 connection and reused
    outside Django.
    """
    terms = query_terms(question)

    if not terms:
        return []

    cursor = connection.cursor()

    try:
        if not _table_exists(cursor, FTS_TABLE) or not _table_exists(
            cursor, PASSAGE_TABLE
        ) or not _table_exists(cursor, DOCUMENT_TABLE):
            return []

        marker = (
            "?" if cursor.__class__.__module__.startswith("sqlite3") else "%s"
        )

        candidate_limit = max(top_k * 8, top_k + 10)

        cursor.execute(
            f"""
            SELECT p.source_id, p.document_id, d.title,
                   d.source_url AS url, p.section, p.page,
                   d.date_checked AS date, d.status, p.text,
                   bm25({FTS_TABLE}) AS rank
            FROM {FTS_TABLE}
            JOIN {PASSAGE_TABLE} AS p ON p.id = {FTS_TABLE}.rowid
            JOIN {DOCUMENT_TABLE} AS d ON d.id = p.document_id
            WHERE {FTS_TABLE} MATCH {marker}
            ORDER BY rank
            LIMIT {marker}
            """,
            [_fts_query(terms), candidate_limit],
        )
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
    finally:
        cursor.close()

    results = []

    for row in rows:
        record = dict(zip(columns, row))

        if _is_heading(record):
            continue

        text = record.get("text") or ""
        overlap = terms & tokenize(text)
        record["score"] = round(len(overlap) / len(terms), 4) if terms else 0.0
        record.pop("rank", None)
        results.append(record)

    results = [r for r in results if r["score"] >= min_score]
    results.sort(
        key=lambda item: (item["score"], _is_general_rule(item.get("text", ""))),
        reverse=True,
    )
    return results[:top_k]


def retrieve_evidence(
    question: str,
    passages: list[dict] | None = None,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = MIN_SCORE,
    min_coverage: float = MIN_COVERAGE,
) -> tuple[str, list[dict]]:
    """
    Layer 1 of the two-layer fallback (spec §Retrieval).

    Uses the FTS5 path when Person 1's corpus is in the database, otherwise
    the in-memory `passages` argument. Returns `(status, passages)`:
    - `insufficient_evidence` — no hits, too few question terms covered, or
      best score below `MIN_SCORE`. No model call happens after this.
    - `retrieved` — passages for `generate_answer(evidence, question)`.
    """
    retrieved = _search(question, passages, top_k, min_score)

    if not retrieved:
        return INSUFFICIENT_EVIDENCE, []

    if coverage(question, retrieved) < min_coverage:
        return INSUFFICIENT_EVIDENCE, []

    return RETRIEVED, retrieved


def _search(
    question: str,
    passages: list[dict] | None,
    top_k: int,
    min_score: float,
) -> list[dict]:
    if passages is None:
        try:
            return retrieve_from_db(question, top_k=top_k, min_score=min_score)
        except Exception:
            return []

    return retrieve(question, passages, top_k=top_k, min_score=min_score)


def retrieve_with_status(
    question: str,
    passages: list[dict],
    top_k: int = DEFAULT_TOP_K,
    min_score: float = MIN_SCORE,
    min_coverage: float = MIN_COVERAGE,
) -> tuple[str, list[dict]]:
    """Backwards-compatible wrapper around `retrieve_evidence`."""
    return retrieve_evidence(
        question,
        passages=passages,
        top_k=top_k,
        min_score=min_score,
        min_coverage=min_coverage,
    )

