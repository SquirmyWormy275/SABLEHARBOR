# Main source protection

Prepared September 15, 2026 UTC. Initial API read reports ADMIN access, no rulesets,
and HTTP 404 for branch protection. This is an observation, not an active-control claim.

## Prepared configuration

Apply `.github/main-protection.json` to the existing `main` branch with the branch
protection API after the unconditional `Source integrity / required` check is available.
Require a pull request, resolved conversations, strict up-to-date source-integrity check,
no force pushes and no deletion. The workflow has no path filter, preventing a skipped
required context from stranding unrelated PRs. Existing scoped validation gates still
apply under MAINTAINERS.md; this required context is a universal minimum, not a substitute.

Owner-directed integration can proceed without an invented second human owner or
self-approval: required approving review count is zero. Independent substantive review
is retained in the evidence receipt. Administrator enforcement is disabled solely for
an explicit emergency process: document incident, exact SHA, failed/unavailable gate,
reason normal PR delivery cannot proceed, owner authorization and restoration/retest.
Use normal checked PR delivery for ordinary work; do not use this exception to hide
failed reconciliation. GitHub still records administrative changes and merges.

Do not retire branches during this closeout without unique-content and live-owner review.
The active audit-suite branch and worktree are reserved. No branch deletion is needed
to protect current main.

The final receipt must retain the request JSON, response projection and a fresh readback,
including `protected: true`. Prepared bytes alone are not evidence of enforcement.
