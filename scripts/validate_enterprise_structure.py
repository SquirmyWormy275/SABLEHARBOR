#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/enterprise/business_units.json"


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    if not REGISTRY.exists():
        print(f"missing registry: {REGISTRY}")
        return 1
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    units = data.get("units", [])
    if len(units) != 7:
        fail(errors, f"expected 7 current business lines, found {len(units)}")
    ids = [unit.get("id") for unit in units]
    if len(ids) != len(set(ids)):
        fail(errors, "duplicate business-unit IDs")

    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = ROOT / "docs/business-lines/README.md"
    if not index.exists():
        fail(errors, "missing business-line index")
    else:
        index_text = index.read_text(encoding="utf-8")
        for unit in units:
            page_rel = f"docs/business-lines/{unit['page']}"
            wiki_rel = f"docs/wiki/{unit['wiki']}"
            required = [
                page_rel,
                wiki_rel,
                unit["org_page"],
                unit["org_chart"],
                f"assets/brand/logos/{unit['logo_slug']}__primary-horizontal.svg",
                f"assets/brand/logos/{unit['logo_slug']}__primary-horizontal.png",
                f"assets/brand/logos/{unit['logo_slug']}__stacked.svg",
                f"assets/brand/logos/{unit['logo_slug']}__mark.svg",
                f"assets/brand/logos/{unit['logo_slug']}__reverse-horizontal.svg",
                f"assets/brand/logos/{unit['logo_slug']}__one-color-horizontal.svg",
                f"assets/brand/collateral/letterhead/business-lines/{unit['letterhead_slug']}-letterhead-us-letter.svg",
            ]
            required.extend(unit.get("canon_links", []))
            required.extend(f"db/sql/{name}.sql" for name in unit.get("queries", []))
            for rel in required:
                path = ROOT / rel
                if not path.exists() or (path.is_file() and path.stat().st_size == 0):
                    fail(errors, f"{unit['id']}: missing/empty {rel}")
            if unit["page"] not in root_readme:
                fail(errors, f"root README missing {unit['page']}")
            if unit["page"] not in index_text:
                fail(errors, f"business-line index missing {unit['page']}")
            page = ROOT / page_rel
            if page.exists():
                text = page.read_text(encoding="utf-8")
                for marker in ("Standalone export", "NOT IMPLEMENTED", "Unit export specification"):
                    if marker not in text:
                        fail(errors, f"{unit['id']}: dossier missing marker {marker!r}")

    required_enterprise = [
        "docs/company/README.md",
        "docs/audit/REPOSITORY_AUDIT_2026-09-01.md",
        "docs/audit/BRANCH_AND_PR_REGISTER.md",
        "docs/audit/UNIT_EXPORT_SPECIFICATION.md",
        "docs/governance/REPOSITORY_GOVERNANCE.md",
        "docs/wiki/Home.md",
        "docs/wiki/_Sidebar.md",
        "docs/wiki/PUBLISH_STATUS.md",
        "db/README.md",
    ]
    for rel in required_enterprise:
        if not (ROOT / rel).exists():
            fail(errors, f"missing enterprise control file: {rel}")

    forbidden_names = {".connector-push-probe", ".DS_Store", "Thumbs.db"}
    for path in ROOT.rglob("*"):
        if path.name in forbidden_names or path.suffix == ".pyc" or "__pycache__" in path.parts:
            fail(errors, f"repository hygiene artifact present: {path.relative_to(ROOT)}")

    if errors:
        print("ENTERPRISE STRUCTURE VALIDATION FAILED")
        print("\n".join(f"- {item}" for item in errors))
        return 1
    print(f"PASS: {len(units)} business-line dossiers, identity/organization/data links, wiki source, and hygiene controls validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
