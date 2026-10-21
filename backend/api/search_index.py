from django.db import connection


def rebuild_search_index():
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO passage_fts(passage_fts) VALUES('rebuild')")


def search_index(match_query, limit=10):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rowid, bm25(passage_fts) FROM passage_fts "
            "WHERE passage_fts MATCH %s ORDER BY bm25(passage_fts) LIMIT %s",
            [match_query, limit],
        )
        return cursor.fetchall()
