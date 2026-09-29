# State-tax computational handoff

Prepared September 15, 2026 UTC; PENDING_REPOSITORY_ACCEPTANCE. Primary sources
accessed September 15 UTC. Supplements STATE_UNITARY_ANALYSIS.md; finance owns
asset registers, monetary provisions and return schedules. No new election is made.

## Illinois transport conversion

Use Subgroup Schedule instructions **R-03/26**, pages 2–3, implementing
86 Ill. Adm. Code 100.3600. For each transport member i define E_i as eligible
external business receipts, N_i as its section304(d) Illinois numerator and D_i
as its transport denominator. Eliminate group intercompany receipts throughout.

```
S = sum(transport subgroup E_i)
D = sum(transport subgroup D_i)
converted_IL_i = round6(N_i / D) * S
member_group_factor = round6(converted_IL_i / sum(all group E_i))
```

E includes qualifying nontransport business receipts; D includes transport
receipts. Apply whole-dollar return rounding separately from precise workpapers.
A zero denominator requires an explicit disposition, not division or a fabricated
factor. Finnigan reallocates nontaxable members' converted Illinois receipts to
taxable members through the Schedule UB allocation worksheet.

Illustration, not SH data: two members E=(300,700), N=(5,8), D=(25,175).
Converted Illinois receipts are (25,40), since subgroup D=200 and S=1000.
With another sales member E=1000 and Illinois receipts=100, group factor is
(25+40+100)/2000 = 0.082500. Multiplying each member's own N/D by its own E
would produce a different, incorrect conversion.

[Illinois Subgroup Schedule instructions](https://tax.illinois.gov/content/dam/soi/en/web/tax/forms/incometax/documents/currentyear/business/miscellaneous/schedule-ub-subgroup-instr.pdf).

## Illinois asset-vintage bridge

For qualified assets acquired and placed in service after January19,2025 with
100% federal section168(k) bonus, add back that federal bonus on IL4562 and deduct
hypothetical regular federal depreciation as if the taxpayer elected out under
168(k)(7). Track each asset's Illinois basis and prior additions/subtractions.
Final-year/disposal adjustments reverse the relevant cumulative differences;
do not subtract original basis a second time. Earlier bonus vintages have their
own formulas and cannot inherit this treatment automatically. Qualified production
property under section168(n) is likewise decoupled for tax years beginning2026,
with hypothetical depreciation absent that deduction. No selected property is
classified under168(n) merely because it is industrial.

[IL4562 instructions, lines1/3/16/18](https://tax.illinois.gov/forms/incometax/currentyear/iit-bit-shared-forms/il-4562-instr.html),
[2026 changes, Public Act104-0453](https://tax.illinois.gov/research/publications/bulletins/fy-2026-15.html).

## West Virginia 2026 conformity

Enrolled SB393 adopts federal changes made during2025, retroactively where federal
law allows, and excludes changes enacted on/after January1,2026. It passed
February23,2026, effective from passage; Governor approval was March2. Thus the
2025 OBBBA section168(k) and174A changes enter the selected2026 corporate starting
base. Section11-24-6 does not impose a general bonus or174A addback. Apply its
specific income-tax and federal-NOL modifications, then the state combined/member
NOL rules; do not treat federal consolidated taxable income as a state return.
No pollution-control acceleration election is authored by this conclusion.

[Enrolled SB393](https://www.wvlegislature.gov/bill_status/bills_text.cfm?billdoc=sb393+enr.htm&i=393&sesstype=RS&yr=2026),
[official approval history](https://www.wvlegislature.gov/Bill_Status/bills_history.cfm?INPUT=393&sessiontype=RS&year=2026),
[West Virginia section11-24-6](https://code.wvlegislature.gov/11-24-6/).

## Input and validation boundary

Receipt markets come from `enterprise/closeout/source/receipt_markets.json`
(integration b62f6ff1), not this memorandum or staff locations. Tax asset basis,
recovery, entity membership dates and source receipts remain separately traceable.
Finance should test unequal subgroup E/D ratios, eliminated intercompany receipts,
member-specific NOLs, vintage/disposal basis and federal/state deferred reversals.
This authority handoff is not evidence that those numerical checks already passed.
