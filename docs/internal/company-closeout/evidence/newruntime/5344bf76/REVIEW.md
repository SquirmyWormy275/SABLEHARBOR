# Committed portal runtime review — 2026-09-22

Pin: 5344bf76413ffe2cd378b957dbb5f7d56d04ea19. Isolated detached checkout: /tmp/sh-portal-runtime-review-5344bf76. No active portal data, services, private payloads, or uncommitted files were used. This evidence is not a merged company acceptance or a replacement company release.

## Reproduction

From the exact checkout: `uv sync --extra dev --extra audit-suite --frozen`.

Run `.venv/bin/python -m pytest -q` with these exact modules: tests/audit_suite/test_company_disposal_runtime.py, test_company_disposal_runtime_review.py, test_company_data_quality_runtime.py, test_company_data_quality_runtime_review.py, test_company_access_review_successor.py, test_company_recovery_period.py, test_company_recovery_period_review.py, test_recovery.py, test_company_service.py (all under tests/audit_suite/). Add `--junitxml=<new-output>/results.xml`.

Separately run `.venv/bin/python -m pytest -q tests/audit_suite/test_instructor_key_service.py --junitxml=<new-output>/http-results.xml`.

In audit_suite_web: `npm ci --ignore-scripts`, then `npm test -- src/instructorGraph.test.ts`. All tests create disposable fixtures or pure projection inputs; no active service is needed.

## Claim matrix

- Owned-copy hold/disposal: native real unlink now implemented and exercised. Explicit local holds, retention deadlines, authorization expiry, active/backup copy populations, durable intent, interruption and exact retry, same-byte replacement rejection, metadata-only retained originals. It is restricted to newly created nonpersonal fixture copies, max32 /64KiB each. This resolves the old assertion that no runnable local hold/disposal slice existed; it does not establish approved company record-class retention or legal hold release.
- Recovery: real configuration-byte backup/restore with independent scheduled denominator, missed occurrence and failure/retry preservation; older engagement backup invalidates all prior credentials/sessions. This is bounded actual software behavior, not external deployment/RPO approval.
- Deleted/held content after older backup restore: still unfulfilled for company edition originals. company_disposal_runtime is not connected to recovery.restore or CompanyStore content disposition. Its 'BACKUP' inventory copy is a disposable local copy, not an older company database restoration with a later hold/disposal overlay. No source evidence supports claiming that cross-system gate passed.
- Dataset corrections: exact source versions, partial failed populations, real joins/totals, missing IDs and later known-on visibility are implemented and tested. Does not make local fixtures a complete current company census or approve corrected business facts.
- Access review: adjacent-quarter predecessor evidence is verified; missing P014/cohort and unauthorized rights remain unresolved rather than being promoted to closure.
- Indirect HTTP disclosure: native systems/record-list metadata, future records, revoked systems and collection, unrelated principals, CSRF and instructor-only index/detail denial/tamper masking are exercised. Six graph tests establish exact authored references, valid pointer/type/population limits and no invented relationship; they are not by themselves authorization tests.
- Remaining indirect surfaces: no new evidence here establishes universal search/snippet/citation/count/graph/tool/personal-memory/export enforcement or model-inference/prompt-injection evaluation across the company edition. Committed docs report private browser journeys; those reports were not treated as independently reperformed evidence or opened.

## Disposition

SH-RES-RUNTIME remains partial. Narrow it to company-class policy/retention acceptance, cross-store restore of later hold/disposal state, the remaining declared disclosure surfaces and actual environment/deployment boundaries. Reuse these exact committed APIs in a future selected-edition rehearsal after coordination with portal owner. Do not merge portal-owner code merely to carry a test receipt.

Pinned portal uv.lock retains its own dependency versions; running its supported frozen environment is not adoption of those dependencies into the company release. source-hashes.json records maintained runtime source and selected tests; installed.txt records this test environment. XML/log files are actual execution evidence. No professional audit opinion is asserted.
