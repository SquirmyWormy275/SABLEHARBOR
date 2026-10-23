# Historical legal dependency: accepted Klein/Fort successor

**Record:** `SH-LEGAL-DEPENDENCY-SUCCESSOR-001` · **Audited:** September 13, 2026  
**Disposition:** exact dependency compatibility; no new legal approval or document revision.

[Accepted PR #162](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/162) changed the
Klein shop and Fort occupancy history in the current [site register](../../../../geospatial/registers/SITE_REGISTER.csv).
The controlling [occupancy decision](../../../canon/KLEIN_FORT_OCCUPANCY_2026-09-13.md)
records separate premises and staged relocation during 2024.

The frozen [original manifest](../manifest.json) pins the earlier whole register for
`SH-LEGAL-DRAFT-HOST-RIGHTS`, the [Cradle host agreement](../source/host-rights.md).
Its actual schedules reference Kelly Gang Mining (`SH-SITE-0023`) and Demotte
(`SH-SITE-0027`). Both complete rows are unchanged. Bedford (`SH-SITE-0005`) and
Red Wash (`SH-SITE-0006`) are also unchanged. Red Wash is not the instrument owning
this manifest dependency.

The [machine-readable audit](PR162.json) records both whole-file SHA-256 hashes,
the accepted merge commit, controlling canon hash, and complete before/after
values for the only two changed records: `SH-SITE-0002` and `SH-SITE-0003`.
All 60 stable IDs, all column definitions, and the other 58 complete records
remain unchanged. The [before snapshot](SITE_REGISTER.before-PR162.csv) preserves
exact earlier bytes for offline verification; it is historical audit evidence,
not a second current register.

The original 17 instruments, their 90 source/publication/manifest files and their
original hashes remain unchanged. The old whole-file pin does **not** match current
main and is not silently rewritten. The validator prints an explicit dependency
successor disposition after checking the exact accepted transition. This permits
the unchanged host agreement to remain reviewable against current geography.
It does not certify a changed dependency as belonging to the historical release.

[Validation code](../../../../tools/legal_gaps/dependency_successors.py) permits
only this document ID, dependency path, original hash, accepted current hash and
pinned audit evidence. The exception is never applied to source files, generated
artifacts or other instruments. Any further byte change, including another site,
requires a separately reviewed successor. Missing or altered audit evidence fails
closed. No network access or full Git history is needed during CI validation.

```bash
python -m pytest -q tests/publications/test_legal_dependency_successors.py tests/publications/test_legal_gap_instruments.py
python tools/legal_gaps/validate.py
```

The original revision comparator still reports unchanged instrument bytes. The
practice/accounting manifests do not pin this site-register dependency. Existing
term reconciliation continues to check the actual host identities and external
host classifications directly from the current register. Source-impact reporting
must continue to show the whole-register change; this disposition does not hide
that change or authorize source-impact baseline refreshes by itself. The successor review bundle includes this audit for current-main compatibility.
Earlier bundles and their original snapshot pins remain unchanged.
