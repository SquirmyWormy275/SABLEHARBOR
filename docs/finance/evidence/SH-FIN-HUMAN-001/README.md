# Foundry Field invoice evidence — draft review

One packet, not a finance release. **Status: awaiting exact-version user review.** No approval of broader document production is inferred.

Open [the local review page](review.html) in a browser for the retained corporate stationery reference beside the draft, followed by every PDF page and workbook sheet. GitHub displays the [Markdown packet](PACKET.md); download the [PDF](packet.pdf) or [Excel workbook](reconciliation.xlsx) for ordinary document reading. This draft uses the existing corporate publication renderer; its white body pages differ deliberately from the retained blank correspondence template shown for reference.

The packet follows invoice `INV-base-FF-003-TERM-0`, base scenario, from January billing to October 2027 recovery. It contains one invoice, one contract, two first-term contract versions, five movements, two credit notes, six source events and twelve journal lines. No source amounts, financial models or approved artwork were changed.

- [Complete selected rows and source-member hashes](source.json)
- [Accounting-ID and human-artifact catalog record](catalog.json) — linked in the existing institutional database through `reader_evidence_link`, retaining draft status
- [Draft artifact manifest](manifest.json)
- [Visual review and limitations](qa/REVIEW.md)

## Rebuild and check

Use the repository Python environment with its existing XlsxWriter, openpyxl and publication dependencies, plus LibreOffice and Ghostscript. From repository root:

```bash
python docs/finance/evidence/SH-FIN-HUMAN-001/build.py
python docs/finance/evidence/SH-FIN-HUMAN-001/review.py
python -m pytest -q docs/finance/evidence/SH-FIN-HUMAN-001/test_packet.py
```

To re-extract evidence, pass `--archive /path/to/sable-harbor-business-operations-v1.0.0.zip` to `build.py`. It rejects bytes that do not match the pinned published archive SHA-256 and verifies all seven source-table CSV populations against the corresponding released SQLite tables before selection. Without that option, the build reads the committed extract. All selected source columns are preserved there; reader worksheets intentionally present a smaller useful column set. Extraction equality against the downloaded archive was verified during draft QA.

PDFs use the current controlled corporate renderer and its pypdf normalization; the local adapter only starts Reconciliation on a new page. The new XLSX uses the repository's existing XlsxWriter dependency, not a replacement for the separately governed operating-review workbook. Same-environment repeat builds of PDF, XLSX and manifests were byte-identical during review. Cross-office/font/toolchain byte identity is not promised.

Source: [business operations v1.0.0](https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/business-operations-v1.0.0), commit `57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e`. Parent archive hashes and native source IDs are retained. This derivative is not independent corroborating evidence.
