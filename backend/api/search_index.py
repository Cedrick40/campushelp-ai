from django.db import connection


def rebuild_search_index():
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO api_passage_fts(api_passage_fts) VALUES('rebuild')")
