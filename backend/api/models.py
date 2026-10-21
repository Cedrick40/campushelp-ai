from django.db import models


class Document(models.Model):
    """One source file (a handbook, a calendar, a regulation...)."""

    class Status(models.TextChoices):
        CURRENT = "current", "Current"
        SUPERSEDED = "superseded", "Superseded"
        UNKNOWN = "unknown", "Unknown"

    class CorpusType(models.TextChoices):
        SAMPLE = "sample", "Sample data"
        OFFICIAL = "official", "Official documents"

    external_id = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=300)
    issuer = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    checked_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNKNOWN)
    corpus_type = models.CharField(max_length=10, choices=CorpusType.choices, default=CorpusType.SAMPLE)
    file_path = models.CharField(max_length=500)
    extraction_notes = models.TextField(blank=True)

    def __str__(self):
        return self.title


class Passage(models.Model):
    """A searchable piece of a document."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="passages")
    section = models.CharField(max_length=300, blank=True)
    page = models.PositiveIntegerField(null=True, blank=True)
    position = models.PositiveIntegerField()
    text = models.TextField()

    class Meta:
        ordering = ["document_id", "position"]

    def __str__(self):
        return f"{self.document.title} #{self.position}"


class CorpusConfig(models.Model):
    """Exactly one row: the banner data and the optional office line."""

    corpus_type = models.CharField(max_length=10, choices=Document.CorpusType.choices,
                                   default=Document.CorpusType.SAMPLE)
    university = models.CharField(max_length=200, default="Placeholder University")
    last_checked = models.DateField(null=True, blank=True)
    contact_office = models.CharField(max_length=200, blank=True)
    contact_source = models.CharField(max_length=300, blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
