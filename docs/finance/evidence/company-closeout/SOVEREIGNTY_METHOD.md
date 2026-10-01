# Continuing sovereignty reporting

**Document ID:** SH-CAP-SOVEREIGNTY-2026-09-15
**Version:** 1.0.0
Prepared September 15, 2026 UTC; implementation pending integrated acceptance.
Authority: [SH-VOICE-CAP-01](../../../canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md).

Sovereignty here means less recurring member-funding dependence while preserving
accepted ownership and governance. It does not mean legal sovereignty, removal of
investors, unlimited financing or a promised attainment year. Every successor must
retain the objective, these source populations and explanations of improvements
and reversals. The generator does not optimize a margin, payment date or target curve.

## Reproduction and accounting populations

`enterprise.closeout.report` consumes the final composed legal/consolidated books
after tax and Treasury allocation. Its `sovereignty.enrich` step joins the existing
industrial journal, asset/debt schedules and Core obligation/payment history.
`sovereignty.csv` has three scenarios × six years, 2026–2031. These are distinct
annual source-calibration/forecast rows, not completed-period bank evidence.
`sovereignty_investment_purposes.csv` identifies the underlying cash sources;
`sovereignty_entity_liquidity.csv` preserves each legal entity and consolidated
monthly cash view without adding the views together or granting transfers.

The seven source IDs producing predecessor base-2027 member cash
$13,325,751.3907 remain a separate reperformance. Their total is not a forced
successor result. Actual successor amounts come from SHI cash legs with source
type MEMBER_EQUITY, once; downstream contributions eliminate at consolidation.
Existing holders' cash is external financing regardless of unchanged ownership.
Capacity, requests and hypothetical refinancing are not received cash or binding
commitments. Exact holder allocation follows its own accepted register; a proposal
does not fill missing material rights by implication.

## Source-based investment purposes

These classifications are expressly authored management purposes, not changes to
the accepted invoices, asset costs, accounting classes or legal obligations.

| Population | Sustaining | Growth |
|---|---|---|
| 2026 ARU budget | Existing $3.3M sustaining and $11M catch-up | $5.25M interface |
| 2026 RWH budget | Existing $4M sustaining and $5M rehabilitation | $3.25M interface |
| Industrial 2027–2031 | Native paid replacement-capital source entries | Native paid construction entries |
| Core legacy equipment | Routine equipment refresh within existing operations | None assigned to this small existing population |
| New research equipment | None assigned | Existing asset-receipt requests for new capability |
| Runtime hardware | Refresh of prior capacity on the existing four-year cycle | Initial deployment and incremental capacity |
| Runtime facilities | None assigned | Existing conditional facility requests |
| Existing ARU acquisition | None | Existing acquisition cash presentation, net of $2M acquired cash |

The runtime refresh share is the smaller of current and preceding capacity cost,
divided by current equipment cost, only in the source-defined refresh year. The
remaining portion adds capacity. Funded obligation history applies that share to
actual modeled payments, including deferred payments made later. Unknown new
investment sources fail validation rather than inheriting a convenient purpose.
Four-decimal monetary rounding can leave sub-cent classification differences;
the reconciliation tolerance is one cent and never changes journal cash.

Net paid sustaining plus net paid growth must equal consolidated investing cash
outflow for every scenario/year. Acquired cash offsets acquisition investment;
it is not operating generation. Planned remaining project budgets, deferred
capital and booked unpaid obligations remain separate states. No binding
commitment or independent payment evidence is inferred from these model records.

## Cash attribution and unpaid obligations

Let **O** be reported operating cash flow, **S** sustaining cash investment,
**F** paid debt principal and other financing payments, and **ΔR** the change in
recorded unpaid due requirements, unresolved land settlement and separately
booked current tax payables, including unpaid employer payroll levies.
`sovereignty_tax_requirements.csv` retains each legal
entity/account balance; `booked_current_tax_payables_usd` does not assert all those
balances are already past due. `outstanding_booked_cash_requirements_usd` is the
combined population. Deferred tax is excluded; a refund position in one entity
does not offset another entity's unpaid tax. The older
`outstanding_due_or_unresolved_settlement_usd` retains its original nontax scope.
Then current-year cash available before growth is **O − S − F − max(ΔR, 0)**. Interest and tax cash
already in O are not subtracted again. The land settlement is an existing recorded
liability, not a new loan or assumed vendor-finance arrangement. Its unchanged
balance is not repeatedly deducted each year. These are payment requirements,
not segregated funded reserves. Aggregate cash coverage and requirements exceeding
cash are shown before other operating needs/floors and legal transfer restrictions.
A reduction in prior requirements has unknown funding origins and is not added
to current-year internal generation. Actual payments enter the source cash flow once.
The existing acquisition financing presentation is grossed up using its $13.5M
refinance and $0.3M issuance costs: draw and cash uses increase equally; net cash
and growth attribution remain unchanged.

Growth attribution uses current-year available internal cash first. Current-year
member and other external financing inflows first cover any deficit in that
availability measure; their remainder can fund paid growth. A third amount remains
**unattributed** where opening cash origin or unpaid-obligation timing prevents
an evidenced assignment. It is never relabeled internal generation or filled by
a fictitious receipt. The three portions sum to net paid growth. This annual
management attribution is not a legal-entity cash-transfer authorization or an
assertion that fungible bank balances identify the origin of each dollar.

Closing unpaid amounts and the within-year peak remain explicit. Accumulating
unpaid bills cannot improve internal growth attribution: the reserve change removes
the apparent operating-cash benefit. Reduced annual member cash may coexist with
arrears, refinancing, consumed opening cash or deferred growth. The report exposes
those conditions and does not infer resilience or all-growth self-funding from zero
member receipts. The inherited $2M floors retain their original entity/group scope;
this report creates no universal reserve.

## Meaningful validation

Tests reject unknown investment purposes and unavailable-funding assumptions,
preserve the hardware refresh cycle, reconcile all investing populations to the
statements, and verify that unpaid-bill timing, previously reserved payments and
tax/interest already in operating cash cannot be counted twice. CSV/SQLite import
reperformance separately verifies journal population identity and cash equations.
The final edition receipt identifies the tested source revision and actual totals.
