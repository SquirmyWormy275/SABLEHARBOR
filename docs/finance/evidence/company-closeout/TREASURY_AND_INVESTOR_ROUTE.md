# Treasury timing, debt/security and investor reading route

Prepared September 15, 2026 UTC. SH-C04 implementation extension, pending
repository acceptance. All company records here are synthetic. This source
publication describes the generated timing views; it does not certify solvency,
independent bank evidence or covenant compliance. The owner adopted corporate tax
from formation and the exact five-holder register; final monetary integration and
repository acceptance are identified in the company release receipt.

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
September, October and November, three scenarios. The exporter lists every selected scenario/journal/line/source ID and source
availability, and produces 546 weekly rows over six legal entities plus
consolidated, two explicit timing cases. The selected cash-leg count follows the
composed tax and payment population; the initial 333-leg run is historical
implementation evidence, not a fixed successor population. One duplicate cash identity fails validation. There are
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

The original pre-tax timing sensitivity first showed negative SHI cash in week 4
ending September 28 and a November shortfall. Those amounts are historical
implementation evidence, not the final tax-adjusted answer. Read the current
`treasury_13week.csv` and `treasury_month_bridge.csv` from the same frozen edition
for exact cash, source population and shortfalls. This sensitivity does not
rewrite the original base-case zero-arrears finding. Uniform timing and assumed
member receipts cannot prove daily sufficiency. Booked unpaid tax requirements
also remain separately visible in `sovereignty_tax_requirements.csv`; a cash
balance does not extinguish a payable.

## Dated payment/filing checkpoints: not additional journal entries

| Native record | Supported date/period | Amount or condition | State and treasury treatment |
|---|---|---|---|
| ARU new term principal | October 7, 2026 | $375,000 principal | Accepted model payment date; already within October legal cash, never added a second time |
| ARU term interest | October 2026 | $122,956 in regenerated debt schedule | Monthly ACT/365 modeled expense/cash; an independent lender value date is not established |
| ARU lease principal/interest | October 2026 | $42,466 / $8,973 | Separately modeled in October; no invented lender settlement confirmation |
| ARU intended 338 election | October 15, 2026 | Eligibility, participation/signatures and submission evidence | Filing-ready source is not submitted; no cash-tax amount inferred from election due date |
| ARU retention second installment | January 7, 2027 | $250,000 | Outside this 13-week window; remains in commitments navigation |
| Workforce payroll/tax | Completed payroll, retention and tax calendar sources | Regular gross-to-net and July employer-levy accrual are separate populations | The weekly allocation does not prove tax remittance; an accrued/unremitted liability remains outstanding |

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

The [current debt and host disposition](../../../internal/company-closeout/DEBT_AND_HOST_DISPOSITIONS.md)
supplies the expressly authored existing creditor identity, selected clearing
records and opening/activity/closing bridges. Earlier generic lender-identity
review fields no longer remain unanswered. Definitive maturity/prepayment terms,
numerical covenants, asset-specific collateral and old encumbrance releases
remain separate material instrument limits, DEBT-R01 and DEBT-R02. The model's
amortization horizon is not a lender-agreed maturity. Common ownership does not
make every entity a guarantor. No goodwill-removal default or covenant headroom
is inferred without the governing definition. Corporate finance/legal owns these
specific rights questions; supported principal and cash arithmetic remains usable.

## Investor reading route from the same edition

1. **Identity and governance:** `industrial/source/entities.json` and
   `docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md`. Start with LLC identity,
   legal ownership chains, nine-member board, CEO/Chair separation and investor/
   independent roles; never infer new entities from business-line names.
2. **Ownership and financing history:** 2021-06-18 and 2022-10-28 board minutes,
   plus `enterprise/closeout/source/capital_register.json` and the dated owner
   direction. Exact authored subscriptions are $48 million/$135 million, and the
   approved five-holder schedule totals 100 million equal participating units.
   `docs/internal/company-closeout/FOUNDER_ADMISSION_BASIS.md` explains the newly
   authored formation value, zero founder contribution and initial basis.
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
   `enterprise_funding.csv`, `sovereignty.csv`, `sovereignty_tax_requirements.csv`
   and the composed current/deferred/payment tax workpapers.
   Annual operating cash, all net investment and member money remain distinct;
   report current dependence and reversals without promised attainment year.
6. **Debt, related parties and downside:** ARU debt/lease source schedule,
   reciprocal ownership funding, intercompany eliminations and the unavailable
   member-cash timing case. A balanced consolidated model is not committed
   funding, an independent bank confirmation or an investment recommendation.

## Approved ownership and contribution states

The owner adopted Daniel 33.25%, Priya 19.95%, Jon 13.30%, Harrison Vale 18.50%
and Wolf Ridge 15.00%. Each financing lead is expressly authored as its round's
sole registered subscriber; this is not inferred from the word “led.” The exact
register preserves existing board roles and grants no new preferences, ordinary
operating veto or compulsory funding obligation. Substantive designation and
replacement thresholds and any unlisted side letters remain outside the adopted
scope; the register does not assert that unknown instruments are absent.

`enterprise/closeout/capital_register.py` consumes each final SHI MEMBER_EQUITY
source event and delegates cash-cent allocation to `capital.py`. The participation
shares sum to one. Largest-remainder allocation, with holder-ID tie break,
reconciles each cash request while retaining the source journal's four-decimal
amount and explicit source-to-cash rounding bridge. Historical $183 million
subscriptions are paid-in capital history, not additional 2026 cash. Retained
earnings and initialization corrections remain separate equity components.

The working model's voluntary proportional contributions issue no new units.
Scenario capacity, commitment, request/authority, due date, receipt and issuance
remain separate states; month-only modeled receipts do not fabricate a daily
settlement date or binding capital call. An unavailable holder's shortfall does
not transfer another holder's cash, change ownership, or authorize borrowing.
The final edition identifies exact holder-level rollforwards and the tax-adjusted
funding population. Source implementation and repository acceptance are distinct.
