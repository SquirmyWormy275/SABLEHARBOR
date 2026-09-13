# Protecting accepted visual files

Run `python tools/documents/approval_guard.py` before changing publications or visual assets.
This read-only check compares existing acceptance records with their pinned Git versions,
then verifies the original SHA-256 values against current files. Changing an image and
updating its manifest hash together fails. Missing historical Git objects also fail;
the error supplies the revision to fetch. No generation or automatic rebaseline occurs.

| Existing authority | Protected scope | Files |
|---|---|---:|
| [Foundry Field acceptance](../finance/evidence/SH-FIN-HUMAN-001/ACCEPTANCE.json) | Exact PDF, workbook, sources, builder, manifests and review evidence | 18 |
| [V08 acceptance](../../geospatial/facilities/visitor/ACCEPTANCE.json) | Selected visitor PNG and PDF | 2 |
| [Sacramento R01 manifest](../facilities/references/sacramento-hq/r01-approved/MANIFEST.json) | Four original PNGs, recovered archive and three controlling handover files | 8 |
| [Brand manifest](../../assets/brand/manifest.json) | Two J2 PNG entries explicitly identified as controlling user-approved source assets | 2 |

The guard also preserves the two dated canonical acceptance documents referenced by
Foundry Field and V08. It reads hashes from existing records rather than maintaining a
second approval register. Its JSON output names each pinned revision and reports 30
protected artifacts. R01 successor-link maintenance and unrelated brand-manifest entries
remain editable; neither gives a successor the original's approval.

## What this does and does not establish

A passing hash check establishes preservation of the listed bytes. It does not establish
visual quality, correctness of underlying business facts, or approval of a new design.
The original approval's scope still controls. R01 approval does not establish construction
or occupancy; the accepted accounting packet remains synthetic evidence.

Organization publications, other logos, general maps and newly proposed accounting/legal
designs are outside this exact-file guard. Continue running their existing organization,
geography, publication and brand validators. Those consistency checks must not be described
as exact-file user acceptance. Extend protection only when an accepted record identifies
the specific files; do not freeze every generated derivative or invent missing approvals.

For an intentional new design, preserve the accepted original, save a separately versioned
candidate, obtain exact-file review, and record the accepted supersession scope through
repository governance. Any change to this guard's revision pins requires review of that
accepted decision. Code and CI themselves still depend on repository review protections;
a script cannot prevent an authorized editor from deleting its check.

Validation: `python -m pytest -q tests/publications/test_approval_guard.py` exercises changed
bytes, simultaneous hash resealing, missing files and missing Git history for all four
record formats. R01 successor navigation is tested separately from original-file approval.
