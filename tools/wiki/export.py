#!/usr/bin/env python3
"""Export accepted wiki Markdown without modifying sources or copying asset bytes."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from markdown_it import MarkdownIt

REPOSITORY = "SquirmyWormy275/SABLEHARBOR"
MANIFEST = "sable-harbor-wiki-manifest.json"
MARKDOWN = MarkdownIt("commonmark", {"html": True}).enable("table")
# Repository Markdown uses inline destinations or reference definitions. Unsupported
# syntax is rejected by parsing the result and checking for unresolved local links.
INLINE = re.compile(r'(\]\()(<[^>\n]+>|[^\s()]+)(?=\s*(?:["\'][^\n]*["\']\s*)?\))')
REFERENCE = re.compile(r"^( {0,3}\[[^\]\n]+\]:\s*)(<[^>\n]+>|\S+)", re.M)
ATTRIBUTE = re.compile(r'\b(href|src)\s*=\s*(["\'])(.*?)\2', re.I)
CODE = re.compile(
    r"(^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?^ {0,3}\2\s*$|`+[^`\n]*`+)", re.M
)


class Exporter:
    def __init__(self, root: Path, revision: str):
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("revision must be a full Git commit SHA")
        self.root = root.resolve()
        self.revision = revision
        self.wiki = self.root / "docs/wiki"
        self.pages = sorted(self.wiki.rglob("*.md"))
        self.names = {
            p: "--".join(p.relative_to(self.wiki).with_suffix("").parts)
            for p in self.pages
        }
        if len({name.casefold() for name in self.names.values()}) != len(self.names):
            raise ValueError("Wiki page names collide after flattening")
        if self.wiki / "Home.md" not in self.names:
            raise ValueError("Wiki Home.md is required")
        self.links = 0
        plan = self.root / "tools/wiki/reading.json"
        self.reading = json.loads(plan.read_text()) if plan.exists() else {"sources": [], "articles": {}}
        for page in self.reading["articles"]:
            if (self.wiki / page).resolve() not in self.pages:
                raise ValueError(f"Article target is not a Wiki page: {page}")
        self.records = []
        for relative in self.reading["sources"]:
            source = (self.root / relative).resolve()
            if not source.is_relative_to(self.root) or not source.is_file() or source.suffix != ".md":
                raise ValueError(f"Invalid reading source: {relative}")
            if source in self.names:
                raise ValueError(f"Reading source duplicates a Wiki page: {relative}")
            self.names[source] = "records--" + "--".join(Path(relative).with_suffix("").parts)
            self.records.append(source)
        if len({name.casefold() for name in self.names.values()}) != len(self.names):
            raise ValueError("Reading page names collide")

    def target(self, source: Path, value: str, image: bool = False) -> str:
        parsed = urlsplit(html.unescape(value))
        if parsed.scheme or parsed.netloc:
            return value
        if not parsed.path:
            if parsed.fragment and source in self.records:
                return f"https://github.com/{REPOSITORY}/wiki/{quote(self.names[source])}#{parsed.fragment}"
            return value
        target = (source.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(self.root) or not target.exists():
            raise ValueError(
                f"{source.relative_to(self.root)}: missing/outside target {value}"
            )
        self.links += 1
        base = f"https://github.com/{REPOSITORY}"
        if target in self.names and not image:
            path = f"{base}/wiki/{quote(self.names[target])}"
        else:
            relative = quote(target.relative_to(self.root).as_posix(), safe="/")
            if image:
                path = f"https://raw.githubusercontent.com/{REPOSITORY}/{self.revision}/{relative}"
            else:
                kind = "tree" if target.is_dir() else "blob"
                path = f"{base}/{kind}/{self.revision}/{relative}"
        return urlunsplit((*urlsplit(path)[:3], parsed.query, parsed.fragment))

    def rewrite(self, source: Path, original: str | None = None) -> str:
        original = source.read_text() if original is None else original
        image_targets = set()
        for token in MARKDOWN.parse(original):
            for child in token.children or []:
                if child.type == "image":
                    image_targets.add(child.attrGet("src"))

        def destination(match):
            value = match[2]
            bracketed = value.startswith("<")
            value = value[1:-1] if bracketed else value
            # Image destinations need raw bytes. Ordinary links to images use blob URLs.
            image = value in image_targets
            value = self.target(source, value, image=image)
            return match[1] + (f"<{value}>" if bracketed else value)

        def prose(value):
            value = INLINE.sub(destination, value)
            value = REFERENCE.sub(destination, value)
            return ATTRIBUTE.sub(
                lambda m: (
                    f"{m[1]}={m[2]}{self.target(source, m[3], m[1].lower() == 'src')}{m[2]}"
                ),
                value,
            )

        chunks, offset = [], 0
        for match in CODE.finditer(original):
            chunks.extend((prose(original[offset : match.start()]), match[0]))
            offset = match.end()
        chunks.append(prose(original[offset:]))
        result = "".join(chunks)
        # Render solely for validation: catches unresolved destinations in unsupported
        # Markdown syntax, including references, nested links and raw HTML.
        rendered = MARKDOWN.render(result)
        for match in ATTRIBUTE.finditer(rendered):
            parsed = urlsplit(html.unescape(match[3]))
            if parsed.path and not parsed.scheme and not parsed.netloc:
                raise ValueError(f"Unconverted link in {source}: {match[3]}")
        return result

    @staticmethod
    def contents(text: str) -> str:
        counts = {}
        rows = []
        tokens = MARKDOWN.parse(text)
        for i, token in enumerate(tokens):
            if token.type != "heading_open":
                continue
            title = tokens[i + 1].content
            plain = html.unescape(re.sub(r"<[^>]+>", "", MARKDOWN.renderInline(title)))
            slug = re.sub(r"[^\w\- ]", "", plain.lower()).replace(" ", "-")
            occurrence = counts.get(slug, 0)
            counts[slug] = occurrence + 1
            anchor = slug + (f"-{occurrence}" if occurrence else "")
            if token.tag in ("h2", "h3"):
                rows.append(f"- [{title}](#{anchor})")
        if len(rows) < 3:
            return text
        navigation = "<details>\n<summary>On this page</summary>\n\n" + "\n".join(rows) + "\n\n</details>\n\n"
        first = re.search(r"^## ", text, re.M)
        if first:
            return text[:first.start()] + navigation + text[first.start():]
        return text

    def source_link(self, source: Path) -> str:
        relative = quote(source.relative_to(self.root).as_posix(), safe="/")
        return f"https://github.com/{REPOSITORY}/blob/{self.revision}/{relative}"

    def excerpt(self, entry: dict) -> str:
        source = (self.root / entry["source"]).resolve()
        if source not in self.records:
            raise ValueError(f"Article source absent from reading inventory: {source}")
        original = source.read_text()
        tokens = MARKDOWN.parse(original)
        lines = original.splitlines(keepends=True)
        sections = entry.get("sections")
        if sections:
            ranges = []
            found = []
            headings = [(i, t) for i, t in enumerate(tokens) if t.type == "heading_open" and t.tag == "h2"]
            for position, (i, token) in enumerate(headings):
                title = tokens[i + 1].content
                if title in sections:
                    end = headings[position + 1][1].map[0] if position + 1 < len(headings) else len(lines)
                    ranges.append("".join(lines[token.map[0]:end]))
                    found.append(title)
            if set(found) != set(sections):
                raise ValueError(f"Unmatched article sections in {source}: {set(sections) - set(found)}")
            original = "\n".join(ranges)
        # Demote only real parsed headings; code examples are retained verbatim.
        lines = original.splitlines(keepends=True)
        for token in reversed(MARKDOWN.parse(original)):
            if token.type == "heading_open":
                start, end = token.map
                level = int(token.tag[1])
                if level == 1:
                    del lines[start:end]
                else:
                    title = " ".join(line.strip().lstrip("#").strip() for line in lines[start:end])
                    lines[start:end] = ["#" * min(level + 1, 6) + " " + title + "\n"]
        body = self.rewrite(source, "".join(lines).strip())
        title = re.search(r"^# (.+)$", source.read_text(), re.M)
        label = title[1] if title else source.stem
        return (
            f"### Source: {label}\n\n"
            f"[Full reading edition](https://github.com/{REPOSITORY}/wiki/{quote(self.names[source])}) · "
            f"[Repository source]({self.source_link(source)})\n\n"
            "Source wording follows. Its dates, qualifications and supersession scope apply; "
            "this reading edition does not resolve open decisions.\n\n" + body + "\n"
        )

    def article(self, page: Path) -> str:
        result = self.rewrite(page)
        entries = self.reading["articles"].get(page.relative_to(self.wiki).as_posix(), [])
        if entries:
            chapter = "\n## In-depth reading\n\n" + "\n".join(self.excerpt(e) for e in entries) + "\n"
            # Keep the identity and overview first, followed by substantive source text.
            match = re.search(r"^## (?:Read and use the records|Organization and people|Organization and identity|Operating, legal and control records)", result, re.M)
            if match:
                result = result[:match.start()] + chapter + result[match.start():]
            else:
                result += chapter
        return result

    def reading_pages(self) -> dict[str, str]:
        result = {}
        groups = {}
        for source in self.records:
            relative = source.relative_to(self.root)
            group = (relative.parts[1] if len(relative.parts) > 2 else "reference") if relative.parts[0] == "docs" else (relative.parts[0] if len(relative.parts) > 1 else "reference")
            groups.setdefault(group, []).append(source)
            title = re.search(r"^# (.+)$", source.read_text(), re.M)
            label = title[1] if title else source.stem
            nav = (
                f"[Wiki home](https://github.com/{REPOSITORY}/wiki/Home) · "
                f"[Reading room](https://github.com/{REPOSITORY}/wiki/Reading) · "
                f"[Topic](https://github.com/{REPOSITORY}/wiki/Reading--{quote(group)}) · "
                f"[Repository source]({self.source_link(source)})\n\n"
                "**Reading edition:** Full source text from the published repository snapshot. "
                "Original status, dates, historical limits and later supersession still apply.\n\n"
            )
            result[self.names[source] + ".md"] = nav + self.rewrite(source)
        index = ["# Reading room", "", "Read the accepted public records in full inside the Wiki. Business and department articles include their core operating text; these editions provide the supporting doctrine, rosters, history, finance, places and exercises.", "", "[Wiki home](Home) · [Businesses](businesses--README) · [Departments](departments--README) · [History](subjects--README)", "", "Source wording is preserved. Acceptance into the repository does not turn a provisional assumption, historical proposal, generated scenario or open decision into established fact. Pending legal publications and private evidence are outside this edition.", ""]
        for group, sources in sorted(groups.items()):
            index.append(f"- [{group.replace('-', ' ').title()}](Reading--{group}) — {len(sources)} full records")
            rows = [f"# {group.replace('-', ' ').title()} reading room", "", "[All topics](Reading) · [Wiki home](Home)", ""]
            for source in sorted(sources):
                heading = re.search(r"^# (.+)$", source.read_text(), re.M)
                label = heading[1] if heading else source.stem
                rows.append(f"- [{label}]({quote(self.names[source])})")
            result[f"Reading--{group}.md"] = "\n".join(rows) + "\n"
        result["Reading.md"] = "\n".join(index) + "\n"
        return result

    def build(self, output: Path) -> dict:
        output = output.resolve()
        if output == self.root or output.is_relative_to(self.root):
            raise ValueError("Export output must be outside the source checkout")
        if output.exists() and any(output.iterdir()):
            raise ValueError("Export output must be empty")
        # Validate everything before writing any publication files.
        content = {self.names[p] + ".md": self.article(p) for p in self.pages}
        if self.records:
            content.update(self.reading_pages())
        sidebar = [
            "# Sable Harbor",
            "",
            "[Home](Home)",
            "",
            "- [Business directory](businesses--README)",
            "- [Department directory](departments--README)",
            "- [History and subjects](subjects--README)",
            "- [Document library](Library)",
            *(["- [Full-text reading room](Reading)"] if self.records else []),
            "",
        ]
        for directory, title in (
            ("businesses", "Businesses"),
            ("departments", "Departments and institutions"),
            ("subjects", "History and subjects"),
        ):
            sidebar.extend([f"## {title}", ""])
            for page in self.pages:
                if page.parent.name == directory and page.stem != "README":
                    heading = re.search(r"^# (.+)$", page.read_text(), re.M)
                    label = heading[1] if heading else page.stem
                    sidebar.append(f"- [{label}]({self.names[page]})")
            sidebar.append("")
        content = {name: self.contents(body) for name, body in content.items()}
        content["_Sidebar.md"] = "\n".join(sidebar) + "\n"
        output.mkdir(parents=True, exist_ok=True)
        files = {}
        for name, text in sorted(content.items()):
            payload = text.encode()
            (output / name).write_bytes(payload)
            files[name] = hashlib.sha256(payload).hexdigest()
        manifest = {
            "repository": REPOSITORY,
            "source_revision": self.revision,
            "source_directory": "docs/wiki",
            "converted_links": self.links,
            "files": files,
            "reading_sources": {
                str(p.relative_to(self.root)): {
                    "page": self.names[p] + ".md",
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                } for p in self.records
            },
            "expanded_articles": sorted(self.reading["articles"]),
        }
        (output / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
        return manifest


def sync(export: Path, wiki: Path):
    """Update only manifest-owned files; preserve unrelated wiki pages and history."""
    new = json.loads((export / MANIFEST).read_text())
    old_path = wiki / MANIFEST
    if old_path.is_symlink():
        raise ValueError("Refusing wiki manifest symlink")
    old = json.loads(old_path.read_text()) if old_path.exists() else {"files": {}}
    for manifest in (old, new):
        for name in manifest["files"]:
            if Path(name).name != name or not name.endswith(".md"):
                raise ValueError("Unsafe manifest filename")
            if (wiki / name).is_symlink():
                raise ValueError("Refusing wiki symlink")
    for name, digest in new["files"].items():
        if hashlib.sha256((export / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Export checksum mismatch: {name}")
    for name in old["files"].keys() - new["files"].keys():
        (wiki / name).unlink(missing_ok=True)
    for name in new["files"]:
        shutil.copyfile(export / name, wiki / name)
    shutil.copyfile(export / MANIFEST, wiki / MANIFEST)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sync-to", type=Path)
    args = parser.parse_args()
    manifest = Exporter(args.root, args.revision).build(args.output)
    if args.sync_to:
        sync(args.output, args.sync_to)
    print(
        f"Exported {len(manifest['files'])} pages; converted {manifest['converted_links']} links"
    )
