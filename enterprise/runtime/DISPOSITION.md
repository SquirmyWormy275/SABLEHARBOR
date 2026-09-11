# PR119 implementation disposition

Prepared 2026-09-11. Owner-authorized branch work, pending repository acceptance.
This record describes executed implementation, not actual provider or facility operation.
The controlling mandate remains the September 11 PR119 handover.

| Finding | Changed input and consumer | Output / regression evidence | Scope remaining |
|---|---|---|---|
| R119-01 | Original runtime pair; services loader and runtime model | services `runtime.json`; required-field deletion and loader mutation tests | None for source consumption |
| R119-02 | Explicit FAC/ENV/runtime/geo crosswalk | services components and runtime SQLite; ID tests | Actual placements unaccepted |
| R119-03 | Selected provider IDs and draft agreement IDs | counterparty/dependency export; service tests | Legal contracting parties unverified |
| R119-04 | `sync_runtime.py` reads original site source | catalog, parcel, GeoPackage, QGIS/registers; geodesic/idempotence tests | Native QGIS evidence must match candidate |
| R119-05 | Selected states preserved in sync output | geographic census/site register | No tenancy claimed |
| R119-06 | SHI joined to industrial entity source | deed and validation reject parent substitution | None for identity |
| R119-07 | Runtime adjustment adapter integrated in enterprise builder | balanced journals and exact statement bridge | Accepted-event transaction reference covers commitment, deposit, invoice, retention, payment, cancellation and in-service transfer; actual transactions absent |
| R119-08 | Ten cost phases; explicit study/design/commission/reserve costs | monthly/annual requirements; budget/delay tests | Deposit/retention alternatives and cancellation tests implemented; actual negotiated terms absent |
| R119-09 | Separate runtime successor output path/schema | 2026 land overlay and unchanged other 2026 journals verified | Prior releases remain historical |
| R119-10 | Land, CIP, IT, accumulated depreciation and expense accounts | land/CIP no-depreciation tests; conditional IT depreciation | Phase-I component useful lives and conditional transfers modeled separately; no actual plant acceptance |
| R119-11 | Ten staffing pools and productive-time assumptions | 20 proposed technical FTE, separate owned coverage; allocation tests | Phased requirements, 16 headquarters/4 roving allocation, included project lead and specialist bridge; actual qualifications/occupancy gated |
| R119-12 | 39 local records referencing existing CCF IDs/objectives/risks | repository join validation and SQLite local-control table | Actual evidence absent |
| R119-13 | Separate definition/implementation/assessment/evidence fields | synthetic promotion rejection and evidence tests | No operating-effectiveness assertion |
| R119-14 | Common proposed MSA, two orders, schedules A–G | controlled contract PDF; proposed credit calculations/tests | Commercial assumptions and alternative deposit/retention cases reconciled; binding supplier variables gated |
| R119-15 | Causal Boise class sizing, retained provisional 25 kW | 23.6 kW / 3 racks nominal; 28 kW reference maximum exceeds 25 kW; recovery insufficiency tests | Thermal/connector/vendor acceptance not demonstrated |
| R119-16 | Required/verified/evidence independent fields | rejects diversity-as-verification | Actual independent bootstrap/carrier evidence absent |
| R119-17 | Demand, context, retention, hardware, growth and efficiency drivers | workload/retention/context mutations; per-rack packing | IOPS, ingest, AI task mix, recovery service order and unmeasured throughput bounds implemented; measurements gated |
| R119-18 | Separate gross cash and common-scope investment views | terminal timing, no-power-double-charge, four scenarios | Conditional second module/refurbishment and terminal cash modeled; component sensitivity explicitly Phase I only |
| R119-19 | Source-driven room, rack and phase renderers | 12 SVG/PDF/PNG concept plates, inspected | Component-rated UPS/generator/cooling/feeder arithmetic and dimensioned enclosures implemented; licensed engineering gated |
| R119-20 | Phase dependencies plus evidence-bearing temporal state engine | September cutoffs, shell/commission/operation tests | Future events are reference fixtures, not accepted history |
| R119-21 | Thirteen explicit controlled-publication registrations | 13 PDFs, catalog JSON/SQLite and publication manifest | Final release index awaits package acceptance |
| R119-22 | `readiness.json` field-level references with access limits | validated source/gate register in runtime export | Nine public references plus accepted enterprise vendor canon with field-level provenance; actual reports and supplier acceptance gated |
| R119-23 | Separate SOC1 customer-ICFR and SOC2 scope | assurance PDF and provisional native-control mapping | Full authoritative criteria and practitioner scope absent |
| R119-24 | Runtime, finance, security, temporal and integration tests | negative/mutation/funding/recovery/SQLite assertions | Source mutation exercises services, finance, geography, contract cover and catalog; archive tampering tests implemented |
| R119-25 | Services/geo CI consume source; new runtime CI builds actual output | accepted-output digest, workbook reproduction, two financial builds | Exact candidate CI recorded separately |
| R119-26 | Dated reconciliation index and runtime navigation | current branch scope distinguished from pinned history | Runtime reconciliation and release navigation identify current successor and preserved history |
| R119-27 | Boundary policies, six runbooks, executable authorization/deletion | security tests including live held-record denial | OS, database, object storage, identity and lifecycle/configuration schema selected; deployment qualification gated |
| R119-28 | Explicit uncontracted/uninstalled/uncommissioned state | world-state tests reject forecast promotion | September actual operating history remains unknown |

## Acceptance boundary

The implementation resolves the ignored-source defect across service, geographic,
financial, publication and query consumers. The table distinguishes implemented
reference behavior from external evidence needed before actual execution. The
component asset schedule is a Phase-I acceptance sensitivity; later investment
module/refurbishment cash does not become an actual depreciable asset without a
separate accepted cohort. No synthetic test establishes operating effectiveness.

Final repository acceptance requires clean source reproduction, actual candidate
CI, publication review and an immutable indexed release. Keep PR119 draft while
those checks run. The separate external gates in [`readiness.json`](readiness.json)
remain open after a successful design release. They do not authorize fabricated
contracts, funding, personnel, construction or assurance evidence.

The distinct runtime workbook uses local XlsxWriter because Artifact Tool was not
available and its public package returned 404; the owner authorized choosing the
execution environment. Old reviewed Artifact Tool workbook bytes and acceptance
checks are preserved. The tooling substitution is disclosed, not a claim that the
requested Artifact Tool pipeline ran.
