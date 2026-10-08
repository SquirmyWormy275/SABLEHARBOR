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
        self.visible_links, self.details = [], []
        self.link_visible = True
        self.heading = None
        self.link = None
        self.duplicates = {}
        self.feed(MARKDOWN.render(source))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "details":
            self.details.append("open" in attrs)
        for key in ("id", "name"):
            if attrs.get(key):
                self.anchors.add(attrs[key])
        if re.fullmatch("h[1-6]", tag):
            self.heading = [int(tag[1]), ""]
        if tag == "a" and "href" in attrs:
            self.link = [attrs["href"], ""]
            self.link_visible = all(self.details)
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
            if self.link_visible:
                self.visible_links.append(tuple(self.link))
            self.link = None
        if tag == "details" and self.details:
            self.details.pop()


def distances(edges, start):
    """Count actual link selections; opening collapsed details is not a free click."""
    result, queue = {start: 0}, deque([start])
    while queue:
        current = queue.popleft()
        for target in edges.get(current, set()):
            if target not in result:
                result[target] = result[current] + 1
                queue.append(target)
    return result


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


def audit_export(directory, root=ROOT):
    """Check the actual composed Wiki, including all records and generated rooms."""
    pages = {p.stem: Page(p.read_text()) for p in directory.glob("*.md")}
    edges = {name: set() for name in pages}
    visible_edges = {name: set() for name in pages}
    errors, checked = [], 0
    prefix = "/SquirmyWormy275/SABLEHARBOR/wiki/"
    for name, page in pages.items():
        for href, label in page.links:
            url = urlsplit(href)
            if url.netloc == "github.com" and url.path.startswith(prefix):
                target = unquote(url.path[len(prefix) :])
            elif not url.scheme and not url.netloc:
                target = unquote(url.path) or name
            else:
                continue
            checked += 1
            if target not in pages:
                errors.append(f"{name}: missing Wiki page {href}")
            else:
                edges[name].add(target)
                if (href, label) in page.visible_links:
                    visible_edges[name].add(target)
                if url.fragment and unquote(url.fragment) not in pages[target].anchors:
                    errors.append(f"{name}: missing Wiki anchor {href}")
    manifest_path = directory / "sable-harbor-wiki-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    aliases = {Path(k).stem: Path(v).stem for k, v in manifest.get("aliases", {}).items()}
    for alias, target in aliases.items():
        if alias not in pages or target not in pages or target not in edges.get(alias, set()):
            errors.append(f"{alias}: invalid historical page route to {target}")
    seen, queue = set(), deque(["Home", "_Sidebar", "_Footer"])
    while queue:
        page = queue.popleft()
        if page not in seen:
            seen.add(page)
            queue.extend(edges.get(page, set()) - seen)
    for name in set(pages) - seen - aliases.keys():
        errors.append(f"{name}: unreachable exported Wiki page")
    click_report = {}
    if manifest.get("file_directory"):
        # Measure from the visible Home article alone. This route also works
        # when GitHub collapses its sidebar on narrow screens.
        home_distances = distances(visible_edges, "Home")
        for name in pages.keys() - aliases.keys() - {"_Sidebar", "_Footer"}:
            if home_distances.get(name, 4) > 3:
                errors.append(f"{name}: more than three clicks from Wiki Home")
        prefix = f"https://github.com/{manifest['repository']}/blob/{manifest['source_revision']}/"
        file_depths = {}
        from tools.wiki.files import tracked_files

        expected_files = {p.relative_to(root).as_posix() for p in tracked_files(root)}
        if expected_files != manifest["file_directory"].keys():
            errors.append("File directory differs from the tracked repository inventory")
        for relative, filename in manifest["file_directory"].items():
            page_name = Path(filename).stem
            index_page = pages.get(page_name)
            matching = [
                href
                for href, _ in (index_page.visible_links if index_page else [])
                if href.startswith(prefix)
                and unquote(urlsplit(href).path.split("/", 5)[-1]) == relative
            ]
            if not matching:
                errors.append(f"{relative}: missing visible original-file link in {filename}")
            depth = home_distances.get(page_name, 4) + 1
            file_depths[relative] = depth
            if depth > 3:
                errors.append(f"{relative}: more than three clicks from Wiki Home")
        # The README must offer the same direct entrance to the directory.
        readme_path = root / "README.md"
        if readme_path.exists():
            readme = Page(readme_path.read_text())
            if not any(
                href == "https://github.com/SquirmyWormy275/SABLEHARBOR/wiki/Files"
                for href, _ in readme.visible_links
            ):
                errors.append("README: missing direct All files link")
        else:
            errors.append("README: missing repository entry point")
        click_report = {
            "indexed_files": len(file_depths),
            "maximum_file_clicks": max(file_depths.values(), default=0),
            "maximum_article_clicks": max(
                (
                    home_distances.get(name, 4)
                    for name in pages.keys() - aliases.keys() - {"_Sidebar", "_Footer"}
                ),
                default=0,
            ),
        }
        downloads = manifest.get("release_downloads", [])
        if downloads:
            links = {href for href, _ in pages.get("Downloads", Page("")).visible_links}
            if set(downloads) - links:
                errors.append("Release directory is missing visible asset links")
            if home_distances.get("Downloads", 4) + 1 > 3:
                errors.append("Release downloads require more than three clicks")
            click_report["release_downloads"] = len(downloads)
    return {
        "pages": len(pages),
        "wiki_destinations": checked,
        "reachable_pages": len((seen | aliases.keys()) & pages.keys()),
        "canonical_pages": len(pages) - len(aliases),
        "historical_addresses": len(aliases),
        **click_report,
        "errors": sorted(errors),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()
    report = audit_export(args.export) if args.export else audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report["errors"]))
