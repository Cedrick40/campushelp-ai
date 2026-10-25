from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DOCUMENTS_PATH = Path(__file__).resolve().parents[2] / "metadata" / "documents.json"
DEFAULT_DOCUMENTS_DIR = Path(__file__).resolve().parents[2] / "documents"


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a stable metadata dictionary for the ingestion pipeline."""
    if not isinstance(record, dict):
        raise TypeError("Each corpus record must be a dictionary.")

    return {
        "id": str(record.get("id") or record.get("source_id") or "doc-unknown"),
        "title": str(record.get("title") or "Untitled document"),
        "institution": record.get("institution") or record.get("issuer") or "",
        "source_url": record.get("source_url") or record.get("url") or "",
        "publication_date": record.get("publication_date") or record.get("date") or None,
        "date_checked": record.get("date_checked") or record.get("checked_date") or None,
        "status": str(record.get("status") or "unknown"),
        "corpus_type": str(record.get("corpus_type") or "sample"),
        "document_type": str(record.get("document_type") or "text"),
        "section_hint": record.get("section_hint") or record.get("section") or "",
        "local_path": record.get("local_path") or record.get("file_path") or None,
        "contact_line": record.get("contact_line") or None,
    }


def load_metadata(path: str | Path = DEFAULT_DOCUMENTS_PATH) -> list[dict[str, Any]]:
    """Read the curated metadata JSON file and return records in a consistent shape."""
    metadata_path = Path(path)
    if not metadata_path.exists():
        return []

    with metadata_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict):
        payload = payload.get("documents", payload.get("items", [payload]))

    if not isinstance(payload, list):
        raise TypeError("Metadata payload must be a list or a documents object.")

    return [normalize_record(item) for item in payload if isinstance(item, dict)]


def build_corpus_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize a batch of metadata records before ingestion."""
    return [normalize_record(record) for record in records]


def _resolve_local_path(document_id: str, documents_dir: str | Path) -> Path | None:
    directory = Path(documents_dir)
    if not directory.exists():
        return None

    candidates = [
        directory / f"{document_id}.txt",
        directory / f"{document_id}.md",
        directory / f"{document_id}.pdf",
        directory / f"{document_id}.html",
        directory / f"{document_id}.docx",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    for candidate in sorted(directory.iterdir()):
        if candidate.is_file() and document_id.lower() in candidate.stem.lower():
            return candidate

    return None


def extract_text(file_path: str | Path) -> str:
    """Extract text from a supported file type, with a clear error for unsupported inputs."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".html", ".htm"}:
        return path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".pdf":
        try:
            from pdfminer.high_level import extract_text as pdf_extract_text
        except ImportError as exc:  # pragma: no cover - optional dependency path
            raise ValueError("PDF extraction requires pdfminer.six to be installed.") from exc
        return pdf_extract_text(str(path))

    if suffix == ".docx":
        try:
            import docx
        except ImportError as exc:  # pragma: no cover - optional dependency path
            raise ValueError("DOCX extraction requires python-docx to be installed.") from exc
        document = docx.Document(str(path))
        return "\n\n".join(paragraph.text for paragraph in document.paragraphs)

    raise ValueError(f"Unsupported document type: {suffix or path.name}")


def split_passages(text: str) -> list[str]:
    """Split a document into passage-sized chunks with section boundaries preserved."""
    chunks = [part.strip() for part in re.split(r"\n\s*\n+", text) if part and part.strip()]
    if not chunks:
        return [text.strip()] if text and text.strip() else []
    return chunks


def ingest_documents(documents_dir: str | Path = DEFAULT_DOCUMENTS_DIR, metadata_path: str | Path = DEFAULT_DOCUMENTS_PATH):
    """Load the corpus metadata, extract text, and return the number of documents ingested."""
    from api.models import CorpusConfig, Document, Passage  # local import for Django safety

    records = load_metadata(metadata_path)
    if not records:
        CorpusConfig.objects.update_or_create(
            pk=1,
            defaults={
                "corpus_type": "sample",
                "university": "CampusHelp Demo",
                "last_checked": None,
                "contact_office": "",
                "contact_source": "",
            },
        )
        return {"documents": 0, "passages": 0, "message": "No metadata records were found."}

    directory = Path(documents_dir)
    created_passages = 0
    created_documents = 0

    for record in records:
        local_path = record.get("local_path")
        if local_path:
            candidate = Path(local_path)
            if not candidate.is_absolute():
                candidate = directory / candidate
        else:
            candidate = _resolve_local_path(record["id"], directory)
        if candidate is None or not candidate.exists():
            continue

        try:
            text = extract_text(candidate)
        except ValueError:
            raise

        document, _ = Document.objects.update_or_create(
            id=record["id"],
            defaults={
                "title": record["title"],
                "institution": record["institution"],
                "source_url": record["source_url"],
                "publication_date": record["publication_date"],
                "date_checked": record["date_checked"],
                "status": record["status"],
                "corpus_type": record["corpus_type"],
                "document_type": record["document_type"],
                "section_hint": record["section_hint"],
                "file_path": str(candidate),
                "extraction_notes": "",
            },
        )

        Passage.objects.filter(document=document).delete()
        chunks = split_passages(text)
        for position, chunk in enumerate(chunks):
            Passage.objects.create(
                document=document,
                section=record["section_hint"] or "",
                page=None,
                position=position,
                text=chunk,
                source_id=f"{document.id}-{position + 1}",
            )
            created_passages += 1
        created_documents += 1

    corpus_type = records[0].get("corpus_type", "sample")
    university_name = records[0].get("institution") or "CampusHelp Demo"
    last_checked = records[0].get("date_checked")
    contact_office = ""
    contact_source = ""
    if records[0].get("contact_line"):
        contact_line = records[0]["contact_line"]
        if isinstance(contact_line, dict):
            contact_office = str(contact_line.get("office") or "")
            contact_source = str(contact_line.get("source") or "")

    CorpusConfig.objects.update_or_create(
        pk=1,
        defaults={
            "corpus_type": corpus_type,
            "university": university_name,
            "last_checked": last_checked,
            "contact_office": contact_office,
            "contact_source": contact_source,
        },
    )

    return {"documents": created_documents, "passages": created_passages, "message": "Ingestion complete."}
