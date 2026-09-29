"""Real fixed-schema dataset correction and transformation in disposable company stores."""

from copy import deepcopy

import pytest

from enterprise.audit_suite import company_data_quality_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database, native
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.inference import _json as decode
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_activity import ROOT

AT = "2027-06-02T00:00:00Z"
LATER = "2027-06-02T01:00:00Z"


def plan():
    return {
        "runtime_id": "QUALITY-LOCAL",
        "company": "SH",
        "branch": "local-quality",
        "dataset_id": "LOCAL-UNITS",
        "owner_id": "AS-P014",
        "declared_at": "2027-05-31T00:00:00Z",
        "input_at": AT,
        "event_window": {"start": "2027-06-01T00:00:00Z", "end": AT},
        "expected_record_ids": ["R1", "R2", "R3", "R4"],
        "reference_rows": [
            {"entity_id": "E1", "category": "CAT-A"},
            {"entity_id": "E2", "category": "CAT-B"},
        ],
        "maximum_units": 100,
        "local_rule_basis": "Explicit local nonpersonal fixture rules; no source acceptance",
    }


def rows():
    return [
        {"record_id": "R1", "entity_id": "E1", "units": 5, "observed_at": "2027-06-01T01:00:00Z"},
        {"record_id": "R2", "entity_id": "E1", "units": "7", "observed_at": "2027-06-01T02:00:00Z"},
        {"record_id": "R2", "entity_id": "E2", "units": 9, "observed_at": "2027-06-01T03:00:00Z"},
        {
            "record_id": "RX",
            "entity_id": "UNKNOWN",
            "units": -1,
            "observed_at": "2027-06-01T04:00:00Z",
        },
    ]


@pytest.fixture
def prepared(tmp_path):
    root = tmp_path / "runtime"
    raw = encoded(rows())
    initial = runtime.initialize(root, repository=ROOT, plan=plan(), raw_records=raw)
    return root, initial, raw


def view(p, at=LATER):
    return runtime.inspect(p[0], expected_runtime_sha256=p[1]["runtime_sha256"], as_of=at)


def args(p, command, operation="TRANSFORM", parameters=None, at=AT):
    state = view(p, at)
    return {
        "expected_runtime_sha256": p[1]["runtime_sha256"],
        "expected_revision": state["revision"],
        "command_id": command,
        "actor_id": "AS-P014",
        "operation": operation,
        "event_at": at,
        "rationale": "Explicit local fixture operation, not managerial accuracy acceptance",
        "parameters": parameters or {"input_pin": state["state"]["input_pin"]},
    }


def content(p, ref):
    with database(p[0]) as db:
        return native(db, ref)["content"]


def corrections(p, partial=False):
    source = decode(content(p, view(p)["state"]["input_pin"]))
    fixed = deepcopy(source)
    fixed[1]["units"] = 7
    fixed[2]["record_id"] = "R3"
    fixed[3].update(record_id="R4", entity_id="E2", units=2)
    return {
        "input_pin": view(p)["state"]["input_pin"],
        "replacements": [
            {"index": i, "before_row_sha256": sha(encoded(source[i])), "replacement": fixed[i]}
            for i in ([1, 2] if partial else [1, 2, 3])
        ],
    }


def snapshot(p):
    with database(p[0]) as db:
        return {
            t: [tuple(r) for r in db.execute("SELECT * FROM " + t + " ORDER BY 1")]
            for t in ("versions", "quality_commands", "quality_state")
        }


def test_failed_rows_retained_exact_correction_and_real_join_aggregate(prepared):
    p = prepared
    first = runtime.execute(p[0], **args(p, "initial"))
    report = first["observation"]["report"]
    assert report["status"] == "PARTIAL_UNRELIABLE"
    assert (
        report["input_rows"],
        report["accepted_rows"],
        report["failed_rows"],
        report["intentional_exclusions"],
    ) == (4, 1, 3, 0)
    assert report["missing_expected_in_window_ids"] == ["R3", "R4"]
    aggregate = decode(content(p, first["outputs"][1]))
    assert (
        aggregate["accepted_rows_only_total"] == 5 and aggregate["status"] == "PARTIAL_UNRELIABLE"
    )
    old_original = content(p, p[1]["input_pin"])
    correct = runtime.execute(p[0], **args(p, "correct", "CORRECT", corrections(p), LATER))
    assert correct["observation"]["row_count_preserved"] == 4
    assert view(p)["state"]["last_transform"] is None
    assert view(p)["state"]["input_pin"]["version"] == 2
    result = runtime.execute(p[0], **args(p, "after", at=LATER))
    assert result["observation"]["report"]["status"] == "LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE"
    assert decode(content(p, result["outputs"][1]))["groups"] == [
        {"category": "CAT-A", "accepted_rows": 2, "accepted_units": 12},
        {"category": "CAT-B", "accepted_rows": 2, "accepted_units": 11},
    ]
    assert content(p, p[1]["input_pin"]) == old_original == p[2]
    assert decode(content(p, first["outputs"][1])) == aggregate
    with database(p[0]) as db:
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 11
        assert all(
            db.execute("SELECT COUNT(*) FROM " + t).fetchone()[0] == 0
            for t in ("grants", "collections", "access_events")
        )


def test_partial_correction_never_promotes_incomplete_total(prepared):
    p = prepared
    runtime.execute(p[0], **args(p, "correct", "CORRECT", corrections(p, True)))
    result = runtime.execute(p[0], **args(p, "partial"))
    report = result["observation"]["report"]
    assert report["status"] == "PARTIAL_UNRELIABLE" and report[
        "missing_expected_in_window_ids"
    ] == ["R4"]
    derived, aggregate = [decode(content(p, x)) for x in result["outputs"]]
    assert derived["status"] == aggregate["status"] == "PARTIAL_UNRELIABLE"
    assert aggregate["accepted_rows_only_total"] == 21


@pytest.mark.parametrize("units", [True, False, 7.0, "7", -1, 101, None])
def test_exact_numeric_type_and_bound_not_coerced(prepared, units):
    p = prepared
    declaration = decode((p[0] / "RUNTIME.json").read_bytes())
    raw = rows()[:1]
    raw[0]["units"] = units
    declaration["plan"]["expected_record_ids"] = ["R1"]
    report, _, aggregate = runtime._transform(declaration, raw, runtime._stamp(AT))
    assert report["failed_rows"] == 1 and report["status"] == "PARTIAL_UNRELIABLE"
    assert aggregate["accepted_rows_only_total"] == 0


def test_outside_window_is_separate_from_expected_missing_and_offsets(prepared):
    cfg = decode((prepared[0] / "RUNTIME.json").read_bytes())
    cfg["plan"]["expected_record_ids"] = ["R1"]
    source = [
        rows()[0],
        rows()[0] | {"record_id": "OUT", "observed_at": "2027-06-01T17:00:00-07:00"},
    ]
    report, _, _ = runtime._transform(cfg, source, runtime._stamp(AT))
    assert report["status"] == "LOCAL_RULES_PASSED_NOT_SOURCE_ACCEPTANCE"
    assert report["intentional_exclusions"] == 1 and report["failed_rows"] == 0
    cfg["plan"]["expected_record_ids"].append("OUT")
    report, _, _ = runtime._transform(cfg, source, runtime._stamp(AT))
    assert (
        report["missing_expected_in_window_ids"] == ["OUT"]
        and report["status"] == "PARTIAL_UNRELIABLE"
    )


def test_missing_expected_rows_degrade_even_without_bad_rows(prepared):
    cfg = decode((prepared[0] / "RUNTIME.json").read_bytes())
    report, derived, aggregate = runtime._transform(cfg, rows()[:1], runtime._stamp(AT))
    assert (
        report["failed_rows"] == 0
        and report["status"] == derived["status"] == aggregate["status"] == "PARTIAL_UNRELIABLE"
    )


def test_future_query_and_correction_visibility(prepared):
    p = prepared
    request = args(p, "correct", "CORRECT", corrections(p), LATER)
    result = runtime.execute(p[0], **request)
    with pytest.raises(CompanyStoreError, match="cutoff"):
        view(p, AT)
    ref = result["outputs"][0]
    store = CompanyStore(p[0])
    route = ("collector", "scope", ref["company"], ref["branch"], ref["system"], ref["record"])
    store.grant(*route[:5])
    with pytest.raises(CompanyStoreError):
        store.read_version(*route, version=ref["version"], as_of=AT)
    assert store.read_version(*route, version=ref["version"], as_of=LATER)["content"] == content(
        p, ref
    )
    store.grant(*route[:5], active=False)
    with pytest.raises(CompanyStoreError):
        store.read_version(*route, version=ref["version"], as_of=LATER)
    cfg = decode((p[0] / "RUNTIME.json").read_bytes())
    with pytest.raises(CompanyStoreError, match="not closed"):
        runtime._transform(cfg, rows(), runtime._stamp("2027-06-01T12:00:00Z"))
    report, _, _ = runtime._transform(
        cfg, [rows()[0] | {"observed_at": "2027-07-01T00:00:00Z"}], runtime._stamp(AT)
    )
    assert "FUTURE_EVENT" in report["failures"][0]["reasons"]


def test_exact_replay_cas_and_changed_pin_or_command(prepared):
    p = prepared
    request = args(p, "transform")
    result = runtime.execute(p[0], **request)
    before = snapshot(p)
    assert runtime.execute(p[0], **request) == result and snapshot(p) == before
    for replacement in (
        {"rationale": "changed"},
        {"actor_id": "AS-P003"},
        {"expected_revision": True},
    ):
        with pytest.raises(CompanyStoreError):
            runtime.execute(p[0], **(request | replacement))
    with pytest.raises(CompanyStoreError, match="Revision"):
        runtime.execute(p[0], **(request | {"command_id": "new-stale"}))
    wrong = args(p, "wrong")
    wrong["parameters"]["input_pin"]["version"] = True
    with pytest.raises(CompanyStoreError):
        runtime.execute(p[0], **wrong)
    assert snapshot(p) == before


def test_correction_exact_row_hash_and_duplicate_index(prepared):
    p = prepared
    parameters = corrections(p)
    original = snapshot(p)
    for mutate in (
        lambda x: x["replacements"][0].update(before_row_sha256="0" * 64),
        lambda x: x["replacements"].append(deepcopy(x["replacements"][0])),
        lambda x: x["replacements"][0].update(index=True),
    ):
        bad = deepcopy(parameters)
        mutate(bad)
        with pytest.raises(CompanyStoreError):
            runtime.execute(p[0], **args(p, "bad", "CORRECT", bad))
    assert snapshot(p) == original


def test_batch_failure_rolls_back_all_products_and_revision(prepared, monkeypatch):
    p = prepared
    before = snapshot(p)
    insert = runtime._insert
    calls = 0

    def failed(*a):
        nonlocal calls
        calls += 1
        result = insert(*a)
        if calls == 2:
            raise CompanyStoreError("Injected aggregate write failure")
        return result

    monkeypatch.setattr(runtime, "_insert", failed)
    with pytest.raises(CompanyStoreError, match="aggregate write"):
        runtime.execute(p[0], **args(p, "atomic"))
    assert snapshot(p) == before


def test_final_config_race_rolls_back_and_code_change_rejects(prepared, monkeypatch):
    p = prepared
    before = snapshot(p)
    request = args(p, "race")
    read = runtime._config
    calls = 0

    def changed(*a):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise CompanyStoreError("Injected final definition change")
        return read(*a)

    monkeypatch.setattr(runtime, "_config", changed)
    with pytest.raises(CompanyStoreError, match="final definition"):
        runtime.execute(p[0], **request)
    assert snapshot(p) == before
    monkeypatch.setattr(runtime, "_config", read)
    code = runtime._code
    monkeypatch.setattr(runtime, "_code", lambda: code() | {"inference.py": "0" * 64})
    with pytest.raises(CompanyStoreError, match="code"):
        runtime.execute(p[0], **request)


@pytest.mark.parametrize(
    "raw", [b'[{"record_id":"A","record_id":"B"}]', b'[{"units":NaN}]', b'[{"units":1e999}]']
)
def test_ambiguous_or_nonfinite_raw_source_rejected_before_publication(tmp_path, raw):
    target = tmp_path / "bad"
    with pytest.raises(CompanyStoreError):
        runtime.initialize(target, repository=ROOT, plan=plan(), raw_records=raw)
    assert not target.exists()


def test_native_metadata_and_replay_receipt_tamper_rejected(prepared):
    p = prepared
    request = args(p, "first")
    runtime.execute(p[0], **request)
    with database(p[0], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET imported_at='2025-01-01T00:00:00Z' WHERE system='quality_derived'"
        )
    with pytest.raises(CompanyStoreError, match="metadata"):
        runtime.execute(p[0], **request)


def test_oversized_metadata_cannot_bypass_prefetch_with_null_neighbor(prepared):
    p = prepared
    with database(p[0], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET event_at=NULL,input_digest=? WHERE system='quality_definition'",
            ("x" * 1000000,),
        )
    with pytest.raises(CompanyStoreError, match="Bounded retained table metadata"):
        view(p)


def test_fully_repinned_false_result_still_fails_recomputation(prepared):
    p = prepared
    request = args(p, "transform")
    result = runtime.execute(p[0], **request)
    forged = deepcopy(result)
    forged["observation"]["report"]["accepted_rows"] = 99
    body = {k: v for k, v in forged.items() if k != "operation_pin"}
    cfg = decode((p[0] / "RUNTIME.json").read_bytes())
    raw = encoded(body)
    meta = runtime._metadata(
        cfg, "quality_operation", "OP-1", 1, raw, result["event_at"], result["imported_at"]
    )
    forged["operation_pin"] = {k: meta[k] for k in runtime.FIELDS}
    with database(p[0], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("DROP TRIGGER quality_no_update")
        db.execute(
            "UPDATE versions SET content=?,sha256=?,input_digest=? "
            "WHERE system='quality_operation'",
            (raw, meta["sha256"], meta["input_digest"]),
        )
        db.execute("UPDATE quality_commands SET receipt=?", (encoded(forged),))
    with pytest.raises(CompanyStoreError, match="Recomputed transformation"):
        runtime.execute(p[0], **request)


def test_stale_pre_correction_input_cannot_drive_new_transform(prepared):
    p = prepared
    old = p[1]["input_pin"]
    runtime.execute(p[0], **args(p, "correction", "CORRECT", corrections(p)))
    before = snapshot(p)
    with pytest.raises(CompanyStoreError, match="current raw source"):
        runtime.execute(p[0], **args(p, "stale-input", parameters={"input_pin": old}))
    assert snapshot(p) == before


def test_missing_control_assignment_not_vacuously_authorized(tmp_path, monkeypatch):
    snapshot_org = runtime.snapshot
    monkeypatch.setattr(
        runtime, "snapshot", lambda *a, **k: snapshot_org(*a, **k) | {"control_assignments": []}
    )
    with pytest.raises(CompanyStoreError, match="assignments"):
        runtime.initialize(
            tmp_path / "absent", repository=ROOT, plan=plan(), raw_records=encoded(rows())
        )
    assert not (tmp_path / "absent").exists()


def test_initial_code_change_never_publishes_runtime(tmp_path, monkeypatch):
    code = runtime._code
    calls = 0

    def changed():
        nonlocal calls
        calls += 1
        value = code()
        if calls >= 2:
            value["inference.py"] = "0" * 64
        return value

    monkeypatch.setattr(runtime, "_code", changed)
    with pytest.raises(CompanyStoreError, match="before publication"):
        runtime.initialize(
            tmp_path / "changed", repository=ROOT, plan=plan(), raw_records=encoded(rows())
        )
    assert not (tmp_path / "changed").exists()
