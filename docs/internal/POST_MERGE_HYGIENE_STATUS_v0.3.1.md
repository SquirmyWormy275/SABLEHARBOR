# Post-Merge Hygiene Status v0.3.1

**Status date:** September 3, 2026  
**Scope:** Immediate hygiene after PR #16 merge  
**Record type:** Implementation/hygiene status; not Sable Harbor canon

## Completed in repository

- Added root `MAINTAINERS.md` to define source-of-truth, generated artifact, validation, issue, and slop-control rules.
- Added `OPEN_CANON_AND_HYGIENE_ISSUE_INDEX.md` to group unresolved canon and hygiene issues without converting issues into canon.
- Added release notes for the `canon-v0.3-ccf-j2-alexandria` merge point.
- Preserved PR #16's board paper trail, chat canon ledger, controlled-document index, institutional catalog, and validation claims as discoverable audit trail.

## Completed in GitHub issues

- Open-canon issues exist for Internal Audit, legal mechanics, J2 staffing, Orientation ranks, Alexandria runtime, Collection entitlement, Semaphore vocabulary, retention/deletion, spatial/AR, Daedalus runtime, business-line Alexandria interface, and Finance portal boundaries.
- Post-merge hygiene issues exist for tag/branch cleanup, fresh-clone validation, generated/binary artifact lifecycle, controlled-publication reproducibility, wiki sync, root navigation, validator scope, public-repository safety, release notes, and issue indexing.
- Duplicate administrative issues created during immediate triage were closed as duplicates where identified.

## Operations still requiring local Git or release privileges

The available connector cannot create Git tags, publish GitHub releases, delete remote branches, or run local/fresh-clone commands. The following remain tracked issues rather than silently claimed as done:

- create tag `canon-v0.3-ccf-j2-alexandria` at merge commit `9e11161cdaaeec5d5e834068a903c0cabff3377f`;
- delete merged branch `architecture/common-controls-framework-v0.1` after tag confirmation;
- remove accidental empty hygiene branches created during connector-driven triage if they exist remotely;
- run fresh-clone validation of `main`;
- produce local validation evidence packet;
- audit repository weight and generated binary artifacts;
- decide whether distributable ZIPs move to releases.

## Local validation command set

```bash
git clone git@github.com:SquirmyWormy275/SABLEHARBOR.git sableharbor-main-validate
cd sableharbor-main-validate
git checkout main
python scripts/validate_governance_j2.py
python scripts/validate_institutional_catalog.py
python scripts/validate_organization_maps.py
python scripts/validate_repository_hygiene.py
python -m pytest -q
git diff --check
git status --short
```

## Tag and branch cleanup command set

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
git tag canon-v0.3-ccf-j2-alexandria 9e11161cdaaeec5d5e834068a903c0cabff3377f
git push origin canon-v0.3-ccf-j2-alexandria
git push origin --delete architecture/common-controls-framework-v0.1
```

If additional empty hygiene branches were created during connector triage, delete them after confirming no PR or commit depends on them.
