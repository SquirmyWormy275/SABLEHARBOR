# Treasury timing, debt/security and investor reading route

Prepared September 15, 2026 UTC. SH-C04 implementation extension, pending
repository acceptance. All company records here are synthetic. This source
publication describes the generated timing views; it does not certify solvency,
independent bank evidence, covenant compliance or an adopted parent tax provision.

## Thirteen-week contract

`python -m enterprise.closeout.treasury enterprise/generated/company-closeout-v1`
exports `treasury_13week.csv`, `treasury_month_bridge.csv` and
`treasury_cash_population.csv`. The company build invokes the exporter and
includes these outputs in its manifest. The period is September 1–November 30,
2026: thirteen consecutive Tuesday–Monday weeks, America/Los_Angeles. Opening
cash is the accepted-source model's August 31 close. September 15 known-on date
means this entire view is a newly prepared conditional timing reconstruction,
not bank evidence retrospectively available September 1.

Population: every cash-account 1000 leg in the composed enterprise journal for
September, October and November, three scenarios. The initial run selects 333
cash legs, lists their scenario/journal/line/source IDs and source availability,
and produces 546 weekly rows over six legal entities plus consolidated, two
explicit timing cases. One duplicate cash identity fails validation. There are
126 entity/scenario/case/month reconciliations. An omitted cash leg fails its
month bridge rather than becoming a favorable liquidity assumption.

**Uniform timing assumption:** allocate each monthly cash leg evenly over the
calendar days, at four decimal USD precision; the month's final day receives the
rounding remainder. This is deliberately explicit arithmetic, not a claim that
customers, employees, vendors, tax authorities or lenders settle daily. Each
week satisfies opening + receipts − payments = closing. Each month closes to
the source statement exactly. Source-provided net allocations remain net; the
view cannot reconstruct individual gross receipts/payments absent from them.
Consolidated receipts/payments net matched source/flow legs before counting, so
interentity cash transfers do not become external funding. Their legal cash
consequences remain visible separately; consolidated cash is not automatically
available to each legal entity.

**Unavailable-member-cash sensitivity:** omit SHI cash legs with source type
MEMBER_EQUITY and retain every source payment/transfer to expose the funding
shortfall. No extra borrowing, dilution, compulsory call, alternative holder
cash, payment waiver or automatic spending cut is created. The month bridge is
source closing less cumulative unavailable cash. Negative balances signify an
infeasible unchanged payment plan requiring management response, not a claim
that negative bank cash was actually permitted or that a modeled obligation was
paid without funds. Subsidiary transfers remain scheduled; their feasibility
now depends on fixing the parent shortfall.

In the initial base run, SHI uniform-timing cash stays approximately at the
scoped $2M model floor (fractional allocation differences reverse at each month
end). With member cash unavailable, it first shows a negative weekly close in
week 4 ending September 28 (−$377,105.7912); November 30 closing shortfall is
−$5,719,577.1334. This sensitivity does **not** overturn the source base-case
zero-arrears finding. Uniform timing and assumed member receipts cannot prove
actual daily sufficiency. Parent tax remains a separate unposted sensitivity.

## Dated payment/filing checkpoints: not additional journal entries

| Native record | Supported date/period | Amount or condition | State and treasury treatment |
|---|---|---|---|
| ARU new term principal | October 7, 2026 | $375,000 principal | Accepted model payment date; already within October legal cash, never added a second time |
| ARU term interest | October 2026 | $122,956 in regenerated debt schedule | Monthly ACT/365 modeled expense/cash; an independent lender value date is not established |
| ARU lease principal/interest | October 2026 | $42,466 / $8,973 | Separately modeled in October; no invented lender settlement confirmation |
| ARU intended 338 election | October 15, 2026 | Eligibility, participation/signatures and submission evidence | Filing-ready source is not submitted; no cash-tax amount inferred from election due date |
| ARU retention second installment | January 7, 2027 | $250,000 | Outside this 13-week window; remains in commitments navigation |
| Parent payroll/tax | Period-specific population required | No employee-net-pay/remittance dates supplied by aggregate cash legs | The weekly allocation is not a remittance calendar; join completed workforce sources before claiming payable clearance |

The October source term rollforward is $21,750,000 opening − $375,000 principal
= $21,375,000 closing. The 6.75%, ACT/365 principal-date calculation is in
`industrial/tools/build_financials.py`; the generated
`industrial/generated/finance/aru_2026_debt_leases.csv` is independently
reproducible from `industrial/source/finance.json`. The full October interest
is not all interest due on October 7; no such lender assertion is made.

## Debt and security perimeter

[Transaction accounting](../../../../industrial/finance/TRANSACTION_ACCOUNTING.md)
records the $22.5M initial term financing, $375,000 quarterly amortization,
6.75% ACT/365 convention and $5M undrawn revolver with 0.25% modeled commitment
fee. The revolver is capacity, not cash. Retained leases are separately modeled.
The old $13.5M term/revolver payoff belongs to acquisition sources/uses and
excludes leases. An accounting payoff is not proof of release of collateral.

[Debt/security draft source](../../../legal/gap-instruments/source/debt-liens.json)
retains exact missing terms: DEBT-U01 lender/grantors/guarantors; U02 contractual
maturity/business-day/late-interest/prepayment terms; U03 collateral and consents;
U04 payoff value date and instrument-specific releases; U05 numerical covenants
and definitions. The model's amortization horizon cannot become a lender-agreed
maturity. None of the companies is declared a guarantor merely from common
ownership. No covenant headroom can be certified and no goodwill-removal default
can be asserted without the governing definition. The affected claim is security
and covenant enforceability/compliance, not whether the model's principal
arithmetic balances. Next owner: corporate finance/legal implementation.

## Investor reading route from the same edition

1. **Identity and governance:** `industrial/source/entities.json` and
   `docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md`. Start with LLC identity,
   legal ownership chains, nine-member board, CEO/Chair separation and investor/
   independent roles; never infer new entities from business-line names.
2. **Ownership and financing history:** 2021-06-18 and 2022-10-28 board minutes,
   plus `docs/legal/evidence/corporate/SH-LEGAL-READ-CAPITAL-001.md`. Approximate
   $48M/$135M rounds and 66.5/33.5 ownership are not exact subscriptions.
3. **Results and revenue quality:** edition legal/unit statements and source
   journal; follow Foundry Field FF-003 separately through billing evidence.
   Customer principal, seller-borne tax, credits and collections have distinct
   populations. September–November forecasts are not completed historical sales.
   Business contract/workload sources supply project and concentration context;
   no forecast contract value is labeled audited backlog or recurring ARR.
4. **Estimates and commitments:** ARU acquisition/tax bridges, Red Wash closure
   calibration and runtime construction budget/asset sensitivities. Land/CIP,
   external-host rights and planned investment do not equal accepted operating
   buildings or funded construction commitments. Goodwill correction is noncash.
5. **Liquidity and dependence:** `treasury_13week.csv`, its monthly bridge,
   `enterprise_funding.csv`, `sovereignty.csv` and `parent_tax_sensitivity.csv`.
   Annual operating cash, all net investment and member money remain distinct;
   report current dependence and reversals without promised attainment year.
6. **Debt, related parties and downside:** ARU debt/lease source schedule,
   reciprocal ownership funding, intercompany eliminations and the unavailable
   member-cash timing case. A balanced consolidated model is not committed
   funding, an independent bank confirmation or an investment recommendation.

## Exact ownership residual and prepared allocation

FIN-U01/U02/U03/U05 in the financing source remain the operative narrow gaps:
subscriber identities and allocations, class/quantity/price, designation
thresholds and preference/conversion/anti-dilution/transfer economics. No accepted
complete subscriber list has been found; lead firms cannot be expanded into a
syndicate or treated as sole subscribers. The unknowns affect who can be asked
for how much, whether the agreed participation basis is economic or voting, and
whether additional paid-in contributions without interests preserve each class's
rights. They do not block arithmetic preparation or justify new outside investors.

`enterprise/closeout/capital.py` prepares proportional requests only after an
established participation basis totals one. It preserves supplied rights,
separates requested/committed/received/issued states and allocates rounding by
largest remainder with holder-ID tie break. Its test holders are clearly fixtures.
No request has been sent and no fictional holder settlement has been asserted.
The remaining operation is to reconcile/adopt the actual rights schedule under
existing authority, then supply its stable IDs and source to the allocator; no
rounded back-solve of the historic cap table is allowed.
