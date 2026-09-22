# Capital rights and ARU debt: source completion and decision-ready terms

**Record:** SH-FIN-RESIDUAL-2026-09-22. **Prepared:** September 22, 2026 UTC.
**State:** OPEN material proposals; source arithmetic complete for review.
**Baseline:** `812676c2ac739d6fba91f770ee1369eea9f2b46d`.
This is a dated successor workpaper for SH-RES-CAP-RIGHTS and DEBT-R01/R02.
It does not amend the accepted company edition or describe proposals as executed.
No accounting entry, payment, preference, guarantee or security interest is created.

## Completed source work

[WORKPAPER.json](WORKPAPER.json) records exact source hashes, two newly authored
administrative identifiers for existing payoff components, and reproducible arithmetic.
Run `python docs/internal/company-closeout/residual-finance-2026-09-22/reperform.py`.
The output should equal the retained JSON. This uses accepted sources, not generated
statements or a missing-bank-record inference.

| Finding | Source and consequence |
|---|---|
| The $13.5M old-debt payoff already has a recoverable principal split | `industrial/source/finance.json`: $12.5M opening-2025 term less $1M 2025 principal = **$11.5M term**, plus **$2M revolver**. The $2.5M retained lease pool is excluded. Missing instrument identities are not missing principal amounts. |
| A maturity date already exists in the accepted forecast | `industrial/planning/source/forecast.json`, debt: **January 7, 2031**. Its express basis is an interpretation of the 60-month issuance-cost amortization period, and refinancing is conditional. This establishes the scenario's date, not independently recovered contractual maturity. |
| The January 2031 scheduled balloon is $15.375M | Nineteen $375,000 installments before maturity reduce $22.5M by $7.125M. The generator queues the entire opening balance at maturity; do not deduct a twentieth installment and then omit it from total cash due. |
| Current directors and exact holdings are settled | Harrison Vale 18.5M units, Wolf Ridge 15M, total 100M. Evan Mercer and Marianne Voss retain their accepted seats. Voluntary paid-in cash issues no units; nonparticipation does not itself change eligibility or remove a director. |
| Rights gaps are expressly bounded | September 15 directions exclude designation thresholds and do not adopt unlisted side letters. The 2021 board record makes the Harrison Vale seat conditional on an unspecified negotiated ownership threshold. Drafts expressly leave threshold, replacement, maturity, prepayment, numerical covenants and collateral unresolved. |

The payoff components are **principal-only source allocations** of the accepted $13.5M.
They do not invent pre-close lender interest, releases, payoff premiums or creditor receipts.
Any independently established additional amount must reconcile separately.

### History searched

- `9e11161c`: board/capital foundation and stored governance/chat authority;
  `22bb70d6`: current founder-name governance successor.
- `c792dfcd` / underlying `131af567`: industrial finance and ARU transaction history.
- `fc354cb8` (accepted through #99): explicit 2031 maturity/refinancing model.
- `17664143`: original seventeen draft legal instruments, including their unresolved fields.
- `a840c64f`: exact owner-approved five-holder direction, subsequently accepted;
  current capital register includes the later founder and industrial-capital history.
- Current canon, 2021/2022 board minutes, governance constitution, debt/financing
  drafts, `LEGAL_DISPOSITIONS.json`, source finance and forecast, and stored chat ledgers.

`git log --all -S maturity -- industrial docs/legal/gap-instruments/source/debt-liens.md`
and the corresponding designation-threshold history identify the model assumption and
explicit draft boundary; no definitive maturity, numeric covenant, pledged-asset schedule,
replacement threshold or side-letter text was found in these represented sources.
This is a bounded repository search result, not proof that no private instrument existed.

## Ordinary completion already authorized

The following work needs no new broad owner preference:

1. Retain the two existing-facility IDs and exact $11.5M/$2M principal allocation in
   the payoff reconciliation; use ARU-CL-03 and the already authored internal settlement
   reference. Label lender confirmation and instrument-level release separately.
2. Carry the existing forecast date and finite refinancing schedule into inspection
   records with its conditional state. Do not leave the scenario date described as absent.
3. Prepare Secretary-owned designation notices and a side-letter **source inventory**:
   no side-letter document located in the searched population; no unlisted right
   adopted. That limited result is complete. It is not an all-history absence warranty.
4. Reuse the existing borrower, creditor administrative identity, accountable officers,
   capital allocations and board structure. No new legal entity or lender is needed.
5. Draft instrument text and due-date/control registers after the material choices
   below, then author explicitly synthetic execution/receipt evidence within the approved
   scope. Do not manufacture a lender signature while its rights remain undecided.

## CAP-DEC-01: precise proposed designation schedule

Both options preserve nine directors, four independents, CEO/Chair separation, one
Harrison Vale seat and one Wolf Ridge seat while eligible. No observer, operating veto,
preference, cash-funding obligation or privileged commercial access is added.

| Proposal | Harrison Vale threshold | Wolf Ridge threshold | Consequence |
|---|---:|---:|---|
| A — at least half of original registered units | 9,250,000 units | 7,500,000 units | Threshold is fixed in units, adjusted only for splits/consolidations. Future dilution alone does not remove the seat. |
| B — at least 10% of current outstanding ordinary units | 10,000,000 at current capitalization | 10,000,000 at current capitalization | Both qualify now; later issuance can remove eligibility even if no units are sold. |

**Recommended draft A**, because the existing ownership-preserving contribution mechanism
should not silently turn cash nonparticipation into loss of board voice. This is a proposal,
not a recovered historical threshold. If approved, the investor may replace its own nominee
by written notice while eligible; the nominee remains subject to applicable qualification,
conflict and fiduciary requirements. No holder may replace an independent director through
this designation right. Falling below the threshold ends the designation right and creates
a vacancy to be filled through the governing nomination/appointment process; it does not
reduce board size or transfer the seat automatically to a founder. These cessation and
replacement consequences are substantive parts of the proposed approval.

An eligibility schedule can be effective prospectively on the later accepted synthetic
adoption date. It must not falsely assert this was the unlocated 2021/2022 negotiated text.
Historical appointments remain supported independently. Full historical enforceability
therefore remains a narrower claim than a complete current rights schedule.

**Side letters:** for a complete current fictional rights perimeter, a prospective integration
record can state that the listed governing instruments are the entire current agreement,
with each of the five holders' explicit synthetic assent. That changes rights if an unknown
prior promise existed; it requires approval with CAP-DEC-01. It is preferable to inventing
negative historical correspondence or declaring every possible side letter nonexistent.

The current Delaware statute permits agreement-defined management/designation arrangements;
it does not select either threshold. Primary current authority checked September 22, 2026:
[6 Del. C. §§18-401–404](https://delcode.delaware.gov/title6/c018/sc04/index.html) and
[§18-1101(b)](https://delcode.delaware.gov/title6/c018/sc11/index.html).
This supports prospective fictional drafting only; it is not a historical enforceability
opinion or authority to eliminate duties.

## DEBT-DEC-01: definitive terms that match the existing modeled economics

**Recommended review bundle:** January 7, 2031 maturity, $375,000 quarterly principal
from April 7, 2026, 6.75% ACT/365, and a balloon equal to then-unpaid principal.
No increased borrowing, guarantee or mandatory holder contribution. Adopt the existing
45-day quarterly reporting / five-business-day material-dispute notices as proposed
administrative lender terms only if the same bundle is approved.

The genuinely new economic selections are:

- Voluntary principal prepayment at par plus accrued ordinary interest, **no premium**,
  no reborrowing; apply against balloon first. Alternative 1% premium would cost
  **$217,500** on a full August $21.75M term payoff. No prepayment is modeled now.
- No additional default-rate uplift and no automatic interest capitalization. Alternative
  +2 percentage points would add **$435,000/year** on that same balance, before timing.
  Either selection affects creditor remedies; silence is not zero-cost permission.
- **No financial-maintenance covenant** beyond payment/reporting terms, rather than
  inventing an EBITDA definition or numerical ceiling. This needs express adoption;
  current reporting cannot call nonexistent tests “passed.” If a financial covenant is
  wanted, define its legal-entity perimeter, numerator/denominator, testing dates,
  threshold and cure mechanism before claiming compliance. The cultural 5/9 and 6/9
  governance targets are not lender voting rights or covenant definitions.

The recommended maturity preserves current forecast timing. A fully amortizing alternative
at $375,000 quarterly would run to **January 7, 2041** and remove the modeled 2031 balloon;
that is a material ten-year extension, not ordinary date completion. It would require new
interest, tax, debt-service and sovereignty runs. No such change is made here.

| Existing January 2031 conditional refinancing | Capacity | Draw against scheduled $15.375M | Principal requiring other cash | Fee requiring cash |
|---|---:|---:|---:|---:|
| Base | $18M | $15.375M | $0 | $153,750 |
| Downside | $12M | $12M | $3.375M | $180,000 |
| Expansion | $20M | $15.375M | $0 | $153,750 |

These are **schedule sensitivities**, not binding commitments or a prediction of default.
The downside principal-plus-fee need is $3.555M before lease, tax and other needs.
Actual forecast cash allocation may fund it; capacity shortfall is not automatically unpaid
debt. Unused capacity is not cash. No new lender relationship is adopted by this table.

## DEBT-DEC-02: security and old releases

No accepted source identifies an asset-specific security grant. The $13.5M payoff and
$34M acquired book PPE cannot establish collateral, title, perfection or a release population.
The modeled 45%/55% ARU/BST asset allocation is not evidence that every asset is pledgeable.

Two finite current-contract alternatives are ready for selection:

- **A — explicitly unsecured ARU-only term facility**, no parent or subsidiary guarantee,
  no lien or negative pledge. This adds no foreclosure right; it makes unsecured status
  an express newly authored term rather than an inference from missing evidence.
- **B — specifically secured ARU-only facility**, excluding BST, RWH, PS and parent assets,
  retained leased equipment and customer property. Requires an actual owned-asset schedule,
  title/consent and priority review before execution; neither a group-wide lien nor a
  value equal to the term principal can be invented to complete the schedule.

A is the least additional-rights proposal, not an assertion that a real lender would accept
these economics unsecured. B introduces material creditor rights and cannot be implemented
from ordinary identifiers alone. Neither option authorizes lending beyond $22.5M.

**Old releases remain a distinct historical fact question.** Ordinary drafting may provide
internal settlement allocation and a request checklist. It cannot turn principal payment
into a blanket lien release. A finite newly authored historical completion would need an
expressly selected old-security premise (unsecured, or a specified historical collateral
population), creditor release scope and synthetic delivery record. Ask for that premise as
part of DEBT-DEC-02 if the intended claim is complete historical lien discharge. Otherwise
retain only the precise historical release residual while resolving current debt terms.
Retained leases and their owner title are excluded in either case.

## Acceptance transaction

Root may incorporate the completed source reconciliation independently of the choices.
Material terms remain OPEN until the owner selects a concrete bundle and it is preserved
in a dated decision. Implementation then creates a separately versioned current instrument,
its synthetic approvals, obligations and source-to-book bridges. Existing financial releases,
unsigned design packets and their hashes remain discoverable and unchanged. A prospective
rights schedule must not be mislabeled a recovered historical agreement.
