# Foundry Field — Copperreach billing record

**Package ID:** SH-FIN-BILL-001 · **Version:** 1.0.0

**Status:** Owner-authorized successor; controlling on acceptance into main.

**Period:** January 31, 2027 issuance; public synthetic conditional forecast.

Read the [invoice](INVOICE.md) or its [Foundry Field letterhead PDF](invoice.pdf).
The [workbook](billing.xlsx) contains the invoice, tax calculation, principal reconciliation
and supplemental journal. [record.json](record.json) supplies editable structured source;
[reconciliation.json](reconciliation.json), [journal.csv](journal.csv), and
[billing.sqlite3](billing.sqlite3) expose the numerical records. All are independently saved.

The [September 13 adoption](../../../../canon/FOUNDRY_FIELD_BILLING_ADOPTION_2026-09-13.md)
resolves all three decisions from [PR #138](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/138).
The old [proposal](../../billing-proposal/README.md) remains dated historical evidence;
its “keep draft” wording no longer controls this successor. All fourteen field dispositions
are recorded. Customer and issuer legal names are complete, and tax treatment is explicit.

## Amounts and scope

The customer owes **$1,740,000**, representing 12 months at $145,000 for 140 seats.
Sable Harbor, LLC operates as Foundry Field and bears the sales tax without charging customer
reimbursement. At the adopted 8.75% planning rate, **$152,250 expense and payable** supplement
the issuance accounting. This lowers pretax earnings; it is not tax-free or included-tax pricing.
There is no added customer receivable or invented tax payment.

The original invoice-linked source population balances at **$3,813,500 debits and credits**.
Its later forecast movements reconcile as follows:

| Disposition of original subscription claim | USD |
|---|---:|
| Cash collected, including $174,000 recovery | 609,000 |
| Credits against the written-off claim | 159,500 |
| Surviving written-off claim, not recognized AR | 971,500 |
| Remaining recognized customer AR | 0 |
| Total original subscription claim | 1,740,000 |

These later movements are not facts known on the January invoice date. The selected journal
excludes contract-wide revenue recognition and allowance allocations. It cannot establish
the full contract's revenue or deferred-revenue balance. Neither the $0 AR nor a customer
writeoff establishes payment, legal release of the surviving claim, or discharge of tax.
The tax supplement ends at issuance; it makes no later tax-return or settlement claim.

## Reproduction and discovery

Run `python tools/documents/billing_record.py build`, then
`python tools/documents/billing_record.py validate`.
The established Foundry Field logo, letterhead renderer, and accepted workbook typography
are reused. The original accepted packet is preserved byte-for-byte.
[manifest.json](manifest.json) binds all saved outputs and their inputs; the
[evidence register](evidence-register.json) adds the package to the existing institutional
database and reader library. [QA.md](QA.md) records visual and numerical inspection.

The future tax rate is an explicit dated model assumption. The street strings are fictional
correspondence details; they add no sites. Contacts use `.invalid`, and the public archive
intentionally supplies no operational payment endpoint or government registration assertion.
