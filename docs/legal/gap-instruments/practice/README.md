# Public worked legal and accounting practice

Four source-backed learning packets. Start with a task and its blank workbook; open the worked explanation separately. These public examples are expressly shared learning material, not private assessment keys. All amounts retain their source scenario and period. The new workbook designs remain draft for exact-file review.

| Packet | Start | Separate worked example |
|---|---|---|
| ARU acquisition accounting | [Task](acquisition/TASK.md) · [Blank workbook](acquisition/blank.xlsx) | [Explanation](acquisition/WORKED.md) · [Worked workbook](acquisition/worked.xlsx) |
| ARU debt reconciliation | [Task](debt/TASK.md) · [Blank workbook](debt/blank.xlsx) | [Explanation](debt/WORKED.md) · [Worked workbook](debt/worked.xlsx) |
| Foundry Field revenue and credit dispute | [Task](revenue-dispute/TASK.md) · [Blank workbook](revenue-dispute/blank.xlsx) | [Explanation](revenue-dispute/WORKED.md) · [Worked workbook](revenue-dispute/worked.xlsx) |
| Taylor–Red Wash legal due diligence | [Task](legal-due-diligence/TASK.md) · [Blank workbook](legal-due-diligence/blank.xlsx) | [Explanation](legal-due-diligence/WORKED.md) · [Worked workbook](legal-due-diligence/worked.xlsx) |

[Structured practice database](practice.sqlite3) stores complete packet, evidence, calculation and finding records. Each packet JSON retains native source identifiers and selected rows. [Build manifest](manifest.json) records source and derivative hashes.

Build: `python tools/legal_gaps/practice.py build`. Validate: `python tools/legal_gaps/practice.py validate`. Optional native workbook review renders: `python tools/legal_gaps/practice.py render`.
