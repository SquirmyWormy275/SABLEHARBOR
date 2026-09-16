import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from tools.wiki.audit import audit_export

SPEC = importlib.util.spec_from_file_location(
    "wiki_export", Path(__file__).resolve().parents[2] / "tools/wiki/export.py"
)
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
        self.home.write_text("""# Home
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
""")
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
        self.assertEqual(
            (self.base / "one" / MODULE.MANIFEST).read_bytes(),
            (self.base / "two" / MODULE.MANIFEST).read_bytes(),
        )
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

    def reading_plan(self, sections=None):
        plan = self.root / "tools/wiki/reading.json"
        plan.parent.mkdir(parents=True)
        source = self.root / "source file.md"
        source.write_text(
            "# Source\n\n**Status:** PROVISIONAL\n\n## Purpose\n\n"
            "Real source text. [Detail](#detail)\n\n## Detail\n\n"
            "Keep unresolved.\n\n```md\n## Code heading\n```\n"
        )
        entry = {"source": "source file.md"}
        if sections:
            entry["sections"] = sections
        plan.write_text(
            json.dumps({"sources": ["source file.md"], "articles": {"Home.md": [entry]}})
        )
        return source

    def test_full_reading_and_article_preserve_source_and_fragments(self):
        source = self.reading_plan(["Purpose"])
        for name in (
            "Library.md",
            "Locations.md",
            "Records-and-Decisions.md",
            "businesses/README.md",
            "departments/README.md",
            "subjects/README.md",
        ):
            page = self.home.parent / name
            page.parent.mkdir(exist_ok=True)
            page.write_text("# Directory\n")
        original = source.read_bytes()
        output = self.base / "output"
        manifest = MODULE.Exporter(self.root, SHA).build(output)
        home = (output / "Home.md").read_text()
        record = (output / "records--source file.md").read_text()
        self.assertIn("Real source text.", home)
        self.assertNotIn("Keep unresolved.", home)
        self.assertIn("Keep unresolved.", record)
        self.assertIn("**Status:** PROVISIONAL", record)
        self.assertIn("/wiki/records--source%20file#detail", home)
        self.assertIn(f"/blob/{SHA}/source%20file.md", record)
        self.assertIn("```md\n## Code heading\n```", record)
        self.assertEqual(source.read_bytes(), original)
        self.assertIn("source file.md", manifest["reading_sources"])
        self.assertEqual(manifest["expanded_articles"], ["Home.md"])
        self.assertIn(
            "<details>\n<summary>Supporting records and decision history</summary>", home
        )
        self.assertNotIn("<details open", home)
        self.assertIn("/wiki/Records-and-Decisions", home)
        sidebar = (output / "_Sidebar.md").read_text()
        self.assertIn("[Locations and facilities](Locations)", sidebar)
        self.assertIn("[Records and decisions](Records-and-Decisions)", sidebar)
        self.assertEqual(audit_export(output)["errors"], [])

    def test_changed_section_fails_before_publication(self):
        self.reading_plan(["Deleted section"])
        with self.assertRaisesRegex(ValueError, "Unmatched article sections"):
            MODULE.Exporter(self.root, SHA).build(self.base / "output")
        self.assertFalse((self.base / "output").exists())

    def test_reading_inventory_cannot_escape_checkout(self):
        self.reading_plan()
        (self.base / "outside.md").write_text("# Outside")
        (self.root / "tools/wiki/reading.json").write_text(
            json.dumps({"sources": ["../outside.md"], "articles": {}})
        )
        with self.assertRaisesRegex(ValueError, "Invalid reading source"):
            MODULE.Exporter(self.root, SHA)

    def test_contents_handles_duplicate_and_formatted_headings(self):
        text = "# Home\n\n## **One**\n\n## One\n\n## `Three`\n"
        result = MODULE.Exporter.contents(text)
        self.assertIn("[**One**](#one)", result)
        self.assertIn("[One](#one-1)", result)
        self.assertIn("[`Three`](#three)", result)

    def test_readable_titles_preserve_bookmarks_fragments_and_literal_code(self):
        other = self.home.parent / "businesses/One.md"
        other.parent.mkdir()
        other.write_text("# One\n\n## Detail\n\nThe actual article.\n")
        self.home.write_text(
            "# Home\n\n[One](businesses/One.md#detail)\n\n`[Literal](businesses--One)`\n"
        )
        config = self.root / "tools/wiki/titles.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"businesses--One": "One"}))
        (config.parent / "legacy-sections.json").write_text(
            json.dumps({"routes": {"businesses--One": {"previous-detail": "detail"}}})
        )
        output = self.base / "output"
        manifest = MODULE.Exporter(self.root, SHA).build(output)
        self.assertIn("/wiki/One#detail", (output / "Home.md").read_text())
        self.assertIn("`[Literal](businesses--One)`", (output / "Home.md").read_text())
        self.assertIn("The actual article.", (output / "One.md").read_text())
        old = (output / "businesses--One.md").read_text()
        self.assertIn('id="detail"', old)
        self.assertIn('id="previous-detail"', old)
        self.assertIn("/wiki/One#detail", old)
        self.assertEqual(manifest["aliases"], {"businesses--One.md": "One.md"})
        self.assertIn("tools/wiki/titles.json", manifest["inputs"])
        config.write_text(json.dumps({"businesses--One": "Home"}))
        with self.assertRaisesRegex(ValueError, "collide"):
            MODULE.Exporter(self.root, SHA).build(self.base / "collision")
        self.assertFalse((self.base / "collision").exists())

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
