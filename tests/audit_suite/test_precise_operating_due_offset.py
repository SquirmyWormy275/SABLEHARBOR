"""Small source-only policy deadline mechanics; no actual source or audit data."""

from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from enterprise.audit_suite import company_operating_depth_runtime as depth
from enterprise.audit_suite import company_policy_delivery_runtime as policy
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError, _time
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.source_library_audit import typed_content

REPO = Path(__file__).resolve().parents[2]
START = _time("2027-11-01T09:00:00Z")
END = _time("2027-11-02T09:00:00Z")
DUE = _time("2027-11-02T00:00:00Z")
LATE = _time("2027-11-03T10:00:00Z")


def original(store, system, record, body, *, at=START, owner="AS-P007"):
    store.register_system("SH", "OWN-PRECISE", system, owner)
    return depth.pin(
        store.append_version(
            "SH",
            "OWN-PRECISE",
            system,
            record,
            expected_version=0,
            command_id="OWN-" + sha(encoded([system, record])),
            event_at=at,
            available_at=at,
            content=encoded(body),
            provenance={
                "source_reference": "OWN-INDEPENDENT-SOURCE",
                "name": record + ".json",
                "content_type": "application/json",
            },
        )
    )


def calendar():
    return dict(
        declared_at=START,
        period_start=START,
        period_end_exclusive=END,
        cadence_days=1,
        due_offset_seconds=54000,
        items=[
            dict(
                id="NOVEMBER",
                system_id="NOVEMBER-V2",
                kind="POLICY",
                operating_from=START,
                operating_to_exclusive=_time("2027-11-04T00:00:00Z"),
                commissioning_ref=None,
            )
        ],
        exclusions=[],
    )


def inventory(cal, document_sha="0" * 64):
    return {
        "systems": [
            {
                "system": "NOVEMBER-V2",
                "owner": "AS-P005",
                "recipients": ["AS-P007", "AS-P014"],
                "document_sha256": document_sha,
            }
        ],
        "whole_estate_claim": "Two named OWN policy recipients; no enterprise or human approval.",
        "operating_depth_calendar": cal,
    }


def register(store, inv, *, recorded="2027-11-01T09:01:00Z"):
    return depth.register_declaration(
        store,
        repository=REPO,
        business_inventory_pin=inv,
        retained_period_refs=[],
        runtime_id="OWN-PRECISE-NOVEMBER",
        actor_id="AS-P007",
        recorded_at=recorded,
        command_id="OWN-PRECISE-REGISTER",
    )


def test_real_native_policy_15hour_due_missing_late_receipts_and_typed_collection(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir(mode=0o700)
    source = CompanyStore(source_root)
    raw_body = {"edition": 2, "text": "OWN November exact native policy; no human acknowledgement"}
    document = original(
        source, "supplementalops.policy_document", "NOVEMBER-V2", raw_body, owner="AS-P005"
    )
    inv = original(
        source, "business_inventory", "NOVEMBER-CALENDAR", inventory(calendar(), document["sha256"])
    )
    old_rows = {"document": document, "inventory": inv}
    definition = register(source, inv)
    selected = depth.declare(
        source, repository=REPO, declaration_pin=depth.pin(definition), as_of="2027-11-01T09:01:00Z"
    )
    assert selected["schedule"][0]["due_at"] == DUE
    runtime = tmp_path / "policy"
    initial = policy.initialize_native(
        runtime,
        repository=REPO,
        plan=dict(
            runtime_id="OWN-EXACT-POLICY",
            company="SH",
            branch="OWN-PRECISE",
            owner_id="AS-P005",
            cycle_id="NOVEMBER",
            declared_at="2027-11-01T09:05:00Z",
            due_at=DUE,
            recipients=["AS-P007", "AS-P014"],
            local_basis="OWN recipients; source before local operations; no audit outcome",
        ),
        documents=[dict(id="NOVEMBER-V2", source_root=str(source_root), source_pin=document)],
    )
    runtime_sha = initial["runtime_sha256"]
    doc = policy.inspect(runtime, expected_runtime_sha256=runtime_sha, as_of=DUE)["report"][
        "selected_document_pin"
    ]
    for rev, op in enumerate(["DELIVER", "READ_RETURN"]):
        policy.execute(
            runtime,
            expected_runtime_sha256=runtime_sha,
            expected_revision=rev,
            command_id="OWN-TIMELY-" + op,
            actor_id="AS-P005" if rev == 0 else "AS-P007",
            operation=op,
            event_at="2027-11-01T09:10:00Z",
            rationale="Actual native-byte local delivery and read return before exact15hour due",
            parameters={"recipient_id": "AS-P007", "document_pin": doc},
        )
    bound = depth.policy_binding(
        source,
        declaration_pin=depth.pin(definition),
        slot_id="NOVEMBER:0",
        runtime_root=runtime,
        runtime_sha256=runtime_sha,
        actor_id="AS-P005",
        command_id="OWN-BIND-DUE",
        event_at=DUE,
    )
    with source._db() as db:
        bound_row = depth.selected(db, depth.pin(bound), DUE)[0]
    observation = depth.decode(bound_row["content"])["observation"]
    assert observation["all_recipients_delivered"] is False
    missing = next(
        r
        for r in observation["recorded_policy_report"]["recipients"]
        if r["recipient_id"] == "AS-P014"
    )
    assert missing["delivery_status"] == "MISSING_DUE"
    assert observation["human_acknowledgment"] == "NOT_ESTABLISHED"
    for rev, op in enumerate(["DELIVER", "READ_RETURN"], start=2):
        policy.execute(
            runtime,
            expected_runtime_sha256=runtime_sha,
            expected_revision=rev,
            command_id="OWN-LATE-" + op,
            actor_id="AS-P005" if rev == 2 else "AS-P014",
            operation=op,
            event_at=LATE,
            rationale="Explicit late native byte return; old missed deadline retained",
            parameters={"recipient_id": "AS-P014", "document_pin": doc},
        )
    late = depth.policy_binding(
        source,
        declaration_pin=depth.pin(definition),
        slot_id="NOVEMBER:0",
        runtime_root=runtime,
        runtime_sha256=runtime_sha,
        actor_id="AS-P005",
        command_id="OWN-BIND-LATE",
        event_at=LATE,
        expected_version=1,
    )
    with source._db() as db:
        late_row = depth.selected(db, depth.pin(late), LATE)[0]
    late_obs = depth.decode(late_row["content"])["observation"]
    assert late_obs["all_recipients_delivered"] is True
    assert late_obs["all_recipients_read_return"] is True
    recipient = next(
        r
        for r in late_obs["recorded_policy_report"]["recipients"]
        if r["recipient_id"] == "AS-P014"
    )
    assert recipient["late"] is True
    assert depth.decode(late_row["content"])["slot"]["due_at"] == DUE
    view = depth.inspect(source, declaration_pin=depth.pin(definition), as_of=LATE)
    assert len(view["slots"][0]["history"]) == 2
    with source._db() as db:
        for p in old_rows.values():
            assert depth.pin(depth.selected(db, p, LATE)[0]) == p
    source.grant("OWN-AUDITOR", "OWN-FRESH-AUDIT", "SH", "OWN-PRECISE", depth.SYSTEM)
    for row in (bound_row, late_row):
        receipt = source.collect(
            "OWN-AUDITOR",
            "OWN-FRESH-AUDIT",
            "SH",
            "OWN-PRECISE",
            depth.SYSTEM,
            row["record"],
            version=row["version"],
            as_of=LATE,
            command_id="OWN-COLLECT-" + str(row["version"]),
        )
        assert receipt["source"]["sha256"] == row["sha256"]
        actual = source.read_version(
            "OWN-AUDITOR",
            "OWN-FRESH-AUDIT",
            "SH",
            "OWN-PRECISE",
            depth.SYSTEM,
            row["record"],
            version=row["version"],
            as_of=LATE,
        )
        assert actual["content"] == row["content"]
        assert typed_content(actual)[0]["schema"] == "SH_NATIVE_OPERATING_DEPTH_OBSERVATION_V1"


@pytest.mark.parametrize(
    "change",
    [
        "both",
        "missing",
        "bool_seconds",
        "float_seconds",
        "zero_seconds",
        "negative_seconds",
        "exceeds_cadence",
        "over_maximum",
        "bool_cadence",
        "zero_days",
        "bool_days",
        "fraction_days",
        "days_exceed_cadence",
        "extra_field",
        "declared_after_start",
        "unnormalized_clock",
    ],
)
def test_invalid_offset_or_clock_refuses_before_native_append(tmp_path, change):
    root = tmp_path / "source"
    root.mkdir(mode=0o700)
    source = CompanyStore(root)
    cal = calendar()
    if change == "both":
        cal["due_offset_days"] = 1
    elif change == "missing":
        cal.pop("due_offset_seconds")
    elif change == "bool_seconds":
        cal["due_offset_seconds"] = True
    elif change == "float_seconds":
        cal["due_offset_seconds"] = 54000.0
    elif change == "zero_seconds":
        cal["due_offset_seconds"] = 0
    elif change == "negative_seconds":
        cal["due_offset_seconds"] = -1
    elif change == "exceeds_cadence":
        cal["due_offset_seconds"] = 86401
    elif change == "over_maximum":
        cal["due_offset_seconds"] = 366 * 86400 + 1
    elif change == "bool_cadence":
        cal["cadence_days"] = True
    elif change in {"zero_days", "bool_days", "fraction_days", "days_exceed_cadence"}:
        cal.pop("due_offset_seconds")
        cal["due_offset_days"] = {
            "zero_days": 0,
            "bool_days": True,
            "fraction_days": 0.625,
            "days_exceed_cadence": 2,
        }[change]
    elif change == "extra_field":
        cal["due_offset_minutes"] = 900
    elif change == "declared_after_start":
        cal["declared_at"] = _time("2027-11-01T09:00:01Z")
    elif change == "unnormalized_clock":
        cal["declared_at"] = "2027-11-01T09:00:00Z"
    inv = original(source, "business_inventory", "INVALID-CALENDAR", inventory(cal))
    before = source.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        register(source, inv)
    assert source.path.read_bytes() == before


@pytest.mark.parametrize("cadence,offset,duration", [(1, 1, 1), (30, 5, 31), (366, 366, 367)])
def test_old_day_boundaries_and_equivalent_exact_second_offset(cadence, offset, duration):
    cal = calendar()
    cal.pop("due_offset_seconds")
    cal.update(cadence_days=cadence, due_offset_days=offset)
    start = datetime.fromisoformat(START)
    stop = start + timedelta(days=duration)
    cal["period_end_exclusive"] = stop.isoformat(timespec="microseconds")
    cal["items"][0]["operating_to_exclusive"] = cal["period_end_exclusive"]
    old = []
    current = start
    while current < stop:
        end = min(current + timedelta(days=cadence), stop)
        old.append(min(current + timedelta(days=offset), end).isoformat(timespec="microseconds"))
        current = end
    days = depth.schedule(cal)
    seconds = deepcopy(cal)
    seconds.pop("due_offset_days")
    seconds["due_offset_seconds"] = offset * 86400
    assert days == depth.schedule(seconds)
    assert [s["due_at"] for s in days] == old
