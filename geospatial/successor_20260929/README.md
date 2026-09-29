# September 29 accepted-source geographic delta

This issue #108 review pins accepted main `3dd5e15f58d39b28291782bde5bf4dbf3744a03e`
through `54dd6a46bd386475e7d5ea170d7419f80ae89d0a`. It inventories
**all 81 changed Git paths**, their old/new blob IDs and SHA-256 digests, and
assigns a geographic-authority boundary to each. There were **no changed
controlling canon documents** in this interval. Eleven material sources
received targeted geographic review, including the newly accepted 40-mile
operating selector, provisional early alignment, and five public 2027 portal
company sources. The other paths retain native source, engineering candidate,
publication, implementation or owning-domain labels. This is not a universal
legal, tax or IT audit.

The modern rail selector preserves the 40-mile total, 11 route-segment IDs,
26 structure IDs and nine-mile truck-only mine road. Its accepted downstream
reperformance leaves the modeled journal/cash/tax delta at zero. Proposed
terminal/warehouse leads are not placed in service. The historical southwest
line remains newly authored fiction, without recovered survey, real right of
way, or current asset. The public portal sources do not activate a 2027 host or
create a physical site by naming one.

The accepted 78,145 original geographic carriers remain fully dispositioned;
this is a **later source interval**, not a revived carrier backlog. Detailed
rail/site engineering and real-right boundaries still belong to #107. Sources
accepted after `54dd6a46` need another explicit review before a claim of
complete current geographic source coverage.

```bash
python -m geospatial.successor_20260929.source_delta
python -m pytest -q geospatial/tests/test_source_delta_20260929.py
```

The generator uses the repository's pinned Git objects, rather than the
current working tree, so ongoing changes cannot silently rewrite this
historical review. The tests compare every row with Git's exact changed-path
population, check targeted source bytes, and reproduce the compressed output.
