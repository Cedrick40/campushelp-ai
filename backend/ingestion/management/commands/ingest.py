from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ingestion.ingest import ingest_documents


class Command(BaseCommand):
    help = "Ingest the curated corpus metadata and source documents into the database."

    def handle(self, *args, **options):
        root_dir = Path(settings.BASE_DIR).parent
        metadata_path = root_dir / "metadata" / "documents.json"
        documents_dir = root_dir / "documents"

        try:
            summary = ingest_documents(documents_dir, metadata_path)
        except Exception as exc:  # pragma: no cover - surfaced to CLI users
            raise CommandError(f"Ingestion failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Ingested {summary['documents']} document(s) and {summary['passages']} passage(s)."
            )
        )
