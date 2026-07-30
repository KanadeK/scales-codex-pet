from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scales_pet.provenance import verify_provenance


class ProvenanceTests(unittest.TestCase):
    def test_valid_hash_and_license_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            reference = root / "artwork/references/source.png"
            reference.parent.mkdir(parents=True)
            reference.write_bytes(b"reference bytes")
            digest = hashlib.sha256(reference.read_bytes()).hexdigest()
            manifest = reference.parent / "sources.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "attribution": "Example",
                        "sources": [
                            {
                                "path": "artwork/references/source.png",
                                "sha256": digest,
                                "page_url": "https://example.test/source",
                                "license": "CC-BY-3.0",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = verify_provenance(manifest)

        self.assertTrue(report["ok"], report)

    def test_hash_drift_fails_with_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            reference = root / "artwork/references/source.png"
            reference.parent.mkdir(parents=True)
            reference.write_bytes(b"changed")
            manifest = reference.parent / "sources.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "sources": [
                            {
                                "path": "artwork/references/source.png",
                                "sha256": "0" * 64,
                                "page_url": "https://example.test/source",
                                "license": "CC-BY-3.0",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = verify_provenance(manifest)

        self.assertFalse(report["ok"])
        self.assertEqual(report["errors"][0]["code"], "source-hash")


if __name__ == "__main__":
    unittest.main()
