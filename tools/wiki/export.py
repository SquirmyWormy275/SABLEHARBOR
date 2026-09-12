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
CODE = re.compile(r"(^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?^ {0,3}\2\s*$|`+[^`\n]*`+)", re.M)


class Exporter:
    def __init__(self, root: Path, revision: str):
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("revision must be a full Git commit SHA")
        self.root = root.resolve()
        self.revision = revision
        self.wiki = self.root / "docs/wiki"
        self.pages = sorted(self.wiki.rglob("*.md"))
        self.names = {
            p: "--".join(p.relative_to(self.wiki).with_suffix("").parts) for p in self.pages
        }
        if len({name.casefold() for name in self.names.values()}) != len(self.names):
            raise ValueError("Wiki page names collide after flattening")
        if self.wiki / "Home.md" not in self.names:
            raise ValueError("Wiki Home.md is required")
        self.links = 0

    def target(self, source: Path, value: str, image: bool = False) -> str:
        parsed = urlsplit(html.unescape(value))
        if parsed.scheme or parsed.netloc or not parsed.path:
            return value
        target = (source.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(self.root) or not target.exists():
            raise ValueError(f"{source.relative_to(self.root)}: missing/outside target {value}")
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

    def rewrite(self, source: Path) -> str:
        original = source.read_text()
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
                lambda m: f"{m[1]}={m[2]}{self.target(source, m[3], m[1].lower() == 'src')}{m[2]}",
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

    def build(self, output: Path) -> dict:
        output = output.resolve()
        if output == self.root or output.is_relative_to(self.root):
            raise ValueError("Export output must be outside the source checkout")
        if output.exists() and any(output.iterdir()):
            raise ValueError("Export output must be empty")
        # Validate everything before writing any publication files.
        content = {self.names[p] + ".md": self.rewrite(p) for p in self.pages}
        sidebar = ["# Sable Harbor", "", "[Home](Home)", "[Library](Library)", ""]
        sidebar.extend(
            f"- [{p.stem}]({self.names[p]})"
            for p in self.pages
            if p.parent.name == "businesses" and p.stem != "README"
        )
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
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sync-to", type=Path)
    args = parser.parse_args()
    manifest = Exporter(args.root, args.revision).build(args.output)
    if args.sync_to:
        sync(args.output, args.sync_to)
    print(f"Exported {len(manifest['files'])} pages; converted {manifest['converted_links']} links")
