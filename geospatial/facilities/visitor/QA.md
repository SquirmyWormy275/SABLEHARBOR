# Visitor map V01 — review evidence

**State:** technically checked draft; owner visual acceptance pending.

## Preserved reference and scope

The main agent inspected all four immutable approved R01 PNGs at original resolution before drawing. The approved campus master is the direct composition reference; the existing `Sheet` primitives provide the R01 page proportions, typography, palette, rules and title block. All source hashes are recorded and checked by the build.

One map is supplied in SVG, PNG and PDF, with a separate local review page. No floor plan, source model, approved original, production map allocation or published atlas was changed.

## Visual checks

The main agent inspected the full-resolution draft PNG, a rendering of its single PDF page, and the side-by-side browser view. The draft retains the source arrangement and adds only the visitor-oriented wording and symbols documented in SOURCE.json/README.md.

Corrections before presentation:

- Moved the entrance triangle above the highlighted path so it remains visible at Corporate reception.
- Added a restrained P label to each existing parking area and a matching legend entry; unassigned visitor bays remain unassigned.
- Restored the source-supported drop-off label.

The review interface was exercised in six combinations: desktop 1600×1050 and mobile 390×844, each in comparison, draft-only and reference-only mode. No page-width overflow or broken image appeared. Full-width/direct-image views are available because side-by-side thumbnails alone are insufficient for judging detailed labels. Temporary screenshots are kept outside the repository.

## Numerical and artifact checks

`python geospatial/facilities/visitor/validate.py` passes:

- Four approved reference hashes plus source/artifact hashes.
- Four building entrances located on their accepted south facades.
- The highlighted path is contained by the existing walking geometry and crosses no building interior.
- SVG parses; PDF has one page, all extracted text lies within its page bounds, and required labels are present.

Two builds produced byte-identical SVG, PNG and PDF files in the local toolchain. These checks do not establish property tenure, accessibility certification, actual visitor arrangements or human visual approval.

## Next decision

Review the arrival path, building identification and visual continuity in `review.html`. Record any correction against V01. After exact-file acceptance, allocate the map through the existing map register and deliberately integrate its saved assets with the atlas. Do not substitute a later modified draft under an earlier acceptance.
