from django.db import migrations


def create_fts(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        return
    schema_editor.execute(
        "CREATE VIRTUAL TABLE api_passage_fts USING fts5(text, content='api_passage', content_rowid='id');"
    )


def remove_fts(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        return
    schema_editor.execute("DROP TABLE IF EXISTS api_passage_fts;")


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_fts, remove_fts),
    ]
