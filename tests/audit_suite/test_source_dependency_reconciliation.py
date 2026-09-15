from copy import deepcopy

import pytest

from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.source_dependency_reconciliation import analyze, reconcile, write_report
from enterprise.audit_suite.store import DomainError, digest
from tests.audit_suite.test_portfolio_explanation import setup as base_setup

SCOPE = {"period_start": "2027-01-01", "period_end": "2027-12-31", "boundaries": ["corporate"]}


def native(id, component, record, sha="a" * 64):
    return dict(
        id=id,
        source_store_id=component,
        company="C",
        branch="B",
        system="records",
        record=record,
        version=1,
        sha256=sha,
        available_at="2027-02-01T00:00:00Z",
    )


def test_native_producer_label_is_not_component_and_wrong_pins_are_not_matches():
    source, target = native("L", "logging", "L"), native("E", "engineering", "E")
    plan = {
        "adapters": [
            {
                "kind": "LOG_UPSTREAM",
                "source_ref_id": "L",
                "target_component_id": "engineering",
                "producer_label_expected": "producer-original",
            }
        ],
        "period_contracts": [],
    }
    link = {k: target[k] for k in ("company", "branch", "system", "record", "version", "sha256")}
    link["source_store_id"] = "producer-original"
    bodies = {"L": {"event": {"upstream": link}}}
    result = analyze(plan, [source, target], bodies, SCOPE)
    assert result["dependencies"][0]["status"] == "EXACT_MATCH"
    assert result["coherent_operating_year"] == "NOT_ESTABLISHED"
    assert (
        analyze(plan, [source], bodies, SCOPE)["dependencies"][0]["status"]
        == "MISSING_SELECTED_TARGET"
    )
    wrong = deepcopy(target)
    wrong["sha256"] = "b" * 64
    assert (
        analyze(plan, [source, wrong], bodies, SCOPE)["dependencies"][0]["status"]
        == "DIGEST_MISMATCH"
    )
    wrong = deepcopy(target)
    wrong["branch"] = "OTHER"
    assert (
        analyze(plan, [source, wrong], bodies, SCOPE)["dependencies"][0]["status"]
        == "MISSING_SELECTED_TARGET"
    )
    link["source_store_id"] = "engineering"
    assert (
        analyze(plan, [source, target], bodies, SCOPE)["dependencies"][0]["status"]
        == "PRODUCER_LABEL_MISMATCH"
    )


def test_cfg_renamed_native_identity_and_later_support_are_explicit():
    source, target = native("C", "cfg", "C"), native("E", "eng", "E")
    target["available_at"] = "2027-02-02T00:00:00Z"
    link = {
        "company_id": "C",
        "branch_id": "B",
        "system_id": "records",
        "record_id": "E",
        "version": 1,
        "sha256": target["sha256"],
        "source_store_id": "producer",
    }
    plan = {
        "adapters": [
            {
                "kind": "CFG_UPSTREAM",
                "source_ref_id": "C",
                "target_component_id": "eng",
                "producer_label_expected": "producer",
            }
        ],
        "period_contracts": [],
    }
    result = analyze(plan, [source, target], {"C": {"build": link}}, SCOPE)
    assert result["dependencies"][0]["status"] == "EXACT_MATCH"
    assert result["dependencies"][0]["timing"] == "LATER_SUPPORT"
    assert result["dependencies"][0]["causal_assertion"] == "NOT_INFERRED_FROM_REFERENCE"


def period_fixture():
    refs = [native(k, "iam", k) for k in ("P", "D", "R")]
    bodies = {
        k: {
            "control_id": "SH-IAM-007",
            "declared_employee_ids": ["LOCAL1"],
            "period_start": "2027-01-01T00:00:00Z",
            "period_end_exclusive": "2027-04-01T00:00:00Z",
        }
        for k in ("P", "D", "R")
    }
    contract = {
        "control_id": "SH-IAM-007",
        "boundary_id": "corporate",
        "inventory_ref_id": "P",
        "expected_slots": [
            {"id": "Q1", "start": "2027-01-01T00:00:00Z", "end": "2027-04-01T00:00:00Z"},
            {"id": "Q2", "start": "2027-04-01T00:00:00Z", "end": "2027-07-01T00:00:00Z"},
        ],
        "sources": [
            {"source_ref_id": k, "role": v}
            for k, v in zip(
                ("P", "D", "R"), ("POPULATION", "DECISIONS", "RECONCILIATION"), strict=True
            )
        ],
        "basis": "EXPLICIT_LOCAL_REFERENCE_PLAN",
    }
    for ref, field in zip(refs, ("members", "decisions", "hr_sources"), strict=True):
        ref["system"] = {
            "P": "review_population",
            "D": "review_decisions",
            "R": "review_reconciliation",
        }[ref["id"]]
        bodies[ref["id"]][field] = []
    return {"adapters": [], "period_contracts": [contract]}, refs, bodies


def test_quarter_roles_are_not_population_or_year_coverage():
    plan, refs, bodies = period_fixture()
    report = analyze(plan, refs, bodies, SCOPE)
    p = report["period_support"][0]
    assert all(v["status"] == "REQUIRED_ROLE_PRESENT" for v in p["slots"][0]["roles"].values())
    assert all(v["status"] == "MISSING_SELECTED_SUPPORT" for v in p["slots"][1]["roles"].values())
    assert p["operating_period_coverage"] == "NOT_ESTABLISHED"
    bodies["R"].pop("period_start")
    assert (
        analyze(plan, refs, bodies, SCOPE)["period_support"][0]["observations"][2]["status"]
        == "UNDATED"
    )
    plan["period_contracts"][0]["expected_slots"][1]["start"] = "2027-03-01T00:00:00Z"
    with pytest.raises(DomainError):
        analyze(plan, refs, bodies, SCOPE)


@pytest.fixture
def setup(tmp_path):
    return base_setup.__wrapped__(tmp_path)


def prepared(setup):
    e, args, *_ = setup
    actor = args["audited_actor_id"]
    eid = args["engagement_id"]
    state = e.store.get(actor, eid)
    plan = {
        "registry_sha256": e.company_store.binding["registry_sha256"],
        "scope_sha256": digest(state["scope"]),
        "source_refs": args["source_refs"][:1],
        "adapters": [],
        "period_contracts": [],
    }
    return e, actor, eid, plan


def test_actual_authorized_snapshot_new_only_output_and_no_state_change(setup, tmp_path):
    e, actor, eid, plan = prepared(setup)
    before = e.store.get(actor, eid)
    result = write_report(e, actor, eid, plan, output=tmp_path / "report")
    assert result["manifest_sha256"]
    assert e.store.get(actor, eid) == before
    with pytest.raises(DomainError):
        write_report(e, actor, eid, plan, output=tmp_path / "report")
    with pytest.raises(DomainError):
        write_report(e, actor, eid, plan, output=e.store.root / "nested")


@pytest.mark.parametrize("case", ["revoked", "future", "digest", "scope", "registry"])
def test_selected_source_or_context_failure_never_falls_back(setup, case):
    e, actor, eid, plan = prepared(setup)
    args = setup[1]
    if case == "revoked":
        plan["source_refs"] = [args["source_refs"][1]]
    elif case == "future":
        plan["source_refs"] = [args["source_refs"][2]]
    elif case == "digest":
        plan["source_refs"][0]["sha256"] = "b" * 64
    elif case == "scope":
        plan["scope_sha256"] = "b" * 64
    else:
        plan["registry_sha256"] = "b" * 64
    with pytest.raises((DomainError, CompanyStoreError)):
        reconcile(e, actor, eid, plan)


@pytest.mark.parametrize("change", ["grant", "registry", "revision"])
def test_context_changes_after_capture_prevent_publication(setup, tmp_path, monkeypatch, change):
    import json

    from enterprise.audit_suite import source_dependency_reconciliation as module

    e, actor, eid, plan = prepared(setup)
    original = module.analyze

    def changed(*args):
        result = original(*args)
        if change == "grant":
            setup[2]["one"].grant(actor, eid, "NATIVE", "branch", "records", active=False)
        elif change == "registry":
            path = setup[4]
            value = json.loads(path.read_text())
            value["components"]["one"]["namespace"] = "CHANGED"
            path.write_text(json.dumps(value))
        else:
            state = e.store.get(actor, eid)
            e.store.command(
                actor,
                eid,
                {
                    "command_id": "changed",
                    "expected_revision": state["revision"],
                    "kind": "fixture.change",
                    "payload": {},
                },
                lambda s, c, a: s,
                permissions={"learn"},
            )
        return result

    monkeypatch.setattr(module, "analyze", changed)
    with pytest.raises((DomainError, CompanyStoreError)):
        write_report(e, actor, eid, plan, output=tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("fault", ["relabel", "inventory_control", "inventory_branch", "duplicate"])
def test_native_role_and_inventory_constraints(fault):
    plan, refs, bodies = period_fixture()
    contract = plan["period_contracts"][0]
    if fault == "relabel":
        contract["sources"] = [
            {"source_ref_id": "P", "role": role}
            for role in ("POPULATION", "DECISIONS", "RECONCILIATION")
        ]
    elif fault == "inventory_control":
        bodies["P"]["control_id"] = "OTHER"
    elif fault == "inventory_branch":
        refs[1]["branch"] = "OTHER"
    else:
        contract["sources"].append(deepcopy(contract["sources"][0]))
    with pytest.raises(DomainError):
        analyze(plan, refs, bodies, SCOPE)


def test_inventory_difference_missing_plan_window_and_conflicting_period_visible():
    plan, refs, bodies = period_fixture()
    bodies["D"]["declared_employee_ids"] = ["OTHER"]
    bodies["R"]["period_end_exclusive"] = "2027-03-01T00:00:00Z"
    result = analyze(plan, refs, bodies, SCOPE)["period_support"][0]
    assert result["slots"][0]["roles"]["DECISIONS"]["status"] == "ROLE_PRESENT_INVENTORY_DIFFERS"
    assert result["slots"][0]["roles"]["RECONCILIATION"]["status"] == "MISSING_SELECTED_SUPPORT"
    assert result["observations"][2]["slot_alignment"] == "UNDATED_OR_CONFLICTING_PERIOD"
    assert result["unplanned_intervals"] == [
        {
            "start": "2027-07-01T00:00:00+00:00",
            "end": "2028-01-01T00:00:00+00:00",
            "status": "NO_EXPECTED_SLOT_AUTHORED",
        }
    ]


@pytest.mark.parametrize("kind", ["LOG_UPSTREAM", "CFG_UPSTREAM"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("version", True),
        ("version", 1.0),
        ("version", 0),
        ("sha256", "bad"),
        ("company", True),
        ("source_store_id", []),
    ],
)
def test_malformed_native_link_never_matches_selected_original(kind, field, value):
    source, target = native("S", "source", "S"), native("T", "target", "T")
    link = {k: target[k] for k in ("company", "branch", "system", "record", "version", "sha256")}
    link["source_store_id"] = "producer"
    link[field] = value
    if kind == "CFG_UPSTREAM":
        link = {
            (
                {
                    "company": "company_id",
                    "branch": "branch_id",
                    "system": "system_id",
                    "record": "record_id",
                }.get(k, k)
            ): v
            for k, v in link.items()
        }
    body = {"event": {"upstream": link}} if kind == "LOG_UPSTREAM" else {"build": link}
    plan = {
        "adapters": [
            {
                "kind": kind,
                "source_ref_id": "S",
                "target_component_id": "target",
                "producer_label_expected": "producer",
            }
        ],
        "period_contracts": [],
    }
    with pytest.raises(DomainError):
        analyze(plan, [source, target], {"S": body}, SCOPE)


def test_publication_freezes_original_plan_before_caller_mutation(setup, tmp_path, monkeypatch):
    import json

    from enterprise.audit_suite import source_dependency_reconciliation as module

    e, actor, eid, plan = prepared(setup)
    expected = digest(plan)
    original = module.analyze

    def mutate(*args):
        result = original(*args)
        plan["scope_sha256"] = "b" * 64
        return result

    monkeypatch.setattr(module, "analyze", mutate)
    output = tmp_path / "frozen"
    write_report(e, actor, eid, plan, output=output)
    manifest = json.loads((output / "MANIFEST.json").read_text())
    report = json.loads((output / "REPORT.json").read_text())
    retained = json.loads((output / "PLAN.json").read_text())
    assert report["plan_sha256"] == manifest["plan_sha256"] == digest(retained) == expected
    assert digest(plan) != expected
