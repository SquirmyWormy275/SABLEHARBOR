# Branch and pull-request disposition register

**Audited:** September 1, 2026  
**Default branch at audit:** `main` @ `c111ec6f4900edea656a52a391c71c600b880be1`

| Branch / PR | Audit classification | Disposition |
|---|---|---|
| `main` | Accepted canon, logos, organization maps, and briefing | KEEP; protect with required checks |
| `finance/enterprise-financial-platform-v0.1` / PR #9 | Active finance release candidate | KEEP; review-blocked until finance acceptance findings close |
| `integration/enterprise-audit-and-dossiers-v0.1` | Active stacked integration branch | KEEP until stacked PR is accepted |
| `assets/brand-integration-and-collateral-v0.2` | Stranded unique collateral/wiki source, now recovered | DELETE AFTER integration acceptance and hash/content review |
| `architecture/corporate-operating-model-v0.1` / PR #1 | Superseded calibration draft | Close PR as superseded; retain branch temporarily for provenance, then archive/delete |
| `assets/corporate-logo-system-v0.1` | Merged work branch | DELETE AFTER audit acceptance |
| `canon/corporate-lore-v0.2` | Merged work branch | DELETE AFTER audit acceptance |
| `docs/official-logo-org-briefing-v1.0` | Merged work branch | DELETE AFTER audit acceptance |
| `docs/organization-maps-v0.1` | Merged work branch | DELETE AFTER audit acceptance |
| `brand/logo-system-v0.1` | Older diverged brand implementation; tracked cache artifact | Confirm no unique accepted asset, then delete |
| `blackridge/m00-foundation` | Old scaffolding commit | Archive/delete after confirming main history contains required foundation |
| `blackridge/m00-v0.1.0-final` | Duplicate pointer to old foundation commit | Delete |
| `blackridge/m00-v0.1.0-review` | Connector probe only beyond old base | Delete |
| `blackridge/m00-ci-fix` / `blackridge/m00-v0.1.0` | Minimal probe/status branch | Preserve status text if useful, remove probe, then delete |

## Pull requests

| PR | Status at audit | Action |
|---|---|---|
| #1 | Open draft, obsolete baseline | Close as superseded by corporate lore v0.2 and PR #9's reversible finance reconciliation |
| #9 | Open, non-draft in GitHub despite release-candidate blockers | Mark/describe as review-blocked; convert to draft when the GitHub mutation is available |
| #2, #3, #6 | Closed superseded drafts | No action |
| #4, #5, #7, #8 | Merged | Delete source branches after the integration audit is accepted |

Branch deletion is intentionally deferred until unique material is recovered and the integration PR is accepted. Deleting first would destroy audit evidence.
