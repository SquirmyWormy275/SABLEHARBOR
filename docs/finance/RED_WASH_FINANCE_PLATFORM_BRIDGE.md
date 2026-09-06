# Red Wash Finance-Platform Bridge

**Bridge ID:** `FIN-RW-BRIDGE-001`
**Version:** 1.0.0
**Source record:** `SH-PS-RW-TOR-001`
**Source package:** deterministic Red Wash release 1.0.0
**Current target:** standalone public case package
**Enterprise target:** a separately authorized finance-platform v0.2 or later

## Release boundary

The merged enterprise financial platform v0.1 remains a closed, reproducible release
whose quantitative perimeter and source lock predate the selected Red Wash case. This
closeout does not silently inject Red Wash assumptions into the v0.1 configuration,
rewrite its released statements, or relabel its synthetic calibration data.

Red Wash therefore ships first as its own versioned source, CSV, SQLite, statement,
manifest, and release package. Enterprise integration is a successor change that must
be implemented deliberately with a new source lock, assumptions version, migration,
scenario/run identity, reconciliation baseline, and release acceptance. No file at
`config/finance/assumptions/red_wash_transaction_operating_record.yml` is part of v0.1
or this release, and that nonexistent path must not be used as a side-door input. The
only Red Wash release inputs are the three controlled files under `red_wash/source/`.

## Entity mapping for a successor release

| Red Wash record | Future finance-platform treatment | State |
|---|---|---|
| Sable Harbor | Existing controlling company (`SHI`) | Existing platform convention |
| Pale Sun | Business-line / management-reporting dimension, not a legal entity | LOCKED |
| Dedicated Red Wash operator | Separate legal-entity book; `RWH` remains a reversible system code | LOCKED shape / OPEN exact legal name and jurisdiction |
| Northstar Resources | Seller/predecessor display name only | PROVISIONAL; exact legal identity OPEN |
| ARU and BS&T | No 2025 Red Wash book, carrier revenue, intercompany entry, purchase accounting, or custody role from this bridge | LOCKED boundary |

## Time and evidence semantics

There is no historical `ACTUAL` layer in the Red Wash package.

| Period | Required role | Meaning |
|---|---|---|
| January–August 2026 | `SYNTHETIC_CALIBRATION` | Shared synthetic calibration rows; neither observed nor audited |
| September–December 2026 | `MANAGEMENT_FORECAST` | Synthetic prospective case rows |

Every future journal, subledger, report, workbook, and export must also preserve record
origin, fact state, epistemic state, generation-run identity, scenario identity, source
manifest, legal-entity scope, accounting period, and cutoff. A date before the cutoff
does not make a generated record actual.

## Driver and accounting chain

```text
transaction terms → opening net assets / PPA
resource basis → mine plan → mill mass balance → finished inventory
contract book → modeled delivery / assay / title → modeled revenue and receivable
incurred production cost + DD&A → weighted-average inventory → cost of sales
subledgers → journal / trial balance → statements → cash-flow reconciliation
```

The selected case reconciles $42.0M operating assets plus $4.5M current assets less a
$16.0M ARO and $2.5M other liabilities to $28.0M net identifiable assets and cash
consideration, with no goodwill and no transaction debt. Escrow and holdback are
separately disclosed risk-allocation mechanisms and are not added to consideration a
second time.

Production cost and DD&A are incurred measures. A successor platform must apply the
same transparent weighted-average inventory method as the standalone package rather
than expensing all incurred cost or plugging cost of sales. Revenue, inventory, cost of
sales, taxes, royalties, freight, ARO, capital, working capital, and cash must trace to
identified source rows and assumptions.

## Limited ARU/BS&T bridge treatment

`SH-PS-RW-LOG-001` changes no 2025 Red Wash annual sales or revenue. Qualified external
carriers remain authoritative throughout 2025. The $15.0M Red Wash interface figure is
an unbooked `PROVISIONAL_ASSUMPTION` screen—not approved capital, an ARU purchase price,
an intercompany transaction, or a basis for ARU financial statements. No freight cost,
revenue, asset, liability, or uranium custody transfers to ARU/BS&T until a later
authorized event and all relevant gates support it.

## Supersession

The earlier exploratory Red Wash values—$24.7M revenue, $22.3M generic operating cost,
126 employees, $18.5M ARO, and exploratory acquisition financing—are `SUPERSEDED`.
They are excluded from active standalone inputs and may be retained only as labeled
archaeology. The selected values reside in `red_wash/source/core_operating_data.json`;
the limited bridge resides in `red_wash/source/aru_bst_bridge.json`.

## Successor enterprise acceptance gates

A future enterprise release must, at minimum:

1. adopt the final public merge commit and source hashes in a new finance source lock;
2. add an explicit versioned assumption contract without weakening schema validation;
3. create migrations and prove both SQLite and PostgreSQL paths;
4. preserve generation-run and scenario isolation, cutoff semantics, consolidation,
   eliminations, and legal-entity ownership;
5. reconcile operating drivers through journals, trial balance, statements, workbooks,
   exports, and release manifests;
6. prove that no superseded Red Wash value remains active; and
7. issue its own release evidence rather than modifying finance-platform v0.1 in place.
