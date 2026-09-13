# Geographic history and source review

The chronology turns accepted dates into a usable historical record: 72 events and observations, 34 corporate site/component histories, and an offline timeline with dated railway views. It includes 18 existing corporate/railway events, 12 facility openings, 26 structure construction years, 14 safety events and two directly bound site observations.

The original shop's **2021 lease observation** is bound to both its narrative heading and lease sentence. This is stronger evidence than the previous generic 2020–2022 programme label, but still does not establish exact occupancy endpoints. The [Klein/Fort continuity proposal](CONTINUITY_PROPOSAL.md) supplies a reviewable choice for the missing fictional history. It is expressly excluded from accepted events and geometry.

## Use and reproduce

The [geographic release index](../../docs/releases/GEOGRAPHIC_EVIDENCE_RELEASES.md) supplies the full versioned package. Open `chronology/history.html` after extraction. Timeline filters, source inspection, CSV export, site histories and route-date controls work offline. External source links are optional; exact source excerpts travel in the embedded data and JSON.

```bash
uv run python -m geospatial.chronology.build --output var/history-preview
uv run python -m geospatial.chronology.operations_review --output var/history-review
```

Sources are pinned to accepted commit `9cc0d2a5c31700dcd166ef9acf1dd284bddb6e8d`; older primary references retain their original commits. Each event identifies its source bytes, locator, exact record, original date precision and stable object links. Corporate date metadata absent from a short primary quote is separately bound to its accepted catalog record. The ARU acquisition date is checked against `entities.json#/entities/4/ownership_effective_on`, correcting the previous indirect locator in the derived event record without rewriting the archived catalog.

The route view uses the three accepted route intervals and five existing segment geometries. The 1898 and 1954 views explicitly have no sourced alignment. Facilities' opening dates and structures' construction years do not project current footprints or modern alignments backward in time. Safety events stay unlocated unless their source supplies an exact asset link.

## Industrial operations discovery review

`OPERATIONS_REVIEW.csv.gz` classifies all **295** discovery occurrences in the hash-pinned baseline operations source. Every leaf value must equal its exact JSON pointer. Containing records, stable asset links and temporal/precision qualifications remain attached. Distinct contract allocations are preserved even when they mention the same facility. Mobile equipment, staffing and capacity language do not become new geographic assets.

Together with the three prior disjoint batches, this gives **69,479 classified discovery carriers**, leaving **8,666** outside those four batches. This is not full semantic review of every field in all 919 sources, nor review of every subsequent source delta. The original three-batch residual table in the predecessor review edition retains its 8,961 records; the new operations table supplies the additional 295 dispositions without rewriting that historical edition.

`OPERATIONS_REVIEW.json` records source and output hashes and disposition counts. Tests compare the committed review output with a fresh extraction, reject source mismatches, preserve year uncertainty and verify the historical route boundary. Browser checks exercise light/dark themes, mobile/desktop widths, filtering, exact route-opening boundaries, record details and exported CSV.

## Remaining decisions

#106 still requires an accepted shop/Fort continuity decision. #108 still has broader semantic, occupancy and historical geometry requirements. Proposed history must pass through a controlling accepted decision before appearing as fact in this viewer. A visually complete timeline is not evidence that missing history is known.
