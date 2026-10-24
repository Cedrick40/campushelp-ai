from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CorpusConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('corpus_type', models.CharField(choices=[('sample', 'sample'), ('official', 'official')], default='sample', max_length=20)),
                ('university', models.CharField(default='CampusHelp Demo', max_length=255)),
                ('last_checked', models.DateField(blank=True, null=True)),
                ('contact_office', models.CharField(blank=True, default='', max_length=255)),
                ('contact_source', models.URLField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('institution', models.CharField(blank=True, default='', max_length=255)),
                ('source_url', models.URLField(blank=True, default='')),
                ('publication_date', models.DateField(blank=True, null=True)),
                ('date_checked', models.DateField(blank=True, null=True)),
                ('status', models.CharField(default='unknown', max_length=50)),
                ('corpus_type', models.CharField(default='sample', max_length=20)),
                ('document_type', models.CharField(default='text', max_length=50)),
                ('section_hint', models.CharField(blank=True, default='', max_length=255)),
                ('file_path', models.CharField(blank=True, default='', max_length=500)),
                ('extraction_notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['title'],
            },
        ),
        migrations.CreateModel(
            name='Passage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_id', models.CharField(blank=True, default='', max_length=255, unique=True)),
                ('section', models.CharField(blank=True, default='', max_length=255)),
                ('page', models.IntegerField(blank=True, null=True)),
                ('position', models.IntegerField(default=0)),
                ('text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='passages', to='api.document')),
            ],
            options={
                'ordering': ['document_id', 'position'],
            },
        ),
    ]
