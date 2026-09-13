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


def test_cross_book_corruption_is_detected():
    data = {p.stem: m.rows(p.read_bytes()) for p in (HERE.parent / "close/source").glob("*.csv")}
    row = data["legal_trial_balance"][0]
    row["signed_usd"] = str(m.num(row, "signed_usd") + 1)
    checks = {r["check"]: r for r in m.checks(data, "close")}
    assert checks["Unit to legal account/month bridge"]["status"] == "FAIL"


def test_replacement_source_corruption_is_detected():
    data = {p.stem: m.rows(p.read_bytes()) for p in (HERE.parent / "close/source").glob("*.csv")}
    row = next(
        r for r in data["enterprise_journal"] if r["source_type"] == "BUSINESS_DRIVEN_FORECAST"
    )
    row["source_id"] += "-WRONG"
    checks = {r["check"]: r for r in m.checks(data, "close")}
    assert checks["Core to enterprise replacement source/account bridge"]["status"] == "FAIL"
