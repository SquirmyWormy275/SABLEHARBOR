import copy
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from enterprise.audit_suite import company_activity_producer_plan as runner
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_activity_linked_plan import linked as existing_fixture
from tests.audit_suite.test_company_activity_linked_plan import write
from tests.audit_suite.test_company_backup_activity import recipe as backup_recipe
from tests.audit_suite.test_company_change_activity import recipe as change_recipe

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def producer(tmp_path):
    old, _ = existing_fixture.__wrapped__(tmp_path)
    consumer = copy.deepcopy(old["jobs"][1])
    consumer["depends_on"] = ["backup"]
    consumer["sources"] = {"source": {"source_job": "backup", "metadata_mode": runner.CAPTURE}}
    consumer["recipe"].pop("source_versions_sha256")
    return {
        "format": runner.FORMAT,
        "inputs": {},
        "jobs": [
            {
                "id": "backup",
                "kind": "backup",
                "depends_on": [],
                "sources": {},
                "recipe": asdict(backup_recipe()),
            },
            consumer,
        ],
    }


def test_actual_selected_producer_once_capture_and_frozen_rechecks(tmp_path, producer, monkeypatch):
    import enterprise.audit_suite.company_activity_source_capture as capture

    actual = capture.capture_source
    calls = []

    def counted(**kwargs):
        calls.append(kwargs)
        return actual(**kwargs)

    monkeypatch.setattr(capture, "capture_source", counted)
    producer["jobs"].append(
        {
            "id": "later",
            "kind": "change",
            "depends_on": ["nonhuman"],
            "sources": {},
            "recipe": asdict(change_recipe()),
        }
    )
    path = write(tmp_path / "plan.json", producer)
    result = runner.run(path, tmp_path / "out", repository=ROOT)
    assert result["status"] == "COMPLETE", result
    assert len(calls) == 1
    assert calls[0]["destination"] == tmp_path / "out/jobs/nonhuman"
    assert result["jobs"][1]["counts"]["versions"] == 35
    assert (tmp_path / "out/PLAN.json").read_bytes() == path.read_bytes()
    original = producer["jobs"][1]["recipe"]
    resolved = json.loads((tmp_path / "out/recipes/nonhuman.json").read_bytes())
    assert "source_versions_sha256" not in original
    assert {k: v for k, v in resolved.items() if k != "source_versions_sha256"} == original
    assert (
        resolved["source_versions_sha256"]
        == result["jobs"][1]["sources"]["source"]["selected_metadata_sha256"]
    )
    assert (
        result["jobs"][1]["source_captures"]["source"]["capture_basis"]
        == "CAPTURED_AFTER_VERIFIED_PRODUCER_NOT_CALLER_PREDECLARED"
    )
    assert result["jobs"][1]["dependency_manifest_sha256"] == {
        "backup": result["jobs"][0]["manifest_sha256"]
    }
    manifest = json.loads((tmp_path / "out/MANIFEST.json").read_bytes())
    for name, pin in manifest["members"].items():
        assert hashlib.sha256((tmp_path / "out" / name).read_bytes()).hexdigest() == pin


@pytest.mark.parametrize(
    "mutation",
    ["null", "supplied", "not_dependency", "forward", "native_bool", "native_missing", "bad_mode"],
)
def test_complete_structure_rejected_before_any_output(tmp_path, producer, mutation):
    job = producer["jobs"][1]
    if mutation == "null":
        job["recipe"]["source_versions_sha256"] = None
    if mutation == "supplied":
        job["recipe"]["source_versions_sha256"] = "0" * 64
    if mutation == "not_dependency":
        job["depends_on"] = []
    if mutation == "forward":
        producer["jobs"].reverse()
    if mutation == "native_bool":
        job["recipe"]["source_refs"][0]["version"] = True
    if mutation == "native_missing":
        job["recipe"]["source_refs"][0].pop("sha256")
    if mutation == "bad_mode":
        job["sources"]["source"]["metadata_mode"] = "LATEST"
    with pytest.raises(CompanyStoreError):
        runner.run(write(tmp_path / "plan.json", producer), tmp_path / "out", repository=ROOT)
    assert not (tmp_path / "out").exists()


def test_wrong_expected_native_hash_fails_after_producer_without_deriving_hash(tmp_path, producer):
    producer["jobs"][1]["recipe"]["source_refs"][0]["sha256"] = "0" * 64
    result = runner.run(write(tmp_path / "plan.json", producer), tmp_path / "out", repository=ROOT)
    assert [j["status"] for j in result["jobs"]] == ["COMPLETE", "FAILED"]
    assert not (tmp_path / "out/jobs/nonhuman").exists()
    assert not (tmp_path / "out/recipes/nonhuman.json").exists()


def test_existing_exact_input_contract_preserved(tmp_path):
    plan, _ = existing_fixture.__wrapped__(tmp_path)
    plan["format"] = runner.FORMAT
    for job in plan["jobs"]:
        job["sources"] = {k: {"input_id": v} for k, v in job["sources"].items()}
    result = runner.run(write(tmp_path / "plan.json", plan), tmp_path / "out", repository=ROOT)
    assert result["status"] == "COMPLETE", result
    assert result["jobs"][1]["source_captures"] == {}
    assert (
        json.loads((tmp_path / "out/recipes/nonhuman.json").read_bytes())
        == plan["jobs"][1]["recipe"]
    )


def test_later_producer_mutation_invalidates_run_without_recapture(tmp_path, producer, monkeypatch):
    import enterprise.audit_suite.company_activity_source_capture as capture

    original = capture.capture_source
    calls = []

    def counted(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(capture, "capture_source", counted)
    producer["jobs"].append(
        {
            "id": "later",
            "kind": "change",
            "depends_on": ["nonhuman"],
            "sources": {},
            "recipe": asdict(change_recipe()),
        }
    )
    actual = runner.operator.run

    def changed(kind, *args, **kwargs):
        result = actual(kind, *args, **kwargs)
        if kind == "change":
            (tmp_path / "out/jobs/backup/RECIPE.json").write_bytes(b"changed")
        return result

    monkeypatch.setattr(runner.operator, "run", changed)
    result = runner.run(write(tmp_path / "plan.json", producer), tmp_path / "out", repository=ROOT)
    assert result["status"] == "FAILED" and len(calls) == 1
    assert result["jobs"][-1]["published_output"]["acceptance"] == "POSTCHECK_FAILED_NOT_DEPENDENCY"
    manifest = json.loads((tmp_path / "out/MANIFEST.json").read_bytes())
    assert "jobs/later/MANIFEST.json" in manifest["members"]


def test_actual_risk_mixes_existing_groups_with_captured_change_producer(tmp_path):
    from enterprise.audit_suite.company_change_activity import ChangeRecipe
    from enterprise.audit_suite.company_configuration_activity import read_originals
    from enterprise.audit_suite.company_security_logging_activity import LoggingRecipe
    from tests.audit_suite.test_company_incident_activity import recipe as incident_recipe
    from tests.audit_suite.test_company_provider_intake_activity import recipe as provider_recipe
    from tests.audit_suite.test_company_risk_assessment_activity import make_recipe

    tmp_path.chmod(0o700)
    change = ChangeRecipe(
        "SABLEHARBOR",
        "release-a",
        "release-b",
        "CYCLE",
        "2027-02-01T00:00:00Z",
        "2027-02-03T00:00:00Z",
        "Local reference release rule only",
    )

    def produce(key, kind, recipe, **kwargs):
        dest = tmp_path / key
        runner.operator.run(
            kind, write(tmp_path / (key + ".json"), asdict(recipe)), dest, repository=ROOT, **kwargs
        )
        return dest / "company"

    roots = {"change": produce("change", "change", change)}
    _, pin = read_originals(roots["change"])
    roots["log"] = produce(
        "log",
        "security-logging",
        LoggingRecipe(
            "SABLEHARBOR",
            "change-original",
            pin,
            "release-b",
            "logging-a",
            "logging-b",
            "LOCAL-RELEASE",
        ),
        source_root=roots["change"],
    )
    roots["incident"] = produce(
        "incident", "incident", replace(incident_recipe(), company_id="SABLEHARBOR")
    )
    roots["provider"] = produce("provider", "provider-intake", provider_recipe())
    selectors = {
        "incident": (
            "incident-clean",
            {
                ("monitoring", "INC-01-monitoring", 1),
                ("postincident_review", "INC-01-postincident_review", 1),
            },
        ),
        "provider": (
            "provider-complete",
            {
                ("planned_dependency_inventory", "DEPENDENCIES", 1),
                ("vendor_register", "CP-IDACORE", 1),
            },
        ),
        "log": (
            "logging-a",
            {("publisher_events", "EVENT-1", 1), ("detection_alerts", "AUTH-ALERT-1", 1)},
        ),
        "change": (
            "release-b",
            {
                ("release_gate", "GATE-PROPOSED", 1),
                ("local_releases", "RELEASE-PROPOSED", 1),
                ("release_gate", "GATE-CORRECTED", 1),
            },
        ),
    }
    recipe = make_recipe(roots, selectors)
    plan = {
        "format": runner.FORMAT,
        "inputs": {
            k: {
                "root": str(v),
                "manifest_sha256": hashlib.sha256(
                    (v.parent / "MANIFEST.json").read_bytes()
                ).hexdigest(),
            }
            for k, v in roots.items()
        },
        "jobs": [
            {
                "id": "risk",
                "kind": "risk-assessment",
                "depends_on": [],
                "sources": {k: k for k in roots},
                "recipe": asdict(recipe),
            }
        ],
    }
    plan["format"] = runner.FORMAT
    plan["inputs"].pop("change")
    risk = plan["jobs"][0]
    risk["sources"] = {k: {"input_id": k} for k in roots if k != "change"}
    risk["sources"]["change"] = {"source_job": "new-change", "metadata_mode": runner.CAPTURE}
    risk["depends_on"] = ["new-change"]
    for group in risk["recipe"]["source_groups"]:
        if group["id"] == "change":
            group.pop("source_versions_sha256")
    plan["jobs"].insert(
        0,
        {
            "id": "new-change",
            "kind": "change",
            "depends_on": [],
            "sources": {},
            "recipe": asdict(change),
        },
    )
    plan["inputs"].pop("log")
    risk["sources"]["log"] = {"source_job": "new-log", "metadata_mode": runner.CAPTURE}
    risk["depends_on"] = ["new-change", "new-cfg", "new-log"]
    for group in risk["recipe"]["source_groups"]:
        if group["id"] == "log":
            group.pop("source_versions_sha256")
    config = {
        "company_id": "SABLEHARBOR",
        "source_store_id": "change-original",
        "branch_ids": ["release-a", "release-b"],
        "checkpoints": ["2027-02-01T12:30:00Z", "2027-02-01T14:00:00Z"],
        "local_asset_id": "LOCAL-TARGET",
    }
    logging = asdict(
        LoggingRecipe(
            "SABLEHARBOR",
            "change-original",
            pin,
            "release-b",
            "logging-a",
            "logging-b",
            "LOCAL-RELEASE",
        )
    )
    logging.pop("source_versions_sha256")
    whole = {"source": {"source_job": "new-change", "metadata_mode": runner.WHOLE_MODE}}
    plan["jobs"][1:1] = [
        {
            "id": "new-cfg",
            "kind": "configuration",
            "depends_on": ["new-change"],
            "recipe": config,
            "sources": copy.deepcopy(whole),
        },
        {
            "id": "new-log",
            "kind": "security-logging",
            "depends_on": ["new-change"],
            "recipe": logging,
            "sources": copy.deepcopy(whole),
        },
    ]
    result = runner.run(write(tmp_path / "plan.json", plan), tmp_path / "out", repository=ROOT)
    assert result["status"] == "COMPLETE", result
    assert result["jobs"][-1]["counts"]["versions"] == 20
    assert set(result["jobs"][-1]["sources"]) == set(roots)

    assert set(result["jobs"][-1]["source_captures"]) == {"change", "log"}


@pytest.mark.parametrize(
    "mutation", ["wrong_kind", "selected_mode", "supplied_digest", "input_mode"]
)
def test_whole_change_contract_rejects_unsupported_mode_before_output(tmp_path, mutation):
    tmp_path.chmod(0o700)
    parent = {
        "id": "change",
        "kind": "change",
        "depends_on": [],
        "sources": {},
        "recipe": asdict(change_recipe()),
    }
    recipe = {
        "company_id": "SH",
        "source_store_id": "local-change",
        "branch_ids": ["release-a", "release-b"],
        "checkpoints": ["2027-02-01T12:30:00Z", "2027-02-01T14:00:00Z"],
        "local_asset_id": "LOCAL",
    }
    child = {
        "id": "cfg",
        "kind": "configuration",
        "depends_on": ["change"],
        "recipe": recipe,
        "sources": {"source": {"source_job": "change", "metadata_mode": runner.WHOLE_MODE}},
    }
    if mutation == "wrong_kind":
        parent.update(kind="backup", recipe=asdict(backup_recipe()))
    if mutation == "selected_mode":
        child["sources"]["source"]["metadata_mode"] = runner.CAPTURE
    if mutation == "supplied_digest":
        recipe["source_versions_sha256"] = "0" * 64
    if mutation == "input_mode":
        child["sources"]["source"] = {"input_id": "somewhere"}
    plan = {"format": runner.FORMAT, "inputs": {}, "jobs": [parent, child]}
    with pytest.raises(CompanyStoreError):
        runner.run(write(tmp_path / "plan.json", plan), tmp_path / "out", repository=ROOT)
    assert not (tmp_path / "out").exists()
