# Revision comparisons and floor overlays

`compare_models(before, after)` compares normalized spatial models by stable site, building, floor and room IDs. Missing or duplicated IDs fail; list order does not create a revision. It detects additions/removals, parent reassignment, rectangle/area geometry, floor heights, doors/cores/circulation/access, names, statuses, capacity categories and other changed attributes. Each change names its exact before/after value and affected map links inherited from the model. Building/site changes include descendant floor links.

The output has `comparisons` (one record per site), `summary` and source hashes. Site records expose `site_id`, `title`, `before_revision`, `after_revision`, `changes` and `overlays`. Changes carry `scope`, `id`, `field`, `category`, `before`, `after`, `affected_maps`. Each affected floor overlay contains actual `before_rooms` and `after_rooms`, full floor objects and both link sets. All rectangles remain local model metres.

`build_comparison(root)` reads accepted baseline `ff5cd67ff980790413f7bfbf0829b47d20d266a3` directly with `git show`: architectural source JSON, runtime bridge and source manifests go into an isolated temporary tree. Every baseline blob hash and byte-identical current source path is recorded. The current normalizer runs separately over both trees. It does not clone the current model and call that history.

Current architectural assumptions are explicitly applied to both normalizations because the accepted baseline predates this spatial publication layer. They appear as `NEW_ARCHITECTURAL_ASSUMPTIONS` information, not historical height/material approval. At implementation, all accepted floor-source geometry is unchanged, giving nineteen site comparisons with zero changes and zero fabricated overlays. New elevations/sections remain modelled assumptions. Future source edits produce actual differences.

```sh
.venv/bin/python geospatial/facilities/spatial/compare.py --output /tmp/current-comparison.json
.venv/bin/python geospatial/facilities/spatial/compare.py \
  --before /tmp/before-model.json --after /tmp/after-model.json \
  --output /tmp/revision.json --output-dir /tmp/revision-overlays
```

CLI export paths must be outside the repository and new files are opened exclusively. No canon, source geometry or accepted artifact is mutated. Overlays use red dashed outlines for before and blue solid outlines for after in a common local frame; the accompanying JSON carries non-geometric changes and links. A floor with only a name/capacity/access edit can have coincident outlines—this correctly shows unchanged geometry. There are no rendered overlays when no floors are affected. The offline viewer imports this JSON directly in its Revision comparison tab; Reset restores the committed comparison. Imported results remain a review and never mutate the model.

Tests exercise unchanged geometry, movement, access/capacity/status/name edits, heights, floor addition/removal, bad IDs, map impact and exact Git baseline provenance.
