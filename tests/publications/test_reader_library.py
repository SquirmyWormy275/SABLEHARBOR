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
