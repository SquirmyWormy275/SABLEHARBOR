# Synthetic control execution and evidence

This module exercises the ten existing local controls in [the business interface registry](../../../docs/structured/business-lines/interfaces.json). It preserves their common-control IDs and owner roles. All records are public synthetic forecasts for 2027–2031. A generated PASS is evidence that the stated source assertions were re-performed in this model. It does not establish that a real company control operated, confer production access, or constitute a professional assurance opinion.

The schedule contains 42 applicable control/unit combinations across seven businesses and corporate. Three scenarios and 60 months produce 7,560 expected occurrences, regardless of whether evidence exists. Monthly exercise frequency is recorded separately from each control's original event-based or close-based frequency.

## Evidence and test coverage

| Existing local control | Source assertions re-performed |
|---|---|
| LC-REVENUE | Journal balance and event lineage; invoice events to AR postings and accepted event/versioned subscription source; nonnegative AR and deferred balances |
| LC-CREDIT | Invoice claim/collection/writeoff/recovery/credit equation; contractual due dates; graded allowance calculation and exposure/allowance to the monthly close |
| LC-RECOVERY | Contained/recovered mineral and hard bypass; complete run-to-capture genealogy; recovered mass and allocated cost on each edge |
| LC-TRANSFER | Explicit gate decision; qualification, receiving owner and maintenance owner before production transfer |
| LC-WORKFORCE | Authorized/occupied position identity; unique person and assigned FTE; protected staffing boundaries; assignments to gross payroll-request journals |
| LC-ESTIMATE | Prior-to-revised forecast decomposed into price, volume, timing and workforce contributions with a preserved vintage identity |
| LC-CONSOLIDATION | Unit trial-balance balance; assets/liabilities/equity; classified cash-flow arithmetic and available management-cost reconciliation |
| LC-ATLAS | Complete eight-part matter permission evidence, client identity, and blocking of work/billing/recognition when rights or another gate fails |
| LC-INDUSTRIAL | Owned-service hours to dated shifts; crew/equipment/interface/maintenance capacity; infeasibility and source/detail quantity and cost reconciliation |
| LC-ADVISORY-VALUE | Certified committed/variable fee arithmetic, immutable baseline hash and value-officer identity; available independent determination fields |

Cradle labor capitalization legitimately reduces payroll expense after a gross payroll request. The workforce test uses only journal entries sourced from PAYROLL_REQUEST events; it does not confuse capitalized labor with missing pay.

The enterprise builder separately proves full legal-to-unit/account reconciliation, the exact retained 2026 reconstruction, source population replacement and journal completeness. Unit control tests complement those build gates. The control module's `enterprise_unit_trial_balance` and `enterprise_unit_statements` source aliases refer to the enterprise result's `unit_rows` and `unit_monthly_rows`. `replacement_bridge` is supplied by the builder. Other table names resolve directly to operating model source exports.

## Results and incomplete coverage

PASS requires nonempty supported required populations, complete evidence attachments and successful source assertions. FAIL means performed assertions failed, or a required artifact was withheld in the explicit exception exercise. NOT_RUN means required evidence is absent, fields are unsupported/malformed, or no assertion could be performed. An empty table is never proof that an activity did not occur. The completeness register preserves missing counts separately from test results.

Some monthly occurrences intentionally remain NOT_RUN. Selected Advisory cases have detailed permissions; Atlas runtime entitlement enforcement is outside this package. Transfer and certification evidence occurs in particular months. The two industrial units do not share identical evidence depth: ARU has dated shifts; Pale Sun retains monthly mine planning and maintenance/cost detail, so this module does not assert a new daily mine control test. Industrial workforce does not acquire a fabricated Core person roster. These limitations are visible by unit, control, month and reason.

An industrial capacity failure is retained even when all software reconciliation tests pass. Such a result identifies a schedule needing operational resolution; the model does not silently resize equipment or claim approval.

## Population integrity

Nine tables contain registry, expected occurrences, population manifests, evidence manifests, original results, completeness, exceptions, actions and retests. Each population manifest identifies the exact scenario/month/reporting-unit slice, table, row count and canonical SHA-256 hash. Underlying source rows remain in their source export instead of being copied into every test record. An evidence artifact binds the same count and hash to explicit synthetic preparer/reviewer identities.

`validate(model)` rebuilds expected records from the live source tables and compares every exported field. Removing an occurrence, changing a source row, relabeling an outcome, removing an evidence attachment or altering a retest fails verification. The validator restores the supplied record set before reporting a failure; it never repairs altered results into apparent compliance.

## Exception lifecycle

One source-configured March 2027 base-scenario Advisory revenue exercise withholds a journal attachment while retaining the underlying ledger. The March result remains FAIL. A temporary synthetic waiver expires at March month-end; April records escalation. May records remediation and a rejected self-review. June closes only when a distinct reviewer re-performs the original March assertions, verifies all required sources and reproduces the original population hash.

The original result is immutable. A current month's PASS, a PASS label supplied in configuration, an unexpired waiver or a preparer's self-test cannot close the finding. Missing or failed original evidence leaves the exception open. These are modeled exercise records, not real waivers or approvals.

## Verification

Run `python -m pytest enterprise/operations/tests/test_controls.py`. Negative cases cover missing evidence, complete monthly scheduling, source and result tampering, incomplete exports, waiver chronology, self-review, original-period retests, invoice/allowance math, payroll capitalization, blocked rights, genealogy and industrial capacity.
