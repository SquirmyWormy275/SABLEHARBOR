# Time, ownership and operating state

The package has two time axes: when a fact applies in the world, and when the database records it. `valid_from` / `valid_to` form half-open effective intervals. `recorded_at` / `superseded_at` preserve the recording history. `source_effective_date` and `world_state_date` are separate, so a GIS download on 6 September 2026 does not imply a corporate acquisition on that day.

The release's narrative snapshot is 5 September 2026. Source material giving only a year remains year precision. It is represented as earliest/latest bounds, with exact date fields null. A null start date is unknown, not existence since the beginning of time. The query functions in `scripts/model.py` return `CERTAIN`, `POSSIBLE`, `ABSENT` or `UNKNOWN`; normal filters return only certain membership unless the caller explicitly requests uncertainty.

Ownership, operation, hosting, leasing and access rights are independent fields. A known operator does not fill `owner_entity`. A corporate transaction does not prove title to every real parcel touched by a study envelope. The July 18, 2025 Red Wash acquisition date is retained independently of the unresolved mine coordinate.

Four initial asset-state records demonstrate the model: historical Evalon, current Willow, historical Emberline and the dedicated Red Wash operator. Evalon and Willow year bounds refer to institutional/operating history, not exact building occupancy. They must not be used to backdate a Hazelwood lease. The entity table records current organizational roles; it is not an all-period corporate family tree without dated relationship evidence.

Tests exercise year precision, unknown starts, half-open transfers and disposal. Synthetic network/test points stay inside test fixtures and are never exported as geographic canon.


## Approved Klein/Fort occupancy successor

The [owner-approved September 13 decision](../../docs/canon/KLEIN_FORT_OCCUPANCY_2026-09-13.md) resolves the narrow continuity question. Historical initial states retain their original source and recording times and are superseded at the successor's recording timestamp. New occupancy states derive from explicit approval, not institutional founding: the old shop's uncertain exit and the Fort's uncertain entry both lie in `[2024-01-01, 2025-01-01)`. Exact start/end days and real property rights remain null.

`geospatial.chronology.continuity.occupancy_at(day, known_at=None)` provides a current-knowledge query and an optional recording-time cutoff. Before the approval was recorded, that new history is unknown. During 2024 occupancy is possible at either site; after the year boundary the old shop is absent and the Fort is certain under the accepted continuing-state model. The 2021 lease observation remains separately sourced.
