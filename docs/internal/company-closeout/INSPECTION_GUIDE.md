# Company edition inspection and reproduction

**Document ID:** SH-COMPANY-INSPECTION-2026-09-15
**Version:** 1.0.0
Prepared September 15, 2026 UTC.
Execution/provenance instructions updated September 22, 2026 UTC. The completed
period and September event cutoff below remain unchanged; new evidence is not
backdated to this guide's original preparation date.
This guide defines the package route. The [register](REGISTER.json) and final release
receipt determine accepted scope; this working guide is not a delivery receipt.

## Begin with the edition

Read `CONTRACT.json` and `MANIFEST.json` before querying data. They identify the
exact source commit, component populations, known-on boundary, limitations and
allowed joins. A repository snapshot contains historical and proposed documents
as well as controlling records. Inclusion does not erase their original states.
The three package components are the tracked public source graph, the composed
financial/calibration/forecast package, and completed-period company records.
Inventoried historical ZIPs are excluded from redistribution; their original
locations, flags and hashes remain in the retained delivery indexes.

The packaging cutoff is August 31, 2026, with a separate event ledger through
September 14 America/Los_Angeles. Financial source periods and forecast scenarios
retain their own labels. Later-authored evidence is not available in an earlier
known-on view: use the later of original evidence availability and the edition's
publication/availability boundary. Actual import time is separate again.

Materiality follows represented activity. Every legal/consolidated balance and
each of the seven business-line revenue/cost populations is reconciled; all
declared employee, contract, invoice and obligation populations are included.
Selected physical record chains state their surrounding populations and exclusions.
They do not claim a daily warehouse, dispatch or mine simulator. A failed control
is an inspectable outcome; an unresolved material source gap blocks the claim it
affects. No universal monetary threshold or professional audit opinion is implied.

## Five reading routes

| Inspector | Forward trace | Reverse/reperformance |
|---|---|---|
| Financial/tax | Owner directions → accepted adjustments/tax history → legal journals → eliminations → statements → exports | `enterprise.closeout.reperform`, standalone CSV/SQLite inspection, historical/current tax and asset schedules |
| IT | Effective workforce → access and qualifications → control evidence/review → revocation/restore | Completed-period validators, reference authorization negatives, pinned CompanyStore import/backup/restore receipt |
| Relevant regulator | Entity/site/activity → primary provision/version → fictional facts → expected occurrence → performance/report/exception | Current applicability, fourteen rail cases, fourteen permit condition populations, shipment qualification and visible failures |
| Investor | Ownership/rights and financing status → revenue/aging → margins/commitments/debt → cash and sovereignty | Treasury thirteen-week assumptions, member-source IDs, investment-purpose bridges, unpaid obligations and downside |
| Agentic evaluator | Contract/schema/population definitions → exact public originals → existing CSV/SQLite tables | Independent import, stable-ID joins, as-of/known-on filtering and scoped access negatives |

Company outputs are public synthetic evidence. Candidate work, private scenario
truth, grading rules/results and NAILEX proprietary implementation remain outside
this package under maintainer rules. Neither tests nor public manifests disclose
private grading payloads.

## Current accounting and ownership sources

The [accounting-basis successor](../../finance/evidence/company-closeout/ACCOUNTING_BASIS_SUCCESSOR.md)
defines the synthetic management accrual presentation and exact correction scope.
Legal books, financial consolidation and tax filing groups have separate boundaries.
The edition makes no US GAAP or audit-opinion claim. Use the final release receipt
to identify the implemented tax provision, payment states and numerical effects.

The [adopted directions](../../canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md)
resolve corporate taxation from formation and the exact five-holder register.
The [capital source](../../../enterprise/closeout/source/capital_register.json)
and [founder reconstruction](FOUNDER_ADMISSION_BASIS.md) distinguish historical
subscriptions, admission value, retained earnings and subsequent member cash.
The $183 million subscription history is not additional current cash. Funding
requests preserve the established participation shares and issue no new units.
The [investor route](../../finance/evidence/company-closeout/TREASURY_AND_INVESTOR_ROUTE.md)
joins those records to the same edition's financial results and funding limits.

The register's residuals identify specific rights and capability limits, evidence
reviewed, impact, alternatives and next owner. Accepted packaging cannot establish
an unknown covenant, side-letter disposition, lien release or unexercised runtime
surface. Selected mine examinations and rail-event reporting remain distinct from
complete monthly mine and railway compliance populations.

## Financial and completed-period joins

The financial component also contains `capital_register.json`, eight `capital_*.csv`
schedules and the `statutory_*.json`/CSV workpapers beside the existing exports.
These are supplemental company workpapers, not additional rows to add to the
ledger or copies implicitly included in every unit's SQLite database. Join funding
by `scenario`, `source_id` and `event_id`, and holders by `holder_id`; preserve the
source-to-cash rounding bridge. Join tax by scenario, taxpayer, jurisdiction and
year. Filing/settlement states and interentity payer roles remain distinct from
financial consolidation. The manifest inventories these exact supplemental bytes.


The finance export directory is
`content/enterprise/generated/company-closeout-v1/exports`. Its
`export_schema.json` defines the existing table columns. `enterprise.sqlite3`
contains company/legal/consolidated populations; seven unit extracts are filtered
representations. Never add unit extracts to the enterprise tables or add legal
statements to consolidated statements. Journal natural identity is
`scenario, journal_id, line_no`; source IDs link adjustments and native evidence.

The completed-period directory is
`content/enterprise/generated/completed-period-2026-08`. Its `records.json`, CSVs,
manifest and lane receipt preserve people, positions, payroll, contracts, delivery,
invoices, settlements, inventory/asset balances and September changes. Person IDs
join payroll/access/qualification records; position count is not headcount.
Current invoice IDs join contract, delivery and authority IDs. Current revenue
and payroll are decompositions of existing source expenses/revenue, not additional
journals to post on top of the finance package. Read the explicit source bridges.

Example read-only queries against the financial SQLite export:

```sql
SELECT scenario, entity, year, net_income_usd, ending_cash_usd
FROM annual_statements
WHERE entity = 'CONSOLIDATED'
ORDER BY scenario, CAST(year AS INTEGER);

SELECT scenario, source_id, entity, year, month, account, signed_usd
FROM enterprise_journal
WHERE source_id LIKE 'CO-%' OR source_id LIKE '%FF003%'
ORDER BY scenario, CAST(year AS INTEGER), CAST(month AS INTEGER), journal_id, line_no;
```

Dates and monetary values are represented explicitly in the existing schema;
use decimal arithmetic for reconciliations rather than floating-point rounding.
CSV spreadsheet-injection escaping is intentional and independently checked
against the original SQLite values. No server pagination, hidden filters or
retention window truncates the distributable CSV/SQLite files. Source-specific
population and availability filters still apply.

## Reproduce from the pinned source

Controlled publications use `python -m tools.company_closeout.publications`, the
dated document-population successor to `tools/documents/build_controlled_publications.py`.
It reuses that exact approved renderer, style and source artwork. The predecessor
file is itself pinned by historical finance evidence and retains its original bytes.
When running the maintainer's predecessor command, run the successor afterward,
then `python tools/documents/build_institutional_catalog.py`; this restores the
complete current publication population before catalog verification.

Use a real Git checkout of `MANIFEST.json`'s `source_commit`, then install the
supported dependency environment. `uv.lock` and the repository requirement files
remain source-pinned. Generated directories are temporary outputs, not controlling
canon. Build from a clean checkout for a release; development outputs retain a
dirty-source flag and cannot become an accepted package.

```sh
uv sync --frozen --all-extras
uv run python -m enterprise.closeout.build
uv run python -m enterprise.operations.completed_period
uv run python -m enterprise.operations.completed_period --check
uv run python -m enterprise.operations.september_custody
uv run python -m enterprise.operations.september_custody --check
uv run python -m enterprise.closeout.reperform enterprise/generated/company-closeout-v1
uv run python -m enterprise.operations.reperform_closeout --output var/company-closeout/company-reperformance.json
uv run python -m tools.company_closeout.independent_import enterprise/generated/company-closeout-v1/exports
uv run python -m enterprise.ccf.company_closeout.instruments
uv run python -m enterprise.ccf.company_closeout.current_applicability --reperform-revenue
uv run python -m enterprise.ccf.company_closeout.rail_reporting
uv run python -m enterprise.ccf.company_closeout.shipment
uv run python -m enterprise.ccf.company_closeout.admin_completion
uv run python -m enterprise.ccf.company_closeout.restore_rehearsal
```

The composite reperformance command requires the August, September and finance
outputs to identify the same clean source commit. It independently joins current
invoices, legal balances, asset carrying values, payroll legal-employer expense,
selected debt payments and September freight to the retained source journals.
The separate September `records.json` is included in the completed-company-records
component; it is not omitted merely because its native generator uses another directory.

The release builder uses `tools.company_closeout.compose` to pin the exact generated
and tracked populations. Supply the release receipt's version and availability
timestamp and a new contract filename. `--accepted` requires `--acceptance-pr`
and `--adoption-path`: the builder verifies actual merged PR evidence through the
repository API and requires the exact merge commit as the clean source revision.
The scoped adoption source pins accepted implementation sources and explicitly
preserves pending framework reviews, draft rights, failures and future duties.
The public source archive retains mixed source states; acceptance never labels
every included historical or proposed document controlling canon.

`tools.company_closeout.edition` builds a new immutable
directory and deterministic ZIP. It refuses stale hashes, a mismatched source
revision, omitted/extra members, symlinks, private components and contradictory
acceptance metadata. It rechecks merge evidence when building an accepted package;
offline verification checks the retained receipt and packaged adoption scope.
The receipt identifies its actual API observation date. Offline hashes alone do
not independently prove a remote merge or professional acceptance. Do not replace
an existing archive under the same version.

```sh
uv run python -m tools.company_closeout.edition --output /new/edition --contract /new/CONTRACT.json --zip /new/company-edition.zip
uv run python -m tools.company_closeout.edition --output /new/edition --verify
```

After publication, retrieve the exact GitHub Release asset and verify its external
SHA-256, internal manifest, member counts and independent import. A locally created
ZIP or reserved release URL is not delivery. The indexed release receipt supplies
the concrete filenames and commands for that version.

## Existing portal and professional limits

Follow [PORTAL_CONTRACT.md](PORTAL_CONTRACT.md). The exercised adapter imports exact
originals through the existing committed `CompanyStore` interface in an isolated
directory. It neither edits the active worktree nor reads live/private data.
Reference authorization and old-snapshot restore tests have a separate scope from
the CompanyStore backup. Designed, implemented, exercised, fictional operation and
actual external deployment remain distinct. The existing external readiness gates
are not cleared by synthetic company records or a reference software test.

The final register identifies any surviving tax, rights, engineering, artifact or
runtime residual by affected claim. Ordinary fictional completion is labeled as
authored; source reconstruction is not independent bank, regulator or counsel
confirmation. This edition enables inspection without representing an audit opinion.
