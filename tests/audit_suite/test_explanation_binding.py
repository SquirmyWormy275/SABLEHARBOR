import json
from types import SimpleNamespace

import pytest

from enterprise.audit_suite.artifacts import Artifacts
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.explanation_binding import bind_snapshot, verify_snapshot
from enterprise.audit_suite.operating_source_bridge import sha
from enterprise.audit_suite.store import DomainError, Store


@pytest.fixture
def workspace(tmp_path):
    company = tmp_path / "company"
    company.mkdir(mode=0o700)
    sources = CompanyStore(company)
    audit = Store(tmp_path / "audit")
    instructor = audit.provision("Instructor", ["instructor"])["id"]
    learner = audit.provision("Learner", ["learner"])["id"]
    state = audit.create(
        instructor,
        {
            "scope": {"period_start": "2027-01-01", "period_end": "2027-12-31"},
            "simulated_at": "2027-06-01T00:00:00Z",
            "controls": [{"id": "CONTROL1"}],
            "artifacts": [],
        },
        "create",
    )
    audit.grant(state["id"], learner, "learn")
    sources.register_system("C", "B", "SYS", "OWNER")
    refs = []
    for record, available in [("R1", "2027-05-01T00:00:00Z"), ("R2", "2027-07-01T00:00:00Z")]:
        metadata = sources.append_version(
            "C",
            "B",
            "SYS",
            record,
            expected_version=0,
            command_id=record,
            event_at=available,
            available_at=available,
            content=json.dumps({"record": record}).encode(),
            provenance={"source_reference": record},
        )
        refs.append(
            {
                "id": record,
                **{
                    k: metadata[k]
                    for k in ["company", "branch", "system", "record", "version", "sha256"]
                },
            }
        )
    sources.grant("OPERATOR", state["id"], "C", "B", "SYS")
    sources.grant(learner, state["id"], "C", "B", "SYS")
    engine = SimpleNamespace(
        store=audit,
        company_store=sources,
        company_bindings={state["id"]: {"company": "C", "branch": "B"}},
        repository=tmp_path,
        artifacts=Artifacts(tmp_path / "artifacts"),
    )
    output = tmp_path / "private"
    output.mkdir(mode=0o700)
    args = {
        "instructor_id": instructor,
        "audited_actor_id": learner,
        "engagement_id": state["id"],
        "source_operator_id": "OPERATOR",
        "source_as_of": "2027-08-01T00:00:00Z",
        "source_refs": refs,
        "authored": {
            "issues": [
                {
                    "id": "I1",
                    "control_ids": ["CONTROL1"],
                    "source_ids": ["R1"],
                    "claim": "Instructor interpretation of a bounded source",
                    "uncertainty": "Not professionally validated",
                }
            ],
            "expectations": [
                {
                    "id": "E1",
                    "issue_ids": ["I1"],
                    "procedure": "Inspect the original and seek corroboration",
                    "acceptable_alternatives": ["Obtain other authorized corroboration"],
                }
            ],
            "uncertainty": ["Sufficiency is not assessed"],
            "source_pins": {},
        },
        "output": output / "snapshot",
    }
    return engine, args


def test_bound_exact_bytes_visibility_uncertainty_and_tamper(workspace):
    engine, args = workspace
    receipt = bind_snapshot(engine, **args)
    data = verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])
    assert [r["actor_visibility_at_binding"] for r in data["sources"]] == [
        "DISCOVERABLE_LATEST",
        "FUTURE_UNAVAILABLE",
    ]
    assert data["professional_validation"] == "UNVALIDATED"
    assert data["authored"]["uncertainty"] == args["authored"]["uncertainty"]
    assert (
        sha((args["output"] / "sources/00000.json").read_bytes())
        == args["source_refs"][0]["sha256"]
    )
    with pytest.raises(DomainError):
        bind_snapshot(engine, **args)
    (args["output"] / "sources/00000.json").write_bytes(b"changed")
    with pytest.raises(DomainError):
        verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])


def test_ungranted_auditor_is_separate_from_operator_denial(workspace):
    engine, args = workspace
    engine.company_store.grant(
        args["audited_actor_id"], args["engagement_id"], "C", "B", "SYS", active=False
    )
    receipt = bind_snapshot(engine, **args)
    data = verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])
    assert data["sources"][0]["actor_visibility_at_binding"] == "ACCESS_NOT_GRANTED"
    args["output"] = args["output"].parent / "denied"
    engine.company_store.grant("OPERATOR", args["engagement_id"], "C", "B", "SYS", active=False)
    with pytest.raises(DomainError):
        bind_snapshot(engine, **args)
    assert not args["output"].exists()


@pytest.mark.parametrize("fault", ["learner", "hash", "branch", "unknown_source"])
def test_rejects_unbound_or_unauthorized_claims(workspace, fault):
    engine, args = workspace
    if fault == "learner":
        args["instructor_id"] = args["audited_actor_id"]
    elif fault == "hash":
        args["source_refs"][0]["sha256"] = "0" * 64
    elif fault == "branch":
        args["source_refs"][0]["branch"] = "OTHER"
    else:
        args["authored"]["issues"][0]["source_ids"] = ["absent"]
    with pytest.raises(DomainError):
        bind_snapshot(engine, **args)
    assert not args["output"].exists()


def test_prior_version_remains_readable_and_snapshot_is_not_rebound(workspace):
    engine, args = workspace
    engine.company_store.append_version(
        "C",
        "B",
        "SYS",
        "R1",
        expected_version=1,
        command_id="correction",
        event_at="2027-05-02T00:00:00Z",
        available_at="2027-05-02T00:00:00Z",
        content=b'{"record":"R1","revision":2}',
        provenance={"source_reference": "R1-correction"},
    )
    receipt = bind_snapshot(engine, **args)
    snapshot = verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])
    assert snapshot["sources"][0]["actor_visibility_at_binding"] == "READABLE_PRIOR_VERSION"
    engine.company_store.grant(
        args["audited_actor_id"], args["engagement_id"], "C", "B", "SYS", active=False
    )
    assert (
        verify_snapshot(args["output"], expected_manifest_sha256=receipt["manifest_sha256"])
        == snapshot
    )
