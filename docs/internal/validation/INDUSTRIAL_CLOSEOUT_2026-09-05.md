# Industrial handoff implementation and acceptance

**Record ID:** SH-IND-ACCEPT-001 | **Version:** 1.0.0
**State:** LOCAL_ACCEPTANCE_COMPLETE; integration and distributed asset binding are recorded in the release index
**Case cutoff:** 2026-09-05T23:59:59-07:00
**Reviewed main baseline:** `dd505286d7a66d25a2929981150d028935f27fbe`

The complete selected industrial successor is implemented in [industrial](../../../industrial/README.md). The [release index](../../releases/INDUSTRIAL_CASE_RELEASES.md) records actual integration and delivery. This acceptance record describes executable checks and their scope; it does not certify fictional assets, tax elections or operating permissions as real.

## Verified intake and prior work

The received ZIP SHA-256 is `a13300543de9a66b08d715e062cffd10c21a37d8328910a7dc3bf61572a1643e`; its full Markdown is `6cc8b5093b2060f4a3d1cec44f295656681817c05035087b900979fdaf051751`. ZIP integrity and all 13 listed member checksums passed. The checksum file itself is the fourteenth preserved member. [Repository ingestion](../../handoffs/industrial_r2/repository_ingestion.json) binds every original member to its preserved bytes and classification.

The handoff's `8d20e51` baseline was stale. Work started from current main `dd505286`, preserving the intervening canon closeout. PR #95 at `e385d29c4cd6fc49438e956027c8165102608e1b` supplied a limited baseline draft, not the completed operating/transaction case. Its useful headline arithmetic was independently reconciled; the full draft was not blindly merged. PRs #94 and #96 were reviewed as geospatial references. Only required public reference layers and screened candidate geometry were selectively reused. The earlier release archive, SQLite journal and inconsistent source-commit assertions were not imported as a release.

All thirteen documents pinned by `docs/finance/CANON_SOURCE_LOCK.json` remain byte-exact. The current legal page is a separate `_R2` successor. Historical mine sources/documents and organization sources/graphics are retained with verified hashes. The five supplied PNGs, original Pale Sun/Red Wash masters and superseded mine raster maps retain their original bytes.

## Corrections made through independent review

| Finding | Implemented correction |
| --- | --- |
| New mine anchor conflicted with county, elevation and UTM frame | Sweetwater County, approximately 6,885 ft, NAD83 / UTM 12N; regenerated collars and current maps; old geography preserved as history |
| Proposed branch crossed mapped waterbody; highway crossings used an assumed milepost | Rerouted branch; final pinned-polygon overlap zero; I-80 intersections tied to reference geometry; remaining engineering/rights uncertainty explicit |
| Earlier train formation failed the declared traction screen | Sixteen loaded cars with paired locomotives; crew/branch/slow-order timing and conditional higher-volume capacity reconciled |
| Route history existed only as prose | Added a historical route reconstruction with unlocated early alignment explicitly distinguished from the modern network |
| 225-car planning quantity was liable to become fabricated sales | 205 ordinary + ten project cars billed; ten conditional buffer slots unbilled; 63-car partial 2026 ramp separately invoiced |
| Twice-weekly handling alone could not guarantee 72 elapsed hours | Funded exception/on-call handling; UTC elapsed-time tests across both daylight-saving transitions |
| Earlier interface revenue/EBITDA targets lacked a cost-derived bridge | $583,480 normalized revenue and $203,290 incremental EBITDA retained; variance disclosed; official tariff comparison added without claiming an identical-route quote |
| Capital screen, catch-up, sustaining capital and ownership were conflated | $8.5M phase one split $3.25M mine/$5.25M ARU; $11M ARU catch-up separate; $6.5M screen residual unapproved |
| Mine ARO was frozen across acquisition and January opening | $467,716 H2 accretion; $16,467,716 opening 2026 liability; $1,070,402 2026 accretion and separately modeled $256,250 progressive cash settlement |
| Acquisition tax treatment omitted goodwill amortization and loss timing | Independent $68M conditional tax asset basis/$13M tax goodwill allocation, 180-month amortization, cumulative current tax, quarterly modeled settlement and separate deferred balances |
| Several declared model inputs were unused | Price, volume, costs, debt, leases, fees, working capital and legal allocation inputs now propagate; sensitivity tests check actual numerical effects |
| Retention allocation mixed the seller's consulting cost with an employee's retention award | Separate cost treatment and legal allocation; no automatic seller operating authority |
| Subsidiary accounting support was incomplete | Added AR allowance, parts/fuel/material inventory, rail expense support and explicit zero unsupported EBITDA addbacks |
| Five-year service terms were asserted without an identifiable instrument | Added dated synthetic agreement with parties, rates, free time, cause-based charges, remedies, payment, coverage and termination terms |
| Midmonth cutoff and nested record schemas could admit future results | Fail-closed availability, conservative date-precision bounds, nested JSON/GeoJSON/CSV checks, scenario labels and explicit service simulations |
| PDF renderer silently dropped fenced financial reconciliations | Preserve escaped fenced text; regression test verifies the reconciliation remains in the publication |

## Reconciled final model

All amounts below are synthetic case values, not audited actual results.

| Measure | Selected result |
| --- | ---: |
| ARU 2025 external revenue / EBITDA | $42,000,000 / $9,800,000 |
| ARU acquisition sources / uses before fees | $61,500,000 / $61,500,000 |
| Parent acquisition cash including fees | $40,200,000 |
| ARU 2026 postclose net income / operating cash | $3,091,227 / $6,660,341 |
| ARU 2026 ending cash / subsequent equity funding | $4,198,440 / $16,704,880 |
| Integrated mine 2026 net income / operating cash | $598,341 / $1,123,367 |
| Integrated mine 2026 capex / equity funding | $12,250,000 / $11,126,633 |
| 2026 reciprocal interface revenue/expense eliminated | $171,380 |
| Closing reciprocal receivable/payable eliminated | $49,240 |
| Industrial operating external revenue | $78,729,562 |
| Industrial operating assets | $164,518,432 |
| Industrial operating liabilities + equity | $52,852,567 + $111,665,865 |

The operating consolidation excludes unrelated enterprise businesses and holding-company investment accounts. Its net income before the separately presented $900,000 parent transaction expense is $3,689,568; after that expense it is $2,789,568. The original standalone mine comparison remains $902,095 net income, $1,522,479 operating cash and **negative $7,477,521 free cash flow after $9M capex**. These scopes are not silently combined or labeled as the same model.

## Acceptance evidence

- Full repository pytest: **147 passed, five skipped**. PostgreSQL-dependent coverage is additionally exercised by repository CI. One existing Python datetime-adapter deprecation warning does not affect the balances.
- Industrial tests: **39 passed** — fourteen finance, seventeen operations and eight package-boundary tests.
- Mine tests: **27 passed**; mine reconciliation **514/514**.
- Operating builder: **155 checks passed**, including route length, physical capacity, capital references and source integrity. Independent optional DEM/waterbody verification also passed.
- Independent exported-data validator: **4,245 checks passed**; a separate finance review recalculated **1,989 journals**, trial balances, cash rollforwards, invoice reciprocals, concentration and tax from CSVs.
- Governance/J2, institutional catalog, nine organization charts, repository hygiene, Ruff formatting/lint and mypy passed. All **78** current controlled source/PDF pairs reconcile.
- Participant preview contains **199 selected artifacts** and **79 CSV-derived SQLite tables**, plus lineage. Two independent full builds produced identical ZIP bytes; CRC and every archived member hash passed. Development SHA is deliberately not presented as the distributed release hash.
- Current and historical maps and representative controlled PDFs were visually inspected. A repeat publication build rendered zero changed sources and retained all 78 verified publications.

The release builder requires a clean commit for distribution and records Python, SQLite and zlib versions. Reproducibility claims refer to the same toolchain; the committed PDF bytes carry their source/normalizer provenance. The archive is an explicit dated allowlist, with no raw handoff, superseded maps, private assessment data or whole-repository dump.

## Remaining bounded conditions

Direct uranium custody, a future mine spur and mine-expansion commissioning remain gated. Corridor rights and final engineering are fictional planning assumptions, not surveyed approvals. The tax election's actual submission and conditional accounting judgments remain evidenced limitations; no IRS acceptance is invented. Published tariff comparisons support a screening comparison, not proof that an outside carrier has quoted this exact route. The closure schedule is liability-calibrated, not an independent engineering estimate. These conditions remain visible in the completed case rather than being erased to obtain a nominally clean result.
