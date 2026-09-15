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
