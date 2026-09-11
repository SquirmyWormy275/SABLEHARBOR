# J2 leadership public-scan closeout

This supplements `J2_LEADERSHIP_2026-09-10.md` for PR #118.

The clean-source chart workflow and governance/J2/Alexandria workflow passed on `6fbe779eadfe662f8681a9da812845fd6ad0e3d6`. The chart workflow executed all 19 then-present focused tests and proved regenerated files were current.

Red Wash run `34566666380` passed its 514 reconciliations, 27 tests, repeat-build proof and clean-source participant-package checks, then correctly rejected two organization PDFs at the repository-wide public-safety scan. The current chart-book allowance still named the previous source hash, and its preserved predecessor had moved to a new path not yet in the allowlist.

The corrective change updates only the exact reviewed current chart-book size/hash and adds the exact previously reviewed bytes at their new historical path:

| Path | Exact bytes | SHA-256 |
|---|---:|---|
| `docs/organization/assets/current/Sable-Harbor-Organization-Charts.pdf` | 12412796 | `352dfa4f1247f6089d340b19940f75758a666dce14f239fb38b1c2a300aaa38b` |
| `docs/organization/history/v1.0.0/Sable-Harbor-Organization-Charts.pdf` | 12421998 | `c1589fbd0c0bfcb2a823cc4e582b580510f3d1408a933ddb09188aa217f62665` |

Both files were downloaded, hashed and visually reviewed as recorded in the primary validation note. No artifact bytes are changed by this correction. The 10-MiB default limit, credential/private-path checks, generated-artifact scan, all other reviewed allowances and the industrial models remain unchanged. A modified PDF cannot inherit the allowance merely by retaining its path or size.

Two additional regression tests check exact allowances and rejection of a same-size changed PDF. The persistent organization workflow now executes 21 focused tests in total (six existing, eleven leadership and four archival/publication-boundary tests). Final clean-source results and main acceptance are recorded in PR #118; the superseded failed run is retained as evidence rather than mislabeled successful.
