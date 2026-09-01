# Independent Unit Package Standard

A business subunit is independently auditable only when a pinned release contains enough evidence to inspect the unit and reconcile it to the enterprise without importing unrelated unit data.

## Required package

```text
releases/<version>/<unit>/
├── manifest.json
├── <unit>.sqlite
├── csv/
├── financials/
├── inventory/
├── queries/
├── controls/
├── validation-report.json
└── SHA256SUMS.txt
```

## Required content

1. Canon/evidence-state crosswalk and source commit.
2. Explicit table and column allowlist.
3. Unit scope by entity, segment, project/site, generation run, and scenario.
4. Applicable trial balance and financial statements.
5. Subledger, inventory, asset, workforce, contract, and operating extracts.
6. Intercompany activity and consolidation reconciliation.
7. Source-to-journal and journal-to-source lineage.
8. Assumptions, open facts, exclusions, and limitations.
9. Validation results, schema version/fingerprint, manifest, and checksums.
10. Direct generated-artifact safety scan.

## Non-negotiable controls

- Never create the public or unit SQLite file as an unrestricted source-database backup.
- Do not label synthetic, model, or scenario data as canon or audited actuals.
- Do not sever stable enterprise keys needed for reconciliation.
- Reject cross-unit leakage.
- Require explicit generation-run and scenario selection.
- Reconcile opening plus activity to closing for every applicable rollforward.
- Scan generated SQLite, CSV, XLSX, ZIP, and manifest outputs themselves.
- A green generator test is not a substitute for direct artifact inspection.
