import copy
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from enterprise.audit_suite import company_activity_plan as runner
from enterprise.audit_suite.company_configuration_activity import read_originals
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_change_activity import recipe as change_recipe

ROOT = Path(__file__).resolve().parents[2]


def test_v1_plan_rejects_selected_identity_dependency_before_creating_output(tmp_path):
    value = {
        "format": runner.FORMAT,
        "jobs": [{"id": "identity", "kind": "identity-lifecycle", "depends_on": [], "recipe": {}}],
    }
    path = write_plan(tmp_path, value)
    with pytest.raises(CompanyStoreError, match="Unknown company activity kind"):
        runner.run(path, tmp_path / "run", repository=ROOT)
    assert not (tmp_path / "run").exists()


def plan():
    return {
        "format": runner.FORMAT,
        "jobs": [
            {"id": "change", "kind": "change", "depends_on": [], "recipe": asdict(change_recipe())},
            {
                "id": "configuration",
                "kind": "configuration",
                "depends_on": ["change"],
                "source_job": "change",
                "recipe": {
                    "company_id": "SH",
                    "source_store_id": "explicit-change-label",
                    "branch_ids": ["release-a", "release-b"],
                    "checkpoints": ["2027-02-01T12:30:00Z", "2027-02-01T14:00:00Z"],
                    "local_asset_id": "LOCAL-TARGET",
                },
            },
            {
                "id": "logging",
                "kind": "security-logging",
                "depends_on": ["change", "configuration"],
                "source_job": "change",
                "recipe": {
                    "company_id": "SH",
                    "source_store_id": "explicit-change-label",
                    "source_branch": "release-b",
                    "complete_branch": "log-a",
                    "omission_branch": "log-b",
                    "local_source_id": "LOCAL-RELEASE",
                },
            },
        ],
    }


def write_plan(tmp_path, value=None, raw=None):
    tmp_path.chmod(0o700)
    path = tmp_path / "plan.json"
    path.write_text(raw if raw is not None else json.dumps(value or plan()))
    path.chmod(0o600)
    return path


def test_actual_change_configuration_logging_chain_is_pinned_and_private(tmp_path):
    path = write_plan(tmp_path)
    output = tmp_path / "run"
    result = runner.run(path, output, repository=ROOT)
    assert result["status"] == "COMPLETE" and result["counts"]["COMPLETE"] == 3
    assert (output / "PLAN.json").read_bytes() == path.read_bytes()
    originals, pin = read_originals(output / "jobs/change/company")
    for job in result["jobs"][1:]:
        assert job["dependency"]["source_job"] == "change"
        assert job["dependency"]["source_versions_sha256"] == pin
        assert job["dependency"]["source_root"] == str(output / "jobs/change/company")
        assert job["dependency"]["source_store_id"] == "explicit-change-label"
        resolved = json.loads((output / f"recipes/{job['id']}.json").read_text())
        assert resolved["source_versions_sha256"] == pin
    assert result["jobs"][2]["dependency_manifest_sha256"] == {
        j["id"]: j["manifest_sha256"] for j in result["jobs"][:2]
    }
    assert len(originals) == 32
    assert [j["counts"]["versions"] for j in result["jobs"]] == [32, 12, 32]
    for manifest_path in [
        output / "MANIFEST.json",
        *[output / "jobs" / j["id"] / "MANIFEST.json" for j in result["jobs"]],
    ]:
        for name, expected in json.loads(manifest_path.read_text())["members"].items():
            assert (
                hashlib.sha256((manifest_path.parent / name).read_bytes()).hexdigest() == expected
            )
    assert all(not p.stat().st_mode & 0o077 for p in output.rglob("*"))
    assert all(j["counts"]["grants"] == j["counts"]["collections"] == 0 for j in result["jobs"])
    assert not list(output.rglob("engagements.sqlite3"))
    before = (output / "MANIFEST.json").read_bytes()
    with pytest.raises(CompanyStoreError, match="New private"):
        runner.run(path, output, repository=ROOT)
    assert (output / "MANIFEST.json").read_bytes() == before


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["jobs"][0].update(id="../outside"),
        lambda p: p["jobs"][1].update(id="change"),
        lambda p: p["jobs"][0].update(depends_on=["logging"]),
        lambda p: p["jobs"][1].update(depends_on=[]),
        lambda p: p["jobs"][2].update(source_job="configuration"),
        lambda p: p["jobs"][0].update(source_job="change"),
        lambda p: p["jobs"][0].update(kind="shell"),
        lambda p: p["jobs"][1]["recipe"].update(source_versions_sha256="a" * 64),
        lambda p: p["jobs"][2]["recipe"].update(local_max_ingestion_lag_seconds=True),
        lambda p: p["jobs"][2]["recipe"].update(source_root="/tmp/other"),
        lambda p: p["jobs"][1]["recipe"].update(branch_ids="release-a"),
    ],
)
def test_whole_plan_invalid_before_any_generation(tmp_path, monkeypatch, change):
    value = plan()
    change(value)
    path = write_plan(tmp_path, value)
    monkeypatch.setattr(
        runner.operator, "run", lambda *a, **k: pytest.fail("Generation before plan validation")
    )
    with pytest.raises(CompanyStoreError):
        runner.run(path, tmp_path / "output", repository=ROOT)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("raw", ['{"format":1,"format":2}', '{"jobs":NaN}', '{"jobs":Infinity}'])
def test_strict_json_and_size_limits(tmp_path, raw):
    path = write_plan(tmp_path, raw=raw)
    with pytest.raises(CompanyStoreError):
        runner.run(path, tmp_path / "output", repository=ROOT)
    path.write_bytes(b" " * (runner.MAX_PLAN_BYTES + 1))
    with pytest.raises(CompanyStoreError, match="size limit"):
        runner.run(path, tmp_path / "output", repository=ROOT)


def test_failure_retains_completed_jobs_and_stops_without_retry(tmp_path, monkeypatch):
    path = write_plan(tmp_path)
    original = runner.operator.run
    calls = []

    def fail(kind, *args, **kwargs):
        calls.append(kind)
        if kind == "configuration":
            raise RuntimeError("private native content must not leak")
        return original(kind, *args, **kwargs)

    monkeypatch.setattr(runner.operator, "run", fail)
    output = tmp_path / "output"
    result = runner.run(path, output, repository=ROOT)
    assert [j["status"] for j in result["jobs"]] == ["COMPLETE", "FAILED", "NOT_RUN"]
    assert calls == ["change", "configuration"]
    assert (output / "jobs/change/company/company.sqlite3").exists()
    assert (output / "recipes/configuration.json").exists()
    assert not (output / "recipes/logging.json").exists()
    assert "private native content" not in (output / "RECEIPT.json").read_text()
    assert result["jobs"][1]["dependency"]["source_job"] == "change"


def test_tampered_completed_source_blocks_dependent_generation(tmp_path, monkeypatch):
    path = write_plan(tmp_path)
    original = runner._verify_job
    calls = 0

    def tamper(directory, manifest):
        nonlocal calls
        original(directory, manifest)
        calls += 1
        if calls == 1:
            with (directory / "company/company.sqlite3").open("ab") as stream:
                stream.write(b"changed")

    monkeypatch.setattr(runner, "_verify_job", tamper)
    result = runner.run(path, tmp_path / "output", repository=ROOT)
    assert [j["status"] for j in result["jobs"]] == ["COMPLETE", "FAILED", "NOT_RUN"]
    assert "dependency" not in result["jobs"][1]


def test_private_alias_and_wrong_company_fail_closed(tmp_path):
    path = write_plan(tmp_path)
    path.chmod(0o644)
    with pytest.raises(CompanyStoreError, match="Private"):
        runner.run(path, tmp_path / "public", repository=ROOT)
    path.chmod(0o600)
    alias = tmp_path / "alias"
    alias.symlink_to(path)
    with pytest.raises(CompanyStoreError, match="nonsymlink"):
        runner.run(alias, tmp_path / "aliased", repository=ROOT)
    value = plan()
    value["jobs"][1]["recipe"]["company_id"] = "OTHER"
    path.write_text(json.dumps(value))
    with pytest.raises(CompanyStoreError, match="company differs"):
        runner.run(path, tmp_path / "wrong-company", repository=ROOT)
    assert not (tmp_path / "wrong-company").exists()


def test_validation_preserves_input_and_checks_nested_kind_fields():
    from tests.audit_suite.test_company_training_activity import recipe

    value = {
        "format": runner.FORMAT,
        "jobs": [
            {
                "id": "training",
                "kind": "training",
                "depends_on": [],
                "recipe": json.loads(json.dumps(asdict(recipe()))),
            },
        ],
    }
    before = copy.deepcopy(value)
    assert runner.validate_plan(value) == before and value == before
    value["jobs"][0]["recipe"]["courses"][0]["role_ids"] = [False]
    with pytest.raises(CompanyStoreError, match="Exact recipe field type"):
        runner.validate_plan(value)
