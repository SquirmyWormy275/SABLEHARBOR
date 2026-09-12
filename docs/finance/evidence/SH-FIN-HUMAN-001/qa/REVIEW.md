# Draft visual and numerical review

**Status:** agent-reviewed draft; user visual acceptance pending. No merge or publication authorized by this QA record.

## Surface inspection

Rendered the two packet pages and all five workbook sheets using the actual PDF and LibreOffice print export, then inspected each saved PNG at 108 dpi. Inspected the retained corporate letterhead reference and the 1440-pixel desktop browser review surface. The page provides full-size image links; the side-by-side view is a comparison, not the only reading size.

| Surface | Result |
|---|---|
| PDF page 1 | Invoice identity, source status and chronology readable; no split table |
| PDF page 2 | Reconciliation, accounting scope and provenance readable; explicit missing evidence |
| Workbook Reconciliation | Amounts, formulas and limitations readable; collection and writeoff measures distinct |
| Workbook Movements | All five rows present; event IDs wrap within their column |
| Workbook Journal | All twelve rows and both $3,813,500 totals visible; six events balanced |
| Workbook Terms and credits | Both contract versions and both credits present; synthetic approvals labeled |
| Workbook Source register | Revision/hash and scope visible; native database reference explicit |
| Review HTML | All eight content/reference images load; desktop width has no overflow; direct artifact links exist |

## Corrections made before this draft

- Moved Reconciliation to PDF page 2 after the first render split its table across pages.
- Reduced workbook print widths, added row rules and cell spacing, and wrapped long native IDs so numeric and explanatory columns no longer touch.
- Increased footer clearance after the initial print export clipped the footer.
- Explicitly wrapped the collected-total column header to separate it from the native-ID heading.

- Following parent review, replaced the inherited "Controlled publication" footer with "Draft reconstruction" in the scoped renderer and updated the database-discovery sentence. No other packet layout/content changed in that correction.

The corporate reference is a retained blank stationery layout, while the draft uses the repository's existing controlled-publication body style. The comparison labels that difference; it does not imply a new letterhead was previously approved. Logos, their geometry and approved source bytes are unchanged.

## Validation evidence

Thirteen focused packet/reader tests passed, including draft-discovery and corrupted/missing/scope/native-database-link rejection. The nine packet tests cover: source population/reconciliation, five negative tampering cases, manifest/reference freshness, workbook source-cell/formula/cached-value checks, and Markdown measure consistency. openpyxl emits a benign header/footer parsing warning when reading the XlsxWriter footer; the original XLSX is not rewritten and its actual LibreOffice-rendered footer was inspected successfully.

Fresh extraction from the verified released archive exactly matched committed `source.json`. Before selection, extraction checked SQLite integrity and compared every serialized cell and complete row population in all seven source CSV tables against the matching released unit SQLite tables. The complete row comparison includes all seven source tables, not only the selected arithmetic. Native database member hash is recorded in the source manifest; invoice/event predicates then select the complete bounded population. Two same-environment builds reproduced PDF, XLSX, source/catalog and manifest hashes. No full financial engine or SOC/CCF tests were rerun because no model, posting rule or control implementation changed.

`renders.json` records the seven draft page images and one reference image. Source and primary artifact hashes are in `../manifest.json`. Final Git commit identifies the exact review package. A source or rendered-artifact change requires refreshed tests, previews and review.

## Remaining limits

User acceptance is pending. Draft discovery is integrated through `reader_evidence_link` in the existing institutional database. The packet is invoice-specific, excluding pooled allowance and contract-wide revenue recognition. It provides no signed agreement, bank statement, tax specification, payment instructions or independently confirmed receipt. Closed ledger AR is zero; the derived $971,500 written-off claim is not recognized as an asset by this packet. Separate SOC/CCF implementation is untouched.
