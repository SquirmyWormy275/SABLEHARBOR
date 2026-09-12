# Sources, formats, and reading the archive

**Reviewed:** September 11, 2026 · **Role:** navigation and interpretation guide.

## Read the company, then inspect the evidence

The [wiki](../wiki/Home.md) explains subjects and links to the actual records. The [document library](../wiki/Library.md) is the detailed file inventory. Use an existing document's title, date, status, and successor references before relying on it. A historical record remains useful evidence of what the case represented at that time.

The repository's [authority rules](../../MAINTAINERS.md) govern conflicts. Current canon and accepted dated decisions control their stated scope. The wiki, rendered documents, financial outputs, and database indexes are representations; they do not establish facts independently.

## Three connected forms

The owner requested a human-readable archive on September 11, 2026:

1. **Markdown:** a readable record or explanation accessible in the repository.
2. **Corporate document or workbook:** a formatted corporate publication for documentary records, or a usable Excel workbook for financial/accounting tables and calculations.
3. **Database entry:** an addressable record linked to its sources and human-facing representation.

For a large transaction population, a readable Markdown guide and a workbook with the actual rows are more useful than thousands of nearly identical Markdown files. This is the implementation interpretation used for the audit; it does not claim that an existing CSV meets the workbook requirement. Source documents such as invoices or agreements still need individual readable forms when the exercise relies on them.

For ordinary narrative documents, the existing controlled PDF system is the starting point. Existing publications are not restyled in bulk. Any new visual treatment follows the agreed small-batch preview and exact-file approval process. A technical README, code file, or navigation page is not represented as an in-universe letterhead document.

## Database scope

The existing institutional SQLite index identifies controlled documents. Its reader-library extension records Markdown, PDF and XLSX file locations and hashes, and links source/publication pairs verified by the controlled-publication manifest. This is discovery metadata, not an accounting subledger.

Actual transactions and operational quantities remain in the native scoped financial and operating databases. A catalog row does not satisfy missing transaction detail. The [finance handoff](../handoffs/FINANCE_HUMAN_EVIDENCE_COMPLETION.md) separates human-document completion from native data-model work.

Only explicitly manifested source/publication pairs are called verified. The [format-review queue](../wiki/library/format-review.md) assigns all non-navigation unpaired Markdown records to finance or corporate-document reconciliation. Unmapped files may have a valid counterpart in a release or another manifest; they need reconciliation rather than an invented pairing. The library's coverage report is an inventory, not a certificate that all three forms exist for every record.

## Current and historical material

The detailed library deliberately includes history. Its folder organization is a discovery aid, not an inferred approval state. Open each record to read its actual status. Current subject pages select current entry points and identify important successors. Preserve dated finance release boundaries, including source locks and scenario assumptions.

An external host is not a subsidiary; a selected provider is not an executed contract. Modelled facilities and conditional staffing are not actual occupancy or employees. A synthetic signature or transaction document is not real legal execution.

## Wiki and interactive pages

`docs/wiki/` is the versioned Markdown reading layer. The repository reading layer was accepted through PR #128. On the refreshed September 11 (Pacific) inspection, the separate wiki Git endpoint still returned “Repository not found.” Therefore these pages are delivered as repository pages; live GitHub Wiki publication is not claimed.

The repository pages work directly in GitHub. Interactive HTML requires a local browser or a separately published copy of the same committed files. The atlas and packaged browsers retain their existing instructions. No second content authority is introduced.

## Maintenance

Rebuild the institutional catalog and reader library with:

```bash
python tools/documents/build_institutional_catalog.py
python scripts/validate_institutional_catalog.py
python scripts/validate_reader_navigation.py
```

Publication changes first require the existing controlled-publication build and visual review. See [publication instructions](../../tools/documents/README.md). Check the [reader delivery record](READER_DELIVERY.md) for the exact implemented scope, validation, and pending approvals.
