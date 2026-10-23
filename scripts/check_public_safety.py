#!/usr/bin/env python3
import hashlib
import subprocess
import sys
from pathlib import Path

from sable_harbor.exports.safety import scan_generated_artifacts

FORBIDDEN = ("ghp_", "github_pat_", "sk-proj-", "BEGIN PRIVATE KEY")
MAX_BYTES = 10 * 1024 * 1024
ALLOWED_LARGE_PUBLIC_ARTIFACTS = {
    # Audit workspace integration: exact 5,608-version projection recipe.
    # Reviewed identities, hashes, source references and declared transformations;
    # it contains no credentials, original record bodies or instructor Key payload.
    # Private source databases and actual assessment snapshots remain outside Git.
    Path("enterprise/audit_suite/company_operational_library_projection_registry_v3.json"): (
        16164813,
        "6fa8e6ba1e428762e1554a5e2779402889dbe48983b3362412536f7744995d66",
    ),
    # Tracked convenience catalog retained by GENERATED_RECORDS_LIFECYCLE.md.
    # October 20 CLEAN/MESSY intake and recovery guides: 1,691 public reader
    # files. Compared with the October 18 accepted catalog, the rebuilt database
    # adds those two guides and refreshes the README, local workspace guide and
    # company-record README. Institutional objects and controlled pairs are
    # unchanged; SQLite quick_check and reader regeneration both pass.
    # Exact logical comparison preserves all 148 institutional objects and
    # publication pairs, 294 relationships, 12 evidence packages, 237 evidence
    # artifacts and the existing evidence link. Reader text/search reflects the
    # README, data guides and preserved client text. All 384 counterpart-audit rows are unchanged;
    # full catalog regeneration reproduces its tables. The 148 admitted source/PDF
    # pairs retain their accepted manifest and exact bytes.
    # The documented verifier now runs as a module in both intake guides.
    # Regeneration changed only those two reader-file/text rows and their FTS
    # index entries; all institutional and evidence tables remain unchanged.
    # October 23 historical facilities research intake: compared the rebuilt
    # database with accepted main at 934f1dce. All 148 institutional objects,
    # 148 publication pairs, 294 relationships, 384 counterpart-audit rows,
    # 12 evidence packages, 237 evidence artifacts and the evidence link are
    # unchanged. Reader inventory grows from 1,691 to 1,694 entries for the
    # research README and two historical XLSX models; one existing Wiki source
    # changes, and its reader hash/text/search rows refresh. The DOCX originals
    # are linked from the README but are not reader-index input types. Catalog
    # regeneration, reader navigation and SQLite integrity verification pass.
    # October 23 historical geographic package index: compared with accepted
    # main b978875e, the same 148 objects/pairs, 294 relationships, 384
    # counterpart rows, 12 evidence packages, 237 artifacts and evidence link
    # are exact-equal. One historical README is added to reader inventory
    # (1,694 -> 1,695); four changed guide/source rows refresh. SQLite
    # quick_check and foreign keys pass. No controlled publication changes.
    # The Advisory proposal adds two historical READMEs and two byte-distinct
    # original PDFs to the reader inventory (1,695 -> 1,699). Against the
    # accepted geospatial predecessor catalog at ce8df6c2, all 148 objects,
    # 148 publication pairs, 294 relationships, 384 counterpart rows, 12
    # evidence packages, 237 artifacts and one evidence link are exact-equal.
    # Both databases pass SQLite quick_check and foreign-key verification.
    # The historical staged facilities workline then adds one reader README
    # (1,699 -> 1,700) on accepted main cdb33b6c. All 148 institutional
    # objects/publication pairs, 294 relationships, 384 counterpart rows,
    # 12 evidence packages, 237 artifacts and the evidence link remain
    # logically exact-equal; SQLite quick_check and foreign keys pass.
    # The recovered September 11 office-estate draft adds four historical
    # Markdown source/guide rows (1,700 -> 1,704) against accepted main
    # 53720c58. All 148 institutional objects/publication pairs, 294
    # relationships, 384 counterpart rows, 12 evidence packages, 237
    # artifacts and the evidence link remain logically exact-equal. SQLite
    # quick_check and foreign keys pass. No publication was generated.
    # The historical September 5 industrial R1 handoff adds three reader
    # Markdown rows (1,704 -> 1,707) against accepted main 115763b0. All
    # seven non-reader catalog tables remain exact-equal; SQLite integrity
    # and foreign-key checks pass. Current industrial authority is unchanged.
    # The September 10 service operating-model history adds two Markdown
    # reader rows (1,707 -> 1,709) on the R1 predecessor. All seven
    # non-reader tables remain exact-equal; SQLite integrity and foreign keys
    # pass. This does not approve modeled budgets or alter current services.
    # The September 9 proposed organization history adds four reader rows
    # (1,709 -> 1,713, including two PDFs). The seven non-reader tables
    # remain exact-equal; SQLite integrity and foreign keys pass. The
    # proposal does not revise the accepted current organization chart.
    # The October 2 unadopted encoder experiment adds two historical
    # Markdown reader rows (1,713 -> 1,715). The seven non-reader tables
    # remain exact-equal; SQLite integrity and foreign keys pass. This does
    # not change the accepted canonical codec or signed workroom histories.
    # The September finance build-readiness note adds its dated Markdown
    # source and historical PDF (1,715 -> 1,717 reader rows). Seven non-reader
    # tables remain exact-equal; SQLite integrity and foreign keys pass.
    # Planning language does not become a financing or board approval.
    # The September 14-15 closeout and voice provenance adds five dated
    # Markdown reader rows (1,717 -> 1,722). The seven non-reader tables
    # remain exact-equal; SQLite integrity and foreign keys pass. Source
    # notes do not establish a completed closeout or new current authority.
    # The historical geographic transfer manifest adds one reader guide
    # (1,722 -> 1,723). Its three payloads already match accepted Git
    # history; seven non-reader tables remain exact-equal, with SQLite
    # integrity and foreign keys passing. No new geographic claim is made.
    # The unaccepted v1.5.0 geographic preview stages add three historical
    # Markdown reader rows (1,723 -> 1,726). The seven non-reader tables
    # remain exact-equal; SQLite integrity and foreign keys pass. Neither
    # preview changes the accepted v1.5.0 release or current site decisions.
    # Exact bytes only; later drift requires another hash review.
    Path("docs/internal/institutional_catalog.sqlite3"): (
        16343040,
        "7f868fbddd4d8569ccd8b6bca5133ca48cbee571536893b7ec77c0b66385abc5",
    ),
    # September 13 locally reviewed organization-chart successor; owner visual
    # acceptance remains separate. Preserve the previous version in history.
    Path("docs/organization/assets/current/Sable-Harbor-Organization-Charts.pdf"): (
        12419501,
        "7cf4607406ed56bd7cafdbcaecd136ba53ba7df21706f2fa7080056f908fcdf9",
    ),
    Path("docs/organization/history/v1.1.0/Sable-Harbor-Organization-Charts.pdf"): (
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
    Path(
        "geospatial/sources/canon_snapshot/blackridge/data/public/databases/blackridge_m00_v0.1.0.sqlite3"
    ): (
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
