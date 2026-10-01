"""Build the complete geographic 1.5 distribution from immutable 1.4 bytes.

The predecessor ZIP is nested verbatim. This module never writes a tracked
source or modifies the predecessor. The final package is built on accepted
main; ``--preview`` permits a review build from a pending worktree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE_NAME = "sable-harbor-geographic-evidence-v1.4.0.zip"
BASE_SHA256 = "f106e164a7578d64c32ba1bcc9444b3a96d89881d7c7b92b51bb97cf2bef6df4"
VERSION = "1.5.0"
SUPPLEMENT_DIRS = (
    "geospatial/successor_20260929",
    "geospatial/successor_20260929_final",
    "geospatial/successors/rail_history_2026_09_29",
    "geospatial/engineering_review/interface_successor_20260929",
    "industrial/successors/rail_2026_09_29",
)
SUPPLEMENT_FILES = (
    "docs/canon/GEOGRAPHIC_SYNTHETIC_SCOPE_DISPOSITION_2026-09-29.md",
    "geospatial/docs/PROGRAM_CLOSEOUT_MATRIX.md",
    "geospatial/docs/NEXT_CHAT_HANDOFF.md",
    "geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.json",
    "geospatial/engineering_review/COMPENSATED_40_MILE_CANDIDATE.geojson",
    "geospatial/successors/RAIL_GEO_107_108_DISPOSITION_2026-09-29.md",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_paths() -> list[str]:
    paths = set(SUPPLEMENT_FILES)
    for folder in SUPPLEMENT_DIRS:
        paths.update(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / folder).rglob("*")
            if path.is_file()
            and not any(
                part in {"__pycache__", ".pytest_cache", ".ruff_cache"} for part in path.parts
            )
            and path.suffix != ".pyc"
        )
    if not all((ROOT / path).is_file() for path in paths):
        raise ValueError("A required supplement source is missing")
    return sorted(paths)


def source_revision(preview: bool) -> str:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not preview:
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
            raise ValueError("Final release requires a clean accepted checkout")
        accepted = subprocess.check_output(
            ["git", "rev-parse", "refs/remotes/origin/main"], cwd=ROOT, text=True
        ).strip()
        if accepted != revision:
            raise ValueError("Final release must match the fetched accepted origin/main")
    return revision


def index_html() -> bytes:
    return b"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>Sable Harbor geographic evidence 1.5.0</title>
<h1>Sable Harbor geographic evidence 1.5.0</h1>
<p>Offline synthetic company edition. Extract this package with the documented
import command before opening these links. The unchanged 1.4 evidence base and
dated supplement are both required. Proposed geometry is not surveyed property.</p>
<ul>
<li><a href="base/finalization/index.html">Accepted 1.4 source review</a></li>
<li><a href="base/completion/maps/index.html">Accepted 1.4 map atlas</a></li>
<li><a href="supplement/geospatial/successors/rail_history_2026_09_29/case.svg">Provisional fictional 1954 case</a></li>
<li><a href="supplement/geospatial/engineering_review/interface_successor_20260929/README.md">Current 40-mile site and turnout register</a></li>
<li><a href="supplement/geospatial/successor_20260929_final/README.md">Source delta and limitations</a></li>
</ul></html>"""


def build(base: Path, output: Path, *, preview: bool = False) -> dict:
    if sha256_file(base) != BASE_SHA256:
        raise ValueError("Immutable 1.4 package hash mismatch")
    with zipfile.ZipFile(base) as archive:
        prior = json.loads(archive.read("PACKAGE_MANIFEST.json"))
        if (
            prior.get("version") != "1.4.0"
            or prior.get("source_revision") != "78d4fcdf1df5b8ffc0775b9af22cae1002d456d7"
            or len(prior.get("files", {})) != 1907
        ):
            raise ValueError("Unexpected predecessor manifest")
    revision = source_revision(preview)
    entries = {"base/" + BASE_NAME: {"bytes": base.stat().st_size, "sha256": BASE_SHA256}}
    for path in source_paths():
        source = ROOT / path
        entries["supplement/" + path] = {
            "bytes": source.stat().st_size,
            "sha256": sha256_file(source),
        }
    entries["index.html"] = {
        "bytes": len(index_html()),
        "sha256": hashlib.sha256(index_html()).hexdigest(),
    }
    manifest = {
        "version": VERSION,
        "status": "PREVIEW_UNACCEPTED"
        if preview
        else "ACCEPTED_SOURCE_PACKAGE_PENDING_PUBLICATION",
        "source_revision": revision,
        "base_version": "1.4.0",
        "base_source_revision": prior["source_revision"],
        "base_member_count": len(prior["files"]),
        "base_sha256": BASE_SHA256,
        "supplement_entries": len(entries) - 2,
        "scope": "Finite synthetic company geographic edition at planning precision",
        "limits": [
            "The nested 1.4 archive is byte-identical to its accepted release.",
            "The 1954 case is newly authored fiction, not a recovered survey or real right.",
            "External parcels, field certification, real title and proposed-lead service remain unestablished.",
            "Source acceptance and GitHub publication are distinct from a preview package.",
        ],
        "files": dict(sorted(entries.items())),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
        for path, meta in sorted(entries.items()):
            info = zipfile.ZipInfo(path, (2026, 9, 29, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = (
                zipfile.ZIP_STORED if path.startswith("base/") else zipfile.ZIP_DEFLATED
            )
            data = (
                base.read_bytes()
                if path.startswith("base/")
                else index_html()
                if path == "index.html"
                else (ROOT / path.removeprefix("supplement/")).read_bytes()
            )
            if len(data) != meta["bytes"]:
                raise ValueError("Member changed during packaging: " + path)
            archive.writestr(info, data)
        manifest_raw = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        archive.writestr("MANIFEST.json", manifest_raw)
        checksums = "".join(
            f"{meta['sha256']}  {path}\n" for path, meta in sorted(entries.items())
        ).encode()
        archive.writestr("CHECKSUMS.sha256", checksums)
    return {"path": str(output), "sha256": sha256_file(output), "manifest": manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    result = build(args.base, args.output, preview=args.preview)
    print(json.dumps({k: v for k, v in result.items() if k != "manifest"}, indent=2))


if __name__ == "__main__":
    main()
