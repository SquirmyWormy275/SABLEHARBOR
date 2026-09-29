"""The finite synthetic geography scope reconciles without erasing limits."""

import json
from pathlib import Path

from geospatial.successor_20260929 import source_delta as prior_delta
from geospatial.successor_20260929_final import source_delta as final_delta

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((ROOT / path).read_text())


def test_accepted_source_intervals_are_contiguous_and_complete():
    prior = prior_delta.build()
    final = final_delta.build()
    assert prior["through_accepted_main"] == final["from_accepted_main"]
    assert final["through_accepted_main"] == "bcdf3ade1d83d04774da9a914deb269442ee52f6"
    assert prior["summary"]["changed_paths"] == 83
    assert prior["summary"]["changed_controlling_canon"] == 1
    assert final["summary"]["changed_paths"] == 18
    assert final["summary"]["changed_controlling_canon"] == 0
    baseline = load("geospatial/finalization/SOURCE_REVIEW.json")
    assert baseline["cumulative_reviewed_carriers"] == 78145
    assert baseline["remaining_baseline_carriers"] == 0


def test_synthetic_engineering_scope_does_not_promote_external_claims():
    interface = load("geospatial/engineering_review/interface_successor_20260929/register.json")
    history = load("geospatial/successors/rail_history_2026_09_29/report.json")
    finance = load("industrial/successors/rail_2026_09_29/reperform-result.json")
    assert interface["corrected_route_miles"]["total"] == 40
    assert interface["population"]["facilities"] == 12
    assert interface["population"]["track_register"] == 31
    assert interface["population"]["structures"] == 26
    assert interface["population"]["proposed_turnout_interfaces"] == 8
    assert interface["population"]["real_trackage_rights_geometries"] == 0
    assert all(not site["proposed_lead_in_service"] for site in interface["site_interfaces"])
    assert all(
        row["hardware_number_or_frog_angle"] is None
        and not row["flangeway_and_vehicle_swept_envelope_verified"]
        for row in interface["proposed_turnout_interfaces"]
    )
    assert all(
        not row["hydraulic_capacity_verified"]
        and not row["field_clearance_or_load_rating_verified"]
        for row in interface["structure_design_boundaries"]
    )
    assert all(
        row["external_client_parcel_or_footprint_id"] is None
        for row in interface["external_client_endpoints"]
    )
    assert history["accepted_history_preserved"]["1898_extent_miles"] is None
    assert history["accepted_history_preserved"]["1954_recovered_geometry"] is None
    assert history["accepted_history_preserved"]["real_title_or_right_of_way_instrument"] is None
    assert history["current_operating_asset_count_added"] == 0
    assert history["real_property_instrument_count_added"] == 0
    assert finance["planning_months"] == 180
    assert len(finance["forecast_datasets"]) == 13
    assert finance["modeled_journal_cash_tax_delta_usd"] == 0
