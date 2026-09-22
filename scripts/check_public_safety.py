#!/usr/bin/env python3
import hashlib
import subprocess
import sys
from pathlib import Path

from sable_harbor.exports.safety import scan_generated_artifacts

FORBIDDEN = ("ghp_", "github_pat_", "sk-proj-", "BEGIN PRIVATE KEY")
MAX_BYTES = 10 * 1024 * 1024
ALLOWED_LARGE_PUBLIC_ARTIFACTS = {
    # Tracked convenience catalog retained by GENERATED_RECORDS_LIFECYCLE.md.
    # Company closeout public-source catalog successor; original artifacts remain preserved.
    # Exact bytes only: no general allowance for new databases or later drift.
    Path("docs/internal/institutional_catalog.sqlite3"): (
        12032000,
        "d8619cd7224e105e375338892ff200e0dcf723f61eb8dec7ab442130d1f27f70",
    ),
    # Reviewed September 10 successor: six approved J2 names, unchanged public scope.
    Path("docs/organization/assets/current/Sable-Harbor-Organization-Charts.pdf"): (
        12412796,
        "352dfa4f1247f6089d340b19940f75758a666dce14f239fb38b1c2a300aaa38b",
    ),
    # Exact preserved bytes of the previously reviewed owner-approved chart book.
    Path("docs/organization/history/v1.0.0/Sable-Harbor-Organization-Charts.pdf"): (
        12421998,
        "c1589fbd0c0bfcb2a823cc4e582b580510f3d1408a933ddb09188aa217f62665",
    ),
    # PR164 delegated site decisions and final public geographic source review.
    # All 60 original spatial tables preserve their rows; three screened footprints form one new layer.
    Path("geospatial/master/sable_harbor_master_v0.1.gpkg"): (
        40099840,
        "2749c22b257be1519713b3e6d4011ad1f9b6a2483c509f152ae505b00739f688",
    ),
    # Byte-identical preservation copy of the already approved public database below.
    Path("geospatial/sources/canon_snapshot/blackridge/data/public/databases/blackridge_m00_v0.1.0.sqlite3"): (
        20 * 1024 * 1024,
        "2e6622d0e710f784c49cd6b773514820dbe247c4ec50a18f4c9cbbcf784587d5",
    ),
    Path("blackridge/data/public/databases/blackridge_m00_v0.1.0.sqlite3"): (
        20 * 1024 * 1024,
        "2e6622d0e710f784c49cd6b773514820dbe247c4ec50a18f4c9cbbcf784587d5",
    ),
}


def review_files() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=True,
        capture_output=True,
    ).stdout.decode()
    return [Path(name) for name in output.split("\0") if name]


def main() -> None:
    failures: list[str] = []
    for path in review_files():
        if path in {
            Path("scripts/check_public_safety.py"),
            Path("src/sable_harbor/exports/safety.py"),
        }:
            continue
        if not path.is_file():
            # A pre-commit scan may see paths deleted from the working tree
            # before the index is updated; only materialized content is scannable.
            continue
        if "var/private" in path.as_posix():
            failures.append(f"private benchmark path tracked: {path}")
        if path.stat().st_size > MAX_BYTES:
            allowance = ALLOWED_LARGE_PUBLIC_ARTIFACTS.get(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if allowance is None or path.stat().st_size > allowance[0] or digest != allowance[1]:
                failures.append(f"unapproved large file exceeds 10 MiB: {path}")
        if path.suffix.lower() in {".png", ".pdf", ".pptx", ".zip", ".xlsx"}:
            continue
        text = path.read_text(errors="ignore")
        for marker in FORBIDDEN:
            if marker in text:
                failures.append(f"possible credential marker {marker!r}: {path}")
    if failures:
        raise SystemExit("\n".join(failures))
    for argument in sys.argv[1:]:
        failures.extend(scan_generated_artifacts(Path(argument)))
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        "PASS: no tracked/untracked reviewable private benchmark paths, credential markers, "
        "or unapproved >10 MiB files"
    )


if __name__ == "__main__":
    main()
