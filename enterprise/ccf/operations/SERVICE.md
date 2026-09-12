# Protected CCF workflow API

This service connects signed enterprise access tokens to the existing local workflow's scoped permissions, independent reviews, revision checks and immutable event history. It does not appoint owners, accept framework mappings or establish actual operating effectiveness. No external service is deployed by this repository.

## Identity configuration

Use Python 3.12+ and `uv sync --all-extras` for the production runner. The `ccf-service` extra includes PyJWT's cryptographic verifier and Gunicorn. Create a private (0600), operator-controlled JSON file outside Git with this structure; replace every example value:

```json
{
  "issuer": "https://id.example.invalid/tenant",
  "audience": "ccf-api",
  "max_token_lifetime_seconds": 3600,
  "required_claims": {"token_use": "access"},
  "jwks": {"keys": [{"kty": "RSA", "kid": "REVIEWED-KEY-ID", "alg": "RS256", "use": "sig", "n": "PUBLIC-RSA-MODULUS", "e": "AQAB"}]},
  "bindings": [{"issuer": "https://id.example.invalid/tenant", "subject": "IMMUTABLE-IDP-SUBJECT", "principal": "EXISTING-LOCAL-PRINCIPAL"}]
}
```

Obtain public JWKS through the enterprise issuer's authenticated administrative process, verify provenance and pin the public keys here. Token URLs never select a key source. Rotate the reviewed configuration and restart the service; unknown keys fail closed. Configure an API-specific audience, an explicit provider access-token marker and integer `iat`, `nbf`, `exp` claims. The example marker is provider-specific, not universally present in OIDC tokens; the enterprise app registration must issue the configured marker. The API accepts RS256 only, rejects ID-token purpose, applies zero time leeway and limits token lifetime to at most one hour. Configure the identity provider to require appropriate MFA and conditional access. No password, ID token, browser session cookie or unsigned identity header is accepted.

Bindings use exact issuer and immutable subject, never email or caller-supplied roles. Local principal grants remain authoritative for permitted boundaries, action permissions, expiry and immediate local revocation. The service never holds the local CLI credentials. Those credentials returned during store initialization still require separate private delivery or non-distribution; binding an identity does not erase them. `command_as`, `report_as` and `revoke_as` are trusted in-process integration functions, not unauthenticated network endpoints. Host administrators remain trusted.

## Run and request

Set paths and origin in a private environment file:

```sh
CCF_DATABASE=/var/lib/ccf/workflow.sqlite3
CCF_IDENTITY_CONFIG=/etc/ccf/identity.json
CCF_PUBLIC_ORIGIN=https://ccf.example.invalid
```

The database must already have current-version plans and authorized principals and must be a private regular file. Protect its parent directory as well. A code change that alters the pinned workflow implementation requires explicit history migration; never replace the digest to bypass replay validation.

Development: `uv run --extra ccf-service python -m enterprise.ccf.operations.service --port 8765`. This binds only to loopback and permits cleartext there; use synthetic access tokens on a trusted local workstation. Send the configured Host header. This single-process development runner is not the production HTTP server.

Production: use the reviewed [Gunicorn configuration](deploy/gunicorn.conf.py), [service template](deploy/ccf-workflow.service.example) and [TLS proxy template](deploy/nginx.conf.example). Install a dedicated unprivileged service account, approved TLS certificate and DNS name; review the templates before enabling them. Gunicorn binds loopback only and trusts HTTPS scheme assertions solely from local peers. The WSGI application also rejects nonlocal peers and requires HTTPS outside the explicit development runner. Local machine users and the reverse proxy are part of the trusted transport boundary. There is no CORS allowlist, session cookie or identity-header authentication. The TLS proxy rejects unmatched hosts through a default reject server and exact incoming Host check, preserves the validated Host upstream, and limits request rate and size. Keep access logging disabled or configure a separately reviewed redacted audit sink; workflow events already record authorized actors and mutations without bearer tokens.

All endpoints require `Authorization: Bearer <access-token>`; never put tokens in URLs or commit them. A confidential client or approved interactive OAuth client obtains access tokens from the identity provider. This API intentionally does not implement a new login/password flow.

| Endpoint | Request | Result |
| --- | --- | --- |
| `GET /v1/report` | No query parameters | Current principal's scoped cases and period results |
| `POST /v1/command` | JSON `case_id`, `action`, `payload`, `expected_revision` | Committed case state |
| `POST /v1/revoke` | JSON `subject` containing local principal ID | Local revocation; admin permission required for every subject boundary |

Commands use the existing store action payloads: create, assign, population, intake, review and remediation actions. Read the workflow [README](README.md) and CLI help for their schemas. The outer JSON schema is exact; actor and time are derived internally. Requests are capped at 2 MiB and require an explicit content length. Duplicate JSON keys and nonfinite numbers are rejected. Failed authentication returns 401; rejected scope, permissions, payload or revision returns a generic 400; database unavailability returns 500. Responses are noncacheable. On revision conflict reload before submitting; never automatically advance a revision or replay a mutation blindly.

## Verification and activation gates

Run `uv run --extra ccf-service python -m pytest enterprise/ccf/tests/test_ccf_service.py`. Tests sign synthetic RSA tokens and exercise the actual private SQLite workflow. They cover wrong issuer/audience/subject, expired/future tokens, missing expiration, algorithm confusion, rogue signatures, attacker-selected key URLs, revoked principals, forged actor fields, stale revisions, cross-origin/destination requests, transport scheme and request bounds.

Activation requires real tenant app registration and token-claim contract, reviewed key provenance/rotation, authorized principal grants, TLS/network deployment, private credential delivery, tested backup/restore and monitored runtime. Those facts cannot be supplied by synthetic fixtures. Provider logout does not immediately revoke already-issued access tokens; use short token lifetimes and local principal revocation for immediate workflow removal. Central IdP revocation/introspection, high availability and formal penetration testing remain production rollout decisions.

Verifier behavior follows the [PyJWT API](https://pyjwt.readthedocs.io/en/latest/api.html). The dependency floor excludes its [PyJWK algorithm advisory](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-jq35-7prp-9v3f), and this implementation additionally validates the key/header algorithm and passes the RSA public key directly. The production extra uses the current [Gunicorn security release line](https://gunicorn.org/news/).
