"""Extend the preserved legal review packager with the practical-work addendum."""

import argparse
import html
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.legal_gaps import package as previous

ROOT = previous.ROOT
PREFIX = previous.PREFIX
VERSION = "0.3.0-review.1"
ADDITIONS = ("walkthroughs", "reconciliations", "decision-import")


def build(output, allow_dirty=False):
    output = output.resolve()
    archive = Path(str(output) + ".zip")
    if output.exists() or archive.exists():
        raise ValueError("Use a new output path; never replace a delivered edition")
    # Preserve the prior generator and its QA pins. Extend only this invocation.
    collect_previous, version_previous = previous.collect, previous.VERSION

    def collect():
        selected = set(collect_previous())
        for part in ADDITIONS:
            for path in (ROOT / PREFIX / part).rglob("*.csv"):
                if path.is_symlink():
                    raise ValueError("Symlink addendum source rejected")
                if "/qa/" not in str(path):
                    selected.add(str(path.relative_to(ROOT)))
        return sorted(selected)

    with tempfile.TemporaryDirectory() as scratch:
        intermediate = Path(scratch) / "review"
        try:
            previous.collect = collect
            previous.VERSION = VERSION
            previous.build(intermediate, allow_dirty)
        finally:
            previous.collect, previous.VERSION = collect_previous, version_previous
        manifest = json.loads((intermediate / "MANIFEST.json").read_text())
        selected = set(manifest["original_files"])
        new_companions = {
            p
            for p in selected
            if p.endswith(".md")
            and (
                any("/" + part + "/" in p for part in ADDITIONS)
                or p == PREFIX + "/PRACTICAL_WORK.md"
            )
        }
        all_companions = {
            r["path"][:-5] for r in manifest["files"] if r["path"].endswith(".md.html")
        } | new_companions
        start = (intermediate / "START_HERE.html").read_text()
        css = re.search(r"<style>(.*?)</style>", start, re.S)[1]
        for relative in sorted(new_companions):
            original = ROOT / relative
            body = (
                MarkdownIt("commonmark", {"html": False})
                .enable("table")
                .render(original.read_text())
            )

            def rewrite(match, original=original):
                raw = html.unescape(match[1])
                parsed = urlsplit(raw)
                if parsed.scheme or parsed.netloc:
                    return match[0]
                target = (
                    (original.parent / unquote(parsed.path)).resolve() if parsed.path else original
                )
                if not target.is_relative_to(ROOT):
                    raise ValueError("Addendum link escapes repository")
                dest = str(target.relative_to(ROOT))
                if dest in selected:
                    link = os.path.relpath(
                        dest + (".html" if dest in all_companions else ""),
                        original.parent.relative_to(ROOT),
                    )
                    if parsed.fragment:
                        link += "#" + parsed.fragment
                else:
                    link = f"https://github.com/SquirmyWormy275/SABLEHARBOR/blob/{manifest['source_revision']}/{dest}"
                    if parsed.fragment:
                        link += "#" + parsed.fragment
                return 'href="' + html.escape(link, quote=True) + '"'

            body = re.sub(r'href="([^"]+)"', rewrite, body)
            counts = {}

            def heading(match, counts=counts):
                slug = re.sub(
                    r"[^\w\- ]", "", re.sub(r"<[^>]+>", "", html.unescape(match[2])).lower()
                ).replace(" ", "-")
                n = counts.get(slug, 0)
                counts[slug] = n + 1
                return (
                    f'<h{match[1]} id="{slug}{"-" + str(n) if n else ""}">{match[2]}</h{match[1]}>'
                )

            body = re.sub(r"<h([1-6])>(.*?)</h\1>", heading, body)
            (intermediate / (relative + ".html")).write_text(
                '<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1"><title>'
                + html.escape(original.stem)
                + "</title><style>"
                + css
                + '</style><body><p class="notice">Offline reading companion. '
                "Original source status applies. Additional repository references "
                "may require internet.</p>"
                + body
                + "</body></html>"
            )
        entries = [
            ("Case walkthroughs and evidence requests", "walkthroughs/README.md.html"),
            ("Five reconciliation workpapers", "reconciliations/README.md.html"),
            ("Import a completed decision workbook", "decision-import/README.md.html"),
        ]
        links = "".join(
            '<li><a href="' + PREFIX + "/" + path + '">' + label + "</a></li>"
            for label, path in entries
        )
        start = start.replace("</ul>", links + "</ul>", 1)
        (intermediate / "START_HERE.html").write_text(start)
        for name in ("MANIFEST.json", "SHA256SUMS.txt"):
            (intermediate / name).unlink()
        rows = [
            {
                "path": str(p.relative_to(intermediate)),
                "sha256": previous.digest(p.read_bytes()),
                "bytes": p.stat().st_size,
            }
            for p in sorted(intermediate.rglob("*"))
            if p.is_file()
        ]
        manifest["files"] = rows
        manifest["predecessor"] = "0.2.0-review.1; original release bytes retained"
        (intermediate / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (intermediate / "SHA256SUMS.txt").write_text(
            "".join(r["sha256"] + "  " + r["path"] + "\n" for r in rows)
            + previous.digest((intermediate / "MANIFEST.json").read_bytes())
            + "  MANIFEST.json\n"
        )
        previous.verify(intermediate)
        # Move only after the complete extended manifest and links have passed.
        import shutil

        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(intermediate, output)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for p in sorted(output.rglob("*")):
            if p.is_file():
                info = zipfile.ZipInfo(str(p.relative_to(output)), date_time=(2026, 9, 13, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                zipped.writestr(info, p.read_bytes())
    print(f"{archive}: {previous.digest(archive.read_bytes())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    build(args.output, args.allow_dirty)
