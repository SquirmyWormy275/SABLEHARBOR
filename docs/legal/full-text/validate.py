#!/usr/bin/env python3
"""Independent unabridged-edition checks; never trusts a resealed artifact hash alone.

Markdown is parsed afresh with CommonMark plus tables. Visible text includes all
headings, paragraphs, list bodies, table cells and code blocks; link destinations
are validated separately. Normalization is NFKC, soft-hyphen removal and whitespace
removal only (PDF line wrapping is not a content change). No words, digits, clauses
or punctuation are discarded. HTML body text must match the complete source in
order. Every source block must occur in PDF text, including repeated occurrences.
Running PDF furniture is excluded only within the renderer's declared body bounds.
Manual review is still required for visual quality and page composition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[3]
BASE = Path("docs/legal/full-text")
MARKDOWN = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text):
    return "".join(unicodedata.normalize("NFKC", text).replace("\u00ad", "").split())


class TextParser(HTMLParser):
    def __init__(self, selector=None):
        super().__init__(convert_charrefs=True)
        self.selector = selector
        self.depth = 0
        self.active = selector is None
        self.found = selector is None
        self.parts = []
        self.links = []
        self.ids = set()
        self.suppressed = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag in ("a", "img", "link", "script"):
            link = attrs.get("href") or attrs.get("src")
            if link:
                self.links.append(link)
        if attrs.get("id") == self.selector and self.selector is not None:
            require(not self.found, "Duplicate source-content container")
            self.active = self.found = True
            self.depth = 1
        elif (
            self.active
            and self.selector is not None
            and tag
            not in (
                "img",
                "br",
                "hr",
                "meta",
                "link",
                "input",
                "wbr",
                "source",
            )
        ):
            self.depth += 1
        if self.active and tag in ("script", "style"):
            self.suppressed += 1
        if self.active and tag == "img":
            self.parts.append(attrs.get("alt", ""))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in ("img", "br", "hr", "meta", "link", "input", "wbr", "source"):
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.active and tag in ("script", "style"):
            self.suppressed -= 1
        if self.active and self.selector is not None:
            self.depth -= 1
            if self.depth == 0:
                self.active = False

    def handle_data(self, data):
        if self.active and not self.suppressed:
            self.parts.append(data)

    @property
    def text(self):
        return "".join(self.parts)


def html_text(raw, selector=None):
    parser = TextParser(selector)
    parser.feed(raw)
    require(parser.found, f"Missing HTML #{selector}")
    return parser.text


def source_units(source):
    units = []
    for token in MARKDOWN.parse(source):
        if token.type == "inline":
            units.append(html_text(MARKDOWN.renderInline(token.content)))
        elif token.type in ("fence", "code_block"):
            units.append(token.content)
        elif token.type == "html_block":
            units.append(html_text(token.content))
    return [unit for unit in units if normalize(unit)]


def assert_html_complete(source, rendered):
    expected = normalize(html_text(MARKDOWN.render(source)))
    actual = normalize(html_text(rendered, "source-content"))
    if expected != actual:
        first = next(
            (i for i, pair in enumerate(zip(expected, actual, strict=False)) if pair[0] != pair[1]),
            min(len(expected), len(actual)),
        )
        raise ValidationError(
            f"HTML source text differs at character {first}; "
            f"expected {expected[first : first + 90]!r}; "
            f"found {actual[first : first + 90]!r}"
        )


def assert_pdf_complete(source, text):
    actual = normalize(text)
    missing = []
    for unit, count in Counter(map(normalize, source_units(source))).items():
        if actual.count(unit) < count:
            missing.append(f"{unit[:110]!r} ({actual.count(unit)}/{count})")
    require(not missing, "PDF missing source blocks: " + "; ".join(missing[:12]))


def repository_path(root, relative):
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), f"Path escapes repository: {relative}")
    require(path.is_file(), f"Missing file: {relative}")
    return path


def validate_links(root, path, raw):
    parser = TextParser()
    parser.feed(raw)
    for link in parser.links:
        url = urlsplit(link)
        if url.netloc == "github.com" and url.path.startswith("/SquirmyWormy275/SABLEHARBOR/blob/"):
            revision, _, relative = unquote(url.path).split("/blob/", 1)[1].partition("/")
            result = subprocess.run(
                ["git", "cat-file", "-e", f"{revision}:{relative}"], cwd=root, capture_output=True
            )
            require(result.returncode == 0, f"Broken repository source link {path.name}: {link}")
        if url.scheme or url.netloc:
            continue
        if not url.path:
            require(
                not url.fragment or unquote(url.fragment) in parser.ids,
                f"Broken anchor {path.name}: {link}",
            )
            continue
        target = (
            root / unquote(url.path).lstrip("/")
            if url.path.startswith("/")
            else path.parent / unquote(url.path)
        ).resolve()
        require(
            target.is_relative_to(root.resolve()) and target.exists(),
            f"Broken local link {path.name}: {link}",
        )


def pdf_text(path, expected_pages, body_bounds=None):
    import fitz

    with fitz.open(path) as document:
        require(
            len(document) == expected_pages and expected_pages > 0,
            f"PDF page count mismatch: {path.name}",
        )
        texts = []
        for index, page in enumerate(document):
            body = []
            for block in page.get_text(
                "dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_MEDIABOX_CLIP
            )["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        if not span["text"].strip():
                            continue
                        box = fitz.Rect(span["bbox"])
                        require(
                            box.x0 >= -0.5
                            and box.y0 >= -0.5
                            and box.x1 <= page.rect.width + 0.5
                            and box.y1 <= page.rect.height + 0.5,
                            f"Out-of-page text {path.name} page {index + 1}: "
                            f"{span['text'][:80]} {box}",
                        )
                        if body_bounds is None or (
                            box.y0 >= body_bounds[0] - 1 and box.y1 <= body_bounds[1] + 1
                        ):
                            body.append(span["text"])
            texts.append(" ".join(body))
            for link in page.get_links():
                if link["kind"] == fitz.LINK_GOTO:
                    require(
                        0 <= link["page"] < len(document), f"Broken PDF internal link: {path.name}"
                    )
        return "\n".join(texts)


def validate_browser(paths):
    from playwright.sync_api import sync_playwright

    checks = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="/usr/bin/chromium", args=["--no-sandbox"]
        )
        page = browser.new_page()
        for path in paths:
            for width in (1280, 390):
                page.set_viewport_size({"width": width, "height": 1000})
                page.goto(path.as_uri())
                page.evaluate("document.fonts.ready")
                failures = page.evaluate("""() => {
                  const failures = [];
                  if (document.documentElement.scrollWidth > innerWidth + 1)
                    failures.push('document horizontal overflow');
                  const elements = document.querySelectorAll('#source-content, #source-content *');
                  for (const el of elements) {
                    const s = getComputedStyle(el), r = el.getBoundingClientRect();
                    if (el.textContent.trim() && (s.display === 'none' || s.visibility === 'hidden'
                        || s.opacity === '0'))
                      failures.push('hidden source text: ' + el.textContent.slice(0,80));
                    if (r.width && el.clientWidth && el.scrollWidth > el.clientWidth + 2
                        && !['visible', 'auto', 'scroll'].includes(s.overflowX))
                      failures.push('clipped width: ' + el.textContent.slice(0,80));
                    if (el.clientHeight && el.scrollHeight > el.clientHeight + 2
                        && !['visible', 'auto', 'scroll'].includes(s.overflowY))
                      failures.push('clipped height: ' + el.textContent.slice(0,80));
                  }
                  for (const img of document.images)
                    if (!img.complete || !img.naturalWidth) failures.push('broken image');
                  return failures;
                }""")
                require(not failures, f"{path.name} viewport {width}: {failures[:8]}")
                checks += 1
        browser.close()
    return checks


def validate_database(root, source_manifest, rendered):
    import sqlite3

    with sqlite3.connect(root / BASE / "full-text.sqlite3") as db:
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite corruption")
        require(not db.execute("PRAGMA foreign_key_check").fetchall(), "SQLite foreign key failure")
        expected_sources = sorted(
            (
                r["id"],
                r["family"],
                r["title"],
                r["source"],
                r["source_sha256"],
                source_manifest["source_revision"],
                json.dumps(r["source_status_verbatim"]),
                (root / r["source"]).read_text(),
            )
            for r in source_manifest["records"]
        )
        require(
            db.execute("SELECT * FROM source_document ORDER BY id").fetchall() == expected_sources,
            "SQLite source text, scope or provenance differs",
        )
        expected_publications = sorted(
            (
                r["id"],
                source_manifest["status"],
                r["pdf"],
                r["pdf_sha256"],
                r["html"],
                r["html_sha256"],
                r["pages"],
            )
            for r in rendered
        )
        require(
            db.execute("SELECT * FROM publication ORDER BY source_id").fetchall()
            == expected_publications,
            "SQLite publication paths, hashes or page counts differ",
        )


def validate(root=ROOT, browser=False):
    source_path = root / BASE / "SOURCE_MANIFEST.json"
    source_manifest = json.loads(source_path.read_text())
    manifest = json.loads((root / BASE / "render-manifest.json").read_text())
    require(
        manifest["status"] == source_manifest["status"] == "DRAFT_FOR_EXACT_FILE_REVIEW"
        and manifest["approved"] is False
        and source_manifest["approved"] is False,
        "Unapproved editions must retain draft status",
    )
    records = source_manifest["records"]
    expected = json.loads((root / "docs/reader/transactions/evidence-register.json").read_text())
    expected_sources = {item["path"]: item["sha256"] for item in expected["sources"]}
    require(len(records) == len(expected_sources) == 56, "Expected exactly 56 complete sources")
    require(len({r["id"] for r in records}) == len(records), "Duplicate source IDs")
    require(
        {r["source"]: r["source_sha256"] for r in records} == expected_sources,
        "Full-text source scope/hashes differ from legal evidence register",
    )
    require(
        re.fullmatch(r"[0-9a-f]{40}", source_manifest["source_revision"]),
        "Source revision must be a full Git SHA",
    )
    require(manifest["source_manifest_sha256"] == digest(source_path), "Stale source manifest")
    require(manifest["source_revision"] == source_manifest["source_revision"], "Revision mismatch")
    for dependency in manifest.get("build_inputs", []):
        require(
            digest(repository_path(root, dependency["path"])) == dependency["sha256"],
            f"Stale build input: {dependency['path']}",
        )
    for filename, key in [("build.py", "generator_sha256"), ("style.css", "style_sha256")]:
        require(digest(root / BASE / filename) == manifest[key], f"Stale renderer {filename}")
    rendered = manifest["artifacts"]
    require(
        len(rendered) == 56 and len({r["id"] for r in rendered}) == 56,
        "Missing or duplicate rendered editions",
    )
    by_id = {r["id"]: r for r in rendered}
    require(set(by_id) == {r["id"] for r in records}, "Render/source identity mismatch")
    expected_ids = {r["id"]: r["source"]["path"] for r in expected["instruments"]}
    require({r["id"]: r["source"] for r in records} == expected_ids, "Source ID mapping changed")
    pages = units = 0
    html_paths = []
    for record in records:
        source = repository_path(root, record["source"])
        require(digest(source) == record["source_sha256"], f"Stale source {source}")
        pinned = subprocess.check_output(
            ["git", "show", f"{source_manifest['source_revision']}:{record['source']}"], cwd=root
        )
        require(
            hashlib.sha256(pinned).hexdigest() == record["source_sha256"],
            f"Source does not match pinned Git revision: {source}",
        )
        raw_source = source.read_text()
        require(
            all(status in raw_source for status in record["source_status_verbatim"]),
            f"Invented source status: {record['id']}",
        )
        require(record["family"] and record["brand"], f"Missing identity: {record['id']}")
        output = by_id[record["id"]]
        require(
            output["source"] == record["source"]
            and output["source_sha256"] == record["source_sha256"],
            f"Render source mismatch: {record['id']}",
        )
        require(
            digest(repository_path(root, output["logo"]["path"])) == output["logo"]["sha256"],
            f"Stale logo: {record['id']}",
        )
        for kind in ("html", "pdf"):
            target = repository_path(root, output[kind])
            require(
                target == root / BASE / "editions" / f"{record['id']}.{kind}",
                f"Unstable artifact path: {target}",
            )
            require(digest(target) == output[kind + "_sha256"], f"Stale {kind}: {target}")
        html_path = root / output["html"]
        raw_html = html_path.read_text()
        assert_html_complete(raw_source, raw_html)
        require(
            record["source"] in raw_html
            and record["source_sha256"] in raw_html
            and source_manifest["source_revision"] in raw_html,
            f"Missing source provenance: {record['id']}",
        )
        validate_links(root, html_path, raw_html)
        assert_pdf_complete(
            raw_source,
            pdf_text(
                root / output["pdf"], output["pages"], output.get("body_bounds_pt", [48.96, 743.04])
            ),
        )
        pages += output["pages"]
        units += len(source_units(raw_source))
        html_paths.append(html_path)
    validate_database(root, source_manifest, rendered)
    browser_checks = validate_browser(html_paths) if browser else 0
    return {
        "sources": len(records),
        "pages": pages,
        "source_blocks": units,
        "browser_viewports": browser_checks,
        "result": "PASS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", action="store_true", help="Inspect desktop/mobile overflow")
    args = parser.parse_args()
    try:
        print(json.dumps(validate(browser=args.browser), indent=2))
    except (ValidationError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"FAIL: {exc}") from exc
