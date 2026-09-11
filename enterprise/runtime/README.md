# Runtime estate implementation

Version 1.0.0 development package for PR #119. **Owner-authorized, pending merge;
synthetic design, not an operating estate.** The September 11 source pair under
`enterprise/services/source/runtime_*.json` controls this layer. The six legacy
service inputs retain their original comparison scope and source locks.

```bash
python -m enterprise.runtime.model validate
python -m enterprise.runtime.model build --output /tmp/runtime-review
python -m unittest discover -s enterprise/runtime/tests -v
python -m enterprise.services.model validate --repository-root .
uv run python geospatial/scripts/sync_runtime.py
uv run python geospatial/scripts/build_geopackage.py
```

`model.py` consumes and validates the original runtime records, decorates the
service dependency graph, exports explicit state and reconstructs effective versus
recorded knowledge. `planning.py` derives host counts, accelerator memory and
throughput constraints, storage copies, rack limits, power, workforce and phased
gross cash requirements. `security.py` is a deterministic authorization, deletion,
evidence and SLA reference. It is not deployed IAM or an assurance opinion.

The current service export adds `runtime.json`. Its legacy comparison remains a
historical alternative analysis; it does not become the runtime investment case.
Geographic IDs SH-SITE-0028/0029/0030 identify the new facilities; SH-SITE-0016 stays
the Alexandria hosting concept. Provider coordinates remain unverified regional
constraints. The owned parcel is a 7.5-acre synthetic metric envelope, independently
checked on the WGS84 ellipsoid.

## Source and output contract

The runtime schema is a separate adapter, not an extension of the old 60-month
schema. An entirely absent source pair permits an explicit legacy-only fixture;
one missing file fails. Site fields are explicitly allowlisted; no unrecognized
site fields silently become accepted exports. Repository validation joins SHI to
the existing LLC. Current schema permits design records only; future operational
events require an independently versioned evidence-bearing successor.

The runtime JSON includes inherited scenario envelopes, newly derived capacity,
phases, workforce and gross unfunded monthly/annual finance views. Land appears
once in a balanced reconciliation overlay against unresolved settlement clearing.
Clearing is not a fabricated loan, cash payment or accepted payable. The separate `build_finance` adapter posts the dated land overlay and conditional 2027–2031 requests through consolidated enterprise statements, with an exact predecessor bridge and existing finite Treasury limits.

Required costs are not authorized hires or funds. Run `uv run python -m enterprise.runtime.build_finance` from clean source for the integrated successor. Existing ESS 48/54 conditional
occupancy and J2's 237-billet establishment remain unchanged. Conservative reuse
and displaced-cost credits are zero. Gross technical capacity is 20 proposed FTE;
owned operation adds two facilities positions and six proposed guard positions for
one continuous security seat. Qualified alternates and a roster still gate operation.

## Design records

- [Calculated capacity, engineering, finance and recovery register](docs/MODEL_RESULTS.md)
- [Contract baseline and schedules](docs/CONTRACT_DOSSIER.md)
- [Runtime architecture and operational procedures](docs/ARCHITECTURE_AND_RUNBOOKS.md)
- [Assurance scope and evidence boundary](docs/ASSURANCE_SCOPE.md)

The controlled publications, integrated posting bridge and concept drawings are implemented. See `DISPOSITION.md` for the handover finding-by-finding scope and acceptance evidence; `readiness.json` contains the separately blocked external evidence gates. Selected platform versions, component-rated concepts and construction accounting reference cases remain synthetic design; actual qualification and execution are typed readiness gates.

## Query and review

`python -m enterprise.runtime.model build --output /tmp/runtime-review --database` adds an explicitly allowlisted SQLite query surface: `runtime_site`, `capacity`, `annual_cash`, `local_control`, and `source_identity`. No dynamic source fields become SQL columns. `uv run python -m enterprise.runtime.render --output enterprise/runtime/visuals` builds editable SVGs and PDF/PNG concept plates. `uv run python -m enterprise.runtime.workbook --output enterprise/runtime/publications` authors the distinct local-tooling workbook after integrated finance; older Artifact Tool publications remain unchanged.
