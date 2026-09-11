import copy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "facility_scenario", Path(__file__).with_name("scenario.py")
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    f = {
        "id": "F",
        "site_id": "S",
        "building_id": "B",
        "assigned_desks": 2,
        "shared_desks": 8,
        "touchdown_seats": 2,
        "planned_peak": 32,
        "defaults": {
            "assigned_workers": 2,
            "shared_workers": 8,
            "attendance_percent": 100,
            "sharing_ratio": 1,
            "touchdown_visitors": 2,
            "other_attendees": 0,
        },
    }
    return {
        "source_sha256": {"x": "abc"},
        "floors": [f],
        "campus": {
            "site_id": "S",
            "trainee_peak": 20,
            "resident_capacity": 10,
            "training_floor_id": "F",
            "default_resident_trainees": 8,
        },
    }


def test_baseline_and_nonadditive_residents():
    d = fixture()
    r = m.evaluate(d, m.baseline(d))
    assert r["campus"]["day_people"] == 32
    assert r["campus"]["night_residents"] == 10


def test_sharing_cannot_hide_concurrency():
    d = fixture()
    s = m.baseline(d)
    s["floors"][0].update(shared_workers=16, sharing_ratio=2)
    r = m.evaluate(d, s)
    assert r["status"] == "CONSTRAINT"
    assert r["floors"][0]["required_shared_desks"] == 16
    s["floors"][0]["attendance_percent"] = 50
    r = m.evaluate(d, s)
    assert r["floors"][0]["required_shared_desks"] == 8


def test_exclusive_reservation_not_freed_by_absence():
    d = fixture()
    s = m.baseline(d)
    s["floors"][0].update(assigned_workers=3, attendance_percent=0)
    assert m.evaluate(d, s)["floors"][0]["constraints"][0]["category"] == "assigned_desks"


def test_stale_duplicate_missing_nonfinite_and_fractional_rejected():
    d = fixture()
    base = m.baseline(d)
    for transform in [
        lambda s: s.update(source_sha256={}),
        lambda s: s["floors"].append(copy.deepcopy(s["floors"][0])),
        lambda s: s.update(floors=[]),
        lambda s: s["floors"][0].update(shared_workers=float("nan")),
        lambda s: s["floors"][0].update(shared_workers=1.5),
        lambda s: s["floors"][0].update(attendance_percent=101),
    ]:
        s = copy.deepcopy(base)
        transform(s)
        assert m.evaluate(d, s)["status"] == "INVALID"


def test_cohort_and_night_limits_and_subset():
    d = fixture()
    s = m.baseline(d)
    s["campus"]["resident_trainees"] = 21
    assert m.evaluate(d, s)["status"] == "INVALID"
    s["campus"].update(trainees=30, resident_trainees=12)
    assert len(m.evaluate(d, s)["campus"]["constraints"]) == 2


def test_unknown_is_not_zero_and_input_unchanged():
    d = fixture()
    d["floors"][0]["assigned_desks"] = None
    s = m.baseline(d)
    before = copy.deepcopy(s)
    assert m.evaluate(d, s)["floors"][0]["status"] == "UNKNOWN"
    assert s == before
