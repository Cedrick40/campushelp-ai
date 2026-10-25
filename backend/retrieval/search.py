
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
DEFAULT_TOP_K = 5

INSUFFICIENT_EVIDENCE = "insufficient_evidence"
RETRIEVED = "retrieved"


def tokenize(text: str) -> set[str]:
    """Convert text into lowercase word tokens (single-character noise dropped)."""
    return {
        token
        for token in re.findall(r"\b\w+\b", text.lower())
        if len(token) > 1
    }


def query_terms(question: str) -> set[str]:
    """Meaningful question terms: stopwords dropped, per spec."""
    return tokenize(question) - STOPWORDS


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

        if not isinstance(text, str) or not text.strip():
            continue

        overlap = terms & tokenize(text)

        if overlap:
            score = len(overlap) / len(terms)

            if score >= min_score:
                ranked.append((score, passage))

    ranked.sort(key=lambda item: item[0], reverse=True)

    return [
        {**passage, "score": round(score, 4)}
        for score, passage in ranked[:top_k]
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
    Spec's SQLite FTS5 `MATCH` retrieval via Django's connection. Returns
    [] on any missing-DB condition so callers can fall back cleanly.
    """
    from django.db import connection

    return retrieve_from_connection(
        connection, question, top_k=top_k, min_score=min_score
    )


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
            [_fts_query(terms), top_k],
        )
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
    finally:
        cursor.close()

    results = []

    for row in rows:
        record = dict(zip(columns, row))
        text = record.get("text") or ""
        overlap = terms & tokenize(text)
        record["score"] = round(len(overlap) / len(terms), 4) if terms else 0.0
        record.pop("rank", None)
        results.append(record)

    results = [r for r in results if r["score"] >= min_score]
    results.sort(key=lambda item: item["score"], reverse=True)
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

