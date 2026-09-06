"""Tests target real failure modes: false dates, broken networks and lossy exports."""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

import pytest
from shapely.geometry import LineString,Point,mapping

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/"scripts"))
from model import temporal_membership,state_filter,network_errors,GEOD
from build_geopackage import build,digest
from validate_geospatial import validate


def test_year_precision_does_not_become_exact_day():
    r={"earliest_start":"2022-01-01","latest_start":"2022-12-31"}
    assert temporal_membership(r,"2021-12-31")=="ABSENT"
    assert temporal_membership(r,"2022-06-01")=="POSSIBLE"
    assert temporal_membership(r,"2023-01-01")=="CERTAIN"
    assert state_filter([r],"2022-06-01")==[]


def test_unknown_start_is_not_perpetual_existence():
    r={"snapshot_as_of":"2026-09-05"}
    assert temporal_membership(r,"2018-01-01")=="UNKNOWN"
    assert temporal_membership(r,"2026-09-05")=="CERTAIN"


def test_half_open_ownership_and_disposal():
    rows=[{"valid_from":"2018-01-01","valid_to":"2020-01-01","owner_entity":"A"},{"valid_from":"2020-01-01","disposed_on":"2025-01-01","owner_entity":"B"}]
    assert state_filter(rows,"2020-01-01",owner="A")==[]
    assert len(state_filter(rows,"2020-01-01",owner="B"))==1
    assert state_filter(rows,"2025-01-01",owner="B")==[]


def fixture():
    # Deliberately isolated test geometry; not exported to any canon layer.
    nodes=[{"type":"Feature","geometry":mapping(Point(x,40)),"properties":{"feature_id":n}} for n,x in [("a",-110),("b",-109.99),("c",-109.98),("d",-109.97)]]
    line=LineString([(-110,40),(-109.995,40.001),(-109.99,40)])
    segments=[{"type":"Feature","geometry":mapping(line),"properties":{"feature_id":"s1","from_node_id":"a","to_node_id":"b","owner_entity":"TEST_OWNER","operator_entity":"TEST_OPERATOR","geometry_miles":GEOD.geometry_length(line)/1609.344}}]
    route={"route_id":"r","origin_node":"a","destination_node":"b","segment_ids":["s1"]}
    return nodes,segments,[route]


def test_network_accepts_connected_owned_route():
    assert not network_errors(*fixture())


@pytest.mark.parametrize("mutation",["gap","missing_owner","bad_length","duplicate","disconnected"])
def test_network_rejects_material_errors(mutation):
    nodes,segments,routes=fixture()
    if mutation=="gap":segments[0]["properties"]["to_node_id"]="c"
    if mutation=="missing_owner":segments[0]["properties"]["owner_entity"]=None
    if mutation=="bad_length":segments[0]["properties"]["geometry_miles"]=40
    if mutation=="duplicate":
        x=copy.deepcopy(segments[0]);x["properties"]["feature_id"]="s2";segments.append(x)
    if mutation=="disconnected":
        x=copy.deepcopy(segments[0]);x["geometry"]=mapping(LineString([(-109.98,40),(-109.97,40)]));x["properties"].update(feature_id="s2",from_node_id="c",to_node_id="d",geometry_miles=None);segments.append(x);routes[0]["segment_ids"].append("s2")
    assert network_errors(nodes,segments,routes)


def test_source_pin_is_not_current_canonical_mine():
    c=json.loads((BASE/"sources/catalog.json").read_text())
    mine=next(x for x in c["objects"] if x["object_id"]=="SH-SITE-0006")
    assert mine["canon_status"]=="CANON_SITED"
    anchor=json.loads((BASE/"geojson/red_wash_anchor.geojson").read_text())["features"][0]
    assert anchor["geometry"]["coordinates"]==[-108.18,42.22]
    assert anchor["properties"]["horizontal_accuracy_m"] is None
    claims=json.loads((BASE/"geojson/source_claim_points.geojson").read_text())["features"]
    assert all(x["properties"]["canon_status"]=="HISTORICAL" for x in claims)


def test_selected_route_is_connected_and_never_backdated_to_2025():
    c=json.loads((BASE/"sources/catalog.json").read_text())
    nodes=json.loads((BASE/"geojson/rail_nodes.geojson").read_text())["features"]
    segments=json.loads((BASE/"geojson/rail_network.geojson").read_text())["features"]
    assert len(segments)==1
    assert not network_errors(nodes,segments,c["rail_routes"])
    assert all(s["properties"]["canon_status"]=="PROPOSED" for s in segments)
    assert all(temporal_membership(s["properties"],"2025-12-31")=="UNKNOWN" for s in segments)


def test_formation_profile_is_distinct_from_ground_and_satisfies_screening_limits():
    r=json.loads((BASE/"reports/RAIL_CANDIDATE_COMPARISON.json").read_text())
    c=next(x for x in r["candidates"] if x["candidate_id"]=="TAYLOR-C")
    assert 35<c["legacy_corridor"]["geometry_miles"]<45
    for key in ["legacy_corridor","mine_connector"]:
        m=c[key];v=m["vertical_design"]
        assert v["status"]=="FEASIBLE_PRELIMINARY_PROFILE"
        assert v["maximum_design_grade_pct"]<=1.80001
        assert m["maximum_sampled_ground_grade_pct"]>v["maximum_design_grade_pct"]
        assert m["minimum_sampled_plan_radius_m"]>300
        assert m["waterbody_intersection_length_m"]<.01


def test_geopackage_rebuild_is_byte_deterministic():
    with tempfile.TemporaryDirectory() as td:
        a=build(Path(td)/"a.gpkg");b=build(Path(td)/"b.gpkg")
        assert digest(a)==digest(b)==digest(BASE/"master/sable_harbor_master_v0.1.gpkg")


def test_full_independent_readback():
    result=validate(write=False)
    assert result["errors"]==[]
    assert not result["program_complete"]
    assert result["rail_engineering_status"]=="PRELIMINARY_PROPOSAL_TOPOLOGY_AND_PROFILE_VALIDATED"


def test_approved_no_mine_spur_is_enforced():
    segments=json.loads((BASE/"geojson/rail_network.geojson").read_text())["features"]
    assert {s["properties"]["feature_id"] for s in segments}=={"BST-SEG-001"}
    policy=json.loads((BASE/"sources/APPROVED_OPERATING_DECISIONS_20260906.json").read_text())
    assert policy["red_wash_logistics"]["mine_spur"] is False
    assert policy["acquisition"]["close_date"]=="2026-01-07"
    assert (BASE/"history/superseded_mine_connector.geojson").exists()
