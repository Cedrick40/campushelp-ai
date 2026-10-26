from django.conf import settings
from django.db import models


class Document(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    title = models.CharField(max_length=255)
    institution = models.CharField(max_length=255, blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    publication_date = models.DateField(null=True, blank=True)
    date_checked = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default="unknown")
    corpus_type = models.CharField(max_length=20, default="sample")
    document_type = models.CharField(max_length=50, default="text")
    section_hint = models.CharField(max_length=255, blank=True, default="")
    file_path = models.CharField(max_length=500, blank=True, default="")
    extraction_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Passage(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="passages")
    source_id = models.CharField(max_length=255, unique=True, blank=True, default="")
    section = models.CharField(max_length=255, blank=True, default="")
    page = models.IntegerField(null=True, blank=True)
    position = models.IntegerField(default=0)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_id", "position"]

    def __str__(self):
        return self.source_id or f"Passage {self.id}"


class CorpusConfig(models.Model):
    corpus_type = models.CharField(max_length=20, choices=[("sample", "sample"), ("official", "official")], default="sample")
    university = models.CharField(max_length=255, default="CampusHelp Demo")
    last_checked = models.DateField(null=True, blank=True)
    contact_office = models.CharField(max_length=255, blank=True, default="")
    contact_source = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.corpus_type} corpus for {self.university}"


class ChatEntry(models.Model):
    """One saved question and its answer, owned by a single user.

    History is stored server-side so it survives refreshes, restarts and
    devices. A guest's messages are never written here.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_entries",
    )
    question = models.CharField(max_length=500)
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question[:60]
