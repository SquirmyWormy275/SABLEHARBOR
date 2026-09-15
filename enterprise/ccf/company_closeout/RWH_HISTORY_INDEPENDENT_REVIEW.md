# Independent review: initial Red Wash historical tax source

Reviewed September 15, 2026 UTC. Target finance commit `9655ba08`, read-only.
This review is a correction request, not acceptance of the initial tax result.

## Reperformance

The two `tests/closeout/test_rwh_history.py` tests passed with the supported controls
worktree interpreter. The first attempt used a nonexistent finance-worktree
`.venv/bin/python` and did not run tests; the explicit interpreter rerun passed.
The source cash bridge reaches $2M, with $44.3125M contributed cash, $28M purchase,
$8M rehabilitation and $3M repairs. The 300,000 lb produced less 175,000 sold
leaves 125,000 lb. No new goodwill or cash plug was found.

Initial operating tax cost $26M = $28M consideration + $2.5M fixed assumed
liabilities − $4.5M current assets. Its pro-rata allocation over the authored
$42M ClassV population is arithmetically coherent, excluding the $16M ARO.
Federal plant bonus $13,619,047.6190 splits between $7,944,444.4444 cost of sales
and $5,674,603.1746 closing inventory. Cost depletion $240,147.7833 attaches only
to sold production. California loss is explicitly before apportionment; neither
that number nor a generated loss establishes a filed member NOL or realizable DTA.

## Substantive corrections required

1. The source describes $3M repairs to operating production plant but deducts
   the full amount outside inventory. Routine-repair treatment under section162
   does not remove the section263A inventory allocation requirement. Under the
   selected weighted-average 125,000/300,000 ending fraction, $1.25M of that cost
   remains in tax inventory. This alone reduces the initial claimed federal loss
   by $1.25M. Review other indirect-cost populations before adopting a final loss.
2. Site labor, mineral/property taxes, insurance, administration and mobilization
   require activity-based allocation facts. Calling a row nonproduction does not
   establish that it lacks a production benefit. Sales-based royalties and outbound
   delivery require their separate cost-of-sales/selling treatment.
3. All $22M book plant is treated as bonus-eligible purchased equipment. Author
   the supported recovery-class/component facts, distinguishing equipment from
   long-lived structural buildings. A generic plant label is insufficient to
   establish the entire tax basis qualifies for100%bonus.

[IRS Publication5653, February2025, printed pages75–76](https://www.irs.gov/pub/irs-pdf/p5653.pdf)
identifies production-related indirect costs including repair, insurance and tax
costs, and distinguishes depletion allocated to produced-and-sold units.
[IRS 2014-22 bulletin](https://www.irs.gov/irb/2014-22_IRB) addresses sales-based
royalties and depletion allocation rules. Primary sources accessed September15UTC.

The initial $11,872,092.2277 federal loss and $1,549,568.9655 prepared book
opening correction must not be described as independently accepted by these
passing arithmetic tests. Finance must reconcile the revised cost population,
forward inventory release and book-versus-tax treatment before posting. This
review does not direct a second cash charge or removal of the separately preserved
ARU acquisition balances.

## Revised source retest: aaf13c31 and b91be16c

The three revised history tests passed. Reperformance gives book DD&A
$1,477,832.5123, opening inventory increase $737,430.2135 and opening equity
decrease $740,402.2988. The earlier prepared $1,549,568.9655 correction is
superseded by this method revision, pending forward composition. The retained
$3M abnormal repair/stabilization period expense and $687,500 abnormal
mobilization expense are separate from $1.942M normal book production overhead.
The fictional seven-day outage leaves160 production days; the selected throughput
remains below600tpd. The equipment/building split now excludes the $4M structure
from100%bonus and uses39-year/midmonth depreciation.

Revised federal loss is $8,098,998.0919 and California pre-apportionment loss
$1,896,395.3522. These are intermediate, before the shutdown allowance disposition
below and any forward-provider reconciliation. No additional cash or goodwill
was introduced. Neither passing tests nor a loss establishes deferred realization.

### Shutdown-specific tax refinement

[2025 annual CFR section1.263A-1(e)(3)(iii)(E)](https://www.govinfo.gov/content/pkg/CFR-2025-title26-vol4/xml/CFR-2025-title26-vol4-sec1-263A-1.xml)
excludes temporarily idle depreciation/amortization/cost-recovery allowances from
required capitalization. It does not broadly exempt repair or security spending.
A finite removal from service differs from ordinary breaks or normal interruptions.
Thus the production-benefit repair allocation is supported, but the newly authored
seven-day abnormal shutdown also needs an explicit depreciation allocation/method
disposition. Do not assume an arbitrary7/167 share of one-time bonus without
explaining attribution. Finance was notified to resolve this before final posting.

[FASB Statement151](https://storage.fasb.org/fas151.pdf) supports the model's
abnormal-period-cost and normal-capacity distinction. It is a superseded primary
pronouncement, not current Codification text or a full current USGAAP opinion.
The selected source expressly preserves that professional-conclusion limit.

Primary downloads accessed September15UTC; SHA256:

- `sh-263a.xml`: `2c671ed352e47520454f393f22c992e6a4342a3230c1b4cd47562359501ca26e`
- `sh-fas151.pdf`: `14a65c68921730175fcc5a5879a74d03223829b29418ad840672f3a85b8c425e`

## Posted successor and duplicate-input retest

Read-only review of `3a4ccfc0`, followed by focused retest at finance `3a0871d5c4821411d384f0debb6da0d3e4574157`: five RWH history/book tests pass. No cash or repair-asset duplication found in this scoped review. Current general-service production support allocation is a subsequent workstream, outside these amounts.

The revised 160 active days support 300,000 lb at approximately599.425 tons/day, below the retained600-ton capacity. Federal H2 depreciation11,171,957.6720 is allocated to idle period468,285.6509, ending inventory4,459,863.3421 and sold production6,243,808.6789 (four-decimal rounding). Federal loss8,294,117.1131 and ending tax inventory12,430,488.3421 are calculated attributes, not cash benefits or demonstrated realization. CA depreciation538,924.4039 has separate timing/basis; its preapportionment loss1,905,807.7045 is not a final state return result.

Book normal production indirect1,942,000 enters inventory; accepted abnormal repair3,000,000 and mobilization687,500 remain period expenses. Tax263A treatment is separately supported. The book opening inventory correction737,430.2135 and accumulated depreciation1,477,832.5123 reduce opening equity740,402.2988 without changing cash. August cash-cost inventory8,385,238.1530 plus DDA inventory867,149.3725 totals9,252,387.5255 before the subsequent mixed-service review.

An independent duplicated-positive1200-leg mutation originally inflated inventory by2,329,167. Finance corrected the helper to reject duplicate native `(entity, year, journal_id, account)` keys and require2026. The corrected guard is present and its regression test passes. Source/quantity balances alone had not detected this corruption; the prior failure remains recorded here.
