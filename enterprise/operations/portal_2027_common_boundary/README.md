# Prospective 2027 common company boundary

**Record:** `SH-PORTAL-2027-COMMON-BOUNDARY-v0.1`
**State:** provisional, prospective synthetic company source. This is a source input for portal scoping, not a completed 2027 operation, company-wide control calendar, or audit result.

The controlling structured source is [`../source/portal_2027_common_boundary_2026_09_29.json`](../source/portal_2027_common_boundary_2026_09_29.json). Its accepted-source commit and SHA-256 pins bind the 2026 SHI legal-entity, service, runtime-site, hosting-doctrine and CCF design records. The generated [`opening_v0.1.json`](opening_v0.1.json) retains those pins and gives one importable common A/B boundary. It shows SHI as the legal operator; identity, backup and compute as selected **service designs**; Reno/Boise as selected providers with draft, unexecuted contracts; and the owned site as preconstruction. Actual January 2027 systems, contracts, datasets, people/accounts, privileges and disposal targets remain unknown. It asserts no operated host site.

Five conditional rule rows cover nonhuman account review, RPO-derived backup job monitoring, risk/BIA-based restore exercise, privileged population review and event-triggered disposal. The source CCF procedures explain the conditions. **Company due, observed and missing counts are null**, not zero: no accepted 2027 company inventory, RPO/BIA, retention/hold schedule, contract/activation record or complete period ledger establishes them. No performance source or reviewer conclusion is supplied. The separate SH-IAM-007 payroll-release case is outside this scope.

The portal's A/B workrooms contain five bounded local exercise declarations each, totaling 26 explicitly declared local occurrences per profile. Those declarations are exercise-specific and expressly disclaim enterprise completeness and operated systems. This public source does not import their dates, execution states, exceptions or outcomes, and does not promote them to a corporate calendar. A read-only, private source-identity crosswalk was prepared for the portal owner; only this independently sourced conditional boundary belongs in the public company archive. The A/B records here are identical common source roles with no authored branch delta.

## Reproduce

From repository root:

```bash
python -m tools.company_closeout.portal_2027_common_boundary \
  --source-root . \
  --output enterprise/operations/portal_2027_common_boundary/opening_v0.1.json \
  --check
uv run --extra dev python -m pytest -q tests/company_closeout/test_portal_2027_common_boundary.py
```

The generator rejects changed source hashes, a promoted 2027 inventory/site/contract, unsupported due or performance counts, altered control procedures, A/B company deltas, and a stale export. The newly authored source has a separate authoring time and null repository availability/acceptance until an accepted merge/release records its actual known-on boundary. No pre-acceptance query should treat it as company evidence.
