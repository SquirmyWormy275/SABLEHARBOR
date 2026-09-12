# V08 — illustrated visitor-map finishing pass

[View PNG](artifacts/visitor-map-v08.png) · [Compare V07/V08](review.html) · [Raster PDF](artifacts/visitor-map-v08.pdf)

The owner requested another iteration. V08 uses V07 as the direct edit target through the built-in image-generation tool. It retains the illustrated style, page composition and visitor wording, with less repetitive planting along building bases and clearer entrance thresholds. The not-to-scale label remains.

[Exact prompt](PROMPT.txt) · [Provenance](SOURCE.json) · [Input/output hashes](MANIFEST.json)

This remains an art-direction draft pending owner acceptance. Planting and local geometry differences inherited from V06/V07 are not adopted site-plan changes. V07 and all authoritative campus sources remain unchanged. No production map ID, metric certification or editable vector is claimed.

The generated PNG is preserved unchanged. Image synthesis is nondeterministic. The publication build reproducibly wraps the immutable PNG as PDF.

```sh
python geospatial/facilities/visitor/v08/build.py
python geospatial/facilities/visitor/v08/validate.py
```

## Visual QA

Inspected the complete PNG: four building identifiers, directory, arrival route, entrance markers, courts, bicycles, drop-off, legend, draft revision and not-to-scale label are readable. No text clipping observed. Planting is less uniformly beaded beneath buildings while the prior illustrated direction is recognizable. This is visual review, not metric geometry certification or user acceptance.

Also inspected the PDF raster and desktop comparison. Six desktop/mobile states load all images without horizontal overflow. PDF wrapping reproduces byte-for-byte locally. Artifact/link integrity and V07 preservation pass.
