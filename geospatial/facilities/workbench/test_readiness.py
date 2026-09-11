import copy
import json
from pathlib import Path

from readiness import build_readiness


def model():
    return {
        "site_id": "SITE",
        "status": "MODELLED",
        "buildings": [
            {
                "id": "BUILDING",
                "rect_m": [0, 0, 10, 10],
                "core_zones": [{"name": "Lift", "type": "lift", "rect_m": [8, 8, 2, 2]}],
                "floors": [
                    {
                        "id": "FLOOR",
                        "rooms": [
                            {
                                "id": "ROOM",
                                "rect_m": [0, 0, 4, 4],
                                "door": {"x_m": 4, "y_m": 2, "width_m": 1},
                            }
                        ],
                        "circulation_zones": [{"rect_m": [4, 0, 2, 8]}],
                    }
                ],
            }
        ],
        "access": {"service_arrival_m": [[0, 0], [10, 0]], "public_arrival_m": [[5, -2], [5, 2]]},
        "adjacency": [{"a": "A", "b": "B", "relationship": "separate"}],
    }


def run(tmp_path, data):
    source = tmp_path / "geospatial/facilities/source"
    source.mkdir(parents=True, exist_ok=True)
    (source / "test.json").write_text(json.dumps(data))
    result = build_readiness(tmp_path)
    assert len({c["id"] for c in result["checks"]}) == len(result["checks"])
    return {c["id"].split(":")[-1]: c for c in result["checks"]}


def test_door_mutation(tmp_path):
    data = model()
    assert run(tmp_path, data)["door-circulation-access"]["outcome"] == "PASS"
    data["buildings"][0]["floors"][0]["rooms"][0]["door"]["x_m"] = 2
    assert run(tmp_path, data)["door-circulation-access"]["outcome"] == "FAIL"


def test_circulation_disconnection(tmp_path):
    data = model()
    data["buildings"][0]["floors"][0]["circulation_zones"][0]["rect_m"] = [7, 0, 2, 8]
    assert run(tmp_path, data)["door-circulation-access"]["outcome"] == "REVIEW"


def test_missing_geometry_never_passes(tmp_path):
    data = model()
    data["buildings"][0]["floors"][0].pop("circulation_zones")
    assert run(tmp_path, data)["door-circulation-access"]["outcome"] == "NOT_ASSESSED"
    data["buildings"] = []
    assert run(tmp_path, data)["interior-readiness"]["outcome"] == "NOT_ASSESSED"


def test_core_override_mutation(tmp_path):
    data = model()
    building = data["buildings"][0]
    building["floors"][0]["core_zones"] = copy.deepcopy(building["core_zones"])
    assert run(tmp_path, data)["fixed-core-stacking"]["outcome"] == "PASS"
    building["floors"][0]["core_zones"][0]["rect_m"][0] = 7
    assert run(tmp_path, data)["fixed-core-stacking"]["outcome"] == "FAIL"


def test_overlap_mutation(tmp_path):
    data = model()
    data["buildings"].append({"id": "OTHER", "rect_m": [9, 0, 10, 10], "floors": []})
    assert run(tmp_path, data)["building-separation"]["outcome"] == "FAIL"


def test_loading_crossing_review(tmp_path):
    data = model()
    assert run(tmp_path, data)["service-pedestrian-crossings"]["outcome"] == "REVIEW"
    data["access"]["public_arrival_m"] = [[15, -2], [15, 2]]
    assert run(tmp_path, data)["service-pedestrian-crossings"]["outcome"] == "PASS"


def test_labels_cannot_certify_accessibility_or_egress(tmp_path):
    checks = run(tmp_path, model())
    assert checks["accessibility-evidence"]["outcome"] == "NOT_ASSESSED"
    assert checks["egress-engineering"]["outcome"] == "NOT_ASSESSED"


def test_repository_consumption_is_deterministic():
    root = Path(__file__).resolve().parents[3]
    a = build_readiness(root)
    assert a == build_readiness(root)
    assert a["checks"] and a["summary"]["engineering_certified"] is False
    assert "geospatial/facilities/RUNTIME_BRIDGE.json" in a["source_sha256"]
