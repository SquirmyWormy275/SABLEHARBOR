"""Build a separate fictional early-rail map without changing recovered history."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pyproj import Geod

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
GEOD = Geod(ellps="WGS84")
METRES_PER_MILE = 1609.344


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def miles(coords: list[list[float]]) -> float:
    return sum(GEOD.inv(*a, *b)[2] for a, b in zip(coords, coords[1:])) / METRES_PER_MILE


def render_svg(survivor: list[list[float]], abandoned: list[list[float]], lengths: dict) -> bytes:
    # A fixed local display frame avoids suggesting a cadastral or survey map.
    west, east, south, north = -108.19, -107.94, 41.47, 41.70
    left, top, width, height = 95, 125, 790, 600

    def xy(point: list[float]) -> tuple[float, float]:
        return (
            left + (point[0] - west) / (east - west) * width,
            top + (north - point[1]) / (north - south) * height,
        )

    def path(coords: list[list[float]]) -> str:
        return " ".join(
            ("M" if i == 0 else "L") + f"{xy(p)[0]:.2f},{xy(p)[1]:.2f}"
            for i, p in enumerate(coords)
        )

    junction = xy(survivor[0])
    fork = xy(abandoned[0])
    west_point = xy(survivor[-1])
    coal = xy(abandoned[-1])
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1180 820" role="img" aria-labelledby="title desc">
<title id="title">BS&amp;T coal-era fictional alignment case</title>
<desc id="desc">Provisional newly authored 1954 survivor and abandoned mine-only alignment. No recovered survey or real right of way.</desc>
<rect width="1180" height="820" fill="#f5f2eb"/>
<text x="72" y="62" font-family="sans-serif" font-size="27" font-weight="700" fill="#183445">BS&amp;T coal-era alignment case</text>
<text x="72" y="92" font-family="sans-serif" font-size="15" fill="#415865">Provisional fictional placement · authored 29 Sep 2026 · 1954 rescue-stage illustration</text>
<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="#fffefa" stroke="#9ca9aa"/>
<path d="{path(survivor)}" fill="none" stroke="#126f77" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
<path d="{path(abandoned)}" fill="none" stroke="#a55a36" stroke-width="6" stroke-dasharray="12 8" stroke-linecap="round"/>
<circle cx="{junction[0]:.2f}" cy="{junction[1]:.2f}" r="8" fill="#183445"/>
<circle cx="{fork[0]:.2f}" cy="{fork[1]:.2f}" r="7" fill="#183445"/>
<circle cx="{west_point[0]:.2f}" cy="{west_point[1]:.2f}" r="7" fill="#126f77"/>
<circle cx="{coal[0]:.2f}" cy="{coal[1]:.2f}" r="7" fill="#a55a36"/>
<g font-family="sans-serif" font-size="14" fill="#183445">
 <text x="{junction[0] - 175:.2f}" y="{junction[1] - 18:.2f}">Wamsutter later anchor</text>
 <text x="{west_point[0] + 12:.2f}" y="{west_point[1] + 4:.2f}">fictional west service point</text>
 <text x="{coal[0] + 12:.2f}" y="{coal[1] - 14:.2f}">fictional coal works</text>
</g>
<rect x="916" y="126" width="225" height="445" rx="10" fill="#e6ece9"/>
<g font-family="sans-serif" fill="#183445">
 <text x="936" y="161" font-size="18" font-weight="700">Evidence boundary</text>
 <text x="936" y="195" font-size="14">1898 extent: unknown</text>
 <text x="936" y="220" font-size="14">1954 source: 14–16 mi</text>
 <text x="936" y="245" font-size="14">Surveyed line: unknown</text>
 <text x="936" y="270" font-size="14">Real ROW: not supplied</text>
 <path d="M938 309 L981 309" stroke="#126f77" stroke-width="6"/>
 <text x="938" y="339" font-size="14">Case survivor</text>
 <text x="938" y="360" font-size="14">{lengths["survivor"]:.3f} miles</text>
 <path d="M938 397 L981 397" stroke="#a55a36" stroke-width="6" stroke-dasharray="10 6"/>
 <text x="938" y="427" font-size="14">Case abandoned</text>
 <text x="938" y="448" font-size="14">{lengths["abandoned"]:.3f} miles</text>
 <text x="938" y="499" font-size="13">Not a current asset,</text>
 <text x="938" y="518" font-size="13">construction plan, or</text>
 <text x="938" y="537" font-size="13">property-right record.</text>
</g>
<text x="72" y="780" font-family="sans-serif" font-size="13" fill="#415865">Coordinates are invented scenario anchors. This plate is not a recovered map; the accepted source-evidence history remains unlocated.</text>
</svg>
"""
    return svg.encode()


def build() -> dict[str, bytes]:
    source = json.loads((HERE / "source.json").read_text())
    if (
        source["schema_version"] != "1.1"
        or source["supersedes_source_sha256"]
        != "33dcadb3c185d5c07125d92af9b3cea3bed6585b610f480d5cbf66214db78deb"
        or source["prior_source_accepted_commit"] != "bcdf3ade1d83d04774da9a914deb269442ee52f6"
        or source["prior_source_repository_available_at_utc"] != "2026-09-29T15:22:18Z"
        or "#107B" not in source["authority"]
        or "#108B" in source["authority"]
        or source["state"] != "PROVISIONAL_DERIVED_SYNTHETIC_HISTORY_CASE"
        or source["repository_available_at"] is not None
        or source["repository_accepted_at"] is not None
        or source["selection"]["use"] != "SELECTED_FOR_SEPARATE_FICTIONAL_HISTORY_CASE_MAP_ONLY"
        or source["selection"]["historical_evidence_state"] != "NOT_RECOVERED"
        or source["selection"]["current_operating_network_effect"] != "NONE"
        or source["selection"]["finance_tax_cash_effect"] != "NONE"
        or source["selection"]["property_right_effect"] != "NONE"
        or set(source["selection"].values())
        & {"RECOVERED_SURVEY", "REAL_RIGHT_OF_WAY", "CURRENT_OPERATING_ASSET"}
    ):
        raise ValueError("Historical case authority or availability changed")
    for relative, expected in source["input_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"Changed pinned input: {relative}")
    candidate_source = json.loads(
        (
            ROOT / "geospatial/engineering_review/historical_alignment_2026_09_29/source.json"
        ).read_text()
    )
    candidate = json.loads(
        (
            ROOT / "geospatial/engineering_review/historical_alignment_2026_09_29/candidate.geojson"
        ).read_text()
    )
    accepted = json.loads((ROOT / "industrial/source/operations.json").read_text())
    epochs = {r["epoch"]: r for r in accepted["geography"]["historical_route_epochs"]}
    evidence = source["accepted_history_preserved"]
    if (
        evidence["1898_extent_miles"] is not None
        or evidence["1898_surveyed_geometry"] is not None
        or evidence["1954_recovered_geometry"] is not None
        or evidence["abandoned_recovered_geometry"] is not None
        or evidence["real_title_or_right_of_way_instrument"] is not None
        or epochs["1898"]["route_miles"] is not None
        or epochs["1954"]["route_miles"] is not None
        or evidence["1954_survivor_source_range_miles"]
        != [
            epochs["1954"]["surviving_route_miles_low"],
            epochs["1954"]["surviving_route_miles_high"],
        ]
        or source["historical_time_interpretation"]["abandonment_date"] is not None
        or source["historical_time_interpretation"]["survivor_retirement_date"] is not None
        or source["historical_time_interpretation"]["1953_parent_failure"] != "YEAR_PRECISION_ONLY"
        or source["historical_time_interpretation"]["1954_rescue"]
        != "1954-07-01_SYNTHETIC_ACCEPTED_EVENT"
        or source["historical_time_interpretation"]["1968_modern_main_completion"]
        != epochs["1968"]["effective_date"]
    ):
        raise ValueError("Accepted historical uncertainty or date precision changed")
    if (
        candidate_source["hypothesis"]["scenario_id"]
        != source["selection"]["candidate_scenario_id"]
        or len(candidate["features"]) != 2
        or {f["id"] for f in candidate["features"]}
        != {"HYP-BST-1954-SURVIVOR", "HYP-BST-MINE-ONLY-ABANDONED"}
    ):
        raise ValueError("Selected provisional candidate differs")
    by_id = {f["id"]: f for f in candidate["features"]}
    survivor = by_id["HYP-BST-1954-SURVIVOR"]["geometry"]["coordinates"]
    abandoned = by_id["HYP-BST-MINE-ONLY-ABANDONED"]["geometry"]["coordinates"]
    if (
        survivor[0] != accepted["geography"]["wamsutter_junction_lon_lat"]
        or abandoned[0] not in survivor
        or not 14 <= miles(survivor) <= 16
        or not 20 <= miles(survivor) + miles(abandoned) <= 24
        or any(f["properties"].get("accepted_geometry") is not None for f in candidate["features"])
    ):
        raise ValueError("Fictional geometry conflicts with accepted historical bounds")
    lengths = {"survivor": miles(survivor), "abandoned": miles(abandoned)}
    features = []
    for feature, role in [
        (by_id["HYP-BST-1954-SURVIVOR"], "ILLUSTRATIVE_1954_SURVIVOR"),
        (by_id["HYP-BST-MINE-ONLY-ABANDONED"], "ILLUSTRATIVE_ABANDONED_MINE_ONLY"),
    ]:
        features.append(
            {
                "type": "Feature",
                "id": feature["id"],
                "geometry": feature["geometry"],
                "properties": {
                    "history_case_record_id": source["record_id"],
                    "candidate_source_id": candidate_source["record_id"],
                    "scenario_id": source["selection"]["candidate_scenario_id"],
                    "role": role,
                    "fact_state": source["state"],
                    "event_or_snapshot_date": "1954-07-01"
                    if role == "ILLUSTRATIVE_1954_SURVIVOR"
                    else None,
                    "exact_abandonment_date": None,
                    "continuous_operating_interval": None,
                    "accepted_recovered_geometry": None,
                    "real_title_or_right_of_way": None,
                    "current_asset_id": None,
                    "current_operating_effect": "NONE",
                },
            }
        )
    geojson = {"type": "FeatureCollection", "features": features}
    report = {
        "record_id": source["record_id"],
        "source_schema_version": source["schema_version"],
        "supersedes_source_sha256": source["supersedes_source_sha256"],
        "prior_source_accepted_commit": source["prior_source_accepted_commit"],
        "prior_source_repository_available_at_utc": source[
            "prior_source_repository_available_at_utc"
        ],
        "attribution_correction": source["attribution_correction"],
        "state": source["state"],
        "authored_at_utc": source["authored_at_utc"],
        "repository_available_at": None,
        "source_sha256": digest(HERE / "source.json"),
        "input_sha256": source["input_sha256"],
        "candidate_scenario_id": source["selection"]["candidate_scenario_id"],
        "lengths_miles": lengths,
        "illustrative_prefailure_total_miles": sum(lengths.values()),
        "accepted_history_preserved": evidence,
        "snapshot_dispositions": [
            {"date": "1898-04-06", "recovered_linework": 0, "illustrative_linework": 0},
            {"date": "1954-07-01", "recovered_linework": 0, "illustrative_linework": 1},
            {
                "date": "1968-10-14",
                "recovered_linework": 0,
                "illustrative_linework": 0,
                "modern_route_source_separate": True,
            },
        ],
        "current_operating_asset_count_added": 0,
        "finance_tax_cash_delta_usd": 0,
        "real_property_instrument_count_added": 0,
        "limits": [
            "The source-evidence view of 1898, 1954 and abandoned geometry remains unlocated.",
            "This separate map case selects authored coordinates for an illustrative historical fiction, not a recovered survey or real property right.",
            "The 1954 date is the rescue event/snapshot, not proof of full-line commencement or continuous operation; abandonment and retirement days remain unknown.",
            "No modern route, milepost, operating forecast, legal right or financial release changes.",
        ],
    }
    outputs = {
        "case.geojson": encoded(geojson),
        "report.json": encoded(report),
        "case.svg": render_svg(survivor, abandoned, lengths),
    }
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build()
    for name, raw in outputs.items():
        path = HERE / name
        if args.check:
            if path.read_bytes() != raw:
                raise ValueError(f"Stale historical case output: {name}")
        else:
            path.write_bytes(raw)
    print("PASS separate provisional historical case", len(outputs), "outputs")


if __name__ == "__main__":
    main()
