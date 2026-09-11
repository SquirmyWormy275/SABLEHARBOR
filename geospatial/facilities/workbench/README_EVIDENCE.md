# Evidence intake and review candidates

`evidence.py` builds an evidence queue from stable coverage IDs and provenance. Missing values stay unknown. A queue item is not a demand for a new building or a claim that evidence exists. Templates contain no invented evidence.

```sh
python geospatial/facilities/workbench/evidence.py queue
python geospatial/facilities/workbench/evidence.py template > /tmp/evidence-submission.json
python geospatial/facilities/workbench/evidence.py validate --input /tmp/evidence-submission.json
python geospatial/facilities/workbench/evidence.py stage --input /tmp/evidence-submission.json --output /tmp/review-candidate.json
```

The empty template intentionally fails validation until populated from supported evidence. `review` validates a submitted review record; it does not grant approval. `export` and `stage` write the same reviewable candidate wrapper, exclusively to a new file outside the repository. They never modify canon, coverage, source locks or publications. `--input` always takes the submission object, not the exported wrapper.

Required fields: `evidence_id` (`SH-EVID-*`), current `baseline` (coverage SHA-256 and source-main SHA), nonempty `scope_ids`, `claim_type` (`parcel`, `tenure`, `occupancy`, `workforce`, `engineering`), `evidence_kind`, source repository-relative `path`/`sha256`/`locator`, effective `start`/`end` dates (unknown may be null), precision, fictionality, explicit changes (`scope_id`, `field`, `before`, `after`), reviewer, decision and decision provenance. Unknown fields, changed baselines/source bytes, unknown IDs, invalid dates, duplicate changes and unsupported status promotions fail closed. Source files must already exist; remote URLs do not substitute for archived, hashed evidence.

`SOURCE_EVIDENCE` and `PLANNING_ASSUMPTION` remain distinct. Review decisions are `PENDING`, `REQUEST_CHANGES`, `REJECTED` or `ACCEPTED_CANDIDATE`. Acceptance is still only a candidate export; this module has no promotion command. Assumptions cannot become accepted source evidence through this interface.

For `ACCEPTED_CANDIDATE`, the reviewer must cite a hashed Markdown decision under `docs/canon/`, a full accepted commit SHA, and an exact machine-readable claim binding. The commit must be an ancestor of the locally fetched `refs/remotes/origin/main`; the decision must still have identical bytes there. Fetch current main before review. A pending local branch, arbitrary approval boolean, document title or checksum alone does not satisfy this test. The accepted decision contains a fenced `facility-evidence-decision` JSON block with `decision: "ACCEPTED"`, `reviewer`, and `claim_sha256`. That hash is `canonical_hash` of the submission’s evidence ID, scopes, claim type, source, effective interval, precision, fictionality, evidence kind and proposed changes. It binds the exact substantive claim, not merely an evidence ID. Existing canon does not acquire such blocks automatically; a necessary dated decision/addendum must undergo the repository’s normal review and acceptance first.

The authority hierarchy in [MAINTAINERS.md](../../../../MAINTAINERS.md) and [canon boundaries](../../../../docs/internal/CANON_AUTHORITY_AND_PUBLICATION_BOUNDARIES.md) still controls. The validator cannot independently authenticate the truth of an archived document or replace human review of conflicting sources, legal title, survey quality or appointments. Accepted downstream changes require explicit source reconciliation and repository gates; immutable historical releases remain intact.

Tests use isolated temporary repositories and conspicuously labeled fixture evidence. Run `python -m pytest geospatial/facilities/workbench/test_evidence.py -q`.
