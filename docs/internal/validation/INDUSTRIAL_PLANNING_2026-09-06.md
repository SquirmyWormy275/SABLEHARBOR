# Industrial planning and enterprise v2 acceptance

This is editorial delivery evidence for the September 6 planning successor, outside the dated participant corpus. The implementation follows [SH-IND-PLAN-DEC-002](../../canon/INDUSTRIAL_PLANNING_SUCCESSOR_2026-09-06.md). Exact accepted source, release and retrieval identities are recorded in the [release index](../../releases/INDUSTRIAL_CASE_RELEASES.md); a development archive is not a published release.

## Delivered scope

The successor connects 180 physical scenario-months to 360 industrial entity-month statements for 2027–2031, then reconstructs the six legal enterprise books and elimination book from January 2026. It exports 1,728 legal/elimination/consolidated monthly statements, 1,944 operating-unit monthly statements and 306 annual statement views. Operating units remain management views, with explicit reporting clearing; they do not create new legal corporations.

The selected participant corpus has 271 artifacts, including all 199 preserved v1 artifacts. Its 120 CSV tables preserve exact cell text in SQLite; 26 financial extracts plus a source index preserve exact text in the workbook. The offline browser includes 41 planning tables and 103 documents/maps. All 518,562 planning records remain searchable; repeated metadata is dictionary-encoded without altering displayed text or decimal money. No server, network account, external script or private data is required.

Procurement has 4,500 matched order/receipt/invoice sets and 900 work orders. Each invoice reaches its posted expense, payable and settlement. There are 900 payroll batches, 23,694 census/position-pool details, 5,134 monthly service manifests and 360 bank reconciliations. Forecast service manifests are allocated monthly physical evidence, not observed individual waybills; payroll details are employer-cost/role allocations, not individual payslips or tax returns. Generated evidence never independently proves its own input assumptions.

## Material corrections found by cross-review

- Growth spending remains construction in progress until funded conditional commissioning. Cash purchase, noncash transfer and subsequent depreciation are distinct. Partial funding cannot commission a complete project.
- Capital appraisal uses the forecast's customer renewal economics, 80% loss-utilization ceiling, replacement life and conditional service/depreciation dates. The common mine project and sunk $8.5M interface are disclosed separately from the incremental logistics comparison.
- Tax receivables and payables remain gross by legal taxpayer where no offset right is assumed. Unit clearing does not net away external current-tax liabilities.
- New-year member funding considers carried unpaid Core obligations. Existing arrears are paid down without being posted again as fresh expense.
- Additional drivers and handlers occupy separate planned position pools. Existing management capacity is not multiplied by an overall segment staffing ratio.
- Release acceptance authenticates current implementation and effective in-memory policy hashes, exact producer artifacts and the current source revision. Stale or modified exports cannot reuse an acceptance report.

## Reconciliation and feasibility

All 61,506 industrial and 6,729 enterprise journal groups balance. Independent exported-data checks recompute all 360 industrial monthly statements/TBs, all 1,728 enterprise monthly statements, all 1,944 unit monthly statements and every legal/unit account balance. Bank clearing reconciles independently to book cash. Separate direct CSV arithmetic recomputes all 306 annual views from monthly flows and December balances. Ownership investments and intercompany balances/income eliminate to four-decimal zero.

The logistics screen at 10% values outsourcing at $821,813 above current capacity and owned expansion at negative $449,985. Owned expansion trails outsourcing by $1,271,798. This is a conditional logistics screen with declared tax, working-capital and terminal-value assumptions, not a standalone appraisal or approval of the common mine project.

| Enterprise scenario | 2031 revenue | 2031 net income | December 2031 cash | Funding feasibility during modeled horizon |
|---|---:|---:|---:|---|
| Base | $256,842,945.1829 | −$5,356,341.6857 | $21,648,522.5140 | Six months with gaps; peak $1,791,058.6187; carried Core arrears fully repaid by the end |
| Downside | $196,882,559.8227 | −$77,422,788.1256 | $4,834,452.0000 | 55 months with gaps; closing unpaid Core obligations $174,739,238.3476 |
| Expansion | $322,680,703.4068 | $31,442,311.8527 | $70,473,301.4008 | Within the expressly conditional funding envelopes |

The retained Core remains a partly top-down synthetic calibration. These enterprise results are conditional scenario arithmetic, not observed or audited company performance. Positive cash does not establish solvency when due obligations remain unpaid. Monthly gap balances repeat outstanding obligations and must not be added as independent new capital requirements.

## Validation evidence

- Full repository suite: 147 passed, five skipped; existing SQLite datetime-adapter deprecation warning retained.
- Complete planning suite: 75 passed, including pytest-style enterprise tests. Use `uv run python -m pytest industrial/planning/tests`; unittest discovery alone omits those enterprise tests.
- Existing industrial/mine suites: 39 and 27 passed; independent industrial acceptance: 4,245 checks.
- Physical operating model: 5,761 checks across 180 months.
- Ruff formatting/lint and existing strict mypy pass.
- Governance, institutional catalog, organization and repository-hygiene validators pass. Six new controlled PDFs bring the catalog to 84 source/publication pairs; all 78 preceding publication bytes remain preserved.
- Browser exercised in local headless Chromium: scenario/year/entity/unit filters, twelve-month cash chart, all data sections, document links and procurement identifier drilldown. Full provisional data loaded in approximately 1.3 seconds on the development machine; this is an observed local timing, not a general performance guarantee.
- Package checks include exact SQLite/OOXML cell readback, source/date/private-content selection, ZIP CRC, every member checksum and deterministic container bytes. CI and final release preparation rebuild the whole pipeline twice to test model-level reproducibility.

No immutable finance source pin, accepted v1 numerical artifact, approved artwork, private control-repository payload or open corporate policy was rewritten. New complete ZIPs are release assets; source, controlled documents and code remain in Git.
