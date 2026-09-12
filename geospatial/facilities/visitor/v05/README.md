# Sacramento visitor guide V05 — recomposed review draft

[Compare V02 and V05](review.html) · [PNG](artifacts/visitor-map-v05.png) · [PDF](artifacts/visitor-map-v05.pdf) · [SVG](artifacts/visitor-map-v05.svg)

V02 remains the preferred baseline. After the owner rejected the superficial changes in V03/V04, V05 rebuilds the page around a single axonometric campus illustration. The directory moves below the map. Visitor information, site geometry and earlier drafts are preserved.

Buildings use [the existing spatial model](../../spatial/MODEL.json) and [architectural assumptions](../../spatial/ARCHITECTURAL_ASSUMPTIONS.json), including floor heights, parapets and the same proposed facade bay rhythm and perimeter-core exclusions used in the saved elevation studies. These are still modelled concepts, not recovered or approved construction details. The illustration introduces no new windows into the authoritative source; it depicts the existing study's proposals.

Projection is explicit in [SOURCE.json](SOURCE.json). Ground coordinates are transformed together, including tree locations, roads, courts, parking, entrances and the arrival route. The north arrow follows the projected north direction. This view is not to scale for measurement; underlying orthographic plans are unchanged.

## Design references

The actual [Getty visitor guide](https://www.getty.edu/visit/downloads/getty_center_map.pdf), [Salk entrance map](https://www.salk.edu/wp-content/uploads/2017/11/MAPsalk-campus.pdf), and [Wolfson illustrated map](https://klacey.com/portfolio/illustrated-visitor-map-wolfson-college/) were reviewed during this workline. V05 applies the architectural illustration and open composition lessons while retaining Sable Harbor's restrained palette. Third-party artwork is linked, not copied into the repository.

[Source/artifact hashes and geometric records](MANIFEST.json) · [Visual QA](QA.md)

```sh
python geospatial/facilities/visitor/v05/build.py
python geospatial/facilities/visitor/v05/validate.py
```

Status: isolated review draft. Owner visual acceptance, production map-ID allocation and atlas publication remain pending.
