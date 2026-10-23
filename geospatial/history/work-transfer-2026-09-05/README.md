# September 5 unified Work transfer provenance

The local `SABLE_HARBOR_Work_Transfer_Prompt_and_Maps.zip` is a 5,452,525-byte
transport wrapper with SHA-256
`c9223a49d98c8d3b5c26730b1186b4b50a8864d43e3c10c5d03581744d857425`.
Its four regular members passed ZIP CRC and byte checks on October 23. The
three payload sources are already present in accepted public Git at exact
bytes:

| ZIP member | Accepted source |
|---|---|
| `SABLE_HARBOR_Unified_Work_Super_Prompt.md` | [Master execution mandate](../../sources/MASTER_EXECUTION_MANDATE.md) |
| `source_assets/red_wash__site_overview.png` | [Red Wash site overview](../../../assets/brand/maps/red_wash__site_overview.png) |
| `source_assets/red_wash__underground_plan.png` | [Red Wash underground plan](../../../assets/brand/maps/red_wash__underground_plan.png) |

The fourth member, [original transfer manifest](TRANSFER_MANIFEST.json), was
unique. It is preserved here without byte edits. It connects the transfer to
two otherwise generic-named raw geospatial handovers; their exact bytes are
members of the already accepted [historical geospatial addendum release](../foundation-addendum-2026-09-05/README.md).
The manifest explicitly says repository execution and geographic conflict
resolution had **not** been performed at transfer time. Current accepted
geospatial and brand sources govern later work.

[SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) records the outer ZIP identity,
the original manifest hash, three accepted Git destinations, two historical
release members and authority. Run `python -I verify.py` to check the manifest
and accepted local bytes. An independent fresh GitHub retrieval of the two
generic raw members matched the accepted release; the full ZIP and all source
Downloads remain protected until the final reconciliation and cleanup gate.
