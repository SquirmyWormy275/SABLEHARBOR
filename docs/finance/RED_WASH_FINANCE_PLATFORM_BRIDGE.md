# RED WASH FINANCE-PLATFORM BRIDGE

**Bridge ID:** `FIN-RW-BRIDGE-001`  
**Source record:** `SH-PS-RW-TOR-001`  
**Target:** Sable Harbor enterprise financial data platform v0.1

The Red Wash Transaction and Operating Record supplies attributable transaction, production, mine-plan, mill, inventory, contract, delivery, journal, trial-balance, statement, fixed-asset, and ARO sources to the merged enterprise financial platform.

It does **not** bypass:

- generation-run identity;
- scenario identity;
- source manifest and provenance;
- the actual/forecast cutoff;
- accounting-period close;
- legal-entity scope;
- intercompany elimination;
- consolidation;
- versioned assumptions;
- public/private package boundaries.

## Entity mapping

| Red Wash record | Finance-platform treatment |
|---|---|
| Sable Harbor parent | `SHI` controlling company |
| Pale Sun | internal business line / management reporting dimension |
| Red Wash Operating Company | dedicated legal operating-company book, `RWH` |
| Northstar Resources (Wyoming) LLC | seller / predecessor, not a consolidated post-close entity |

## Reporting cutoff

Actual Red Wash records run through **August 31, 2026**. September through December records are `MANAGEMENT_FORECAST`. The platform must preserve that distinction at journal, subledger, report, workbook, and export level.

## Required source relationships

```text
transaction terms and purchase-price allocation
        ↓
opening legal-entity balances and asset registers
        ↓
geology/resource basis → mine plan → production
        ↓
mill mass balance → product lots → inventory
        ↓
contracts → deliveries → assay/title → invoices/receipts
        ↓
GL/subledgers → entity trial balance → consolidated statements
```

## No plug rule

Red Wash revenue, cost of sales, inventory, DD&A, ARO, taxes, royalties, capex, working capital, and cash arise from identified source records and assumptions. No consolidated statement plug is authorized.
