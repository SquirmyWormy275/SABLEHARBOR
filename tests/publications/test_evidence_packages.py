"""Source integrity and identity checks for human evidence discovery."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "evidence_packages", ROOT / "tools/documents/evidence_packages.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EvidencePackageTests(unittest.TestCase):
    def test_integrity_identity_and_path_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "docs/finance/evidence/customer"
            package.mkdir(parents=True)
            source = package / "rows.csv"
            source.write_text("id,amount\none,42\n")
            markdown = package / "README.md"
            markdown.write_text("# Customer evidence\n")
            record = {
                "package_id": "TEST-001",
                "title": "Test",
                "status": "DRAFT",
                "markdown": str(markdown.relative_to(root)),
                "sources": [
                    {
                        "path": str(source.relative_to(root)),
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    }
                ],
            }
            register = package / "evidence-register.json"
            register.write_text(json.dumps(record))
            self.assertEqual(MODULE.records(root)[0][0], "TEST-001")
            source.write_text("id,amount\nother,43\n")
            with self.assertRaisesRegex(ValueError, "Stale evidence source"):
                MODULE.records(root)
            record["sources"][0]["path"] = "../../outside.csv"
            register.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "unsafe evidence path"):
                MODULE.records(root)
            record["sources"][0] = {
                "path": str(source.relative_to(root)),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
            register.write_text(json.dumps(record))
            duplicate = root / "docs/legal/evidence/commercial"
            duplicate.mkdir(parents=True)
            (duplicate / "evidence-register.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "Duplicate/empty evidence package ID"):
                MODULE.records(root)


class ReviewArtifactTests(unittest.TestCase):
    def test_draft_link_checks_bytes_and_source_without_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "docs/finance/evidence/customer"
            (folder / "draft").mkdir(parents=True)
            guide = folder / "README.md"
            guide.write_text("# Evidence\n")
            relative = str(guide.relative_to(root))
            data = {
                "package_id": "TEST",
                "title": "Test",
                "status": "SOURCE_ONLY",
                "markdown": relative,
                "sources": [
                    {"path": relative, "sha256": hashlib.sha256(guide.read_bytes()).hexdigest()}
                ],
            }
            register = folder / "evidence-register.json"
            register.write_text(json.dumps(data))
            pdf = folder / "draft/paper.pdf"
            pdf.write_bytes(b"draft bytes")
            manifest = folder / "draft/manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "status": "DRAFT_FOR_EXACT_FILE_REVIEW",
                        "source_register_sha256": hashlib.sha256(register.read_bytes()).hexdigest(),
                        "artifacts": {
                            str(pdf.relative_to(root)): hashlib.sha256(pdf.read_bytes()).hexdigest()
                        },
                    }
                )
            )
            row = MODULE.artifact_records(root)[0]
            self.assertEqual(row[3], "DRAFT_FOR_EXACT_FILE_REVIEW")
            pdf.write_bytes(b"unreviewed changed bytes")
            with self.assertRaisesRegex(ValueError, "Stale review artifact"):
                MODULE.artifact_records(root)
