# Blackridge — separate case universe

Blackridge is a separate case, not a Sable Harbor subsidiary. Its 2015 mine/enterprise records, accounting assumptions and scenario period stay separate from Sable Harbor's company history and books. The [boundary record](../../business-lines/HISTORICAL_AND_EXTERNAL_BOUNDARIES.md) controls that separation.

| Reader task | Open |
|---|---|
| Inspect the existing human-facing workbook | [Blackridge master tracker XLSX](../../../blackridge/data/public/workbooks/BLACKRIDGE_MASTER_TRACKER_v0.1.0.xlsx) |
| Review workbook rendering evidence | [Saved workbook preview PDF](../../../blackridge/reports/workbook_previews/BLACKRIDGE_WORKBOOK_RENDER_PREVIEWS.pdf), [workbook QA report](../../../blackridge/reports/WORKBOOK_QA_REPORT.md) |
| Understand accounting and model scope | [Accounting policies](../../../blackridge/docs/accounting/BLACKRIDGE_ACCOUNTING_POLICIES.md), [financial model guide](../../../blackridge/docs/accounting/BLACKRIDGE_FINANCIAL_MODEL_GUIDE.md) |
| Query the small committed starting database | [m00 SQLite](../../../blackridge/data/public/databases/blackridge_m00_v0.1.0.sqlite3) |
| Build the larger 2015 data population | [Blackridge build instructions](../../../blackridge/README.md) |
| Understand dated evidence access | [Snapshot guide](../../../blackridge/docs/case/BLACKRIDGE_CASE_SNAPSHOT_GUIDE.md) |

Download the workbook to open it in a spreadsheet application. The full-profile database named in the [data manifest](../../../blackridge/data/public/manifests/DATA_MANIFEST.json) is not the committed m00 database. Use the documented generation/export commands for the full profile; do not treat a manifest path as a delivered download or replace it with the smaller database while claiming the same population.

The workbook is a generated interface and the case database is its own structured source. A workbook row or preview is not an independently obtained mine record. Keep profile, seed, period and dataset version with any analysis. This page introduces no new distribution release and no new financial assumptions.

[Subject directory](README.md) · [Business directory](../businesses/README.md) · [Department directory](../departments/README.md) · [Wiki home](../Home.md)
