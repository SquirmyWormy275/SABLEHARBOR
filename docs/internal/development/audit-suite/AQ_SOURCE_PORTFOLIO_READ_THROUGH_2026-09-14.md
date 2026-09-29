# Read-through company source portfolio — September 14, 2026

A fresh audit can investigate original documentary, identity, incident, training and backup systems through one explicit company-source portfolio. The portfolio routes requests to the original stores. It neither copies a prepared audit package into a company universe nor merges native records, histories, actor appointments or source qualifications.

## Operator contract

`FederatedCompanyStore(registry_path, profile_id)` reads a private bounded JSON registry. `Engine(..., company_registry=path, company_profile=id)` selects it instead of `company_root`. Existing concrete-store configuration remains supported.

The registry has exact top-level fields `schema`, `components`, and `profiles`. Schema is `COMPANY_SOURCE_PORTFOLIO_V1`. Each named component declares its existing private absolute `root`, exact physical `company` and `branch`, a distinct colon-free `namespace`, and an explicit `systems` list. Each profile declares a logical `company`, selected component IDs, and qualification `QUALIFIED_SOURCE_PORTFOLIO_NOT_COHERENT_OPERATING_YEAR`.

The logical system name is `namespace:native-system`. Original native IDs may themselves contain colons. Namespaces are unique within a profile; duplicate physical routes and ambiguous aliases are rejected. All source paths and the registry require private regular files/directories without symlink aliases. The existing database schema is checked read-only; a missing or invalid database is not initialized by the facade.

The selected profile's normalized manifest digest is frozen in the engagement's existing `company_source_binding` as `{company, branch, registry_sha256}`. Here `branch` is the explicit profile ID. Every operation revalidates that manifest before returning data; changing a profile cannot silently redirect an existing audit. Native source versions may continue to append. The registry does not select branches from audit mode.

## Authority and exact identity

The trusted operator grants the actual audit principal and engagement access to each physical system separately. There is no automatic grant propagation, source-owner reassignment or cross-profile fallback. Discovery and exact reads retain current source grants and the server-derived simulated clock. Original owner IDs still determine which scoped company persona may use a bounded sample.

Collector metadata preserves the physical company, branch, system, record, version and SHA. It adds `source_store_id`, `source_system_alias` and `registry_sha256` for unambiguous portfolio identity. The exact original collection receipt remains under `upstream_receipt`. The ordinary audit collector includes these routing fields in duplicate detection, so identical native IDs and bytes in distinct stores cannot collapse into one source. Native content is never rewritten.

The facade's direct collection idempotence is scoped to source component and profile; upstream command IDs include those pins. The Engine command journal continues to enforce engagement-level command idempotence. This is not a distributed transaction across the company journals and audit store.

## Explicitly unsupported operations

Each source read/page has its own native transaction. Portfolio discovery is not an atomic cross-store snapshot, complete audit population or assertion about unseen records.

The implementation advertises `company_populations=False`, `explanation_binding=False`, and `global_snapshot=False`. Those unsupported operations fail with `FEDERATION_OPERATION_UNSUPPORTED`. Per-source impact comparison is now supported with `source_impact=True`, as described below. No fabricated `_db` union is provided. A later implementation must bind each population or explanation source to a concrete transaction and retain its own clock/membership pins; aggregating independent snapshots cannot claim global atomicity.

Administrative work status preserves portfolio and provisional documentary custody qualifiers and exact source-store identity. It does not turn collected artifacts into procedure completion, professional review or whole-control effectiveness.

## Actual portfolio and validation

The private `company-portfolio-2026-09-14/reference-v2/` run selects documentary archives, one full-year identity branch, March incident and backup exercises, and the January–February training cycle. A second explicitly configured profile retains the counterpart branches; it is not selected from audit mode. Full-year identity is used instead of also including overlapping mover/half-year copies.

All registered systems are included, including a training follow-up system with no records in the selected branch. Native `SH` and `SABLEHARBOR` company IDs remain unchanged behind the explicit logical routing. Documents remain documentary, site references remain nonoperating, and discrete exercise dates are not padded into a coherent operating year. No new canon decision or professional sufficiency acceptance is implied.

`SOURCE_INVENTORY.json` retains physical roots, registered systems and original version/membership pins. `registry.json`, `bindings.json`, `access.json`, `audit-state/`, `COMMANDS.json` and `RECEIPT.json` support the new local walkthrough. Credentials remain private. Root controls service launch; this task does not replace a live backend.

The prior `reference-v1` rehearsal is preserved. It contained all declared aliases but omitted one registered empty system; v2 corrects that operator registry inventory. Current focused tests, independent facade review and prior concrete-store regression results are pinned separately; an earlier repository-wide test run is not relabelled to include these later changes.

The actual v2 engagement is `ENG-ab98cc63f5e66267539aeca3`: 70 scoped controls, 107 registered system aliases, 17 original retained artifacts from all five families, and revision 33 after the source rehearsal. Its source grants remain available only for the explicitly created local investigator and this engagement. The predecessor's newly created source grants were revoked separately and recorded in `reference-v1/DISPOSITION.json`; previous sources and receipts were not rewritten.

Sixty-one focused tests pass, covering the facade and existing concrete collection/persona/population/explanation/impact/readiness paths. The v2 `VALIDATION.json` pins that test receipt and current operator-run evidence.

The direct company-persona check exercised scoped owners selected from each of the five families, verified exact source references and grants, rejected a supplied private-key sentinel, and found no absolute repository path in returned context. It made no model call and left the engagement revision unchanged. Its bounded first-owner/system selector actually represented only backup and documentary families; `PERSONA_CHECK.json` records this limitation. Source availability across five families is not proof that every question receives relevant context. Explicit relevant-record targeting remains a separate improvement.

## Explicit conversation source selection

The conversation API now accepts an optional `source_records` array in the existing `meeting.message` payload. Each of one to four distinct pins has exactly `system_id`, `record_id`, positive integer `version`, and lowercase 64-character `sha256`. The system ID is the discovered native ID or portfolio alias. Callers omit the field to retain the original automatic sampler; an explicitly empty or null selection is invalid.

The server reloads current engagement authority, checks the frozen company binding, verifies that the meeting contact owns each selected system, and reads only the exact permitted source versions at the actual simulation time. It verifies original SHA values, enforces the existing aggregate byte/character limits, and uses bounded sandbox extraction. Unavailable, changed, wrong-owner, oversized, empty-extraction or truncated selections fail explicitly rather than substituting different documents. Current source authority is checked again after extraction and inside the final message-commit path after inference, without a second parse or model call.

The user message retains the exact chosen pins; context source IDs and original/portfolio identities remain distinct. The model notice says that a qualified source portfolio does not establish a coherent full operating year. `company_message_sources` advertises support only when company sources are configured. Background jobs already retain the exact payload/digest and expose it only through authorized explicit input inspection.

`PERSONA_SELECTED_CHECK.json` records a current read-only check selecting one native original from each of the five actual portfolio families. All five selected families reached context with exact source pins, no omitted extraction locations, no absolute private repository path and no engagement revision change. No real model call was made. Deterministic provider stubs separately verify actual Engine commit/replay and rejection when source access is revoked during inference; this is not a claim of model response quality or professional validation.


## Per-source impact comparison

The impact report now resolves each retained portfolio receipt through its exact `source_store_id`, `source_system_alias` and frozen `registry_sha256`, and verifies that the route still identifies its original physical company, branch and system. Original native identity and upstream receipt identity remain separate from logical routing. Two stores with identical native IDs and bytes are compared independently.

The report verifies retained artifact integrity and reads the original and latest observed source versions under current actor grants and simulation time. Pagination is bounded and checked for repeated/incomplete membership. It rechecks each candidate's source access after aggregation and rejects changes to the engagement revision, scope, clock or binding before returning. A corrupt or inaccessible original increments `unavailable_comparisons`; it cannot become an unchanged assertion.

Returned fields include engagement ID/revision, real report start/end, simulated as-of, comparison count and explicit `PER_SOURCE_OPERATION_NOT_GLOBAL` isolation. Each change retains physical and portfolio IDs, old/new version/SHA, discovery/recheck timestamps and explicit linked workspace IDs. Source-authored correction/withdrawal qualifiers are passed through as strings. A withdrawal notice is a later observable source version, not automatic deletion or invalidation of the previously retained evidence. New appends after discovery are outside this non-atomic comparison.

Twenty-two focused tests cover corrections isolated to one source component, withdrawal notices, future versions, changed registries, cross-component identity mismatch, grant revocation after discovery, incomplete pagination and corrupted retained originals, alongside existing concrete-source/facade regression cases. Evidence is under `reference-v2/source-impact-validation/`; all changed source fixtures are disposable test stores. No live company source, audit state or model was mutated by this implementation task.
