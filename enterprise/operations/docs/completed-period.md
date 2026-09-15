# August 2026 people and operating reconstruction

**Record:** SH-OPS-COMPLETED-2026-08 · **Version:** 0.1.0
**Company period:** August 1–31, 2026 · **Authored/available:** September 15, 2026 UTC
**Canon state:** PROVISIONAL · **Repository acceptance:** pending integration
**Work packages:** SH-C01, SH-C03, SH-C07

This source completes a declared synthetic employee population and individual
payroll input for company-closeout review. It does not establish that the
composite company edition is accepted. Newly authored employment, compensation,
residence, withholding certificates, time and payment records are retrospective
fiction, distinguishable from recovered source facts. No payment, payroll filing,
license or government acknowledgement occurred outside the fiction.

## Sources and reproduction

The controlling structured input is
[completed_period_2026_08.json](../source/completed_period_2026_08.json). Its source
list identifies accepted organization, J2, industrial and mine records. The
[generator](../completed_period.py) extends the existing operations package and
uses its legal-entity/person/unit concepts. It does not change the conditional
2027–2031 roster, original financial releases, source locks or the portal runtime.

```bash
python -m enterprise.operations.completed_period
python -m enterprise.operations.completed_period --check
python -m pytest enterprise/operations/tests/test_completed_period.py -q
```

Outputs are `enterprise/generated/completed-period-2026-08/`: `records.json`, one
CSV per table and `manifest.json` binding source hashes, row totals, output hashes
and source commit. These are inputs to the integration-owned composite Release;
a scratch build alone is not delivery. `--output PATH` selects an isolated import
folder. `--check` rejects changed source or generated CSV bytes. The complete
JSON includes each table's rows; the CSV files expose the same public synthetic
population for the existing portal/importer. CSV null cells mean unestablished,
not zero. No private assessment answers are included.

## Population and exact overlap

| Population | Employees | Treatment |
|---|---:|---|
| SHI | 431 | Newly authored disjoint operating/ESS/IA/J2/corporate census |
| PS | 12 | Existing selected positions; Evan and Mari counted here once |
| RWH | 128 | Existing selected mine functions; Cole occupies RW-0013 |
| ARU | 73 | Accepted nonrail/corporate census, retaining EMP identifiers |
| BST | 58 | Accepted railway census, separate employer and railroad taxes |
| Total | 702 | One unique person, one position, one payroll per pay date |
| Nonemployee directors | 7 | Separate population; excluded from employee payroll |

All 44 accepted named employee identities remain. Their P identifiers are linked
to the underlying EMP/RW/SH-EMP position/person identifiers, not added as another
population. Mari's Red Wash office does not create a second paid person. Maya
Ortiz (RW-0112), Evan Cross (RW-0113) and Leah Foster (RW-0119) are explicitly new
fictional names assigned to existing mine positions for the controls lane.

The 431 figure is an explicit **new reconstruction choice**, with a changed
perimeter, informed by an older calibration. It does not assert that the old
431-Core row was a payroll census. In particular, Cradle and J2/ESS/IA are now
inside disjoint SHI allocations. The earlier 44-name bridge, 2027 occupancy,
industrial selected cases, 708 legacy total and runtime sizing users have never
been added together. The new census supersedes none until accepted within this
exact scope; old numerical/source bytes remain unchanged.

J2 uses its six accepted establishment groups: 181 reconstructed occupied
positions and 56 deliberately authored vacancies, totaling 237. The vacancies
are new fictional completion, not an inference that unnamed billets were empty.
Internal Audit remains outside ESS. Cross-functional leaders are allocated once;
chart membership does not establish another appointment or workplace.

August employment is an opening reconstruction with `effective_from=2026-08-01`;
that date is not an invented original hire or J2 commission date. Original
source joining years remain separate. Workplace attendance is not inferred from
headcount. The scheduled paid-hours population is 168 hours per employee,
including 16 hours paid leave for one employee; paid leave removes work capacity.
No overtime is modeled and no legal exemption is inferred from salary or title.

## Payroll and source-to-book bridge

Each employee has two semimonthly rows, on August 14 and 31. The August 15
weekend is handled by the earlier payroll date. Individual gross pay is based
on disclosed role bands or the accepted industrial salary and 3% 2026 cost
index. January–July taxable wage history is explicitly reconstructed as seven
monthly amounts solely for annual wage-base calculations, not a claim that
those earlier payroll records have been delivered.

| August measure | USD |
|---|---:|
| Gross earnings | 6,259,287.81 |
| Employee withholding | 1,706,523.80 |
| Net employee payments | 4,552,764.01 |
| Employer loaded burden | 1,877,786.71 |
| Total loaded expense | 8,137,074.52 |

The 1,404 payment records reconcile with 10 legal-employer/pay-date approvals,
payroll journals, individual synthetic clearing records and tax-liability
rollforwards. Net pay and calculated taxes have newly authored synthetic payment
states. Clearing records from the same authoring model are **not independent
bank confirmation**. Preparer and reviewer identities differ; these source
records do not prove live runtime review or access enforcement.

The 30% loaded employer burden remains a modeling envelope. Known employer
FICA/RRTA and $3,117.50 August BST RUIA are separately calculated inside it.
January–July reconstructed wages exhaust every nonrail annual unemployment base,
so August incremental FUTA/state UI is zero. BST's 2.5% experience rate is a newly
authored synthetic notice within the genuine 2026 permitted range, not a recovered
RRB notice. Remaining $1,345,337.82 is allocated to health/welfare administration,
existing employer benefit contributions and workers compensation coverage, with
three declared provider invoices per employer and modeled August 31 settlement.
No new voting, vesting, pension or substantive employee rights are created.
Every calculated withholding component, remittance date, closing liability and GL
leg reconciles. These are synthetic payment states, not filed returns.

**Do not add reconstructed payroll expense to existing payroll.**
`current_book_cost_components` decomposes existing August SHI paid operating cost
$11,968,000, PS platform SGA $233,333 and RWH production inventory-incurred cost
$2,329,167. Payroll is a component inside each unchanged source amount. RWH detail
does not create a second inventory asset or COGS charge. The ARU/BST
`payroll_source_bridges` independently exposes individual-cent versus whole-dollar
segment differences: ARU −$0.08, BST −$0.19, terminals +$0.18, trucking +$0.33,
warehouse −$0.13; retained aggregate source expense is unchanged.
`current_records.verify_current_finance(edition, legacy_snapshot, anchor_rows)`
reperforms the component parents and current revenue against the independently
generated legacy and industrial journals. It posts **zero additional journals**.

## Complete declared August commercial populations

[current_company_2026_08.json](../source/current_company_2026_08.json) and
[current_records.py](../current_records.py) provide 92 contracts, 88 distinct
customers and 104 Core customer service environments. The environments are not
assertions of company-owned physical sites. Every contract joins authority,
accountable employee, delivery, invoice and settlement-state records.

The newly authored Core commercial schedule has 44 Foundry Field, ten Atlas and
four Advisory customers. Along with one Cradle materials project, August SHI
principal revenue totals $11,075,500, independently matching retained book revenue.
Twenty-nine ARU/BST contracts preserve accepted customer identities and match
source journal external invoice amounts. Four mine contracts preserve their
accepted structure and monthly financial allocations. Mine/industrial customer
cash stays explicitly unallocated where source collection detail does not support
invoice-level assignment; monthly financial allocation does not establish
uranium shipment authority or converter acceptance.

Willow has three completed bench experiments with costs and failed/passed bench
outcomes, zero sales and no inferred field approval. Cradle's selected physical
materials project records feed, grade, yield, acceptance, price, direct costs and
three payroll allocations; its direct margin is $500.01 after individual payroll
rounding. A separate failed Demotte AMD experiment has $18,500 cost and no revenue.
These five current projects preserve research failures and distinguish sustaining
services from precommercial research. Corporate is represented by the complete
SHI employee, payroll, approvals and paid-cost component populations. Current
invoice sales-tax fields remain unestablished where the tax applicability work
has not concluded; this table does not infer a blanket exemption.

## Primary payroll authority and fact bounds

The input carries workpapers with URL, 2026 provision/table, access date,
fictional facts and conclusion. Federal withholding uses the 2026 standard
single schedule with the declared W-4 fields, independently checked against a
hand calculation. FICA wage bases and additional Medicare are separate from
income withholding. BST uses RRTA Tier I/Tier II and is not charged FICA again.
Sources: [IRS Publication 15-T](https://www.irs.gov/publications/p15t),
[IRS Publication 15](https://www.irs.gov/publications/p15), and
[RRB 2026 reminders](https://www.rrb.gov/sites/default/files/2025-12/_G-34%20%2812-25%29.pdf).

CA uses [2026 Method B](https://edd.ca.gov/siteassets/files/pdf_pub_ctr/26methb.pdf)
and [2026 SDI rates](https://edd.ca.gov/en/Payroll_Taxes/Rates_and_Withholding).
PA uses [2026 payroll memo 26-01](https://www.pa.gov/content/dam/copapwp-pagov/en/budget/documents/for-commonwealth-agencies-and-employees/for-agencies/payroll/payroll-memo-26-01-federal-withholding-state-unemployment-tax-2026.pdf)
and [Pittsburgh's EIT/LST rules](https://www.pittsburghpa.gov/City-Government/Finance-Budget/Taxes).
WV uses the [March 2026 optional single/one-job schedule](https://tax.wv.gov/Documents/Withholding/it100.2a.pdf).
Wyoming's [official state description](https://www.wyo.gov/about-wyoming)
confirms the absence of individual income tax.

PA employees have newly authored Pittsburgh residence; Bedford employees have
newly authored Fairmont residence. This does not locate a corporate parcel or
change accepted site geography. Fairmont's nonresident employee fee does not
apply to this resident population; resident utility charges are distinct.
The source identifies [ordinance 2057, section 920.03](https://codelibrary.amlegal.com/codes/fairmont/latest/fairmont_wv/0-0-0-24566).
All withholding certificates are modeled, with no pretax deferrals, dependents,
additional withholding or other-employer wages. Changes to those fictional facts
require recalculation. Individual tax returns are not established by these calculations. The separately
authored BST experience-rate record and zero incremental nonrail bases are
explicitly scoped August employer workpapers.

## Access, qualifications and operating chains

One declared company IAM principal maps to each employee. Entitlement resolution
is delegated to the accepted information-nature policy and existing portal owner;
this source creates no rank/unit-based restrictions, authorization engine or
deployed account assertion. September change event SH-HR-2026-09-01 exits ESS-0054 on
September 4, with late revocation on September 7 preserved and an independent
review due September 16. August HR snapshots are not rewritten by that event.
`visible_rows(as_of=..., known_on=...)` filters effective intervals and availability dates
separate; none of these newly authored records is visible in an August known-on
query. September records are not returned as August events. `workforce_state` applies
visible exit/revocation events: August 31 has 702 employed/702 principals;
September 5 has 701 employed/702 principals (the late revocation exception);
September 15 has 701/701. A known-on date before September 15 reveals none of
these newly authored records.

Three industrial driver assignments demonstrate qualified release, an expired
qualification blocking dispatch, and replacement by another qualified driver.
Internal induction is never treated as a professional operating qualification.
The controls lane owns mine examiner designations for RW-0112/RW-0113 and links
the same HR identities without creating extra employees.

Ten selected chains contain 52 linked stages over warehouse receipt/release,
ordinary freight dispatch, maintenance, production/assay custody and environmental
review. Quantities conserve opening + receipts/production − release = closing.
Each chain declares its two-case selection population; it is **not the entire
monthly operational transaction population**. The source-attribution references
create no extra invoice, stock, revenue, expense or journal. Maintenance failure,
quarantine, an unqualified dispatch request and environmental follow-up remain.

The uranium example intentionally holds both assay-passed and rejected material:
existing RW-CUST-002/003 still require packaging/carrier qualification evidence.
The separately dated September successor supplies supported newly authored
external carrier qualification and converter custody receipt; it changes neither
this August hold nor ordinary ARU freight authority. These selected chains still need
full source-month quantity/accounting allocation and independent review before
being treated as complete seven-line operating evidence.

## Validation receipt and bounded residuals

The focused suites include independent payroll-rate examples, wage-base edges,
omitted/duplicate people, wrong legal entity/period, per-component tax/remittance
and GL tampering, benefit settlement, stale derivatives, source availability,
effective-dated exits, independent approval, qualification-before-dispatch,
maintenance-held asset use, custody quantity changes, and independent current-book
cost/revenue reperformance. Review identified chronology, review independence,
tax-component validation and September effective-state defects in the first
implementation; this successor corrects them and retains regression cases.

The declared employee/payroll and material commercial/project populations are
implemented. Full company acceptance remains integration-owned. Material residuals
are invoice-specific industrial cash allocation, unresolved current sales-tax
applicability, full physical transaction-month attribution for selected operating
chains, whole-population uranium custody beyond the selected September successor, and exercised
runtime access/restore behavior. Asset/facility inventories and corporate treasury
are joined from the existing sources by the composite edition, rather than
recreated as a competing database here.

The industrial baseline package rebuilt 199 artifacts and 79 tables with identical
repeat-built archive bytes. The earlier operations suite passed 208 cases. An
initial system-Python run lacked `xlsxwriter`; supported locked-environment runs
resolve this environment error. The integration receipt must record the final
composed-head broad checks, independent review, accepted commit/PR and actual
Release location. Local generated files remain reviewable inputs until packaging.

BST CT-1/RRTA and RUIA are separate from ordinary Form 941 and FUTA. The calculation
assumes the accepted separate railway employer/employee population; changing those
coverage facts requires a new classification bridge. No tax return, agency
acknowledgement or real payment is represented as completed by this source.

## September selected custody successor

`python -m enterprise.operations.september_custody` and its `--check` mode build
`enterprise/generated/september-custody-2026/records.json`. The September input
links [shipment qualification](../../ccf/company_closeout/september_shipment_qualification.json)
and invokes its primary-authority-backed numeric/training validator. The passed
August lot's 200 lb U3O8 equivalent advances to a qualified external motor carrier
on September 13 and a fictional external converter's custodial receiving bay on
September 14. The failed 200 lb lot remains quarantined. Title stays RWH; no new
sale, revenue or inventory valuation change is posted, and no ARU/BST uranium
carriage is implied. Available-on remains September 15, so the successor cannot
appear in an August or earlier known-on query.

A newly authored $1,800 selected specialist freight/handling invoice and September
14 payment are a component of the retained September $50,000 RWH external freight,
assay and handling envelope (account 5100, source RW-FINANCE-SELECTED, journal
RWH_PS-2026-00163). The $48,200 remainder is unallocated monthly source timing,
not a claim that all September services or payments were complete at September 14.
`verify_source_expense` independently matches the retained journal; no second
expense or cash posting is made. Original OPEN source bytes remain unchanged.
