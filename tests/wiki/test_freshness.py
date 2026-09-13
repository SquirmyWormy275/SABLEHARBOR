import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.wiki.freshness import compare


class FreshnessTests(unittest.TestCase):
    def test_unrelated_revision_is_current_but_changed_inputs_are_stale(self):
        with tempfile.TemporaryDirectory() as temp:
            wiki = Path(temp)
            (wiki / "Home.md").write_text("# Home\n")
            digest = hashlib.sha256((wiki / "Home.md").read_bytes()).hexdigest()
            published = {
                "source_revision": "a" * 40,
                "files": {"Home.md": digest},
                "inputs": {"docs/source.md": "old"},
                "directory_trees": {"docs/records": "tree"},
            }
            expected = {**published, "source_revision": "b" * 40}
            self.assertEqual(compare(expected, published, wiki)["state"], "current")
            expected["inputs"] = {"docs/source.md": "new"}
            report = compare(expected, published, wiki)
            self.assertEqual(report["state"], "stale")
            self.assertEqual(report["changed"]["inputs"], ["docs/source.md"])
            expected["inputs"] = published["inputs"]
            expected["directory_trees"] = {"docs/records": "changed"}
            self.assertEqual(compare(expected, published, wiki)["state"], "stale")

    def test_live_edits_missing_pages_and_legacy_manifests_are_not_current(self):
        with tempfile.TemporaryDirectory() as temp:
            wiki = Path(temp)
            (wiki / "Home.md").write_text("# Home\n")
            digest = hashlib.sha256((wiki / "Home.md").read_bytes()).hexdigest()
            published = {"files": {"Home.md": digest}}
            self.assertEqual(compare(published, published, wiki)["state"], "unverifiable")
            published["inputs"] = {"source": "hash"}
            (wiki / "Home.md").write_text("independent edit")
            self.assertEqual(compare(published, published, wiki)["state"], "modified")
            (wiki / "Home.md").unlink()
            self.assertEqual(compare(published, published, wiki)["state"], "modified")
