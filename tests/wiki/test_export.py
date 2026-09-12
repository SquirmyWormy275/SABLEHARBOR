import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("wiki_export", Path(__file__).resolve().parents[2] / "tools/wiki/export.py")
MODULE = importlib.util.module_from_spec(SPEC)
try:
    SPEC.loader.exec_module(MODULE)
except ModuleNotFoundError as error:
    if error.name != "markdown_it":
        raise
    raise unittest.SkipTest("Install tools/wiki/requirements.txt for Wiki export tests") from error
SHA = "a" * 40


class WikiExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.home = self.root / "docs/wiki/Home.md"
        self.home.parent.mkdir(parents=True)
        self.home.write_text("# Home\n")
        (self.root / "asset.png").write_bytes(b"approved bytes")
        (self.root / "source file.md").write_text("# Source\n")

    def test_navigation_images_fragments_and_code(self):
        other = self.home.parent / "businesses/One.md"
        other.parent.mkdir()
        other.write_text("# One\n")
        self.home.write_text('''# Home
[One](businesses/One.md#history)
[Source](../../source%20file.md?raw=1#detail)
[![Logo](../../asset.png)](../../source%20file.md)
<img src="../../asset.png" width="360">
[Reference][source]
[source]: <../../source file.md>
![Reference image][logo]
[logo]: ../../asset.png
[External](https://example.com/a)
[Here](#home)
`[Code](missing.md)`
```md
[Code](missing.md)
```
''')
        output = self.base / "output"
        MODULE.Exporter(self.root, SHA).build(output)
        result = (output / "Home.md").read_text()
        self.assertIn("/wiki/businesses--One#history", result)
        self.assertIn(f"/blob/{SHA}/source%20file.md?raw=1#detail", result)
        self.assertIn(f"raw.githubusercontent.com/{MODULE.REPOSITORY}/{SHA}/asset.png", result)
        self.assertIn('width="360"', result)
        self.assertIn("`[Code](missing.md)`", result)
        self.assertIn("[External](https://example.com/a)", result)
        self.assertEqual((self.root / "asset.png").read_bytes(), b"approved bytes")
        self.assertIn("_Sidebar.md", json.loads((output / MODULE.MANIFEST).read_text())["files"])

    def test_missing_and_escape_fail_before_publication(self):
        for target in ("missing.md", "../../../outside.md"):
            self.home.write_text(f"[bad]({target})")
            with self.assertRaises(ValueError):
                MODULE.Exporter(self.root, SHA).build(self.base / "output")
            self.assertFalse((self.base / "output").exists())

    def test_determinism_and_source_checkout_protection(self):
        for name in ("one", "two"):
            MODULE.Exporter(self.root, SHA).build(self.base / name)
        self.assertEqual((self.base / "one" / MODULE.MANIFEST).read_bytes(),
                         (self.base / "two" / MODULE.MANIFEST).read_bytes())
        with self.assertRaises(ValueError):
            MODULE.Exporter(self.root, SHA).build(self.root / "output")
        with self.assertRaises(ValueError):
            MODULE.Exporter(self.root, "main")

    def test_sync_preserves_unmanaged_pages_and_rejects_tampering(self):
        output = self.base / "output"
        wiki = self.base / "wiki"
        wiki.mkdir()
        (wiki / "Unmanaged.md").write_text("retain")
        MODULE.Exporter(self.root, SHA).build(output)
        MODULE.sync(output, wiki)
        self.assertEqual((wiki / "Home.md").read_text(), "# Home\n")
        self.assertEqual((wiki / "Unmanaged.md").read_text(), "retain")
        (output / "Home.md").write_text("changed")
        with self.assertRaises(ValueError):
            MODULE.sync(output, wiki)
        self.assertEqual((wiki / "Home.md").read_text(), "# Home\n")

    def test_collisions_and_manifest_traversal(self):
        (self.home.parent / "home.md").write_text("collision")
        with self.assertRaises(ValueError):
            MODULE.Exporter(self.root, SHA)
        (self.home.parent / "home.md").unlink()
        output = self.base / "output"
        MODULE.Exporter(self.root, SHA).build(output)
        wiki = self.base / "wiki"
        wiki.mkdir()
        (wiki / MODULE.MANIFEST).write_text(json.dumps({"files": {"../outside.md": "hash"}}))
        with self.assertRaises(ValueError):
            MODULE.sync(output, wiki)


if __name__ == "__main__":
    unittest.main()
