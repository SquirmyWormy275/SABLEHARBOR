# Portal neutral software reperformance — September 22, 2026 UTC

**36 tests passed, zero failures/errors/skips; two dependency deprecation warnings.**
The exact source is portal commit `8f9b8eabed3af1d2c050afc9bfe8935fd41f48ae`,
executed in an isolated detached checkout. This receipt records actual execution,
not adoption of the portal branch or completion of the company IT gate.

[receipt.json](receipt.json) records timestamps, command, installed packages,
implementation and test source hashes, exact output hashes, clean tracked status,
and the claim matrix. [pytest.log](pytest.log) and [pytest.xml](pytest.xml) retain
all outcomes. The warnings concern Starlette's httpx TestClient and AnyIO's
BlockingPortal alias; no test failed or skipped.

## Exercised scope

- Distinct synthetic preparer/reviewer identities, rejected self-review,
  versioned workpapers/export and rejection of reviewer-only collection.
- In-process HTTP authentication, CSRF, future-evidence denial, retained original
  bytes and disappearance of system metadata after source-grant revocation.
- A real temporary filesystem backup taken before principal revocation, restored
  with old credentials and session denied; history, original bytes and a failed
  finding remain intact.
- Company-store restore revokes every read grant, rejects corrupt backups and
  permits exact historical collection replay only after explicit regrant.
- Personal-view recovery retains histories and checks current identity and
  context; corruption and revoked restore authority prevent publication.

These neutral fixtures do not use the frozen company edition. Test identities
are software fixtures, not evidence that a human auditor performed review.
No active portal database, private payload, model, service or live receipt was
read. Only committed source was inspected; the active worktree's dirty
`service.py` and untracked `company_source_register.py` remained untouched.

## Remaining claims

Company-record hold/disposal reconciliation after restoring an older backup is
**not implemented in the inspected recovery path**. `company_store.py` makes
versions and collections append-only through no-delete triggers;
`company_recovery.py` validates/copies that history and revokes grants. This does
not apply a later legal hold or authorized-disposal event to an older backup.
Personal-view clear/history features do not substitute for that company-record
requirement. A retention successor and adversarial older-backup test remain
owned by the portal/runtime workstream.

HTTP testing covers named systems/records and collection endpoints. It does not
establish all search, snippet, citation, count, graph, memory or export disclosure
boundaries, production operation, site resilience or overall control effectiveness.

## Reproduction and ownership

Use an isolated checkout at the exact commit above. Install its locked environment:

```sh
uv sync --extra dev --extra audit-suite --frozen
.venv/bin/python -m pytest -v -o addopts= tests/audit_suite/test_acceptance_commands.py tests/audit_suite/test_company_source_census_review.py tests/audit_suite/test_company_service.py tests/audit_suite/test_recovery.py tests/audit_suite/test_company_operator.py tests/audit_suite/test_personal_views_recovery.py
```

Tests create their own temporary stores and use FastAPI TestClient without
starting an active service. The receipt contains the original command including
its JUnit output location; choose a new receipt location on repetition.

The portal owner retains `build/audit-training-suite` and its active worktree.
The company integration owner may consume this bounded receipt and coordinate a
selected frozen-edition collection → preparation → independent review → export
exercise through the existing input adapter. No portal code is copied into the
company branch by this change. That integration exercise and the remaining
hold/disposal and indirect-disclosure checks require separate evidence.
