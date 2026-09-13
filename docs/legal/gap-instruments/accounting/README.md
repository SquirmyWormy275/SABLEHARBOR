# Contract clauses and accounting evidence

Start with [the clause links](LINKS.md) to trace a draft term to an existing invoice, journal event, account, acquisition schedule or model rule. [The workbook](links.xlsx) presents the same evidence in readable sheets; [JSON](links.json) and [SQLite](links.sqlite3) support exact record lookup. These are review-support derivatives, not new journals or accepted legal terms. The workbook is a new design awaiting exact-file review.

The bridge covers all 17 legal gaps with 23 clause links. For billing, follow the six invoice events through their 12 native journal legs. For acquisition work, compare ARU consideration, goodwill, opening accounts and conditional tax schedules. For workforce, distinguish the eight awards from service-period accrual rules, installments and the separate consultancy. For land, inspect the existing unresolved-settlement rule without inventing a payment. Red Wash title work links to the historical acquisition amounts and does not imply escrow release.

The FF packet is a released **2027 base conditional forecast**. ARU schedules are the independently reproduced **2026 model** identified in [CURRENT_SOURCE_BRIDGE.json](../../../finance/evidence/tax-transaction/CURRENT_SOURCE_BRIDGE.json). Red Wash is a **2025 acquisition**. Runtime land is a **2026 adjustment rule**. None is an external bank confirmation. No global sum across these populations is meaningful. Repeated links to one transaction are references, not additional amounts.

Source selection and interpretation are maintained only in [source.json](source.json). Every clause heading and native file is pinned by SHA-256. JSON pointers, CSV filters and exact code-block delimiters are validated against the pinned file. Native rows retain their account, source, journal, period and scenario identifiers. Missing-entry dispositions preserve the controlling gap register; a draft without execution evidence does not create a posting. Draft review status and the original gap disposition remain separate.

Run from the repository root:

```sh
python tools/legal_gaps/accounting.py
python tools/legal_gaps/accounting.py --check
python -m pytest tests/publications/test_legal_accounting.py
```

The build verifies 15 native reconciliations and generates `LINKS.md`, `links.json`, `links.xlsx` and `links.sqlite3`. Check mode regenerates in temporary storage and compares Markdown, JSON and workbook bytes. SQLite is compared by complete schema, every table and row (including duplicate rows), application/user version metadata, integrity and foreign-key checks. SQLite engine versions can encode identical logical databases with different headers or storage bytes, so cross-version SQLite byte equality is not required. The retained database bytes are preserved; this exception does not permit changed data, missing rows or changed schema. Source hash changes require deliberate review; the generator never refreshes source hashes or changes native records. Workbook sheets are Read first, Coverage, Reconciliation, Links, Sources and one numbered Evidence sheet per clause link. Native fields use a vertical key/value layout for readability.

SQLite tables are `coverage`, `source`, `clause_link` and `reconciliation`. `clause_link.native_value_json` holds the exact selected native value; `selector_json` specifies how to retrieve it again. No posting table or writeback mechanism exists.
