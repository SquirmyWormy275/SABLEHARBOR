# Industrial case releases

**Current release:** [Sable Harbor industrial case v1.0.0](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/sable-harbor-industrial-case-v1.0.0)

**State:** MERGED_MAIN_AND_PUBLISHED; all downloaded release assets verified against local bytes

**Participant cutoff:** 2026-09-05T23:59:59-07:00

**Classification:** PUBLIC_SYNTHETIC_PARTICIPANT_CORPUS

The completed [industrial successor](../../industrial/README.md) was accepted through [PR #98](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/98). The release is built from clean merged source commit [`c792dfcdfaa9b48168cadd3bb9c26d113c24af34`](https://github.com/SquirmyWormy275/SABLEHARBOR/commit/c792dfcdfaa9b48168cadd3bb9c26d113c24af34). This delivery-index followup is intentionally later than that immutable release source; it does not claim the archive was rebuilt from a later documentation commit. Historical published finance and Red Wash v1.0.0 packages retain their original bytes and source scopes.

## Planning successor v2

The [planning and enterprise successor](../../industrial/planning/README.md) is separately versioned from the preserved v1 snapshot. Its [acceptance record](../internal/validation/INDUSTRIAL_PLANNING_2026-09-06.md) documents the five-year model, capital review, operating disruptions, linked evidence, enterprise consolidation and offline browser. Publication identities are added here only after the merged release assets are retrieved and verified.

## Source and integration binding

- Reviewed main baseline: `dd505286d7a66d25a2929981150d028935f27fbe`.
- Implementation branch: `feature/pale-sun-aru-red-wash-closeout`.
- `131af5679122c145f0dd38258073e2eeb74da00f` — Complete the Pale Sun, Red Wash and ARU industrial case
- `2519b91f47c542a1a07687ff36d868230a7083a7` — Validate the current industrial corpus in Red Wash CI
- Accepted merge/source commit: `c792dfcdfaa9b48168cadd3bb9c26d113c24af34`.
- Release tag: `sable-harbor-industrial-case-v1.0.0`; tag target and participant manifest bind to the accepted source above.
- [PR #95](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/95) was closed as superseded after this implementation merged and the release was retrieved. Reviewed draft head: `e385d29c4cd6fc49438e956027c8165102608e1b`. Only its reconciled headline baseline was reused; customer/payroll support, legal books, transaction/tax treatment, operating case and source-bound distribution were completed independently. Its draft was not merged wholesale. Unrelated PRs #94 and #96 remain separate.

## Delivered assets and retrieval evidence

The participant ZIP contains **199 selected artifacts**, **79 CSV-derived SQLite tables**, database lineage, manifests and checksums. Two independent full builds under Python 3.12.14, SQLite 3.53.1 and zlib 1.3.2 produced identical ZIP bytes. After publication, every asset was downloaded from GitHub, compared byte-for-byte with the local release staging files and checked against `release_SHA256SUMS.txt`. The ZIP's internal CRC and every member checksum also passed.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| [SHA256SUMS.txt](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/sable-harbor-industrial-case-v1.0.0/SHA256SUMS.txt) | 113 | `fd1a7da9c7fd1e01f31e6b0b618d9dfeb28d5b822982b0ed2bbe4e6fd495c534` |
| [industrial_delivery_inventory.json](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/sable-harbor-industrial-case-v1.0.0/industrial_delivery_inventory.json) | 81,508 | `33f13f1ac447ce6e008788c84132c77ca242188d5b62404937c5a9b14223e3aa` |
| [participant_manifest.json](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/sable-harbor-industrial-case-v1.0.0/participant_manifest.json) | 148,105 | `a800d81b8e962049be021cbd53f38865dde5a669dd2559032c19602685f53cd9` |
| [release_SHA256SUMS.txt](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/sable-harbor-industrial-case-v1.0.0/release_SHA256SUMS.txt) | 469 | `624619e9d7a4873fed831275bb8f69cc5af1095f755818f26ba6e5885b8ed585` |
| [sable-harbor-industrial-participant-v1.0.0.zip](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/sable-harbor-industrial-case-v1.0.0/sable-harbor-industrial-participant-v1.0.0.zip) | 12,606,089 | `b4d546bdad2e0add933c98d2a70d29658da4b8f2969c4b9e7153dd75906fc0be` |
| [validation.json](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/sable-harbor-industrial-case-v1.0.0/validation.json) | 458 | `818a9fcd33e83685bae835f3691cb71df210bc03050f03bdae05892204b6d253` |

The [delivery inventory](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/download/sable-harbor-industrial-case-v1.0.0/industrial_delivery_inventory.json) is the complete **208-file implementation diff** from the reviewed main baseline through the accepted release source. Each changed file has its status, current hash and prior hash where applicable. It also lists **33 changed controlled source/PDF records**, all changed structured artifacts, and **51 current/historical graphics and graphical publications** with verified hashes and declared roles. These are editorial delivery evidence, outside the dated participant corpus. This release-index Markdown is the separate subsequent delivery-record change.

## Acceptance and reconciliation

The [full acceptance report](../internal/validation/INDUSTRIAL_CLOSEOUT_2026-09-05.md) records corrections, numerical scopes, source preservation and validation evidence. Local full-repository pytest passed **147 tests** with five skips; the separately scoped industrial and mine suites passed **39** and **27** tests. Independent exported-data validation passed **4,245** checks, the operating builder passed **155**, and the mine validator passed **514/514**. All six PR #98 CI jobs passed on the final branch commit, including PostgreSQL 16 and SQLite finance generation, validation, workbook/release/business-unit export and public-safety checks. The stale Red Wash CI artifact selection was replaced with the current participant allowlist and verified clean source binding.

The industrial operating balance sheet reconciles **$164,518,432 assets = $52,852,567 liabilities + $111,665,865 equity**. Acquisition sources/uses, journal debits/credits, cash rollforwards, taxes, capital and funding reconcile. The reciprocal **$171,380** service activity and **$49,240** receivable/payable eliminate exactly. The original standalone mine comparison retains its negative free cash flow; no balancing profit or unproved savings was invented to meet an earlier target.

Commands used for the applicable local checks:

```bash
uv sync --frozen --all-extras
uv run pytest
uv run python -m unittest discover -s industrial/tests -v
uv run python -m unittest discover -s red_wash/tests -v
uv run python industrial/tools/validate_industrial_case.py --generate
uv run python red_wash/tools/validate_red_wash_record.py --generate
uv run python scripts/validate_governance_j2.py
uv run python scripts/validate_institutional_catalog.py
uv run python scripts/validate_organization_maps.py
uv run python scripts/validate_repository_hygiene.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
python tools/documents/build_controlled_publications.py
python tools/documents/build_institutional_catalog.py
git diff --check
```

To rebuild the participant release, check out the exact source commit in a clean checkout, use the recorded toolchain, then run `uv run python industrial/tools/build_package.py` twice and compare `industrial/dist/SHA256SUMS.txt`. The package builder runs its source generators and verifies archive CRC, member hashes, availability and declared prospective states. CI separately extracts the selected archive outside the checkout and runs `PYTHONPATH=src python scripts/check_public_safety.py` against that staging directory. Source/PDF lineage is verified for all **78** current controlled publications; the source regeneration retained their committed bytes.

## Provenance, preserved history and true open conditions

The original ZIP and Markdown hashes, all fourteen original members and five supplied PNGs are bound in [repository ingestion](../handoffs/industrial_r2/repository_ingestion.json). All thirteen finance-pinned source documents remain exact. The delivery inventory links the ten primary operating reference records, twenty-three mine external-source records, pinned geographic layers and DEM, chronology, legal/tax citations, federal/downstream brief and published-tariff comparison. Real references remain distinct from authored fictional records and modeled geometry; retrieval dates and source hashes retain their original provenance.

Current and archived visual roles are controlled by the [industrial maps](../../industrial/visuals/manifest.json), [industrial artwork](../../assets/brand/industrial_visual_manifest.json), [original mine artwork](../../assets/brand/red_wash_visual_manifest.json), [current organization register](../organization/ORGANIZATION_MAP_REGISTER.json) and [organization history](../organization/history/v0.3.0/manifest.json). Original approved artwork and superseded mine raster maps were preserved, with successor geometry published separately.

Direct uranium custody, a mine spur, mine-expansion commissioning, independently established corridor rights/final engineering and actual tax-election filing confirmation remain bounded conditions. The operating consolidation excludes unrelated enterprise businesses and holding-company investment accounts. Forecasts remain forecasts; synthetic execution documents are not authentic signatures or governmental approvals. **No evaluator truth entered SABLEHARBOR**, and the private control repository was not modified.

The archive is distributed through GitHub Releases under the [delivery policy](../governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md); no new ZIP was added to the Git tree.
