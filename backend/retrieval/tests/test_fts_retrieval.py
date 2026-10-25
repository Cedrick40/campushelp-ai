
"""
Proves the spec's SQLite FTS5 retrieval path with a real database.

Builds a throwaway SQLite file with the Passage + FTS5 schema Person 3's
models will create, then checks `retrieve_from_connection()` returns the
same evidence contract as the offline backend. Skipped if FTS5 is not
compiled into this Python's SQLite.
"""

import sqlite3
import unittest

from retrieval.search import (
    MIN_SCORE,
    PASSAGE_TABLE,
    DOCUMENT_TABLE,
    FTS_TABLE,
    retrieve,
    retrieve_from_connection,
)


PASSAGES = [
    {
        "id": 1,
        "source_id": "REG-001",
        "document_id": 1,
        "title": "Registration Policy",
        "url": "https://example.edu/reg",
        "section": "Registration",
        "page": 3,
        "date": "2026-01-10",
        "status": "current",
        "text": "Students must complete registration before the published deadline.",
    },
    {
        "id": 2,
        "source_id": "FEES-001",
        "document_id": 2,
        "title": "Fees Guide",
        "url": "https://example.edu/fees",
        "section": "Tuition",
        "page": 2,
        "date": "2026-01-10",
        "status": "current",
        "text": "Students should consult the approved fees schedule for tuition.",
    },
]


def fts5_available() -> bool:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        connection.close()


def build_db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        f"""
        CREATE TABLE {DOCUMENT_TABLE} (
            id TEXT PRIMARY KEY, title TEXT, source_url TEXT,
            date_checked TEXT, status TEXT
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE {PASSAGE_TABLE} (
            id INTEGER PRIMARY KEY, source_id TEXT, document_id TEXT,
            section TEXT, page INTEGER, text TEXT
        )
        """
    )
    connection.execute(
        f"CREATE VIRTUAL TABLE {FTS_TABLE} USING fts5(text)"
    )

    for passage in PASSAGES:
        connection.execute(
            f"""
            INSERT OR IGNORE INTO {DOCUMENT_TABLE}
            (id, title, source_url, date_checked, status)
            VALUES (?,?,?,?,?)
            """,
            (
                str(passage["document_id"]), passage["title"], passage["url"],
                passage["date"], passage["status"],
            ),
        )
        connection.execute(
            f"""
            INSERT INTO {PASSAGE_TABLE}
            (id, source_id, document_id, section, page, text)
            VALUES (?,?,?,?,?,?)
            """,
            (
                passage["id"], passage["source_id"],
                str(passage["document_id"]), passage["section"],
                passage["page"], passage["text"],
            ),
        )
        connection.execute(
            f"INSERT INTO {FTS_TABLE} (rowid, text) VALUES (?, ?)",
            (passage["id"], passage["text"]),
        )

    connection.commit()
    return connection


@unittest.skipUnless(fts5_available(), "SQLite FTS5 not available")
class Fts5RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.connection = build_db()

    def tearDown(self):
        self.connection.close()

    def test_returns_the_right_passage(self):
        results = retrieve_from_connection(
            self.connection,
            "When must students complete registration?",
        )
        self.assertTrue(results)
        self.assertEqual(results[0]["source_id"], "REG-001")

    def test_preserves_metadata_for_source_cards(self):
        results = retrieve_from_connection(
            self.connection,
            "When must students complete registration?",
        )
        top = results[0]
        self.assertEqual(top["title"], "Registration Policy")
        self.assertEqual(top["section"], "Registration")
        self.assertEqual(top["page"], 3)
        self.assertEqual(top["url"], "https://example.edu/reg")
        self.assertEqual(top["document_id"], "1")

    def test_every_result_carries_a_score(self):
        results = retrieve_from_connection(
            self.connection, "students registration fees"
        )
        self.assertTrue(results)
        for passage in results:
            self.assertIn("score", passage)
            self.assertGreaterEqual(passage["score"], MIN_SCORE)

    def test_no_hits_returns_empty(self):
        results = retrieve_from_connection(self.connection, "xyzqv blorpt")
        self.assertEqual(results, [])

    def test_matches_offline_backend_ranking(self):
        question = "students registration deadline"
        db_ids = [
            p["source_id"]
            for p in retrieve_from_connection(self.connection, question)
        ]
        offline_ids = [
            p["source_id"] for p in retrieve(question, PASSAGES)
        ]
        self.assertEqual(db_ids, offline_ids)

    def test_missing_fts_table_returns_empty(self):
        bare = sqlite3.connect(":memory:")
        try:
            self.assertEqual(
                retrieve_from_connection(bare, "registration"), []
            )
        finally:
            bare.close()


if __name__ == "__main__":
    unittest.main()
