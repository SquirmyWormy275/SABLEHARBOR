import importlib.util
import json
import shutil
from pathlib import Path

from access import build_access

ROOT = Path(__file__).resolve().parents[3]


def fixture(tmp_path):
    for name in ("source/campus.json", "spatial/ACCESS_POLICY.json"):
        dst = tmp_path / "geospatial/facilities" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "geospatial/facilities" / name, dst)
    return tmp_path / "geospatial/facilities/source/campus.json"


def mutate(path, fn):
    data = json.loads(path.read_text())
    fn(data)
    path.write_text(json.dumps(data))


def test_reviewed_routes():
    result = build_access(ROOT)
    assert result["summary"]["verified_routes"] == 21
    assert result["summary"]["reviewed_floors"] == 6
    assert result["summary"]["failures"] == 0
    assert all(s["verified"] for r in result["routes"] for s in r["segments"])
    assert all(len(r["door_ids"]) == 2 for r in result["routes"])
    assert {r["classification"] for r in result["campus_routes"]} == {
        "public",
        "staff",
        "J2",
        "residential",
        "service",
    }
    assert result == build_access(ROOT)


def test_changed_door_fails(tmp_path):
    path = fixture(tmp_path)
    mutate(path, lambda s: s["buildings"][0]["floors"][0]["rooms"][0]["door"].update(x_m=1))
    assert build_access(tmp_path)["summary"]["failures"] > 0


def test_missing_intermediate_door_fails(tmp_path):
    path = fixture(tmp_path)
    mutate(path, lambda s: s["buildings"][0]["floors"][0]["rooms"][12].pop("door"))
    assert build_access(tmp_path)["summary"]["failures"] > 0


def test_changed_intermediate_geometry_fails(tmp_path):
    path = fixture(tmp_path)
    mutate(path, lambda s: s["buildings"][0]["floors"][0]["rooms"][12].update(rect_m=[9, 9, 1, 1]))
    assert build_access(tmp_path)["summary"]["failures"] > 0


def test_security_transition_fails(tmp_path):
    path = fixture(tmp_path)
    mutate(path, lambda s: s["buildings"][0]["floors"][0]["rooms"][12].update(access="audit"))
    result = build_access(tmp_path)
    assert any("assurance" in error for r in result["routes"] for error in r["errors"])


def test_missing_floor_door_fails(tmp_path):
    path = fixture(tmp_path)
    mutate(path, lambda s: s["buildings"][0]["floors"][0].update(doors=[]))
    assert build_access(tmp_path)["summary"]["failures"] > 0


def test_readiness_consumes_validation(tmp_path):
    path = fixture(tmp_path)
    spec = importlib.util.spec_from_file_location(
        "access_readiness_test", ROOT / "geospatial/facilities/workbench/readiness.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    a = module.build_readiness(tmp_path)
    check = next(
        c for c in a["checks"] if c["id"] == "SH-READY:SH-SITE-0001-A-L01:door-circulation-access"
    )
    assert check["outcome"] == "PASS" and len(check["evidence"]["validated_indirect_routes"]) == 4
    mutate(path, lambda s: s["buildings"][0]["floors"][0]["rooms"][12].update(access="private"))
    a = module.build_readiness(tmp_path)
    assert next(c for c in a["checks"] if c["id"] == check["id"])["outcome"] == "FAIL"
