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

The 30% loaded employer burden is a modeling envelope. Known employer FICA or
RRTA is separately calculated inside it; remaining benefits and employer
obligations stay explicit payables awaiting detailed UI/RUIA, benefits and
settlement source schedules. This is not a claim that the balance is all tax,
that every employer duty is remitted, or that the company can afford payments.
Unpaid amounts must not be treated as recurring operational cash generation.

**Do not add the reconstructed payroll expense to existing payroll.** The
`payroll_source_bridges` table independently recomputes August ARU source-loaded
payroll and exposes individual-cent versus whole-dollar segment differences:
ARU −$0.08, BST −$0.19, terminals +$0.18, trucking +$0.33, warehouse −$0.13.
For SHI, PS and RWH the integration owner must decompose existing embedded
operating costs and consume an explicit replacement bridge before claiming
enterprise financial reconciliation. These amounts are source inputs, not
already posted controlling enterprise balances. Cash-timing and tax payment
bridges need the same composition; there is no automatic cash/funding plug.

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
require recalculation. Individual tax returns and employer-specific unemployment
rates are not established by these calculations.

## Access, qualifications and operating chains

One declared company IAM principal maps to each employee. Entitlement resolution
is delegated to the accepted information-nature policy and existing portal owner;
this source creates no rank/unit-based restrictions, authorization engine or
deployed account assertion. September change event SH-HR-2026-09-01 exits ESS-0054 on
September 4, with late revocation on September 7 preserved and an independent
review due September 16. August HR snapshots are not rewritten by that event.
`visible_rows(as_of=..., known_on=...)` keeps effective and availability dates
separate; none of these newly authored records is visible in an August known-on
query. September records are not returned as August events.

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
No external carrier, legal permission or converter acceptance is invented to
complete a diagram. Completed source-to-converter transport remains a C07
residual, distinct from ordinary ARU freight. These selected chains still need
full source-month quantity/accounting allocation and independent review before
being treated as complete seven-line operating evidence.

## Validation receipt and remaining work

The focused suite contains 21 cases: population/deduplication, independently
reperformed federal/CA/WV/PA and railroad tax examples, annual wage-base edges,
omitted/duplicate members, wrong legal book/period, settlement discrepancy,
missing independent review, source availability, stale exports, leave capacity,
unqualified assignment, custody quantity changes and duplicate financial posting.

Lane B delivers implementation and authored company inputs for review. SH-C01
still requires full material client/project/contract/asset/current financial
populations for all seven units and corporate. SH-C03 requires enterprise payroll
replacement composition, remaining employer obligation detail and exercised
runtime access evidence. SH-C07 requires full monthly attribution and the precise
external uranium custody evidence. Integration records the accepted commit/PR,
required broad test results, composite manifest and actual Release location.
The company-readiness gate remains partial until those claims are supported.

### Local execution evidence, September 15

The industrial package rebuilt successfully from baseline 78d4fcd: 199 artifacts,
79 tables, repeat-built archive bytes identical. The operations test suite passed
208 cases in the project's locked dependency environment; the focused 21 cases,
Ruff formatting/lint, regenerated-output check and `git diff --check` also passed.
An initial broader invocation with system Python stopped at collection because
that interpreter lacked `xlsxwriter`; rerunning with the supported project
virtual environment resolved the environment error. It was not a product failure.
Broad maintainer/publication checks remain integration-owned for the composed head.

BST tax treatment assumes the accepted separate railway employer and its railway
employee population. CT-1/RRTA filing and RUIA are separate from ordinary Form941
and FUTA. This workpaper calculates declared compensation tiers; it does not
claim completed employer classification proceedings or filed returns. Changing
railroad coverage facts requires a new classification and calculation bridge.
