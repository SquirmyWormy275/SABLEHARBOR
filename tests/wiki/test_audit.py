import tempfile
import unittest
from pathlib import Path

from tools.wiki.audit import Page, audit, audit_export


class AuditTests(unittest.TestCase):
    def test_inline_heading_and_duplicate_anchors(self):
        page = Page("# Home\n\n## **Current** `roles`\n\n## Current roles\n")
        self.assertEqual(page.anchors, {"home", "current-roles", "current-roles-1"})

    def test_bad_anchor_missing_alt_and_orphan_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wiki = root / "docs/wiki"
            wiki.mkdir(parents=True)
            (wiki / "Home.md").write_text('# Home\n\n[Roles](#missing)\n\n<img src="logo.png">')
            (wiki / "logo.png").write_bytes(b"fixture")
            (wiki / "Orphan.md").write_text("# Orphan\n")
            errors = "\n".join(audit(root)["errors"])
            self.assertIn("missing anchor", errors)
            self.assertIn("lacks a description", errors)
            self.assertIn("unreachable", errors)

    def test_directory_routes_and_encoded_anchors_resolve(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wiki = root / "docs/wiki"
            (wiki / "departments").mkdir(parents=True)
            (wiki / "Home.md").write_text("# Home\n\n[Departments](departments/#current%20roles)")
            (wiki / "departments/README.md").write_text(
                '# Departments\n\n<a id="current roles"></a>'
            )
            result = audit(root)
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["reachable_pages"], 2)


class ExportAuditTests(unittest.TestCase):
    def test_composed_records_anchors_and_reachability(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Home.md").write_text(
                "# Home\n\n[Record]"
                "(https://github.com/SquirmyWormy275/SABLEHARBOR/wiki/Record#detail)\n"
            )
            (root / "Record.md").write_text("# Record\n\n## Detail\n")
            self.assertEqual(audit_export(root)["errors"], [])
            (root / "Record.md").write_text("# Record\n\n[Absent](Missing)\n")
            (root / "Orphan.md").write_text("# Orphan\n")
            errors = "\n".join(audit_export(root)["errors"])
            self.assertIn("missing Wiki page", errors)
            self.assertIn("missing Wiki anchor", errors)
            self.assertIn("unreachable exported Wiki page", errors)
