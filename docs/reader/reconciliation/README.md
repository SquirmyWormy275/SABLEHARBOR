# Document counterpart reconciliation

**Record:** SH-READER-FORMAT-RECONCILIATION-001 · **Source revision:** `8898d2d0310a60bdf0e4753036790c6eda1388cd`.

All **448** rows from the pinned [format-review queue](../../wiki/library/format-review.md) have a stable disposition in [records.json](records.json). This is a completed reconciliation of that population, not a claim that all missing documents were produced. It does not rewrite the live generated queue.

| Disposition | Rows |
|---|---:|
| HISTORICAL_COUNTERPART_UNRESOLVED | 57 |
| NAVIGATION_ALIAS_NO_PUBLICATION | 3 |
| READER_MAINTENANCE_NO_LETTERHEAD | 115 |
| UNRESOLVED_DOCUMENT_COUNTERPART | 229 |
| VERIFIED_ACCEPTED_EVIDENCE_PACKET | 1 |
| VERIFIED_CHART_PUBLICATION | 40 |
| VERIFIED_IDENTICAL_SOURCE_PUBLICATION | 3 |

## What was checked

The audit searched 68 tracked manifest/register JSON files and release-index Markdown files, retaining every searched file hash. Explicit organization-register relations, source hashes in the controlled-publication manifest, and the accepted finance packet manifest establish the verified counterparts. Every artifact cited as verified was read and hash-checked at the same source revision.

A manifest mentioning a Markdown file, a linked PDF, an analogous workbook, or a similarly named release is only a candidate. The audit records these links without promoting them to equivalent publications. External release member bytes were not retrieved in this audit; unresolved rows retain that exact limitation. A separately recorded [release follow-up](RELEASE_FOLLOW_UP.md) does not alter these pinned dispositions. Historical source versions are never matched to a successor solely by title.

Technical navigation and maintainer records are not in-universe letterhead documents under [Sources and Formats](../SOURCES_AND_FORMATS.md). Their disposition applies only to that file. Unpaired policies, contracts, accounting records and other narrative records remain unresolved unless an explicit relation is established. No new PDF, workbook or art was generated.

## Row-by-row review

- [.github: 1 records](github-records.md)
- [CONTRIBUTING.md: 1 records](CONTRIBUTINGmd-records.md)
- [LICENSE.md: 1 records](LICENSEmd-records.md)
- [RED_WASH.md: 1 records](RED_WASHmd-records.md)
- [SECURITY.md: 1 records](SECURITYmd-records.md)
- [assets: 6 records](assets-records.md)
- [blackridge: 30 records](blackridge-records.md)
- [docs: 268 records](docs-records.md)
- [enterprise: 16 records](enterprise-records.md)
- [geospatial: 108 records](geospatial-records.md)
- [red_wash: 15 records](red_wash-records.md)

## Reproduce and check

```bash
python docs/reader/reconciliation/build.py
python docs/reader/reconciliation/build.py --check
```

The pinned source commit is deliberately fixed. A successor audit must record a new queue revision and reconcile additions/removals explicitly; regenerating the shared catalog does not retroactively change this inventory. Shared catalog integration remains the main integrator’s responsibility.
