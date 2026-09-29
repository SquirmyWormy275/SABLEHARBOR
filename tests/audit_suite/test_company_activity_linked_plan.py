import copy
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from enterprise.audit_suite import company_activity_linked_plan as runner
from enterprise.audit_suite.company_lifecycle_activity import read_inputs
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_backup_activity import recipe as backup_recipe
from tests.audit_suite.test_company_change_activity import recipe as change_recipe
from tests.audit_suite.test_company_nonhuman_identity_activity import inputs as nonhuman_inputs

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    return path


@pytest.fixture
def linked(tmp_path):
    _, recipe = nonhuman_inputs.__wrapped__(tmp_path)
    source = tmp_path / "operator-backup"
    runner.operator.run(
        "backup", write(tmp_path / "backup.json", asdict(backup_recipe())), source, repository=ROOT
    )
    _, pin = read_inputs(source / "company", recipe.source_refs)
    recipe = replace(recipe, source_versions_sha256=pin)
    plan = {
        "format": runner.FORMAT,
        "inputs": {
            "backup": {
                "root": str(source / "company"),
                "manifest_sha256": hashlib.sha256(
                    (source / "MANIFEST.json").read_bytes()
                ).hexdigest(),
            }
        },
        "jobs": [
            {
                "id": "change",
                "kind": "change",
                "depends_on": [],
                "recipe": asdict(change_recipe()),
                "sources": {},
            },
            {
                "id": "nonhuman",
                "kind": "nonhuman-identity",
                "depends_on": ["change"],
                "recipe": asdict(recipe),
                "sources": {"source": "backup"},
            },
        ],
    }
    return json.loads(json.dumps(plan)), source


def test_actual_existing_source_and_independent_jobs(tmp_path, linked):
    plan, source = linked
    original = (source / "company/company.sqlite3").read_bytes()
    path = write(tmp_path / "plan.json", plan)
    result = runner.run(path, tmp_path / "out", repository=ROOT)
    assert result["status"] == "COMPLETE", result
    assert result["counts"] == {"COMPLETE": 2, "FAILED": 0, "NOT_RUN": 0}
    assert (tmp_path / "out/PLAN.json").read_bytes() == path.read_bytes()
    assert (source / "company/company.sqlite3").read_bytes() == original
    native = json.loads((tmp_path / "out/jobs/nonhuman/MANIFEST.json").read_bytes())
    assert (
        native["counts"]["versions"] == 35
        and native["counts"]["grants"] == native["counts"]["collections"] == 0
    )
    receipt = result["jobs"][1]
    assert receipt["dependency_manifest_sha256"] == {"change": result["jobs"][0]["manifest_sha256"]}
    assert (
        receipt["sources"]["source"]["selected_metadata_sha256"]
        == plan["jobs"][1]["recipe"]["source_versions_sha256"]
    )
    assert (
        json.loads((tmp_path / "out/recipes/nonhuman.json").read_bytes())
        == plan["jobs"][1]["recipe"]
    )
    manifest = json.loads((tmp_path / "out/MANIFEST.json").read_bytes())
    for member, pin in manifest["members"].items():
        assert hashlib.sha256((tmp_path / "out" / member).read_bytes()).hexdigest() == pin
    with pytest.raises(CompanyStoreError):
        runner.run(path, tmp_path / "out", repository=ROOT)


@pytest.mark.parametrize(
    "mutation", ["source_job", "forward", "missing_slot", "unused", "pin", "future"]
)
def test_entire_plan_and_existing_sources_fail_before_output(tmp_path, linked, mutation):
    plan, _ = linked
    if mutation == "source_job":
        plan["jobs"][1]["source_job"] = "change"
    if mutation == "forward":
        plan["jobs"][0]["depends_on"] = ["nonhuman"]
    if mutation == "missing_slot":
        plan["jobs"][1]["sources"] = {}
    if mutation == "unused":
        plan["jobs"] = plan["jobs"][:1]
    if mutation == "pin":
        plan["inputs"]["backup"]["manifest_sha256"] = "0" * 64
    if mutation == "future":
        plan["jobs"][1]["recipe"]["period_start"] = "2026-01-01T00:00:00Z"
    with pytest.raises(CompanyStoreError):
        runner.run(write(tmp_path / "plan.json", plan), tmp_path / "out", repository=ROOT)
    assert not (tmp_path / "out").exists()


def test_post_consumer_tamper_retains_failure_and_stops(tmp_path, linked, monkeypatch):
    plan, source = linked
    plan["jobs"].append(
        {**copy.deepcopy(plan["jobs"][0]), "id": "later", "depends_on": ["nonhuman"]}
    )
    actual = runner.operator.run

    def changed(kind, *args, **kwargs):
        result = actual(kind, *args, **kwargs)
        if kind == "nonhuman-identity":
            (source / "RECIPE.json").write_bytes(b"changed")
        return result

    monkeypatch.setattr(runner.operator, "run", changed)
    result = runner.run(write(tmp_path / "plan.json", plan), tmp_path / "out", repository=ROOT)
    assert [j["status"] for j in result["jobs"]] == ["COMPLETE", "FAILED", "NOT_RUN"]
    assert result["jobs"][1]["failure_stage"] == "VERIFY_OUTPUT_AND_INPUTS_AFTER_JOB"
    assert (tmp_path / "out/jobs/nonhuman/MANIFEST.json").exists()
    assert not (tmp_path / "out/jobs/later").exists()
    manifest = json.loads((tmp_path / "out/MANIFEST.json").read_bytes())
    assert "jobs/nonhuman/MANIFEST.json" in manifest["members"]
    assert result["jobs"][1]["published_output"]["acceptance"] == "POSTCHECK_FAILED_NOT_DEPENDENCY"
    assert "changed" not in json.dumps(result)


def test_output_cannot_be_inside_source_operator(tmp_path, linked):
    plan, source = linked
    with pytest.raises(CompanyStoreError):
        runner.run(write(tmp_path / "plan.json", plan), source / "nested", repository=ROOT)
    assert not (source / "nested").exists()


def test_independent_consumers_preserve_distinct_local_labels(tmp_path, linked):
    plan, _ = linked
    second = copy.deepcopy(plan["jobs"][1])
    second["id"] = "second-consumer"
    second["recipe"]["source_store_id"] = "another-explicit-local-label"
    plan["jobs"].append(second)
    result = runner.run(write(tmp_path / "plan.json", plan), tmp_path / "out", repository=ROOT)
    assert result["status"] == "COMPLETE", result
    receipts = [j["sources"]["source"] for j in result["jobs"][1:]]
    assert receipts[0]["source_root"] == receipts[1]["source_root"]
    assert receipts[0]["source_store_id"] != receipts[1]["source_store_id"]


def test_actual_four_group_risk_routing(tmp_path):
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
    result = runner.run(write(tmp_path / "plan.json", plan), tmp_path / "out", repository=ROOT)
    assert result["status"] == "COMPLETE", result
    assert result["jobs"][0]["counts"]["versions"] == 20
    assert set(result["jobs"][0]["sources"]) == set(roots)


def test_duplicate_path_spelling_rejected_before_output(tmp_path, linked):
    plan, _ = linked
    plan["inputs"]["same-store"] = {
        **plan["inputs"]["backup"],
        "root": plan["inputs"]["backup"]["root"] + "/",
    }
    with pytest.raises(CompanyStoreError):
        runner.run(write(tmp_path / "plan.json", plan), tmp_path / "out", repository=ROOT)
    assert not (tmp_path / "out").exists()


def test_plan_changes_during_read_rejected(tmp_path, linked, monkeypatch):
    import enterprise.audit_suite.company_activity_plan_sources as resolver

    plan, _ = linked
    path = write(tmp_path / "plan.json", plan)
    original = resolver.os.fdopen

    class Stream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def fileno(self):
            return self.stream.fileno()

        def read(self, *args):
            raw = self.stream.read(*args)
            path.chmod(0o644)
            return raw

    monkeypatch.setattr(resolver.os, "fdopen", lambda *a, **k: Stream(original(*a, **k)))
    with pytest.raises(CompanyStoreError):
        runner.run(path, tmp_path / "out", repository=ROOT)
    assert not (tmp_path / "out").exists()


def test_later_job_cannot_invalidate_earlier_source_and_report_complete(
    tmp_path, linked, monkeypatch
):
    plan, source = linked
    consumer = plan["jobs"][1]
    consumer["depends_on"] = []
    independent = plan["jobs"][0]
    independent["depends_on"] = ["nonhuman"]
    plan["jobs"] = [consumer, independent]
    actual = runner.operator.run

    def changed(kind, *args, **kwargs):
        result = actual(kind, *args, **kwargs)
        if kind == "change":
            (source / "RECIPE.json").write_bytes(b"changed")
        return result

    monkeypatch.setattr(runner.operator, "run", changed)
    result = runner.run(write(tmp_path / "plan.json", plan), tmp_path / "out", repository=ROOT)
    assert result["status"] == "FAILED"
    assert result["jobs"][0]["status"] == "COMPLETE"
    assert result["jobs"][1]["failure_stage"] == "REVERIFY_ALL_COMPLETED_INPUTS"
    assert result["jobs"][1]["source_recheck_job"] == "nonhuman"
    assert result["jobs"][1]["published_output"]["acceptance"] == "POSTCHECK_FAILED_NOT_DEPENDENCY"


def test_published_member_failure_still_indexes_unaccepted_output(tmp_path, linked, monkeypatch):
    plan, _ = linked
    actual = runner.operator.run

    def changed(kind, recipe_path, output, **kwargs):
        result = actual(kind, recipe_path, output, **kwargs)
        (output / "RECIPE.json").write_bytes(b"changed after publication")
        return result

    monkeypatch.setattr(runner.operator, "run", changed)
    result = runner.run(write(tmp_path / "plan.json", plan), tmp_path / "out", repository=ROOT)
    assert [j["status"] for j in result["jobs"]] == ["FAILED", "NOT_RUN"]
    failed = result["jobs"][0]["published_output"]
    assert failed["acceptance"] == "POSTCHECK_FAILED_NOT_DEPENDENCY"
    assert failed["path"] == "jobs/change"
    manifest_path = tmp_path / "out/jobs/change/MANIFEST.json"
    pin = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert failed["manifest_sha256"] == pin
    run_manifest = json.loads((tmp_path / "out/MANIFEST.json").read_bytes())
    assert run_manifest["members"]["jobs/change/MANIFEST.json"] == pin
    assert "manifest_sha256" not in result["jobs"][0]
