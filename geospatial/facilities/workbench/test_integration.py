"""Cross-language contract and real-source invariants."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("workbench_builder", BASE / "build.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def test_real_baseline_and_browser_parity():
    data, _ = b.load_data()
    original = b.baseline(data)
    assert b.evaluate(data, original)["campus"]["day_people"] == 504
    assert b.evaluate(data, original)["campus"]["night_residents"] == 60
    cases = [original]
    for percent in [0, 14, 33.3, 70, 100]:
        s = copy.deepcopy(original)
        s["floors"][0].update(
            shared_workers=50, attendance_percent=percent, sharing_ratio=2, other_attendees=13
        )
        cases.append(s)
    script = """const fs=require('fs');const {calculate}=require(process.argv[1]);const {data,cases}=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(cases.map(s=>calculate(data.floors.map(f=>({...f,...s.floors.find(r=>r.id===f.id)})),s.campus.trainees,s.campus.resident_trainees,s.campus.resident_other,data.campus))));"""
    results = json.loads(
        subprocess.check_output(
            ["node", "-e", script, str(BASE / "app.js")],
            input=json.dumps({"data": data, "cases": cases}),
            text=True,
        )
    )
    for scenario, js in zip(cases, results, strict=True):
        py = b.evaluate(data, scenario)
        assert js["campus_day_concurrent"] == py["campus"]["day_people"]
        assert js["night_residents"] == py["campus"]["night_residents"]
        for p, j in zip(py["floors"], js["floors"], strict=True):
            assert p["day_attendees"] == j["concurrent"]
            if p["day_attendees"] is not None:
                assert p["required_shared_desks"] == j["shared_required"]
                assert p["required_assigned_desks"] == j["assigned_required"]


def test_export_cannot_overwrite_source_or_existing_file(tmp_path):
    with pytest.raises(ValueError):
        b.export_result(BASE / "source.json", {})
    p = tmp_path / "result.json"
    b.export_result(p, {"experiment": True})
    with pytest.raises(FileExistsError):
        b.export_result(p, {"overwrite": True})


def test_invalid_shapes_fail_closed():
    data, _ = b.load_data()
    for value in [None, [], {"floors": [{"id": {}}]}]:
        assert b.evaluate(data, value)["status"] == "INVALID"
