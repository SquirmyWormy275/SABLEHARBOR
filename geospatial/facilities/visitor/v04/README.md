# Sacramento visitor guide V04 — reference-informed review draft

[Compare V02 and V04](review.html) · [PNG](artifacts/visitor-map-v04.png) · [PDF](artifacts/visitor-map-v04.pdf) · [SVG](artifacts/visitor-map-v04.svg)

V02 is the owner's preferred baseline; V03 was not the preferred direction. V04 retains V02 wording and cool neutral palette. Building symbols use the saved footprints, modelled floor counts and floor heights to give the map restrained depth. No architectural facade details or new physical features are introduced.

Ground coordinates are unchanged. Roof offsets are drawing conventions for the oblique building symbols, not shifted footprints. Ground-plane scale applies to the site layout. Previous versions and approved originals are preserved.

## References actually inspected

- [Salk Institute entrance and parking map](https://www.salk.edu/wp-content/uploads/2017/11/MAPsalk-campus.pdf): simple building depth and clear reception routing.
- [Getty Center Map and Highlights](https://www.getty.edu/visit/downloads/getty_center_map.pdf): recognizable building volumes distinct from directory labels.
- [Stanford self-guided tour map](https://visit.stanford.edu/pdf/explore-campus/general_campus_self-guided_tour_map.pdf): route and destination hierarchy.
- [Kati Lacey / Wolfson College](https://klacey.com/portfolio/illustrated-visitor-map-wolfson-college/): reviewed as an expressive comparator; cartoon people, wildlife and textures not adopted.

These are aesthetic references, not corporate canon. Their images were inspected locally and are not redistributed in this repository. Pentagram's Cornell Tech case study was read, but image retrieval returned HTTP 403; no claim is made that its photographs were inspected.

[Source and projection](SOURCE.json) · [Hashes and mass reconciliation](MANIFEST.json) · [QA](QA.md)

```sh
python geospatial/facilities/visitor/v04/build.py
python geospatial/facilities/visitor/v04/validate.py
```

This is an isolated visual-review draft. Production map allocation and atlas publication remain pending owner acceptance.
