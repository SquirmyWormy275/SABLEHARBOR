# V07 — refinement of the V06 illustrated visitor map

[View PNG](artifacts/visitor-map-v07.png) · [Compare V06/V07](review.html) · [Raster PDF](artifacts/visitor-map-v07.pdf)

The owner responded positively to V06 and authorized one further iteration. V07 uses V06 as the direct edit target through the built-in image-generation tool. It retains the illustrated aesthetic and composition, with clearer typography, cleaner roof/paving edges and more controlled foliage. The numeric scale bar is replaced by “ILLUSTRATIVE STUDY · NOT TO SCALE.”

The generated image remains an illustrative study, not a metric plan. V06's added planting, rounded roads and local path/parking changes remain illustrative; they are not adopted into the authoritative campus sources. No production map ID is allocated. V06 and all earlier drafts remain unchanged. Owner acceptance of this exact revision is pending.

[Exact prompt](PROMPT.txt) · [Input and tool provenance](SOURCE.json) · [Source/output hashes](MANIFEST.json)

Image synthesis is nondeterministic. The original output PNG is preserved unchanged. `build.py` reproducibly wraps those bytes as PDF; it does not regenerate the illustration. No editable vector is claimed.

```sh
python geospatial/facilities/visitor/v07/build.py
python geospatial/facilities/visitor/v07/validate.py
```

## Visual review

Inspected the full-resolution PNG: four building names/letters, directory descriptions, arrival wording, legends, entrance markers, court labels, bicycle/drop-off labels, draft status and not-to-scale label are readable. No clipped text observed. The refinement preserves the recognizable V06 composition. This inspection does not certify exact metric geometry or constitute user aesthetic approval.

Inspected the PDF raster and desktop comparison. Six desktop/mobile comparison modes load every image without horizontal overflow. PDF wrapping reproduced byte-for-byte in the local toolchain. Artifact integrity and V06 preservation checks pass.
