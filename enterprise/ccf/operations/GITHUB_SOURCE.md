# GitHub pull-request review source

This read-only source acquires selected merged pull requests and their reviews
from `api.github.com`, preserving original response bytes, source URLs, capture
times and SHA-256 response hashes. It emits normalized `revision_review` records
for SH-ENG-002 and a local evidence connector configuration. It never changes a
repository, posts comments, grants access or approves a population.

```json
{
  "owner": "SquirmyWormy275",
  "repo": "SABLEHARBOR",
  "pull_numbers": [146],
  "scope": {
    "origin": "OPERATOR_SUPPLIED",
    "boundary_id": "corporate",
    "period_start": "2026-09-01T00:00:00Z",
    "period_end": "2026-09-12T19:00:00Z"
  },
  "max_pages_per_pr": 20,
  "max_bytes": 10000000,
  "timeout_seconds": 15
}
```

```sh
uv run python -m enterprise.ccf.operations.github_source /private/github.json \
  --output /private/new-github-export
```

The output directory must be new. All output files are private. The source
receipt contains original bodies as base64, including potentially sensitive
review text: protect it as evidence, not as a public report. Keep this generated
material outside tracked source. `github-evidence.json` is compatible with the
local JSON collection connector; `evidence-connector.json` contains its settings.
Supply a separate independently reviewed census to the collection workflow.
The PR selection is an operator-supplied bounded acquisition list; it does not
establish that all changes or all repositories in scope have been enumerated.

Public repositories need no credential. For a private repository, add
`"credential": {"file": "/private/github-read-token"}` or an environment-variable
reference `{"env": "CCF_GITHUB_TOKEN"}`. Use a fine-grained token scoped to the
specific repository with **Pull requests: read**. Credentials are loaded at run
time and are never written to receipts. Requests use GET only; redirects and
proxies are disabled, public destination IPs are pinned, and TLS is verified.
The source rejects raw or JSON-escaped credential echoes before retention.
Rate-limit/access failures stop acquisition; no partially acquired output is
published. Re-run after the access/rate-limit condition is corrected.

GitHub lists reviews chronologically. Normalization uses the latest substantive
state per immutable numeric GitHub user ID. Comments and pending reviews do not
replace an approval decision. Dismissed or changes-requested states suppress
prior approval by the same reviewer; outstanding changes requested by another
reviewer also prevent an observed approval decision. An accepted observed
approval must refer to the exact PR head Git commit ID, precede merge and come
from someone other than the PR author. Late, stale and self approvals do not
establish that condition. Every latest substantive review state remains in the
normalized evidence, and all original reviews remain in the source receipt.

The source fetches PR metadata before and after review pagination and rejects
visible metadata changes during capture. The REST API is not an atomic snapshot
and does not reconstruct historical dismissal times, qualifications, protection
rules or emergency bypasses. A currently dismissed review cannot establish an
approval at merge; historical proof requires additional retained event evidence.

Git commit IDs are preserved under `github_*_commit_id`. They are **not** relabeled
as SHA-256 artifact digests, and the source does not hash commit-ID strings to
simulate artifact identity. It omits `reviewed_revision_sha256`,
`merged_revision_sha256` and `protected_branch` because this API does not establish
those control facts. Consequently the current full SH-ENG-002 adapter remains
`NOT_RUN`, even when an observed review says `APPROVE`. Supply defensible artifact
bindings, historical branch-policy enforcement and independent review through a
reviewed enrichment procedure; do not edit source receipts to manufacture them.
Reviewer qualification and every BASE/additional manual criterion remain human
review obligations.

Contracts: `acquire(config)` returns records, provenance and `NOT_RUN`;
`export(config, output_dir)` additionally writes private reviewable artifacts.
Live acquisition requires `origin: OPERATOR_SUPPLIED`, the existing workflow origin for actual operator-supplied evidence; `actual_source_acquisition: true` separately identifies live acquisition in provenance. This does not assert accepted control effectiveness. Synthetic tests call normalization
or provide an explicitly mocked transport. No live source is silently classified
as demonstration evidence.

Implementation follows GitHub's official [pull-request review API](https://docs.github.com/en/rest/pulls/reviews): read permission, optional public access, chronological review listing and page size up to 100. It pins API version `2026-03-10`. Collection uses explicit numbered pages until a short terminal page; reaching the configured cap fails rather than truncating review history.
