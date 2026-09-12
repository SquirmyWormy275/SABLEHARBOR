# V05 visual and source review

Status: draft, pending exact-file owner visual acceptance. V02 remains the baseline; V03/V04 were not accepted.

Inspected the complete PNG and PDF raster, desktop side-by-side browser page, and mobile full-width draft page. This revision changes composition and building representation: one axonometric campus illustration, architecture derived from the existing spatial study, and a horizontal directory.

Corrections found during visual review:

- CairoSVG did not honor text paint order; the original halo covered label fills. Replaced it with separate stroke and fill text passes.
- A stacked roof label extended onto the shallow Residence facade. Replaced stacked markers with a single horizontal letter/name group on each roof.
- Restored both reception-court and residential-court labels after removing redundant entrance names.

Final inspection found no clipped labels or unintended label overlaps. Some trees and ground features are occluded by building volumes as expected in an illustrated view. The north arrow follows the projected north direction; the view is visibly labeled not to scale. Source orthographic geometry remains unchanged.

Automated results: four building footprint/height/parapet records reconcile to source; all 81 proposed facade openings match existing-study bays and avoid explicit perimeter cores; arrival route remains within source walks and outside building interiors; four entrance coordinates match source. SVG XML, PDF text bounds, source/artifact/reference hashes and local review links pass. V01/V02 preservation checks pass; V03/V04 remain unchanged and retain their CI checks.

Two same-toolchain builds produced byte-identical SVG/PNG/PDF. Six browser states (comparison, current and previous at desktop 1600 × 1050 and mobile 390 × 844) load all images without horizontal overflow. Direct full-resolution links support inspection beyond reduced mobile previews.

[Review surface](review.html) · [Exact output hashes](MANIFEST.json)
