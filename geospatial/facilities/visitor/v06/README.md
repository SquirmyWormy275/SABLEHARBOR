# V06 — final illustrated visitor-map review

[View the illustration](artifacts/visitor-map-v06.png) · [Compare with V02](review.html) · [Raster PDF](artifacts/visitor-map-v06.pdf)

The final aesthetic pass uses the built-in image-generation tool with V02 as its edit target and the [Getty visitor map](https://www.getty.edu/visit/downloads/getty_center_map.pdf) as a supporting illustration reference. [The exact prompt](PROMPT.txt) is saved. No prior draft, approved original, architectural source or production atlas is changed.

The map retains the four-building arrangement and visitor wording, with drawn foliage, surface texture and more detailed architectural linework. The generated output also adds planting and rounds road corners; paths and parking have local adjustments. These are illustrative departures, not accepted plan changes. Its inherited scale bar must not be used to measure the synthesized drawing.

This is an art-direction raster pending owner acceptance. It is not a geometrically validated successor map or an editable vector. No production map ID is allocated. V02 remains the preferred baseline unless the owner accepts another treatment.

## Provenance and reproducibility

[Source metadata](SOURCE.json) records the tool, exact input and reference hashes, original generated file, and observed departures. [Manifest](MANIFEST.json) binds the prompt, inputs, code, review surface and outputs. Image synthesis is nondeterministic; the generated PNG is preserved as the immutable review artifact. `build.py` reproducibly wraps that PNG in a PDF. No SVG is fabricated from the raster.

```sh
python geospatial/facilities/visitor/v06/build.py
python geospatial/facilities/visitor/v06/validate.py
```

## Visual review

Inspected the complete generated PNG. Building letters/names, directory, reception guidance, four entrance markers, arrival route, parking/bicycle/drop-off labels and draft status are readable. No text clipping observed. Recorded added planting, rounded roads and local geometric differences rather than claiming exact preservation. No further generated iteration was made after the user's last-shot instruction.

The inherited footer remains visibly fictional/modelled. The browser review identifies the geometric limitation beside the download. The PNG is the original tool output, unchanged. Artifact-integrity checks do not imply metric accuracy or user aesthetic acceptance.

Also inspected the raster PDF and desktop comparison rendering. Six desktop/mobile comparison states loaded every image with no horizontal overflow. PDF wrapping reproduced byte-for-byte in the same toolchain. Reader catalog regeneration and repository hygiene checks passed.
