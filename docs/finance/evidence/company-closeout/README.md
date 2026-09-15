# Company finance successor — September 15, 2026

State: pending repository acceptance. Scope: SH-C02 and the supported SH-C04
corrections; **partial**, not a completed after-tax company edition. Authority:
[three owner directions](../../../canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md).
The voice record is dated September 14 America/Los_Angeles; this preparation is
September 15 UTC. Historical/source availability dates are preserved separately.

## Reproduce and inspect

Use the repository dependency environment and a real Git checkout:

```
python -m enterprise.closeout.build
python -m pytest tests/closeout/test_finance.py -q
```

Development builds explicitly require `--allow-working-tree`. Output is the
separate `enterprise/generated/company-closeout-v1/` tree, including legal and
unit trial balances, journals, annual/monthly statements, exact predecessor
replacement bridge, acquisition/tax-allocation bridges, sovereignty CSV and hash
manifest. It reuses runtime/operations/industrial builders. It does not replace
runtime-v1 or any published finance bytes. The identity records dirty development
state, source commit and source hashes. Integration owns package publication and
must rerun on its accepted revision. This document is indexed evidence, not an
assertion that ignored build outputs were delivered.

## Goodwill: source proof and classification

The earliest identifiable commit containing the $30M is
`ebb57694fd6da334cf152bb3d9c2a824a348908b`,
`src/sable_harbor/generation.py`, `opening_layers['SHI']`. It jointly initializes
cash $34.8M, PPE $9M, goodwill $30M, debt $35M and equity $38.8M. It provides no
acquisition counterparty, price allocation or separate acquired value. Later
standard generation dates SHI opening to January 1, 2023. The current legacy
adapter selects PRIMARY_USD SHI; `legacy_core` migrates asset 1600 to LEG_1600
and equity 3000 to LEG_3000 in January 1, 2026 opening reconstruction. Prior P&L
is closed to 3100 independently. This is evidence of initialization, not proof
that goodwill historically arose in a separate balancing journal.

The supported successor corrects the model's opening calibration: debit
LEG_3000 $30M; credit LEG_1600 $30M, once per scenario in 2026 month 0.
Counterpart is initialization equity, not retained operating earnings, expense,
member cash or an asserted return of paid-in cash. Opening SHI initialization
equity becomes $8.8M before other supported opening reconstruction. The dated
correction is newly authored September 15, not evidence available in January.
Historical 2023–2025 releases remain unchanged; this successor corrects 2026
opening and carryforwards. It is not described as a GAAP-restated historical
financial statement or a goodwill impairment.

Accounting basis remains the synthetic management model, with explicitly
conditional acquisition tax judgments. FASB's published ASU 2021-03 reproduces
350-20-05-4A's prohibition on capitalizing internally generated goodwill costs
([primary text](https://asc.fasb.org/layoutComponents/getPdf?fileName=GUID-54CE7C77-8CB5-4061-B0E2-0FB16632A485.pdf&isSitesBucket=false),
accessed September 15, 2026). This supports refusing unsupported goodwill; it
does not establish a real historical ASC 250 error classification. No separate
asset, liability, tax deduction/DTA or cash requirement is inferred. No identified
covenant tied to this unsupported asset has been established; covenant headroom
is not certified by the correction.

ARU is outside the adjustment entity/account population. Its source-derived
$14,762,500 book goodwill and $13,000,000 tax goodwill remain governed by
`industrial/source/finance.json` and the acquisition allocation. The current
build reruns industrial source schedules and acquisition bridges before
composition. Independent exact comparison of ARU/BST emitted legal records is
part of integration evidence; noninterference is not inferred from a consolidated
total. Goodwill-excluded views must use remaining LEG_1600 balance, now zero;
subtracting another $30M is prohibited.

## FF-003 composition

`enterprise/closeout/source/adjustments.json` consumes the accepted issuance-only
supplement for SYN-CUSTOMER-003 on SHI, Foundry Field, January 2027 base only.
Expense +$152,250, payable +$152,250, pretax income -$152,250; principal/AR/cash
unchanged. No payment, default relief or income-tax deduction is invented.
The exact emitted-leg verifier rejects balanced reversal, duplication and wrong
entity/period/scenario. Legal and consolidated statements consume the same legs.

## Capital and sovereignty

`sovereignty.csv` selects only SHI cash account 1000 / source_type MEMBER_EQUITY;
it excludes OPEN-MEMBER-BASIS noncash investment reconstruction and subsidiary
receipts. It lists every source ID, annual/cumulative cash and changes, operating
cash, net investment and cash after both. Taxes/interest already in operating
cash are not subtracted twice. The ratio is member cash / positive operating
cash; otherwise N/A. Existing-member money is external funding. A falling
requirement is not attainment; parent tax remains unresolved and net investment
does not distinguish all sustaining/growth commitments. The report deliberately
carries that limitation on every row. Later revisions must retain the objective
and explain operational causes of increases/decreases, not impose monotonicity.

Historical approximate rounds and 66.5/33.5 split are preserved. Accepted
financing source FIN-U01/U02/U03/U05 explicitly lacks subscribers, class/price,
thresholds and economic rights. Proportional funding cannot use rounded groups
as fictitious exact holders. No compulsory call, issuance, preference, outside
subscriber, dilution or investor exit is added. Unused scenario capacity stays
outside cash. The current finance build therefore cannot prove holder-level
ownership continuity or commitments. Ordinary fictional identifiers can be
completed once the participation rights population is established; precision
alone cannot resolve absent class economics.

## Validation and remaining evidence

The lane ran the full successor build successfully in a supported existing
virtual environment with local `PYTHONPATH=src:.`; nine targeted tests passed.
The source locks ran through the isolated legacy adapter. Required integration
checks and clean accepted-revision rebuild remain the integration owner's gate.

Tax effective history, provision, state apportionment, historical holder bases,
exact participation rights, independent settlement and 13-week cash timing are
not supplied by this partial build. See [tax history workpaper](TAX_HISTORY.md).
No issue closure or completed SH-C04 claim follows from this record.

### Proportional request implementation

`enterprise/closeout/capital.py` implements total × established participation
share with largest-remainder cents and stable holder-ID tie breaking. It rejects
missing/duplicate holders, shares not totaling one, mixed sources and a rounded
or unestablished basis. It retains supplied economic/voting rights unchanged;
request, commitment, receipt and issuance are distinct. Its synthetic test
holders are computational fixtures, not Sable Harbor subscribers. It deliberately
cannot turn the approximate 66.5/33.5 groups into a cap table or receipts.

### Retained correction/retest history

An intermediate change renamed the runtime land bridge action and failed one
existing regression. The implementation restored `ADD_RUNTIME_LAND_OVERLAY`
and introduced `ADD_GOODWILL_OPENING_CORRECTION` only for the new correction;
all 24 finance/tax/runtime tests then passed. A development build rejected source
changes made while it ran, as intended; a final clean-source build is required
for its package identity. The independent reperformance compares 9,778 ARU/BST
legal legs unchanged and reproduces the seven-source $13,325,751.3907 predecessor
funding population. Five additional proportional-request tests pass.
