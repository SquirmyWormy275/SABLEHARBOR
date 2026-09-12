# V03 visual and preservation review

Status: draft, pending owner visual acceptance. Feedback: “Better. But still feels sterile.”

Inspected the full PNG, PDF raster, desktop side-by-side comparison and mobile full-width browser page. The revised canopy symbols, shadows and title-case labels render without visible clipping or overlap. Entrances and the highlighted route remain legible. Earlier drafts are independently preserved.

Automated checks pass: approved original/source/artifact hashes; arrival route within existing walks and outside building interiors; four source entrances; PDF text bounds; SVG parsing; all local comparison links; V01 and V02 validators. Two same-toolchain builds produce byte-identical SVG, PNG and PDF files.

Browser checks cover 1600 × 1050 and 390 × 844, each in comparison, current draft and previous draft modes: all images load, no horizontal overflow. Full-resolution images remain directly accessible for reading the map at mobile screen sizes.

Graphic changes: warm ivory buildings, buff paths, olive canopy colors, varied deterministic canopy outlines, small diagrammatic shadows and softer title-case type. Tree centers and all campus geometry remain unchanged. Colors and shadows do not constitute material or solar specifications.

Reproduce source/link checks with `python geospatial/facilities/visitor/v03/validate.py`. Open [review.html](review.html) for the preserved V02/V03 comparison; see [MANIFEST.json](MANIFEST.json) for exact source and artifact hashes.
