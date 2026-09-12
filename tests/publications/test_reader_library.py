"""Discovery must preserve history without inventing publication pairs."""

import importlib.util
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "reader_library", ROOT / "tools/documents/reader_library.py"
)
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)


class ReaderLibraryTests(unittest.TestCase):
    def test_inventory_pairing_and_rebuild(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "docs/wiki").mkdir(parents=True)
            (root / "docs/example.md").write_text("# A source\n\nState: OPEN\n")
            (root / "docs/example.pdf").write_bytes(b"test publication bytes")
            (root / "docs/unpaired.md").write_text("# No declared counterpart\n")
            artifacts = [{"source": "docs/example.md", "publication": "docs/example.pdf"}]
            subprocess.run(["git", "-C", str(root), "add", "docs"], check=True)
            (root / "scratch.md").write_text("# Untracked scratch must stay out")
            snapshots = []
            for _ in range(2):
                db = sqlite3.connect(":memory:")
                coverage = library.populate(root, db, artifacts)
                self.assertEqual(coverage["files"], 3)
                self.assertEqual(coverage["verified_pairs"], 1)
                self.assertEqual(
                    db.execute(
                        "SELECT count(*) FROM reader_publication_pair "
                        "WHERE source_path='docs/unpaired.md'"
                    ).fetchone()[0],
                    0,
                )
                self.assertEqual(
                    db.execute(
                        "SELECT count(*) FROM reader_search WHERE reader_search MATCH 'OPEN'"
                    ).fetchone()[0],
                    1,
                )
                snapshots.append(
                    (
                        db.execute("SELECT * FROM reader_file ORDER BY path").fetchall(),
                        (root / "docs/wiki/Library.md").read_bytes(),
                    )
                )
                db.close()
            self.assertEqual(*snapshots)
            self.assertNotIn("docs/wiki/Library.md", library.inputs(root))
            self.assertIn("unmapped", (root / "docs/wiki/library/technical.md").read_text())

    def test_missing_manifest_target_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "source.md").write_text("# Source")
            subprocess.run(["git", "-C", str(root), "add", "source.md"], check=True)
            db = sqlite3.connect(":memory:")
            with self.assertRaisesRegex(ValueError, "missing controlled pair"):
                library.populate(root, db, [{"source": "source.md", "publication": "missing.pdf"}])
            db.close()


if __name__ == "__main__":
    unittest.main()

class EvidenceLinkTests(unittest.TestCase):
    def test_packet_discovery_preserves_draft_and_paths(self):
        records = library.evidence_records(ROOT)
        selected = next(row for row in records if row[0] == 'SH-FIN-HUMAN-001')
        self.assertEqual(selected[1], 'DRAFT_FOR_USER_REVIEW')
        self.assertEqual(selected[2], 'INV-base-FF-003-TERM-0')
        self.assertEqual(selected[3:5], ('base', 'foundry-field'))
        self.assertTrue(selected[11].endswith('/PACKET.md'))
        self.assertTrue(selected[12].endswith('/packet.pdf'))
        self.assertTrue(selected[13].endswith('/reconciliation.xlsx'))

    def test_changed_evidence_and_broken_link_rejected(self):
        import shutil
        import json
        source = ROOT / 'docs/finance/evidence/SH-FIN-HUMAN-001'
        for change in ('bytes', 'missing', 'scope'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                dest = root / 'docs/finance/evidence/SH-FIN-HUMAN-001'
                shutil.copytree(source, dest)
                if change == 'bytes':
                    (dest / 'packet.pdf').write_bytes(b'changed')
                elif change == 'missing':
                    (dest / 'reconciliation.xlsx').unlink()
                else:
                    catalog = json.loads((dest / 'catalog.json').read_text())
                    catalog['scenario'] = 'downside'
                    (dest / 'catalog.json').write_text(json.dumps(catalog))
                with self.assertRaises(ValueError):
                    library.evidence_records(root)
