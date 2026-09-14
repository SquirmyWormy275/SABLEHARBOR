# Audit workroom browser

Typed React/TypeScript application for the authenticated audit-training service. The browser stores navigation in its URL; engagement state, identity, permissions, evidence and revisions stay on the service. No credential, private truth, scenario seed or reviewer solution is written to browser storage.

Document inspection and review extraction require Linux with working unprivileged Bubblewrap (`bwrap`) namespaces and a writable temporary directory. The worker has no mounted private state or network access, and runs with memory, CPU, output and wall-time limits. If isolation is unavailable, files remain quarantined or require human review; the service does not fall back to parsing them in its own process. Install Bubblewrap through the host's package manager before running the local suite.

Run `npm ci`, `npm test`, and `npm run build` in this directory. `npm run dev` binds only `127.0.0.1` and proxies `/api` to `127.0.0.1:8780`. Deploy the generated `dist/` behind the same authenticated origin as the service; this package does not deploy anything. Node 22.12+ is required by Vite 7. Node 26.7 was used for validation.

`src/api.ts` defines bootstrap and engagement responses. Login uses `POST /api/session {credential}`; logout uses `POST /api/logout {}`. Mutations use cookie authentication and the CSRF token returned by bootstrap. Commands include a fresh command ID and expected revision. Stale writes remain errors; the user refreshes before resubmitting. Files use multipart upload and original artifact download endpoints. Backend authorization is authoritative, including private reviewer exports.

The configuration editor includes the approved 18 public parent selectors and 110 options, with no MM-08 submenu. `serializeConfiguration()` produces the Python contract, separating incomplete-evidence prevalence from proportional option shares. Custom descriptions are retained; inference and voice must be enabled by an actual backend adapter. Their availability is never simulated. Generation follows service state and requires actual successful validation/build before kickoff.

The ten navigation sections cover scope/kickoff, controls/tasks, PBC/evidence, meetings, people, populations/sampling, notes, calendar, findings/remediation and workpapers/review. Native workpapers and human review exports are primary. Experimental review has an explicit consent step and visible labeling.

`tests/browser.mjs` uses explicitly synthetic public fixtures to check all ten layouts, desktop/narrow overflow, configuration and dialog keyboard behavior. It is **not backend acceptance testing**. Run `node tests/browser.mjs` from this directory with a local Chromium executable at `/usr/bin/chromium`; it starts and stops a loopback-only Vite process. Screenshots and receipts go to ignored `enterprise/generated/audit-suite/build/visuals`. If this machine's `/tmp` quota is exhausted, set `TMPDIR` to a private short workspace-owned path; do not delete another session's files.

The copied corporate SVGs are unchanged originals. `brand-bindings.json` records their source and SHA-256. The selected layout uses a fixed charcoal navigation rail, ivory work surface, orange actions and serif section titles, with dense linked records rather than metrics cards. The horizontal-navigation alternative screenshot preserves more initial width but sacrifices a stable ten-section orientation and engagement identity; the rail was retained. Narrow screens switch to horizontally scrollable navigation and tables without page overflow.

The service tests cover command replay, scoped original downloads, private reviewer denial, retained population versions, prospective retesting and projected learner history exports. The separate private acceptance harness exercises real generated engagements and local company dialogue. The layout fixture remains distinct from that acceptance evidence. Local inference and speech were exercised with actual models; their output is experimental, not professional rubric validation. No external deployment is performed.

Local operator commands (run at repository root; private directories must be mode 0700):

```sh
uv run --extra audit-suite python -m enterprise.audit_suite provision --private-root /path/to/private-state --name Trainer --role instructor --credential-file /path/to/private-directory/trainer.json
uv run --extra audit-suite python -m enterprise.audit_suite serve --private-root /path/to/private-state --web-root audit_suite_web/dist --local-http --corpus-root enterprise/generated/audit-suite/private-corpus --program-pack enterprise/generated/audit-suite/build/program-pack.json --inference-config enterprise/generated/audit-suite/runtime/inference.json --voice-config enterprise/generated/audit-suite/runtime/voice.json
```

The operator starts the separately acquired local model using the private runtime's `start-inference.sh`. The service binds only loopback, disables forwarded-header trust and access logs, and requires TLS unless local development HTTP is explicitly selected. Credential JSON is written only to the requested new private file. Open `http://127.0.0.1:8780` for the explicit local HTTP mode; use its credential field in the login form. This is a local training installation, not a production deployment.

The corpus and program pack in that command are private prerequisites, not files supplied by a public code checkout. The separately delivered `SABLEHARBOR_PRIVATE_AUDIT_SOURCES_2026-09-13.zip` includes 1,110 scenario definitions, 166 clean source plans, five source-backed authority editions and the compiled program pack. Verify and restore it with `tools/audit_suite/private_source_bundle.py` following its companion README; restore only into a new private directory. Publisher source pins retain repository-relative locations and must resolve in the matching authorized checkout. Existing engagement histories and authentication are backed up separately. The source delivery does not include model weights, credentials or licensed AICPA/ISO standards.

Custom authoring has an instructor-only workbench: free-flow intent, bound control, private immutable draft, deterministic validation, independent local critic, inspected sources and explicit acceptance. Inspecting a prior draft makes the next correction a new revision with predecessor lineage. Scope changes invalidate acceptance. A critic with no observations is not proof of professional correctness; an actual negative smoke case remains blocked by its critic observation. Source material, recipes and rubrics remain outside the learner export.

Voice captures audio only after a microphone action. Local ASR returns an editable transcript; placing it in the message draft does not send it. Company playback synthesizes only an existing authorized company message. Experimental review lists exact bounded input locations before consent and checks their digest again before the model call. Population selected-ID imports retain original UTF-8 CSV/text and validate every selected ID against the referenced immutable population version.

IRAP setup uses the installed publisher-pinned non-classified ISM catalog, explicit requirement selection and separate unmapped supporting CCF controls. Scope revisions create new generation epochs while preserving old evidence, requests, tasks and selections. Private reviewer archives contain the authorized frozen world appendix and are excluded from learner projections and downloads.

The control workroom records dated procedure coverage separately from audit scope and receipt dates. Remaining-period gaps and historical exceptions stay visible; explicit proposals and confirmation route existing PBC requests without resetting the case clock. Implementation changes retain original work for reassessment.

The local service bounds uploads to 25 MiB plus multipart framing, streams request-size enforcement, and rate-limits authentication, commands, uploads and inference per process. These safeguards are tested for rejection and recovery; multi-process distributed rate limiting is not claimed. Provider requests use bounded local-tokenizer checks and request-local citation aliases that are restored and validated against exact retained source identifiers. A context-limit failure requires a smaller explicitly reviewed input, rather than silent truncation.

Local operator recovery commands (private, new target directories only):

```sh
uv run --extra audit-suite python -m enterprise.audit_suite backup --private-root /private/state --destination /private/backups/new-backup
uv run --extra audit-suite python -m enterprise.audit_suite restore --source /private/backups/new-backup --destination /private/new-state
uv run --extra audit-suite python -m enterprise.audit_suite provision --private-root /private/new-state --name RecoveryOperator --role instructor --credential-file /private/new-operator.json
uv run --extra audit-suite python -m enterprise.audit_suite grant --private-root /private/new-state --engagement ENG-existing --principal PRINCIPAL-from-new-private-file --permission instruct
```

Both destination parents must already be private mode-0700 directories. Restore never overwrites a working installation. It verifies the backup manifest, immutable original hashes and event chain, then imports supported data into a fresh application schema. All prior credentials are revoked and sessions discarded, including credentials that were valid at backup time; a trusted local operator must provision and grant new access explicitly. This prevents a restored backup from reviving later-revoked access. The application, source corpus, licensed standards and optional model/voice runtime remain separately installed prerequisites. These commands are local operator operations; no HTTP backup or restore route exists.

Scope accepts an IANA timezone (UTC by default). Date-only fieldwork starts, target dates and meetings mean 09:00 in that timezone; daylight-saving changes preserve the local hour. Explicit-offset timestamps retain their instant. The calendar renders the selected zone even when the clock stores a canonical UTC timestamp. Date-only evidence availability starts at local midnight.

Uploads remain capped at 25 MiB each. App-produced review ZIPs use a separate internal retention path capped at 100 MiB compressed and expanded, including full history and indexes, with bounded entry counts and member-integrity checks. Oversized packages fail explicitly; histories are never silently truncated to fit. The internal export path is not exposed as an upload option.
