import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "facility_impact", Path(__file__).with_name("impact.py")
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_transitive_closure_cycles_and_unmapped():
    g = {
        "edges": {
            "source": ["register"],
            "register": ["plan"],
            "plan": ["atlas"],
            "atlas": ["register"],
        },
        "generators": {},
    }
    r = m.impact(g, ["source", "unrelated"])
    assert r["affected_artifacts"] == ["atlas", "plan", "register"]
    assert r["unmapped"] == ["unrelated"]


def test_deletion_and_changed_hash_detected(tmp_path):
    p = tmp_path / "source"
    p.write_text("old")
    g = {"source_sha256": {"source": m.digest(p), "missing": "x"}}
    assert m.stale_sources(tmp_path, g) == ["missing"]
    p.write_text("new")
    assert m.stale_sources(tmp_path, g) == ["source", "missing"]


def test_campus_change_reaches_all_publications():
    root = Path(__file__).resolve().parents[3]
    g = m.dependency_graph(root)
    r = m.impact(g, ["geospatial/facilities/source/campus.json"])
    assert "geospatial/maps/SABLE_HARBOR_Facility_Atlas_v0.2.0.pdf" in r["affected_artifacts"]
    assert "geospatial/maps/workbench.html" in r["affected_artifacts"]
    assert "geospatial/facilities/population/REGISTER.json" in r["affected_artifacts"]
