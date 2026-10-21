from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE VIRTUAL TABLE passage_fts USING fts5(text, content='api_passage', content_rowid='id');",
            reverse_sql="DROP TABLE IF EXISTS passage_fts;",
        ),
    ]
