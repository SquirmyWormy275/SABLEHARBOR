"""Adversarial completeness tests independent of the renderer implementation."""

import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "legal_full_text_validator", Path(__file__).with_name("validate.py")
)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

SOURCE = """# Purchase record

**State:** Proposed; no execution claimed.

Buyer shall pay $17,250 after delivery of the signed closing certificate.

| Obligation | Due date |
| --- | --- |
| Title evidence | September 21, 2026 |
| Tax clearance | October 1, 2026 |

The reserve remains payable.

The reserve remains payable.

## Final exception

No assignment is effective without written consent.
"""


def edition(source):
    return '<article id="source-content">' + validator.MARKDOWN.render(source) + "</article>"


class CompletenessTests(unittest.TestCase):
    def test_full_source_passes(self):
        validator.assert_html_complete(SOURCE, edition(SOURCE))
        validator.assert_pdf_complete(SOURCE, "\n".join(validator.source_units(SOURCE)))

    def test_middle_clause_removal_fails_despite_resealed_hash(self):
        changed = SOURCE.replace(
            "Buyer shall pay $17,250 after delivery of the signed closing certificate.", ""
        )
        rendered = edition(changed)
        # A replacement checksum certifies changed bytes, not completeness.
        self.assertTrue(validator.hashlib.sha256(rendered.encode()).hexdigest())
        with self.assertRaisesRegex(validator.ValidationError, "HTML source text differs"):
            validator.assert_html_complete(SOURCE, rendered)

    def test_table_cell_removed(self):
        with self.assertRaises(validator.ValidationError):
            validator.assert_html_complete(
                SOURCE, edition(SOURCE.replace("September 21, 2026", ""))
            )
        with self.assertRaisesRegex(validator.ValidationError, "PDF missing source blocks"):
            validator.assert_pdf_complete(
                SOURCE, "\n".join(validator.source_units(SOURCE)).replace("September 21, 2026", "")
            )

    def test_last_section_removed(self):
        shortened = SOURCE.split("## Final exception")[0]
        with self.assertRaises(validator.ValidationError):
            validator.assert_html_complete(SOURCE, edition(shortened))
        with self.assertRaises(validator.ValidationError):
            validator.assert_pdf_complete(SOURCE, "\n".join(validator.source_units(shortened)))

    def test_repeated_clause_not_satisfied_by_single_copy(self):
        shortened = SOURCE.replace("The reserve remains payable.", "", 1)
        with self.assertRaises(validator.ValidationError):
            validator.assert_pdf_complete(SOURCE, "\n".join(validator.source_units(shortened)))

    def test_changed_number_or_negation_fails(self):
        for before, after in [("$17,250", "$17,200"), ("No assignment", "An assignment")]:
            with self.subTest(after=after), self.assertRaises(validator.ValidationError):
                validator.assert_pdf_complete(
                    SOURCE, "\n".join(validator.source_units(SOURCE)).replace(before, after)
                )

    def test_section_reordering_rejected_in_html(self):
        first, last = SOURCE.split("## Final exception")
        with self.assertRaises(validator.ValidationError):
            validator.assert_html_complete(SOURCE, edition("## Final exception" + last + first))

    def test_markdown_semantics_and_wrapping(self):
        text = (
            "# Terms\n\n**Buyer** agrees to [clearance](source.md), `A-31` and ~~old~~ new terms.\n"
        )
        expected = "\n".join(validator.source_units(text))
        validator.assert_pdf_complete(text, expected.replace("agrees", "ag\nrees"))
        validator.assert_html_complete(text, edition(text))

    def test_source_container_required(self):
        with self.assertRaisesRegex(validator.ValidationError, "Missing HTML"):
            validator.assert_html_complete(SOURCE, "<p>Summary only.</p>")

    def test_pdf_crop_detected(self):
        import tempfile

        import fitz

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cropped.pdf"
            with fitz.open() as document:
                page = document.new_page(width=100, height=100)
                page.insert_text((90, 40), "CLIPPED CONTRACT CLAUSE", fontsize=12)
                document.save(path)
            with self.assertRaises(validator.ValidationError):
                text = validator.pdf_text(path, 1)
                validator.assert_pdf_complete("CLIPPED CONTRACT CLAUSE", text)

    def test_local_broken_link(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(validator.ValidationError, "Broken local link"):
                validator.validate_links(
                    root, root / "edition.html", '<a href="missing.pdf">Source</a>'
                )


class ResealedArtifactTests(unittest.TestCase):
    """Exercise the real manifest validator against tampered delivery bytes."""

    def fixture(self, destination):
        import json
        import shutil
        import subprocess

        root = validator.ROOT
        base = validator.BASE
        manifest = json.loads((root / base / "render-manifest.json").read_text())
        sources = json.loads((root / base / "SOURCE_MANIFEST.json").read_text())
        paths = {
            str(base / "SOURCE_MANIFEST.json"),
            str(base / "render-manifest.json"),
            str(base / "full-text.sqlite3"),
            str(base / "build.py"),
            str(base / "style.css"),
            "docs/reader/transactions/evidence-register.json",
        }
        paths.update(r["source"] for r in sources["records"])
        for item in manifest["artifacts"]:
            paths.update([item["html"], item["pdf"], item["logo"]["path"]])
        for name in paths:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, target)
        # Use a real isolated Git directory in both ordinary clones and worktrees.
        # Only immutable object lookup is shared; no index, refs or credentials
        # from the owning checkout are copied into a mutation fixture.
        subprocess.run(["git", "init", "--quiet", str(destination)], check=True)
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"], cwd=root, text=True
        ).strip()
        objects = (root / common / "objects").resolve()
        (destination / ".git/objects/info/alternates").write_text(str(objects) + "\n")
        self.assertEqual(validator.validate(destination)["result"], "PASS")
        return manifest

    def test_real_html_clause_deletion_resealed(self):
        import json
        import re
        import tempfile

        if not (validator.ROOT / validator.BASE / "render-manifest.json").exists():
            self.skipTest("Build the 56 editions before artifact mutation tests")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root)
            item = manifest["artifacts"][0]
            path = root / item["html"]
            before = path.read_text()
            after, count = re.subn(
                r'(<article[^>]*id="source-content"[^>]*>.*?)(<p>.*?</p>)',
                r"\1",
                before,
                count=1,
                flags=re.S,
            )
            self.assertEqual(count, 1)
            path.unlink()  # Replace only the isolated fixture artifact.
            path.write_text(after)
            item["html_sha256"] = validator.digest(path)
            manifest_path = root / validator.BASE / "render-manifest.json"
            manifest_path.unlink()
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(validator.ValidationError, "HTML source text differs"):
                validator.validate(root)

    def test_real_pdf_clause_deletion_resealed(self):
        import json
        import tempfile

        import fitz

        if not (validator.ROOT / validator.BASE / "render-manifest.json").exists():
            self.skipTest("Build the 56 editions before artifact mutation tests")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root)
            item = manifest["artifacts"][0]
            path = root / item["pdf"]
            document = fitz.open(path)
            last = document[0]
            blocks = [
                block
                for block in last.get_text("blocks")
                if 80 < block[1] < 720 and len(block[4]) > 80
            ]
            self.assertTrue(blocks)
            last.add_redact_annot(fitz.Rect(blocks[-1][:4]), fill=(1, 1, 1))
            last.apply_redactions()
            replacement = path.with_suffix(".replacement.pdf")
            document.save(replacement)
            document.close()
            replacement.replace(path)
            item["pdf_sha256"] = validator.digest(path)
            manifest_path = root / validator.BASE / "render-manifest.json"
            manifest_path.unlink()
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(validator.ValidationError, "PDF missing source blocks"):
                validator.validate(root)


if __name__ == "__main__":
    unittest.main()
