# Branch and Pull Request Register

**Status:** Active repository hygiene register  
**Updated:** September 3, 2026

## Current pull requests

| PR | Branch | Disposition |
|---:|---|---|
| #9 | `finance/enterprise-financial-platform-v0.1` | RETAIN — substantive finance/data-platform engineering remains review-blocked and unaccepted. Do not merge until its explicit acceptance blockers close. |
| #10 | `integration/enterprise-audit-and-dossiers-v0.1` | CLOSED AS SUPERSEDED — later PR #13 is the surviving enterprise portal/dossier integration path. Preserve branch until unique-content/branch-retirement checks are complete. |
| #13 | `docs/enterprise-portal-and-repo-hygiene-v0.1` | RETAIN / RECONCILE — useful unique portal, dossier, wiki, brand/collateral, and hygiene work remains, but the branch materially predates current September 3 `main` canon. Reconcile before merge; current `main` wins all canon conflicts. |

## Branch-retirement policy

A branch may be deleted after all of the following are true:

1. its associated PR is merged, closed as superseded, or otherwise dispositioned;
2. no accepted unique source, binary, generated publication, or audit evidence would be lost;
3. any historically useful unique material has been preserved on `main` or in an explicit archival location;
4. current canon is not being reconstructed from a stale branch merely to justify retention.

## Immediate retirement candidates

The following historical heads are candidates for deletion after ancestry/unique-content verification:

- `migration/alexandria-control-boundary-v0.1.0` — PR #86 merged;
- `canon/headquarters-closeout-2026-09-03` — headquarters closeout integrated;
- `assets/brand-integration-and-collateral-v0.2`;
- `assets/corporate-logo-system-v0.1`;
- `canon/corporate-lore-v0.2`;
- `docs/official-logo-org-briefing-v1.0`;
- `docs/organization-maps-v0.1`;
- duplicate/superseded Blackridge M00 heads: `blackridge/m00-foundation`, `blackridge/m00-ci-fix`, `blackridge/m00-v0.1.0`, `blackridge/m00-v0.1.0-final`, `blackridge/m00-v0.1.0-review`;
- `brand/logo-system-v0.1` and `architecture/corporate-operating-model-v0.1` after explicit unique-content inspection.

## Retain until active work is resolved

- `main`;
- `finance/enterprise-financial-platform-v0.1` while PR #9 remains active;
- `docs/enterprise-portal-and-repo-hygiene-v0.1` while PR #13 is reconciled;
- `integration/enterprise-audit-and-dossiers-v0.1` only until the superseded-branch unique-content check is complete.

## Current capability constraint

The connected GitHub interface used for this cleanup can inspect and move branch refs but does not expose branch-reference deletion. Therefore destructive branch retirement remains an administrative/local-Git action. This is a tooling limitation, not a reason to treat stale branches as active work.
