from django.db import migrations

# Keep the search table in step with api_passage automatically, so whoever
# writes passages (ingest, tests, the Django shell) never has to remember to
# rebuild the index.
STATEMENTS = [
    """
    CREATE TRIGGER api_passage_ai AFTER INSERT ON api_passage BEGIN
        INSERT INTO api_passage_fts(rowid, text) VALUES (new.id, new.text);
    END
    """,
    """
    CREATE TRIGGER api_passage_ad AFTER DELETE ON api_passage BEGIN
        INSERT INTO api_passage_fts(api_passage_fts, rowid, text) VALUES ('delete', old.id, old.text);
    END
    """,
    """
    CREATE TRIGGER api_passage_au AFTER UPDATE ON api_passage BEGIN
        INSERT INTO api_passage_fts(api_passage_fts, rowid, text) VALUES ('delete', old.id, old.text);
        INSERT INTO api_passage_fts(rowid, text) VALUES (new.id, new.text);
    END
    """,
    "INSERT INTO api_passage_fts(api_passage_fts) VALUES ('rebuild')",
]

REVERSE = [
    "DROP TRIGGER IF EXISTS api_passage_ai",
    "DROP TRIGGER IF EXISTS api_passage_ad",
    "DROP TRIGGER IF EXISTS api_passage_au",
]


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_passage_fts"),
    ]

    operations = [
        migrations.RunSQL(sql=STATEMENTS, reverse_sql=REVERSE),
    ]