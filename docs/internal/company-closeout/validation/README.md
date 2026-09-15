# Integration validation history

Prepared September 15, 2026 UTC. These records retain failed checks and correction evidence. They are development history, not final accepted-head validation.

## Publication/source lock correction

The broad working run started at `693b20ec` using `.venv/bin/python -m pytest -q`. The retained log reports two failures and three skips. Subsequent source integrations and catalog generation occurred before that run finished, so it is not an immutable-head acceptance result.

The billing failure correctly detected a change to `tools/documents/build_controlled_publications.py`, a source pinned by historical finance evidence. Commit `bd9154b5` restores the exact predecessor bytes (SHA-256 `0552479a76b94d128a39e9f9a4a12b87f4ab876e47926918cda3c5aa0a3d872a`) and introduces `tools/company_closeout/publications.py` as a separately versioned document-population wrapper. Historical invoice, workbook, artwork and source-lock bytes are preserved. No lock condition was relaxed.

The large-catalog negative test overlapped a failed catalog rebuild, whose incomplete database was below the test's size threshold. It therefore did not exercise the intended large-artifact precondition. After completing catalog regeneration and recording its exact reviewed size/hash, the affected tests passed. Final broad validation must run after generation with no concurrent source or artifact mutations.

The catalog build separately rejected missing document-ID metadata and then the changed pinned renderer dependency. Explicit metadata and the preserved renderer corrected those failures. Regeneration passed with 135 controlled publication objects, nine Pinakes portals and 12 evidence packages. The dated wrapper retained 134 hash-verified publications and rendered the changed inspection guide; the predecessor's 131 publications retained their original bytes.

Recheck command (13 tests passed):

```sh
.venv/bin/python -m pytest tests/publications/test_billing_record.py tests/unit/test_j2_archive_boundary.py -q
```

The separately recorded final receipt must identify the accepted revision, clean generation, all required checks and final import/restore evidence. Do not cite this historical run as that receipt.
