import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("extract_build", HERE / "build.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_snapshot_time_scope():
    assert m.selected({"scenario": "base", "issue_month": "12"}, 2027)
    assert not m.selected({"scenario": "base", "issue_month": "13"}, 2027)
    assert not m.selected({"scenario": "downside", "year": "2027"}, 2027)
    assert not m.selected({"scenario": "base", "period": "2028-01-31"}, 2027)


def test_accounting_corruption_is_detected():
    data = {}
    for p in (HERE.parent / "customer/source").glob("*.csv"):
        data[p.stem] = m.rows(p.read_bytes())
    data["commercial_deferred_rollforward"][0]["closing_usd"] = "1"
    assert any(r["status"] == "FAIL" for r in m.checks(data, "customer"))


def test_all_extracted_populations():
    spec = importlib.util.spec_from_file_location("extract_validate", HERE / "validate.py")
    v = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v)
    v.validate()
