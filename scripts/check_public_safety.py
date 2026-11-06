#!/usr/bin/env python3
import hashlib
import re
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
    # October 24 Seagate disposition index: against accepted 250344a4,
    # reader inventory grows 1,739 -> 1,740 for one recovery guide and refreshes
    # DATA_AVAILABILITY. All seven institutional/publication/evidence tables
    # remain exact-equal; SQLite quick_check and foreign keys pass. The index
    # records delivery metadata and grants no company or cleanup authority.
    # November 4 reader regeneration: against accepted main 4a313f30, reader
    # inventory grows 1,740 -> 1,741 for LOCAL_RECOVERY_2026-10-23.md (added by
    # #227 without a catalog rebuild) and refreshes the stale LOCAL_RECOVERY
    # 2026-10-20 and LOCAL_WORKSPACE rows. All institutional, publication,
    # relationship, counterpart and evidence tables remain exact-equal; SQLite
    # quick_check and foreign keys pass. November 5: rebuilt after merging the
    # intake-path catalog with the checkout workspace guide (LOCAL_WORKSPACE.md,
    # audit_suite_web/README.md) row refresh. November 6: rebuilt for the
    # workplace-capacity company-record edition count updates (README.md,
    # CONTROLLED_DOCUMENT_INDEX.md, CLEAN_MESSY_INTAKE.md, DATA_AVAILABILITY.md,
    # LOCAL_WORKSPACE.md, company-records/README.md, wiki/Audit.md); inventory
    # stays 1,741 files and the rebuild reproduces exactly.
    # Exact bytes only; later drift requires another hash review.
    Path("docs/internal/institutional_catalog.sqlite3"): (
        16551936,
        "fdcb82202ac4f9fbdd854fb030b624ce48f0c1d1f00dafcc23c1bf283e02c027",
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


# Local workstation paths (``/home/<name>/``, ``/media/<name>/``,
# ``/run/media/<name>/``, ``/Users/<name>/``, ``C:\\Users\\``) must not leak
# into public files. Neutral placeholders such as ``<local-checkout>/`` are
# preferred; the generic account names below are accepted as placeholders.
LOCAL_PATH_PATTERN = re.compile(
    r"(?<![\w.\-])(?:/run)?/media/(?P<media>\w[\w.\-]*)/"
    r"|(?<![\w.\-])/(?:home|Users)/(?P<home>\w[\w.\-]*)/"
    r"|[A-Za-z]:\\{1,2}Users\\{1,2}"
)
LOCAL_PATH_PLACEHOLDER_NAMES = frozenset(
    {
        "operator",  # documentation placeholder
        "runner",  # GitHub Actions hosted runner home
        "user",
        "username",
        "example",
        "private",  # synthetic leak fixture in tests/integration/test_release_package.py
    }
)
LOCAL_PATH_ALLOWLIST = frozenset(
    {
        # Hash-pinned preserved evidence. Each file's exact SHA-256 is recorded
        # in another manifest, receipt, register or the institutional catalog,
        # so editing it would break those integrity chains. Do not add new
        # entries for editable files; scrub the path instead.
        "docs/audit/ISSUE_CLOSEOUT_2026-09-12.md",
        "docs/internal/company-closeout/evidence/dependency-remediation-2026-09-22/pytest.txt",
        "docs/internal/company-closeout/evidence/integration-f5e919e7/company-reperformance-f5e919e7.json",
        "docs/internal/company-closeout/evidence/integration-f5e919e7/pytest-f5e919e7.txt",
        "docs/internal/company-closeout/evidence/portal-edition-f5e919e7/RECEIPT.json",
        "docs/internal/company-closeout/evidence/portal-edition-f5e919e7/SELECTED_REVIEW_PLAN.json",
        "docs/internal/company-closeout/evidence/portal-edition-f5e919e7/SELECTED_REVIEW_RECEIPT.json",
        "docs/internal/company-closeout/evidence/portal-neutral-2026-09-22/pytest.log",
        "docs/internal/company-closeout/evidence/portal-neutral-2026-09-22/receipt.json",
        "docs/internal/company-closeout/evidence/portal-selected-fixture-2026-09-22/RECEIPT.json",
        "docs/internal/company-closeout/evidence/portal-selected-fixture-2026-09-22/initial-incomplete-snapshot.log",
        "docs/internal/company-closeout/validation/pytest-working-693b20ec.txt",
        "docs/internal/development/audit-suite/COMPANY_OPERATIONAL_PROJECTION_2026-10-01.md",
        "docs/internal/institutional_catalog.sqlite3",
        "docs/legal/gap-instruments/case-briefs/qa/cold-start/evidence-proposal/PROPOSAL.original.txt",
        "docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/evidence-proposal/PROPOSAL.original.txt",
        "docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/manifest.json",
        "docs/legal/gap-instruments/case-briefs/qa/cold-start/history-before-context-refresh/manifest.original.json",
        "docs/legal/gap-instruments/case-briefs/qa/cold-start/manifest.json",
        "docs/legal/gap-instruments/case-briefs/qa/cold-start/manifest.original.json",
        "docs/legal/gap-instruments/qa/REVIEW_FACILITIES.txt",
        "docs/legal/gap-instruments/review-support/qa/v4.2/full-pytest.log",
        "docs/legal/gap-instruments/review-support/qa/v4.3/full-pytest.log",
        "docs/legal/gap-instruments/review-support/qa/v4.3/integrated-pre-fix-tests.log",
        "docs/legal/gap-instruments/review-support/qa/v4/full-pytest.log",
        "enterprise/audit_suite/COMPANY_SUPPLEMENTAL_OPERATIONS_2027_2026-10-01.md",
        "enterprise/audit_suite/FICTIONAL_2027_ASSURANCE_OPERATIONS.md",
        "enterprise/audit_suite/FICTIONAL_2027_DAT002_PRIVACY_OPERATIONS.md",
        "enterprise/audit_suite/FICTIONAL_2027_PARTIAL_PORTFOLIO_V2.md",
        "enterprise/audit_suite/FICTIONAL_2027_SOURCE_PORTFOLIO_DIAGNOSTIC.md",
        "enterprise/audit_suite/FRESH_SEC003_EXECUTION_2026-10-01.md",
        "enterprise/audit_suite/LEG001_TRIGGER_SCREENING_2027_IMPLEMENTATION.md",
        "geospatial/facilities/qa/repo-validation/build-results.json",
        "geospatial/facilities/qa/repo-validation/extra-results.json",
        "geospatial/facilities/qa/repo-validation/final-gate-results.json",
        "geospatial/facilities/qa/repo-validation/finance-build-results.json",
        "geospatial/facilities/qa/repo-validation/geo-build-results.json",
        "geospatial/facilities/qa/repo-validation/industrial-validation.log",
        "geospatial/facilities/qa/repo-validation/r02-current-main/clean-test-results.json",
        "geospatial/facilities/qa/repo-validation/r02-current-main/current-validator-results.json",
        "geospatial/facilities/qa/repo-validation/r02-current-main/domain-test-results.json",
        "geospatial/facilities/qa/repo-validation/r02-current-main/root-tests.log",
        "geospatial/facilities/qa/repo-validation/r02/results.json",
        "geospatial/facilities/qa/repo-validation/results.json",
        "geospatial/facilities/qa/repo-validation/root-pytest.log",
        "geospatial/facilities/qa/spatial-integration/PARENT_HTML_QA.json",
        "geospatial/facilities/qa/spatial-integration/REVIEW.json",
        "geospatial/facilities/qa/spatial-integration/baseline-logs/root-pytest.log",
        "geospatial/facilities/qa/workbench/VALIDATION.json",
        "geospatial/facilities/qa/workbench/root-tests.log",
        "geospatial/facilities/visitor/v06/SOURCE.json",
        "geospatial/facilities/visitor/v07/SOURCE.json",
        "geospatial/facilities/visitor/v08/SOURCE.json",
        "geospatial/history/v1.5.0-previews-2026-10-03/provenance/C18-MANIFEST.json",
        "geospatial/history/v1.5.0-previews-2026-10-03/provenance/C19-MANIFEST.json",
        # SHA-256 recorded in company_supplemental_operations_2027.py, which the
        # operational library projection registries pin in turn.
        "enterprise/audit_suite/company_supplemental_operations_2027_spec_v1.json",
    }
)


def local_path_leak(text: str) -> str | None:
    for match in LOCAL_PATH_PATTERN.finditer(text):
        name = match.group("media") or match.group("home")
        if name is None:
            return match.group(0)
        if name.lower() in LOCAL_PATH_PLACEHOLDER_NAMES:
            continue
        return match.group(0)
    return None


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
        payload = path.read_bytes()
        text = payload.decode(errors="ignore")
        for marker in FORBIDDEN:
            if marker in text:
                failures.append(f"possible credential marker {marker!r}: {path}")
        if b"\0" in payload[:8192] or path.as_posix() in LOCAL_PATH_ALLOWLIST:
            continue
        leak = local_path_leak(text)
        if leak is not None:
            failures.append(f"local workstation path {leak!r}: {path}")
    if failures:
        raise SystemExit("\n".join(failures))
    for argument in sys.argv[1:]:
        failures.extend(scan_generated_artifacts(Path(argument)))
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        "PASS: no tracked/untracked reviewable private benchmark paths, credential markers, "
        "local workstation paths, or unapproved >10 MiB files"
    )


if __name__ == "__main__":
    main()
