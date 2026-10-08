# First fresh P1 procedure pilot: selected SEC003 vulnerability trace

**Decision:** pilot the same exact P1 task in a new, disposable A/B engagement:
`TASK-SH-SEC-003-corporate-CHECK-SOC2:CC7.1` (control `SH-SEC-003`,
`SOC2:CC7.1`). Its authored instruction is: “Reconcile inventory, scan and
baseline populations; trace drift and a newly disclosed vulnerability through
detection and correction.” The frozen P1 A and B copies are both
`NOT_STARTED`/`NOT_RUN`; this document does not execute or alter either copy.

SEC003 is the first pilot because the selected fictional SVC-compute source has
an explicit four-asset footprint and two contrasting native histories (11 Clean
and 18 Messy versions). The historical packet offers a relevant *method*
candidate: reconcile asset coverage across scanners and advisories, validate
findings, and verify remediation by rescan or exception. Its old A/B workpaper
locators (`WP-53f4bcc308cea1d0d40ec9b0` and
`WP-f708d3e293dd0cd94168d24a`, respectively) are method locators only. Do
not copy old observations, samples, evidence, outcomes, or the instructor Key.
Current V17 classifies the authored task `UNSUPPORTED_EXACT_CLAUSE`; V15 PBC
keeps its `SH-SEC-003` request `DRAFT_NOT_SENT` and names AS-P008 only as a
proposed contact. P1's `owner_id=AS-P008` identifies the company-side owner,
not the independent auditor or reviewer. Neither state changes through
planning.

## Exact source and population

The pilot's *declared selected cohort* is the four SEC005-managed SVC-compute
assets `SIM-RNO-EDGE-01`, `SIM-RNO-OPS-01`, `SIM-BOI-EDGE-01`, and
`SIM-BOI-OPS-01`, for the fictional 2027-10-12 to 2027-11-11 source interval.
The company-native SEC003 store is the V18 candidate component
`scenario-sec003vuln` (`F27SEC003VULN`), branch
`SEC003-SELECTED-CLEAN` for A and `SEC003-SELECTED-MESSY` for B. The ordinary
source is its `company.sqlite3` under
`enterprise/generated/audit-suite/company-sec003-selected-vulnerability-2026-09-30/main-run-v1/`.
Collect the ten native systems' complete selected-interval version set from
that source, including immutable earlier versions: 11 A, 18 B. Separately
collect the SEC005 upstream inventory and baseline originals, and B's drift,
agent-coverage loss, recheck, correction and restoration references, through
their own ordinary source. A route row, receipt, portfolio, prior collector
copy or producer-supplied list is a locator/reconciliation aid, not the source
population. The four assets are **not** the enterprise asset estate; the
synthetic advisory is not a CVE, executable scan, or network probe.

The population workpaper must record branch, service, time interval, source
query/filter, pagination, version history, all exclusions, expected and
observed asset/version counts, and independent joins between SEC005 inventory,
SEC003 census, baseline, schedule, scan and advisory. Define population
completeness against the selected four-asset footprint from upstream SEC005
and the SEC003 source sequence; never infer enterprise or full-period
completeness from the 11/18 selected receipt counts. Preserve `event_at`,
`available_at`, and actual `imported_at` separately, including what was
available to the October reviewer before the November correction.

## Collection and re-performance sequence

1. Use the independently reviewed V18 selected-source collector as the access
   pattern, then create a **fresh disposable P1 engagement** from the frozen
   baseline, with separate A/B auditor workrooms and no copied historical
   workpapers. Keep the original P1 538-file inventory untouched. Record an
   independently approved narrow test scope and auditor/reviewer separation. The V18
   portfolio candidate and reviewed V18 disposable collector are access
   diagnostics, not this collection or a population claim.
2. In a disposable ordinary-byte source copy, grant the auditor only the A or
   B SEC003 and needed SEC005 systems. Discover the native versions by source
   query (`CompanyStore.list_systems` and paginated `list_records`), then use
   exact-version `collect` for all selected-period rows (11 A/18 B plus exact
   upstream joins), with content hash, source identity and three clocks on
   each retained receipt. Verify every original against the pinned source
   database, manifest and independent review; revoke the grant after
   collection. The V18 collector, like V17, collected only one SEC003 advisory
   per side; reproducing that probe alone is insufficient.
3. Census all four declared assets for October inventory, baseline and scan
   coverage. Select the one synthetic affected asset `SIM-BOI-EDGE-01` for
   deep advisory→finding→triage→approval→fix→retest tracing; also inspect
   `SIM-BOI-OPS-01` explicitly as the missing October coverage item in B.
   This is a 4/4 selected-cohort census plus a judgmental one-finding trace,
   with no statistical or enterprise-period extrapolation. Record selection
   before inspecting branch outcomes.
4. Reperform coverage by **asset ID**, not reported count. Reconstruct the
   October decision from records then available. Compare the November
   correction and retest without rewriting the October snapshot. Check the
   exception's current disposition and whether the reviewer is independent
   of AS-P008's operating sign-off. Attach a new auditor-authored workpaper
   with procedures, population/exclusions, sample basis, exact collected
   receipts, recalculation, contradiction log and a bounded conclusion.

Development-only scenario expectations for independent challenge: A's October
scan covers 4/4, reports a finding on `SIM-BOI-EDGE-01`, and records an
authorized fictional fix, four-asset retest and selected closure. B's October
census/baseline/scan cover only 3/4 but the scan reports four; AS-P008 signs a
false-clean reconciliation. November records correction, 4/4 rescan, fix and
retest, while the historical missed-coverage exception stays **OPEN** and
AS-P008's review of the earlier sign-off is self-review. One unresolved
causal discrepancy must be investigated rather than smoothed over: B omitted
`SIM-BOI-OPS-01`, but the advisory names `SIM-BOI-EDGE-01`, which B's October
scan lists as observed. The omission alone does **not** explain why the
advisory finding was missed. Require an independent explanation from native
baseline/advisory/scan logic or report the unexplained false-clean condition.
Do not seed the auditor's workpaper with these expected results.

## Disposition and credit gate

Current disposition is **no task credit**. The selected source, V17 route,
V15 PBC draft, V18 portfolio and V18 disposable collector do not supply a
complete enterprise/period population or an executed independent audit
procedure. The reviewed V18 collector proves a scoped access path, but its
SEC003 one-advisory collection must be extended to the exact selected cohort
and upstream originals before procedure work. No legal/PHI applicability,
actual deployment or real scanner activity is asserted.

A *bounded performed-task* credit proposal is reviewable only after a fresh
engagement has: (a) an authorized, documented selected-cohort procedure whose
scope is accepted for this task; (b) an independently reconciled selected
population and direct native collection with immutable custody and clocks;
(c) auditor-selected sample and actual re-performance of the steps above;
(d) explicit October/November exception and causal-discrepancy disposition;
and (e) an independent reviewer who was not the source operator or procedure
performer, signing exact workpaper and source hashes. A negative/limited
finding can still document that a procedure was performed; it does not mean
CC7.1 operated effectively. If engagement policy requires the full enterprise
inventory/scan/baseline population to credit this exact authored task, or if
the selected cohort/causality cannot be reconciled, leave the task uncredited
and retain the work as a separately labeled selected-scope pilot. No Key,
grade, SOC 2 Type 2 conclusion or broader 409-task promotion follows from
either outcome.

## Frozen inputs (SHA-256)

All private paths below are relative to the SABLEHARBOR audit-suite private
root, not the tracked repository. Reviewed collector pins prove only a
disposable selected-source access diagnostic.

| Input | SHA-256 |
| --- | --- |
| `enterprise/audit_suite/DOCUMENTARY_283_ROUTE_RECONCILIATION_V17_2026-10-01.json` | `43b33d7ca19e670eea704193fff947c268c2d1c736f0c8829420a556576e8bcb` |
| `enterprise/generated/audit-suite/documentary-283-route-reconciliation-v17-2026-10-01/independent-review-main-v1/REVIEW.json` | `dee0ff288245b0306b79c3b9819f61c940c45fb0355eec5b94a2e73baa0f6db2` |
| `enterprise/audit_suite/UNSUPPORTED_121_PBC_PLAN_V15_2026-10-01.json` | `012aceb233bbaf7cd51f5e3859d6c7b7845992055a4da1e68a069db6e26fa1bc` |
| `enterprise/generated/audit-suite/unsupported-121-pbc-plan-v15-2026-10-01/independent-review-main-v1/REVIEW.json` | `b5d1082b89088d7a08d021efa51cf30d5e6ff938d50e66944a870413d3089586` |
| `enterprise/generated/audit-suite/procedure-method-crosswalk-2026-10-01/main-run-v1/REPORT.json` | `8f7933dd06ffdd80a60d559e06725bbeda22575f9ac9c4d10b7c43c16874ad04` |
| `enterprise/generated/audit-suite/procedure-method-crosswalk-2026-10-01/independent-review-main-v1/REVIEW.json` | `a433740635298a63b1d3877cbeeb619d30660d5cd50da8e46c36fd7cb1221478` |
| `enterprise/audit_suite/sec003_selected_vulnerability_spec_v1.json` | `c4ac9b9de07f046027bb02bdbc4328ef3b49b6f5cba32ad4013280e06e91110d` |
| `enterprise/generated/audit-suite/company-sec003-selected-vulnerability-2026-09-30/main-run-v1/{MANIFEST.json,RECEIPT.json,company.sqlite3}` | `4ae2200e8735ea60e4a85f1158782926fdd50eda96238fc15031d5d9eda69af3`, `85233a1e785ffea73f32996bc3f410e9b5c381720b6cbe941ff8a2bbd5474ff8`, `a94b9f0e2d18e06afd2c83ae2012cea8da72102f9bafcf0e3968959eb6f1539f` |
| `enterprise/generated/audit-suite/company-sec003-selected-vulnerability-2026-09-30/independent-review-main-v1/REVIEW.json` | `f15bc7d94d04fa3599a0f852470e81ea53ce3dc1685d05d0fb15a65901013f36` |
| `enterprise/generated/audit-suite/company-source-portfolio-v18-2026-10-01/main-report-v1/REPORT.json` | `254f5d1cc4d5a93da95f6fc9e5977fc36f0397511b96cd6cb5e7cd59dc56337a` |
| `enterprise/generated/audit-suite/company-source-portfolio-v18-2026-10-01/main-candidate-v1/A.json` | `750de5973825de9750029ccdef1f42faf681dc7addd03b8536241c48872f2d1d` |
| `enterprise/generated/audit-suite/company-source-portfolio-v18-2026-10-01/main-candidate-v1/B.json` | `9332b7f3821dd09dd643cc104c9fc1e4c82679371253d2c779c40983e5bff569` |
| `enterprise/generated/audit-suite/company-source-portfolio-v18-2026-10-01/independent-review-main-v1/REVIEW.json` | `626ce0755804ee22a7963343fc8dee7d1e684098c614e9188b78e0baf1d91a97` |
| `enterprise/generated/audit-suite/company-collection-probe-v17-2026-10-01/main-run-v1/REPORT.json` | `b06818f158e2fc8982db07922255d56d0f867bcdea652fbe2200d7d105422dd0` |
| `enterprise/generated/audit-suite/company-collection-probe-v17-2026-10-01/independent-review-main-v1/REVIEW.json` | `3db47fb5163c7e95a1ac031eff4959cc3f48a5cde711a15bdb51217ae3900fbb` |
| `enterprise/generated/audit-suite/company-collection-probe-v18-2026-10-01/main-run-v1/REPORT.json` | `b881ec73c2d6d0698353254aee4a8f8082c8c92e4af2668c21f44e5b48bc4f9f` |
| `enterprise/generated/audit-suite/company-collection-probe-v18-2026-10-01/independent-review-main-v1/REVIEW.json` | `0b604e7808c54d43c5d34d0aa417c951642d7f1baa46d2f467481422d52479df` |

The frozen P1 inventory is 538 files with inventory SHA-256
`f266ef682b502b3b093170f8a7b64fcf5cbab722d5c8ddf6715a63c0e535360f`.
