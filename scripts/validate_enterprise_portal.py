#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs/business-lines/registry.json"
REQUIRED_HEADINGS = (
    "## Status and scope",
    "## Canon and history",
    "## Identity and collateral",
    "## Organization and authority",
    "## Financials and accounting",
    "## Inventory, assets, and operations",
    "## Database and exports",
    "## Audit controls and unresolved facts",
    "## Download map",
)
REQUIRED_CENTRAL_FILES = (
    "README.md",
    "LICENSE.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/README.md",
    "docs/company/README.md",
    "docs/company/manifest.json",
    "docs/business-lines/README.md",
    "docs/business-lines/registry.json",
    "docs/data/README.md",
    "docs/data/FINANCE_RELEASE_CANDIDATE.md",
    "docs/audit/README.md",
    "docs/audit/REPOSITORY_AUDIT_v0.1.md",
    "docs/audit/BRANCH_AND_PR_REGISTER.md",
    "docs/audit/BUSINESS_LINE_AUDIT_MATRIX.md",
    "docs/audit/UNIT_PACKAGE_STANDARD.md",
    "docs/governance/REPOSITORY_INFORMATION_ARCHITECTURE.md",
    "docs/governance/ARTIFACT_STATUS_POLICY.md",
    "docs/wiki/Home.md",
    "docs/wiki/_Sidebar.md",
    "docs/wiki/PUBLISH_STATUS.md",
)
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".json", ".txt", ".toml"}
SECRET_MARKERS = ("ghp_", "github_pat_", "sk-proj-", "BEGIN PRIVATE KEY")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_file(relative: str, errors: list[str]) -> Path:
    path = ROOT / relative
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        errors.append(f"missing or empty required file: {relative}")
    return path


def iter_portal_markdown() -> Iterable[Path]:
    explicit = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "docs/README.md",
        ROOT / "docs/organization/README.md",
        ROOT / "assets/brand/README.md",
        ROOT / "assets/brand/collateral/README.md",
    ]
    yielded: set[Path] = set()
    for path in explicit:
        if path.exists() and path not in yielded:
            yielded.add(path)
            yield path
    for pattern in (
        "docs/company/**/*.md",
        "docs/business-lines/*.md",
        "docs/data/*.md",
        "docs/audit/*.md",
        "docs/governance/*.md",
    ):
        for path in sorted(ROOT.glob(pattern)):
            if path not in yielded:
                yielded.add(path)
                yield path


def check_local_links(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for raw_target in MARKDOWN_LINK.findall(text):
        target = raw_target.strip().strip("<>")
        if not target or target.startswith(("http://", "https://", "mailto:", "#", "data:")):
            continue
        target = target.split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        target = unquote(target)
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"link escapes repository: {path.relative_to(ROOT)} -> {raw_target}")
            continue
        if not resolved.exists():
            errors.append(f"broken local link: {path.relative_to(ROOT)} -> {raw_target}")


def tracked_files() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z"], check=True, capture_output=True
    ).stdout.decode("utf-8")
    return [ROOT / name for name in output.split("\0") if name]


def check_tracked_hygiene(errors: list[str]) -> None:
    forbidden_parts = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv"}
    forbidden_prefixes = (
        "var/",
        "data/generated/",
        "workbooks/outputs/",
        "releases/generated/",
    )
    for path in tracked_files():
        relative = path.relative_to(ROOT)
        posix = relative.as_posix()
        if forbidden_parts.intersection(relative.parts):
            errors.append(f"tracked cache/environment path: {posix}")
        if path.suffix in {".pyc", ".pyo"} or path.name in {".DS_Store", ".env"}:
            errors.append(f"tracked transient or sensitive file: {posix}")
        if posix.startswith(forbidden_prefixes) or (
            posix.startswith("reports/") and path.suffix.lower() == ".xlsx"
        ):
            errors.append(f"tracked generated output: {posix}")
        if path == ROOT / "scripts/validate_enterprise_portal.py":
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for marker in SECRET_MARKERS:
                if marker in text:
                    errors.append(f"possible credential marker {marker!r}: {posix}")


def main() -> None:
    errors: list[str] = []
    for relative in REQUIRED_CENTRAL_FILES:
        require_file(relative, errors)

    registry = load_json(REGISTRY_PATH)
    units = registry.get("units", [])
    if len(units) != 13:
        errors.append(f"registry must contain 13 dossiers; observed {len(units)}")

    finance = registry.get("finance_release_candidate", {})
    finance_commit = str(finance.get("commit", ""))
    if not COMMIT_SHA.fullmatch(finance_commit):
        errors.append("finance release-candidate commit must be a 40-character SHA")
    if finance.get("status") != "RELEASE_CANDIDATE_NOT_ACCEPTED":
        errors.append("finance platform must remain explicitly not accepted")

    company_manifest = load_json(ROOT / "docs/company/manifest.json")
    company_finance = company_manifest.get("finance_release_candidate", {})
    if company_finance.get("commit") != finance_commit:
        errors.append("company manifest and unit registry pin different finance commits")
    if company_finance.get("status") == "ACCEPTED":
        errors.append("company manifest incorrectly accepts finance release candidate")

    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    business_index = (ROOT / "docs/business-lines/README.md").read_text(encoding="utf-8")
    sidebar = (ROOT / "docs/wiki/_Sidebar.md").read_text(encoding="utf-8")
    data_register = (ROOT / "docs/data/FINANCE_RELEASE_CANDIDATE.md").read_text(
        encoding="utf-8"
    )
    if finance_commit not in root_readme or finance_commit not in data_register:
        errors.append("finance pin is not synchronized across root README and data register")
    if "NOT ACCEPTED" not in data_register.upper():
        errors.append("finance data register does not state NOT ACCEPTED")

    slugs: set[str] = set()
    names: set[str] = set()
    dossiers: set[str] = set()
    classifications: dict[str, int] = {}
    allowed_parent_slugs = {"sable-harbor"}

    for unit in units:
        slug = str(unit.get("slug", ""))
        name = str(unit.get("display_name", ""))
        dossier_relative = str(unit.get("dossier", ""))
        classification = str(unit.get("classification", ""))
        parent = unit.get("parent_slug")

        if not slug or slug in slugs:
            errors.append(f"missing or duplicate unit slug: {slug!r}")
        slugs.add(slug)
        if not name or name in names:
            errors.append(f"missing or duplicate unit display name: {name!r}")
        names.add(name)
        if not dossier_relative or dossier_relative in dossiers:
            errors.append(f"missing or duplicate dossier path: {dossier_relative!r}")
        dossiers.add(dossier_relative)
        classifications[classification] = classifications.get(classification, 0) + 1

        dossier = require_file(dossier_relative, errors)
        if dossier.exists():
            text = dossier.read_text(encoding="utf-8")
            for heading in REQUIRED_HEADINGS:
                if heading not in text:
                    errors.append(f"{dossier_relative}: missing heading {heading!r}")
            if "NOT MATERIALIZED" not in text:
                errors.append(f"{dossier_relative}: missing explicit NOT MATERIALIZED boundary")

        if dossier_relative not in root_readme:
            errors.append(f"root README does not link dossier: {dossier_relative}")
        if Path(dossier_relative).name not in business_index:
            errors.append(f"business-line index does not link dossier: {dossier_relative}")
        if name not in sidebar:
            errors.append(f"wiki sidebar does not list unit: {name}")

        wiki_page = ROOT / "docs/wiki" / f"{name}.md"
        require_file(str(wiki_page.relative_to(ROOT)), errors)

        organization_page = str(unit.get("organization_page", ""))
        require_file(organization_page, errors)
        organization_asset = unit.get("organization_asset")
        if organization_asset:
            require_file(str(organization_asset), errors)

        logo_slug = unit.get("logo_slug")
        if logo_slug:
            require_file(f"assets/brand/logos/{logo_slug}__primary-horizontal.svg", errors)
            require_file(f"assets/brand/logos/{logo_slug}__mark.svg", errors)

        if unit.get("standalone_package_status") != "NOT_MATERIALIZED":
            errors.append(f"{slug}: standalone unit package is incorrectly marked available")
        if "ACCEPTED" in str(unit.get("unit_letterhead_status", "")):
            errors.append(f"{slug}: unit letterhead is incorrectly marked accepted")
        if parent not in (None, "sable-harbor"):
            allowed_parent_slugs.add(str(parent))

    unknown_parents = allowed_parent_slugs - slugs - {"sable-harbor"}
    if unknown_parents:
        errors.append(f"registry contains unknown parent slugs: {sorted(unknown_parents)}")

    current_count = sum(
        classifications.get(key, 0)
        for key in (
            "CURRENT_BUSINESS_LINE",
            "CURRENT_OPERATING_COMPANY_AND_BUSINESS_LINE",
            "EMERGING_CURRENT_BUSINESS_LINE",
        )
    )
    component_count = sum(
        classifications.get(key, 0)
        for key in ("PRODUCT_SUBSTRATE", "OPERATING_ASSET", "OPERATING_COMPONENT")
    )
    historical_count = sum(
        classifications.get(key, 0)
        for key in ("HISTORICAL_BUSINESS_LINE", "HISTORICAL_PREDECESSOR")
    )
    if (current_count, component_count, historical_count) != (7, 3, 2):
        errors.append(
            "classification totals must be 7 current, 3 component/substrate, "
            f"2 historical; observed {(current_count, component_count, historical_count)}"
        )
    if classifications.get("SEPARATE_CASE_UNIVERSE") != 1:
        errors.append("registry must contain exactly one separate case universe")

    for path in iter_portal_markdown():
        check_local_links(path, errors)
    check_tracked_hygiene(errors)

    if errors:
        print("\n".join(sorted(set(errors))))
        raise SystemExit(1)

    print(
        "PASS: enterprise portal, 13 unit dossiers, registry, wiki mirror, local links, "
        "artifact states, and tracked-file hygiene validated."
    )


if __name__ == "__main__":
    main()
