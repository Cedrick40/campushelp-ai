import os
import tempfile
import unittest

from ingestion.ingest import build_corpus_records, load_metadata


class IngestionMetadataTests(unittest.TestCase):
    def test_load_metadata_reads_document_records(self):
        records = load_metadata(os.path.join("..", "metadata", "documents.json"))
        self.assertTrue(records)
        self.assertEqual(records[0]["id"], "cuz-001")
        self.assertEqual(records[0]["corpus_type"], "official")

    def test_build_corpus_records_normalizes_metadata(self):
        records = load_metadata(os.path.join("..", "metadata", "documents.json"))
        normalized = build_corpus_records(records)
        self.assertEqual(len(normalized), len(records))
        self.assertEqual(normalized[0]["title"], "Student Payment and Registration Policy")
        self.assertEqual(normalized[0]["status"], "current")


if __name__ == "__main__":
    unittest.main()
