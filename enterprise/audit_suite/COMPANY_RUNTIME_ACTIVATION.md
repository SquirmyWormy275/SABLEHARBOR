# Company runtime activation contract

`company_runtime_activation.activate(capsule_root, destination, expected_manifest_sha256=...)` seeds a new private writable company source from one sealed operator capsule. `capsule_root` contains `MANIFEST.json` and `company/company.sqlite3`; the destination directly contains `company.sqlite3` and `ACTIVATION.json`.

This is company initialization before an audit, not prepared evidence or an audit cache. It copies every original system and source version across the capsule's branches. It creates no grants, collections, access events, audit state, model work, or automatic operating conclusion. Canonical/synthetic qualifications remain unchanged.

The input must be a completed, exactly pinned operator capsule with original member hashes and zero actual grants, collection receipts and access events. Source paths must be private, regular, nonaliased and not hardlinked. SQLite journal sidecars are rejected. The bounded source connection uses read-only immutable mode, so transient WAL state cannot supply unmanifested rows; source connections close deterministically. Capsule files are verified before the read, after its transaction, and before publication.

A fresh application-owned CompanyStore schema is instantiated. Only `systems` and `versions` rows are copied from the source; its schema, triggers and authority rows are never installed. Ordinary source table column shapes must match the application schema. Registration identities, contiguous versions, foreign keys, canonical timestamps, supported synthetic origin, provenance bounds, original content SHA and original command input digest are validated. Count/byte quotas apply before and during copy.

Every native field is preserved: company/branch/system/record/version, event and availability time, original imported_at, origin, exact provenance text and bytes, content SHA, command ID and input digest. Activation time is a separate real timestamp in the new receipt. It does not replace or fabricate the original import/business timestamps. The new runtime receives a distinct instance ID, not new native source identities.

Publication is private, staged and new-only. Failed moves roll back the staged output; existing targets are never overwritten. Exact systems/versions digests are recomputed from the fresh store. The receipt records capsule manifest SHA, seed database SHA, canonical table digests, native six-field references, original-field preservation, code pins and explicit provenance control-reference counts. Those counts show declared references, not proven control operation.

`seed_database_sha256` describes the activation point only. Later authorized grants and collection journals intentionally change the runtime database while immutable native rows remain. The original capsule and its complete database/member hashes remain sealed. Company federation should route to these runtime directories, with explicit registered-owner source grants; audit activation/collection then uses the normal authorized API. An activation receipt never grants access itself.

Fresh runtimes can later use existing company backup/recovery, retaining their own operational journals. The activation API is not a restore of an old runtime, does not copy its permissions, and does not merge separate stores into a coherent company year.

Verification is in `test_company_runtime_activation.py` and `test_company_runtime_activation_collection.py`: exact row preservation, hostile repinned source/schema rejection, ignored incoming triggers, private path boundaries, descriptor closure, sidecar rejection, rollback, and actual federation/Engine collection. Those tests verify future/revoked access denial and that runtime journals change without altering source capsule bytes.
