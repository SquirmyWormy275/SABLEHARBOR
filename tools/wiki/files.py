"""Build a visible directory of every Git-tracked public repository file."""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

PAGE_SIZE = 250
LABELS = {
    "repository": "Repository guides and configuration",
    "assets": "Artwork and identity",
    "audit_suite_web": "Audit workspace browser",
    "blackridge": "Blackridge case",
    "config": "Model configuration",
    "db": "Database schemas and queries",
    "docs/advisory": "Advisory practice",
    "docs/audit": "Accounting and audit cases",
    "docs/audit-suite": "Audit workspace guides",
    "docs/business-lines": "Business dossiers",
    "docs/canon": "Company decisions and history",
    "docs": "General document indexes",
    "docs/commercialization": "Commercial planning",
    "docs/handoffs": "Document completion guides",
    "docs/procurement": "Procurement records",
    "docs/structured": "Structured company records",
    "docs/technology": "Technology records",
    "docs/controls": "Control framework documents",
    "docs/facilities": "Facility source documents",
    "docs/finance": "Finance and accounting records",
    "docs/governance": "Governance and corporate functions",
    "docs/internal": "Source history and implementation records",
    "docs/j2": "J2 professional practice",
    "docs/legal": "Legal and transaction records",
    "docs/organization": "Organization charts and rosters",
    "docs/reader": "Reading guides and exercises",
    "docs/releases": "Release guides and receipts",
    "docs/wiki": "Wiki articles and document collections",
    "enterprise/audit_suite": "Audit training service",
    "enterprise/business": "Business finance models",
    "enterprise/ccf": "Control examples and assessment tools",
    "enterprise/operations": "Operating models and records",
    "enterprise/runtime": "Runtime design and recovery",
    "enterprise/services": "Shared service records",
    "geospatial/facilities": "Facility plans and source data",
    "geospatial/maps": "Maps and floor plans",
    "industrial": "Industrial cases",
    "red_wash": "Red Wash mining records",
    "releases": "Release manifests",
    "src": "Financial application source",
    "tests": "Tests",
    "tools": "Build and publication tools",
    ".github": "GitHub workflows and templates",
}


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(["git", "ls-files", "--cached", "-z"], cwd=root, capture_output=True)
    if result.returncode:
        # Standalone exporter fixtures need no repository-wide file directory.
        if not (root / "docs/wiki/Files.md").exists():
            return []
        raise ValueError("Cannot inventory tracked repository files")
    files = []
    for relative in sorted(set(result.stdout.decode().split("\0")) - {""}):
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f"Tracked file is missing or outside the checkout: {relative}")
        files.append(path)
    return files


def collection(relative: Path) -> str:
    parts = relative.parts
    if len(parts) == 1:
        return "repository"
    if parts[0] in {"docs", "enterprise", "geospatial"} and len(parts) > 2:
        return "/".join(parts[:2])
    return parts[0]


def build_directory(root: Path, files: list[Path], revision: str, names: dict) -> tuple:
    groups = defaultdict(list)
    for path in files:
        groups[collection(path.relative_to(root))].append(path)
    pages, routes, index = {}, {}, []
    for key in sorted(groups, key=lambda k: (k != "repository", k)):
        sources = groups[key]
        label = LABELS.get(key, key.split("/")[-1].replace("_", " ").replace("-", " ").title())
        for start in range(0, len(sources), PAGE_SIZE):
            batch = sources[start : start + PAGE_SIZE]
            part = start // PAGE_SIZE + 1
            suffix = f"-{part}" if len(sources) > PAGE_SIZE else ""
            slug = re.sub(r"[^a-zA-Z0-9-]", "-", key).strip("-")
            name = f"Files--{slug}{suffix}"
            title = label + (f" — part {part}" if suffix else "")
            index.append(f"| [{title}]({name}) | {len(batch)} |")
            rows = [
                f"# {title}",
                "",
                "[All files](Files) · [Wiki home](Home)",
                "",
                "Open a file below. Paths identify the original files, including older editions.",
                "",
            ]
            for path in batch:
                relative = path.relative_to(root).as_posix()
                url = f"https://github.com/SquirmyWormy275/SABLEHARBOR/blob/{revision}/{quote(relative, safe='/')}"
                # Escaping protects filenames without replacing their visible spelling.
                text = relative.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
                row = f"- [{text}]({url})"
                if path in names:
                    row += f" · [Read in the Wiki]({quote(names[path])})"
                rows.append(row)
                routes[relative] = name + ".md"
            pages[name + ".md"] = "\n".join(rows) + "\n"
    return (
        pages,
        routes,
        "\n".join(
            [
                "## Browse all files",
                "",
                f"This directory lists all {len(files):,} files in the published repository snapshot. "
                "Each link opens the original file. Use your browser’s Find command to locate a filename in a collection.",
                "",
                "| Collection | Files |",
                "|---|---:|",
                *index,
                "",
            ]
        ),
    )


def release_downloads(root: Path) -> tuple[dict, list[str]]:
    source = root / "tools/wiki/downloads.json"
    if not source.exists():
        return {}, []
    inventory = json.loads(source.read_text())
    rows = [
        "# Release downloads",
        "",
        "[All files](Files) · [Wiki home](Home)",
        "",
        "Download a published package or companion file below. Keep its guide, manifest "
        "and checksums with the files when working through an exercise.",
        "",
    ]
    urls = []
    for release in inventory["releases"]:
        rows.extend(
            [
                f"## {release['title'] or release['tag']}",
                "",
                f"[Release notes]({release['url']}) · `{release['tag']}`",
                "",
            ]
        )
        for asset in release["assets"]:
            url = asset["url"]
            if not url.startswith(
                "https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/"
            ):
                raise ValueError("Release asset is outside the public repository")
            label = asset["name"].replace("[", "\\[").replace("]", "\\]")
            rows.append(f"- [{label}]({url})")
            urls.append(url)
        rows.append("")
    return {"Downloads.md": "\n".join(rows)}, urls
