# Data model

```mermaid
erDiagram
  LEGAL_ENTITY ||--o{ ACCOUNTING_BOOK : owns
  ACCOUNTING_BOOK ||--o{ FISCAL_PERIOD : contains
  ACCOUNTING_BOOK ||--o{ JOURNAL_ENTRY : records
  JOURNAL_ENTRY ||--|{ JOURNAL_LINE : balances
  ACCOUNT ||--o{ JOURNAL_LINE : classifies
  CUSTOMER ||--o{ CUSTOMER_CONTRACT : signs
  CUSTOMER_CONTRACT ||--o{ PERFORMANCE_OBLIGATION : allocates
  CUSTOMER_CONTRACT ||--o{ INVOICE : bills
  INVOICE ||--o{ CASH_RECEIPT : settles
  WORKER ||--o{ PAYROLL_LINE : earns
  VENDOR ||--o{ PURCHASE_ORDER : receives
  PURCHASE_ORDER ||--o{ VENDOR_BILL : matches
  FIXED_ASSET ||--o{ DEPRECIATION_RECORD : depreciates
  MINE_PRODUCTION_BATCH ||--o{ URANIUM_SHIPMENT : supplies
```

Effective dates are present on material entity, contract, worker, asset, site, and operational records. Journal dates, periods, source IDs, posting timestamps, and source-record timestamps remain distinct. Posted journals are immutable; corrections use reversal entries. Domain additions currently include mining, logistics, recovery, research, payroll, procurement, assets, and debt.
