# Company obligation review and runtime input boundary

Document ID: SH-C05-C06-REVIEW-2026-09-15. Prepared September 15, 2026 UTC.
Acceptance: pending repository acceptance. Implementation of the closeout assignment;
this record does not claim completed C05/C06 or accepted operating effectiveness.

## Reperform the declared population

```sh
python -m enterprise.ccf.company_closeout.validate
python -m unittest enterprise.ccf.company_closeout.test_validate -v
python -m unittest enterprise.runtime.tests.test_security -v
```

`obligation_census.json` preserves all 14 Red Wash permit entries and 14 historical
rail safety events, exact source rows, source hashes, responsible roles, activity,
condition, individual screening route and missing next facts. These are two complete
source populations, not a company-wide obligation population. The register is a
new September 15 review of source facts through August 31; its availability must
never be backdated into August. It changes no permit, historical incident, financial
balance, corrective-action status or filing state.

The validator rejects omitted/duplicate members, changed facts, stale source or
evidence hashes, premature availability and unsupported performance promotion.
MISSING_EVIDENCE does not mean FAILED, NOT_RUN, NO_OCCURRENCE or NOT_APPLICABLE.
Future-due cannot be inferred where the underlying due date is still unknown.

## Primary authority work and precise limitations

Ten annual primary editions of 49 CFR 225.19 (2014, 2016, 2018–2025) were retrieved
from GovInfo and their reporting-group text read on September 15. The register
records exact URLs and SHA-256 hashes. October annual editions are not automatically
the rule effective on an earlier event date; intrayear amendment/Guide/threshold
checks remain open. The original browser fetch for the 2018 PDF failed; direct
HTTPS retrieval succeeded and is hash-recorded. No external account was contacted.

The [2023 primary text](https://www.govinfo.gov/content/pkg/CFR-2023-title49-vol4/pdf/CFR-2023-title49-vol4-sec225-19.pdf)
distinguishes crossing, equipment and injury groups. The two crossing events need
crossing-definition review without a damage-threshold gate for Group I. The four
derailment events need qualifying repair cost, which cannot be substituted with
the source's combined claim/damage amount. Injury records need causation and
case-specific criteria. Environmental releases need separate spill screening.
Rules/timestamp events retain their corrective actions; absence of a recorded
trigger is not a final legal no-report opinion. Filing evidence remains missing
for every event, independent of whether corrective action was recorded.

[NRC's Wyoming record](https://www.nrc.gov/agreement-states/wyoming) confirms the
September 30, 2018 transfer for the identified milling/byproduct scope. It does not
validate fictional license WYSML-094 or its specific conditions. At the initial review, all 14 permits
needed instrument-specific obligations, due populations and evidence joins. The
August synthetic-instrument successor below now supplies its explicitly bounded scope.
The MW-17/Cell 1 investigation remains unresolved; a trend is not a final liability
finding. No framework has been made universally applicable.

## C06 company-to-existing-runtime input contract

The active `SABLEHARBOR-audit-suite` worktree on `build/audit-training-suite` was read
only. Its `tools/audit_suite/COMPANY_ACTIVITY_LINKED_PLAN.md` describes native
`PRIVATE_COMPANY_ACTIVITY_LINKED_PLAN_V2` inputs and exact-source selection. It is
concurrent work, not accepted main or a new company database. This census is an
upstream review register, **not** a fabricated `PRIVATE_COMPANY_ACTIVITY_RUN_V1`
operator output. Never manufacture wrapper manifests to import it as activity.
The runtime owner must resolve source records into supported native producers and
preserve selected metadata digests, operator/member hashes and source references.
The integration owner's separately exercised capsule adapter may instead import
these public repository documents using the existing `company_store.append_version`
interface and origin `REPOSITORY_SYNTHETIC_DOCUMENT`. Register the system and owner
through `register_system`; supply exact expected version, command ID, event and
available timestamps, content bytes and provenance. Actual `imported_at` is assigned
by the store and cannot be supplied as a historical timestamp. Registration/import
creates no access grant or prior operating history. Do not label this review as
`AUTHORED_TRAINING_SOURCE` performance or use `MIGRATED_SYNTHETIC_HISTORY` to suggest
recovered execution. Fresh-store capsules and linked native activity plans are
different interfaces; preserve each one's declared scope.

For each company-side handoff retain:

- Stable record/source ID, legal entity, unit, effective period and timezone.
- Event and available dates separately from authorship/import/acceptance dates.
- Scenario, fact origin, complete declared population and explicit exclusions.
- Source version/commit/hash, evidence relationships and native access scope.
- Exact selected versions; no newest-version fallback or forecast promotion.
- Preparer and independent reviewer identities, outcome, exceptions and retest state.

Authority and information policy remain in accepted Alexandria doctrine and
`enterprise/runtime/security.py`; this input contract grants no entitlement.
Runtime collection must filter direct and indirect disclosure before retrieval,
including snippets, counts, graph, tool responses and export. Private memory stays
separate; holds preserve protected bytes without restoring ordinary disclosure.
Synthetic source review cannot satisfy ACTUAL_COLLECTED_EVIDENCE.

C09 rejects malformed shared tenant identity and absent/malformed mandatory policy
metadata before any allow path. Its tests cover every disclosure surface, bounded
existence, legitimate OPEN access, mismatched tenants, missing/empty/non-string
identities, malformed purposes and retained revocation/deletion behavior. This is
a reference implementation fix; adoption by the active portal and deployed behavior
need their own integration evidence. Existing readiness gates remain unchanged.

## Residual owners and acceptance boundaries

| Work | Delivered evidence | Exact remaining work / owner |
|---|---|---|
| C05 | 28 source-bound individual dispositions; ten retrieved primary editions | Company compliance lane: instrument terms, complete enterprise activity census, event-date rules, supported performance/filing chains and qualified review |
| C06 | Existing-runtime input boundary and reference disclosure tests | Runtime owner: native company import, actual isolated software backup/restore, independent review, indirect-disclosure integration and external gate evidence |
| C09 | Source regression fix and positive/negative tests | Integration owner: required repository checks, accepted PR and portal integration receipt |

Preserve the CCF denominators: native preparation 166 controls / 1,660 boundaries;
operations 70 baseline or 86 extended / 24 computed assertions; business exercise
7,560 expected occurrences across 42 combinations. This 28-row review is not a
replacement denominator or evidence that the 15 native risk mapping gaps closed.
No IT or regulator acceptance gate is asserted by this source review.


## Supported fictional performance successor

The original census above remains an unchanged record of the initial evidence gap.
`permit_condition_performance.json` now adds 14 explicit **internal** condition
schedules, newly authored September 15. These schedules do not impersonate a
regulator-issued amendment or replace statutory frequencies. Their first monthly
review is due September 30; existing program duties still require the precise
instrument-specific population. Six condition rows have a performed review with
an exception; the other eight retain missing evidence. Do not combine these
internal schedules with the historical 28-row census as one occurrence denominator.

The completed September 15 environmental review reproduces all 180 station/quarter
rows from the existing Red Wash generator (six stations, 2019-Q1 through 2026-Q2).
No 2026-Q3 result is invented at the August cutoff. MW-17's four 2019 readings sum
to 0.0494 mg/L, mean 0.01235; the latest 0.0232 yields +0.01085 mg/L. This exceeds
the newly authored internal investigation trigger of +0.005 mg/L. It is not a
statutory concentration limit or proof of a discharge. A joint groundwater/Cell 1
investigation remains open, due September 30, with prospective October 15 retest.
The existing adverse trend remains visible. The method and primary 2025 BLM
monitoring-plan reference are versioned in the performance source.

`workplace_examinations.json` authors four August 31 examinations in exactly two
places and two shifts. It joins existing workforce IDs RW-0112 (Maya Ortiz),
RW-0113 (Evan Cross) and RW-0119 (Leah Foster). Operator designation is a newly
authored scoped company qualification, not a professional license. One expired
assignment is blocked, replaced by the qualified examiner; renewal remains open.
A slippery walkway is closed, corrected and reinspected before work begins.
The remaining three selected examinations record no adverse condition. Existing
payroll covers these ordinary duties; no incremental invoice, production change
or external cash is added. The collection is authored/available September 15:
these newly created retrospective records cannot enter an August known-on view.
Synthetic preparer/reviewer separation is explicit and does not claim a real
human audit. All other mine workplaces and dates remain outside this sample.

The primary 2025 30 CFR 57.18002 text and contemporaneous July 27, 2026 MSHA notice
are retrieved with hashes in the source. Examination timing, record retention and
hazard handling constrain the records; the notice corroborates existing duties,
and is not a new rule. Public evidence contains no private evaluator answers.

```sh
uv run python red_wash/tools/validate_red_wash_record.py --generate
uv run python -m enterprise.ccf.company_closeout.environmental_review
uv run python -m enterprise.ccf.company_closeout.performance
uv run python -m unittest enterprise.ccf.company_closeout.test_performance -v
uv run python -m enterprise.ccf.company_closeout.restore_rehearsal
```

The Red Wash source build passed 514/514 checks. Performance reconciliation yields
14 condition schedules, 180 monitoring rows, four examinations and one blocked
assignment. Negative tests reject omitted/duplicate examinations, expired
designation, wrong entity, late record, premature hazard release and self-review.

The restore command performs actual filesystem backup and restoration into a
separate temporary directory using existing reference `revoke_graph`, `restore`
and `authorize`. It verifies exact backup/history hashes, replays the current
revocation log after the earlier backup, denies revoked-principal access, removes
three suppressed records from live disclosure, retains one restricted held copy,
and preserves legitimate access to the remaining record. Two history entries
survive. This is exercised local reference software, not backup/restore evidence
for the active portal or a deployed company estate; those integration gates remain.
The fixed fixture backup hash is
`4140b4fe12e2cd0ec4046b8115cada2bb772a336d879c53fbbb589cd5d8e1965`.

## Seven-unit and corporate activity applicability

`activity_applicability.json` extends the original permit/event review with 30
explicit activity/duty boundaries covering all seven businesses and corporate
functions. Each records legal entity, site, jurisdiction, activity, source hash,
owner, condition, population, status and next action. The unit list reuses existing
export slugs. It creates neither a parallel company database nor new legal entities.

| Boundary | Declared source population and principal obligation |
|---|---|
| Foundry Field | 60 conditional contracts; accepted FF-003 issuance supplement separately scoped; delivery/acceptance/billing and source entitlement |
| Atlas Meridian | 15 conditional licenses and 40 evaluation engagements; separate license rights, client/professional-plane boundary and gated acceptance |
| Advisory | 120 conditional matters; outcome acceptance, confidentiality and actual-service professional-scope screening |
| Willow | Four conditional research projects; failure/transfer gates, Fort workplace exposure and receiving-owner qualification |
| Cradle | Stream 17, Demotte and Bedford responsibilities; two distinct recovery processes; host stop/compliance authority, custody/assay/title and accepted sale |
| Pale Sun / RWH | 14 permits, linked environmental/workplace evidence; separate legal operator and source-material responsibility |
| ARU / BST | 12 industrial facilities and 14 historical safety events; custody, qualified assignments, reporting and open-claim boundaries |
| Corporate | Employer/payroll, tax/filing groups, financing, privacy, retention/hold and three separate runtime activation boundaries |

The matrix also joins each unit to the existing information-access contract.
It distinguishes six conditional future-due boundaries, three source-scoped
no-occurrence activation boundaries, performed reference work and missing/not-run
evidence. Counts describe activity boundaries and source populations, not statutory
occurrences. An inactive provider site has no activation in the declared source;
that is not a claim that the entire company has no incidents. Missing PHI or
CCPA-threshold facts mean unresolved applicability, not non-applicability.

Primary authority work is retained in `primary_authority_reviews`: IRS employer
reporting/deposit guidance, 2025 29 CFR Part 516, CPPA's January 2026 regulations and
January 2025 monetary adjustment, and HHS's covered-entity/business-associate
boundary guidance. Exact downloaded primary bytes are hash-recorded where obtained.
The HHS browser page was read, but direct retrieval was forbidden; no fabricated
hash is supplied. DOL fact-sheet retrieval failed twice; GovInfo Part 516 supplied
the primary text instead. These are factual applicability screens, not legal
opinions. Filing-year forms, amendments, worker classifications and instrument
conditions remain necessary for specific executable conclusions.

The payroll route explicitly preserves BST's railroad-tax boundary rather than
assigning ordinary FICA/FUTA to every employee. The payroll lane separately models
RRTA and retains RUIA experience-rating limits. Privacy review uses actual preceding-
year business/processing facts; a future revenue forecast cannot establish CCPA
scope. HIPAA is not imposed because an employer possesses employee information.
Professional-service regulation is screened from actual scope and remuneration,
not from the name Advisory or an internal carry plan. Site duties follow operator
and host responsibility; no blanket framework requirement is created.

```sh
uv run python -m enterprise.ccf.company_closeout.applicability
uv run python -m unittest enterprise.ccf.company_closeout.test_applicability -v
```

Source population selectors independently reconcile contracts, matters, permits,
facilities, events and selected site states. Tests reject omissions/duplicates,
wrong legal identity, stale source, changed counts, premature availability and
unsupported PASS promotion. The initial third-site check expected a colocation
contract field absent from the owned-site schema; the corrected validator tests
owned-site operation and retains contract-state checks only for provider sites.
All declared site/contract checks then passed. SH-C05 remains bounded where actual
occurrence populations, authority details or performance are explicitly missing.

## August fictional instrument and performance successor

`synthetic_permit_instruments_august.json` adds expressly authored instrument terms
and evidence, available September 15, for a finite August scope over all 14 existing
fictional permit identities. It does not represent issuance by an actual regulator,
change a mine right, expand a facility or authorize uranium transport. The initial
census's missing-condition assessment remains inspectable as the earlier review;
this successor resolves selected conditions through newly authored fictional detail.

There are **204 condition occurrences**: 196 performed, three failed then corrected,
two missing-evidence, two performed with unresolved exceptions and one blocked.
Four rows join the existing four workplace examinations; they are **not four new
exams**. Radiation accountability is 128 employees/badges, not 128 numeric dose
measurements. A missing result is not zero exposure. Inspectors/reviewers are named
synthetic role-holders; their review here checks the condition record, not a
professional certification of radiological, engineering or legal compliance.

MW-17 investigation remains open. Physical Cell 1 walkovers do not clear groundwater
trends or establish the pathway. The selected uranium shipment gate remains blocked;
this is not a claim that the annual source model had zero sales. Bond-face evidence
and radon category/phase-area evidence remain separate precise residuals. The
$25 million current closure estimate and $16 million opening accounting ARO are not
asserted bond values. Two future duties and one explicitly declared zero-occurrence
change-request population are separate from performed counts. Other historical
periods and unselected conditions remain outside this completed evidence population.

```sh
python -m enterprise.ccf.company_closeout.instruments
python -m unittest enterprise.ccf.company_closeout.test_instruments -v
```

## CCF denominator and risk reconciliation

`risk_mapping_supplement.json` supplies dated primary risk relationships for exactly
the 15 native controls whose original risk list was empty: ADV-001–004, CRD-001–004,
ETH-001–004, PRD-002, PRD-004 and SEC-006 (all with `SH-` prefix). Each maps to an
existing enterprise risk family with a control-specific rationale. It supplements
the original matrix after September 15 availability; it does not backdate its
September 2/11 records, accept external framework equivalence or approve local
applicability. The composed mapping has zero unmapped native controls while the
historical native-only count remains 15.

| Population | Refreshed scope/count | Meaning |
|---|---|---|
| Native preparation | 166 controls; 1,660 boundary rows still PENDING_LOCAL_REVIEW | Proposed applicability, not completed controls |
| Operational reference baseline | 70 controls × three boundaries = 210 plans | Existing documented SOC2/HIPAA reference selection; legal HIPAA role still factual |
| Operational reference with all extensions | 86 controls × three boundaries = 258 plans | Existing selectable ISO27001/ISO42001/C5 reference scope |
| Automated adapters | 24 | Recounted executable adapter inventory; manual duties still required |
| Business control exercise | 42 control/unit combinations × three scenarios × 60 months = 7,560 | Recounted conditional 2027–2031 expected occurrences; not August actuals |
| Company activity review | 30 activity/duty boundaries across seven units and corporate | Separate source census; neither native boundaries nor performed occurrences |
| August permit successor | 14 conditions / 204 declared occurrences | Newly authored completed-period condition evidence, with adverse states preserved |

Native, adapter and forecast denominators are recomputed by `instruments.report()`.
70/86 and 210/258 are the current operational README's documented selection counts;
this lane does not claim a fresh external normative-source rebuild of that reference
assessment. Exact source/risk and business-interface hashes accompany the report.
The 1,660 local-review decisions are not replaced wholesale by this company's 30
activity rows or 204 permit checks. Reference framework prerequisites and qualified
human review remain explicit at their original scope.

## Selected September external-carrier advancement

`september_shipment_qualification.json` records one newly authored fictional
qualification and receiving packet after the September 6 OPEN boundary. It covers
lot RW-LOT-202608-01 / drum RW-DRUM-202608-01, linked to the passed August production
chain. The failed lot stays quarantined. The August hold remains correct at that
period. Qualification is ready September 13 at 07:30 America/Denver, after the
survey; release is 08:00 and converter receipt September 14 at 14:00. All evidence
is newly authored and available September 15.

Cobalt Basin Specialist Transport and Mesa Conversion Services are expressly
fictional external counterparties. Their registration, training, engineering and
receiving-license schedules are authored synthetic records, not real government
issuance, measured radiation or completed physical transport. No ARU/BS&T uranium
carriage or new SH ownership is introduced. RWH retains title in toll-conversion
custody; receipt alone does not create revenue or cash.

The [primary LSA definition](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-I/subchapter-C/part-173/subpart-I/section-173.403)
supports classification from the specifically authored natural, unirradiated solid
concentrate facts. It does not rely on a made-up activity threshold. The record
separately preserves contained U3O8, concentrate and gross-package mass, synthetic
assay/activity, package design review, survey and wipe data, training and timed
release checks. Source provisions, displayed version and access date are recorded
per conclusion. This is a bounded synthetic inspection record, not a generic
shipping procedure or authority to transport actual material.

```sh
python -m enterprise.ccf.company_closeout.shipment
python -m unittest enterprise.ccf.company_closeout.test_shipment -v
```

The operations lane consumes `shipment.validate(data)` and the eight check records,
then joins custody quantities and the separately supported September expense
allocation. This qualification module posts no financial entries.

## Current activity and historical rail reporting successors

`current_activity_successor.json` joins the current August source, replacing the
older matrix's unresolved current populations where specified: **92 contracts,
88 customers, 104 service environments, five projects, 702 employees and 1,404
payroll events**. Eight business/corporate boundaries preserve each exact ID.
These current contracts are distinct from the older conditional contract counts.
The module rejects stale source hashes and changed or duplicated population IDs.

The SHI CCPA factual screen now uses **$104,900,000 of 2025 retained primary-book
revenue across 12 legs**, recomputed independently of the August commercial
allocator. It exceeds the adjusted $26,625,000 threshold. The newly authored
profile states the California business and personal-information processing facts;
407 California employee records tie to HR. Subsidiaries retain separate legal
applicability analysis. Two synthetic privacy requests retain a late correction
and a documented partial deletion/retention response. Neither the 790 notice
recipient records nor 88 business contacts are extra employees.

The existing benefit administrator's scope is completed as a fictional fully
insured arrangement within its existing cost envelope. Enrollment-only sponsor
data is distinguished from the covered group health plan and from ordinary
customer services, whose declared August population contains no clinical PHI.
This is not blanket HIPAA applicability or an assertion of insurer compliance.

```sh
python -m enterprise.ccf.company_closeout.current_applicability --reperform-revenue
python -m enterprise.ccf.company_closeout.rail_reporting
python -m unittest enterprise.ccf.company_closeout.test_rail_reporting -v
```

The current applicability command needs the integrated C03 `current_records`
source/generator. `--repository PATH` supports a read-only integration checkout;
it invokes supported generators in memory and checks their populations and hashes.

`rail_reporting_successor.json` adds expressly authored repair/clearing/claim,
clinical and filing facts for all 14 historical cases. **Nine events generate 11
selected incident-form records**: eight modeled on-time submissions and one late
submission; five cases have no Part 225 group trigger under the authored facts.
These are incident records, not complete monthly summary reports or proof of
actual FRA submission. Form names describe the reporting family; no government
identifier or acknowledgment is impersonated.

The 2021 late filing remains a failure. The $600,000 2024 claim remains open and
is not treated as rail repair or automatically as property damage. Public/private
crossing status does not remove the crossing reporting group. Medical causation
and reportability are separate from allocation of liability. Two contained spills
retain independent environmental/state permit screening.

The primary annual editions, 2018 threshold rule, 2020 method rule and current
225.9/225.11 source notes are recorded. Exact historical eCFR pages failed; an API
attempt returned HTTP 406. The 2021/2023 thresholds have a US DOT published table,
and 2025 $12,400 is explicitly inferred from FRA's 2026 notice ($12,600, a $200
increase). Original annual notices and full event-day amendment reconciliation
remain narrowly identified legal-review residuals. Fictional performance has been
completed without presenting those residuals as resolved professional conclusions.

### Enacted future digital-tax change

The current successor records [California SB 122, Chapter 23](https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260SB122),
approved June 29, 2026. Its software provisions become operative January 1, 2027.
Actual product classification, exclusions and user-location sourcing must be
reconciled before extending the forecast tax composition. The chaptered primary
text/status were retrieved directly after browser failures; their hashes and
exact scope are retained. This does not change August or duplicate FF-003.

The current successor also completes **58 current Core contracts' August
California billing/use facts**: 44 hosted Foundry Field services, ten Atlas
investigations and four Advisory engagements. These are explicitly new fictional
facts, not recovered customer addresses or 2027 identities. Their 104 logical
service environments do not create physical facilities. No tangible product or
storage medium is delivered. The bounded August service/electronic-delivery tax
screen records zero incremental California sales tax and preserves principal and
cash. Changed use jurisdiction, tangible delivery, amount or period forces renewed
review; this treatment does not persist past the 2027 legal change by default.
The other 34 material/industrial contracts remain separately classified rather
than receiving this service conclusion through a shared issuer or tax field.

## Current industrial transaction tax successor

[industrial_transaction_tax.json](industrial_transaction_tax.json) version1.1 completes
34 August contract/invoice screens over **$6,939,266.00** unchanged principal:
17 Wyoming freight, eight handling, four custody storage, one West Virginia refiner
resale, one Illinois trader resale, and **three taxable Illinois utility purchases**.

Independent review rejected the first draft's unsupported onward-resale premise for
three utility buyers. The accepted contract book identifies utility/cooperative,
procurement-pool and nuclear-utility buyers and transfers title at the Illinois
converter after assay. It establishes no downstream swap. The three rejected synthetic
certificates remain in `rejected_certificates`; they are not exemption evidence.
Ordinary completion now retains utility ownership through toll processing for own use.
The trader and refiner retain two separately supported synthetic resale certificates.

Newly authored jurisdiction precision places the existing external receiving point
within Metropolis, Illinois, outside a special business district. This creates no new
operator, real license, SH site or surveyed geography. Primary IDOR FY2026-26-A sets
7.25% from July1 2026 for this scope (the Interstate North Business District is8.25%
and is expressly excluded). Existing invoice principal is not restated as tax-inclusive,
and no separately billed tax or supported customer reimbursement asset exists:

| Contract | August principal | Seller tax expense/payable |
| --- | ---: | ---: |
| UCA-2019-04 | $762,499.92 | $55,281.24 |
| UCA-2024-11 | $899,999.90 | $65,249.99 |
| UCA-2025-03 | $833,333.24 | $60,416.66 |
| Total | $2,495,833.06 | **$180,947.89** |

Each invoice is multiplied by0.0725 and rounded half-up to cents before summing.
RWH owes the uncollected seller tax. The designated three adjustment IDs must reach
RWH expense/payable once through the finance owner. Cash, customer principal and
revenue do not increase. No tax payment, filing or later reimbursement is inferred.
This module measures the adjustment; it does not claim the accounting overlay is
already posted. Other2026 periods require their own populations and rate/settlement
reperformance; August must not be multiplied by12 blindly.

Wyoming uses the July2026 SF0079 revised statute. Freight/custody charges are distinct
from merchandise, repair, equipment leases and taxable well-site work. Illinois
current resale rules govern the two active certificate scopes; old uranium private
rulings surfaced by search are expressly excluded as revoked. Temporary processing
outside-state-use relief cannot automatically exempt acquisition/title transfer in
Illinois with sellerROT liability. No automatic utility-fuel exemption is asserted.

All customer-use, certificate and municipal precision details are newly authored
synthetic records, available September15; they do not recover contemporary external
evidence. Mine invoices still decompose retained annual equal-month revenue, not
physical August shipments. The separate September200lb toll-custody event retains
RWH title and adds no revenue. Mineral/property/income and company purchase-use taxes
are outside this selected transaction-tax computation.

```sh
python -m enterprise.ccf.company_closeout.industrial_tax --repository /path/to/company-checkout
python -m unittest enterprise.ccf.company_closeout.test_industrial_tax -v
```

The current generator/hash integration check validates all34 IDs, two active and three
rejected certificates, principal and measured tax. Negative tests reject changed use,
wrong tax/rate/district, missing or late evidence and wrong invoice/entity/period.
The operations owner consumes annotations; the finance owner posts and reconciles tax.
