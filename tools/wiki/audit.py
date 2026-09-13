"""Audit Wiki navigation and Markdown accessibility without rebuilding publications."""

from __future__ import annotations

import argparse
import json
import re
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[2]
MARKDOWN = MarkdownIt("commonmark", {"html": True}).enable("table")


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links, self.images, self.headings, self.anchors = [], [], [], set()
        self.heading = None
        self.link = None
        self.duplicates = {}
        self.feed(MARKDOWN.render(source))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ("id", "name"):
            if attrs.get(key):
                self.anchors.add(attrs[key])
        if re.fullmatch("h[1-6]", tag):
            self.heading = [int(tag[1]), ""]
        if tag == "a" and "href" in attrs:
            self.link = [attrs["href"], ""]
        if tag == "img":
            self.images.append(attrs)
            if self.link is not None:
                self.link[1] += attrs.get("alt", "")

    def handle_data(self, text):
        if self.heading is not None:
            self.heading[1] += text
        if self.link is not None:
            self.link[1] += text

    def handle_endtag(self, tag):
        if re.fullmatch("h[1-6]", tag) and self.heading is not None:
            level, title = self.heading
            slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
            occurrence = self.duplicates.get(slug, 0)
            self.duplicates[slug] = occurrence + 1
            self.anchors.add(slug + (f"-{occurrence}" if occurrence else ""))
            self.headings.append((level, title))
            self.heading = None
        if tag == "a" and self.link is not None:
            self.links.append(tuple(self.link))
            self.link = None


def audit(root=ROOT):
    root = root.resolve()
    pages = sorted((root / "docs/wiki").rglob("*.md"))
    cache = {}

    def read(path):
        if path not in cache:
            cache[path] = Page(path.read_text())
        return cache[path]

    errors, edges = [], {page: set() for page in pages}
    checked = 0
    for page in pages:
        parsed = read(page)
        name = str(page.relative_to(root))
        if sum(level == 1 for level, _ in parsed.headings) != 1:
            errors.append(f"{name}: expected one top-level heading")
        previous = 0
        for level, title in parsed.headings:
            if level > previous + 1:
                errors.append(f"{name}: skipped heading level at {title}")
            previous = level
        for img in parsed.images:
            if not img.get("alt", "").strip():
                errors.append(f"{name}: image lacks a description: {img.get('src')}")
        for target, label in parsed.links:
            if label.strip().lower() in ("", "here", "click here", "read more", "more"):
                errors.append(f"{name}: undescriptive link: {target}")
        destinations = [target for target, _ in parsed.links] + [
            img.get("src", "") for img in parsed.images
        ]
        for value in destinations:
            url = urlsplit(value)
            if url.scheme or url.netloc:
                continue
            target = (page.parent / unquote(url.path)).resolve() if url.path else page
            if not target.is_relative_to(root) or not target.exists():
                errors.append(f"{name}: missing local target {value}")
                continue
            if target.is_dir() and (target / "README.md").exists():
                target /= "README.md"
            if target in edges:
                edges[page].add(target)
            if url.fragment and target.suffix.lower() == ".md":
                if unquote(url.fragment) not in read(target).anchors:
                    errors.append(f"{name}: missing anchor {value}")
            checked += 1
    seen = set()
    queue = deque([root / "docs/wiki/Home.md"])
    while queue:
        page = queue.popleft()
        if page not in seen:
            seen.add(page)
            queue.extend(edges.get(page, set()) - seen)
    for page in set(pages) - seen:
        errors.append(f"{page.relative_to(root)}: unreachable from Wiki Home")
    return {
        "pages": len(pages),
        "local_destinations": checked,
        "reachable_pages": len(seen),
        "errors": sorted(errors),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report["errors"]))
