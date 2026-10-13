# Read and deliver the company records

[Scope](SCOPE.md) · [Completion and limits](COMPLETION.md) · [Local workspace](../LOCAL_WORKSPACE.md)

The November edition uses ordinary files and a SHA-256 manifest. It ends at a verified file/read boundary. Consumers need neither Sable Harbor's generators nor another product's implementation. Private selection, source mappings, retained originals and operator checks stay outside the client directory and public Git.

## Read a received directory

Open `SCOPE.md`, `SOURCE_DELIVERY.md` and `manifest.json` in the received directory. JSON and CSV records preserve separate subject, account and entitlement identities. Markdown explains scope and client responses. MP4, VTT and chapter maps supply the staged synthetic walkthrough. Still source views and computer-generated narration are identified explicitly; they are not a recorded employee interview or live system interaction.

A standalone copy of [demo_source_delivery.py](../../../tools/audit_suite/demo_source_delivery.py) needs only Python 3.11 or newer. From any clean consumer directory:

```bash
python demo_source_delivery.py verify RECEIVED_DIRECTORY
```

`RECEIVED_DIRECTORY` means the directory actually received, containing its own `manifest.json`. The reader enumerates every artifact, checks its hash and size, and rejects aliases, escaping paths, altered content, missing members and unexpected files. The exporter produces directories rather than accepting arbitrary archives.

## Manifest contract

The schema is `sableharbor.source-files.v1`. Its only top-level fields are `schema`, `package` and `artifacts`.

| Field | Meaning |
|---|---|
| `package.edition` | Immutable delivery edition identifier. |
| `company`, `boundary` | Client display name and expressly scoped records. |
| `period_start`, `period_end` | Company period, inclusive dates. |
| `cutoff` | Latest simulated source availability for this delivery, with offset. |
| `generated_at` | Actual generation time, separate from fictional events and availability. |
| `artifact_id`, `version` | Stable delivered artifact identity and positive integer version. |
| `path`, `media_type`, `bytes`, `sha256` | Relative member path and exact delivered-byte identity. |
| `source_locator`, `source_sha256` | Opaque company locator and retained original digest; an aggregate view pins the ordered source digest set privately. |
| `event_at`, `available_at` | Original or authored company event and source availability; an unknown historical event remains null. |
| `classification` | `original`, `derivative` or `authored-company-record`. |
| `derives_from`, `supersedes` | Lists of exact artifact ID, version and hash relationships. Retained original references use opaque original IDs. |

An original or newly authored company record must have identical delivered and original hashes. Derivatives explicitly identify retained originals or previously delivered artifacts. A compound derivative's `source_sha256` is the SHA-256 of the pinned source-set descriptor; `derives_from` lists the individual original hashes. An opaque locator can be resolved by the company through its separate private source map. It does not expose an authoring path, branch selection, credential or future delivery.

Keep each submission as received. A source successor names the exact earlier artifact in `supersedes`; a response may separately replace an earlier submission without rewriting the underlying historical record. Relationships can refer to earlier deliveries. A manifest is a company delivery record, not an instruction to change consumer conclusions or workpapers.

## Release one authorized stage

The operator supplies a retained private edition descriptor and prepared-input directory, chooses one authorized stage, and names a new destination:

```bash
python tools/audit_suite/demo_source_delivery.py publish \
  --edition PRIVATE_EDITION_JSON \
  --input-root PRIVATE_PREPARED_INPUTS \
  --stage AUTHORIZED_STAGE \
  --destination NEW_CLIENT_DIRECTORY
```

These names describe arguments, not workstation paths to provision. The controlling local operator report supplies the actual paths and release order. The descriptor must allow every selected source, pin its bytes, and provide a cutoff admitting its availability. The publisher validates all sources before writing, verifies the staged directory, and publishes by directory rename. Existing destinations are refused. An interrupted attempt cannot acquire a completed manifest at the final destination.

The private descriptor contains only the public manifest fields plus `input_path` and `allowed` per source, and its separately configured deny tokens. Unknown artifact or stage fields are rejected. Do not place operator files inside the client archive or grant access to a parent directory holding other stages.

Repeating delivery means publishing the retained inputs to another new directory. It does not mean rerunning historical company generators or resetting a training database. Changed source bytes require an explicit successor edition; a changed input hash fails before publication.
