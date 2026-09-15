import copy
import dataclasses
import json
from typing import get_args, get_origin, get_type_hints

import pytest

from enterprise.audit_suite import company_activity_plan as runner
from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_activity_plan import ROOT, plan, write_plan


@pytest.mark.parametrize("fault", ["conflicting_labels", "shared_label"])
def test_label_source_identity_must_be_one_to_one_before_output(tmp_path, monkeypatch, fault):
    value = plan()
    if fault == "conflicting_labels":
        value["jobs"][2]["recipe"]["source_store_id"] = "other-label"
    else:
        second = copy.deepcopy(value["jobs"][0])
        second["id"] = "change-two"
        value["jobs"].insert(1, second)
        value["jobs"][-1]["depends_on"].append("change-two")
        value["jobs"][-1]["source_job"] = "change-two"
    monkeypatch.setattr(runner.operator, "run", lambda *a, **k: pytest.fail("No generation"))
    with pytest.raises(CompanyStoreError, match="Source labels"):
        runner.run(write_plan(tmp_path, value), tmp_path / "run", repository=ROOT)
    assert not (tmp_path / "run").exists()


def test_published_manifest_must_match_actual_operator_result(tmp_path, monkeypatch):
    native = runner.operator.run

    def substituted(*args, **kwargs):
        result = native(*args, **kwargs)
        path = args[2] / "MANIFEST.json"
        body = json.loads(path.read_text())
        body["recipe_sha256"] = "0" * 64
        path.write_text(json.dumps(body))
        return result

    monkeypatch.setattr(runner.operator, "run", substituted)
    value = plan()
    value["jobs"] = value["jobs"][:1]
    result = runner.run(write_plan(tmp_path, value), tmp_path / "run", repository=ROOT)
    assert result["status"] == "FAILED"
    assert result["jobs"][0]["failure_stage"] == "VERIFY_PUBLISHED_OUTPUT"
    assert "manifest_sha256" not in result["jobs"][0]


def test_non_source_dependency_tampering_blocks_following_job(tmp_path, monkeypatch):
    original = runner._write

    def modified(path, raw):
        original(path, raw)
        if path.name == "01-configuration-result.json":
            target = path.parents[1] / "jobs/configuration/company/company.sqlite3"
            with target.open("ab") as stream:
                stream.write(b"changed prior dependency")

    monkeypatch.setattr(runner, "_write", modified)
    result = runner.run(write_plan(tmp_path), tmp_path / "run", repository=ROOT)
    assert [j["status"] for j in result["jobs"]] == ["COMPLETE", "COMPLETE", "FAILED"]
    assert result["jobs"][-1]["failure_stage"] == "RESOLVE_RECIPE_AND_DEPENDENCY"
    assert not (tmp_path / "run/jobs/logging").exists()


def test_all_maintained_kind_schemas_including_provider_are_structurally_supported():
    def example(annotation):
        if dataclasses.is_dataclass(annotation):
            hints = get_type_hints(annotation)
            return {f.name: example(hints[f.name]) for f in dataclasses.fields(annotation)}
        if get_origin(annotation) is tuple:
            return [example(get_args(annotation)[0])]
        return {str: "explicit-value", int: 1, bool: False, float: 1.0}[annotation]

    seen = set()
    for kind, (cls, _) in runner.operator.KINDS.items():
        recipe = example(cls)
        dependent = kind in runner.operator.SOURCE_KINDS
        jobs = []
        job = {"id": "candidate", "kind": kind, "depends_on": [], "recipe": recipe}
        if dependent:
            source = plan()["jobs"][0]
            source["recipe"]["company_id"] = recipe["company_id"]
            jobs.append(source)
            del recipe["source_versions_sha256"]
            job.update(depends_on=["change"], source_job="change")
        jobs.append(job)
        value = {"format": runner.FORMAT, "jobs": jobs}
        assert runner.validate_plan(value) == value
        seen.add(kind)
    assert len(seen) == 9 and "provider-intake" in seen


def test_native_job_cannot_change_completed_source_and_report_complete(tmp_path, monkeypatch):
    native = runner.operator.run

    def altered(kind, recipe_path, output, **kwargs):
        manifest = native(kind, recipe_path, output, **kwargs)
        if kind == "configuration":
            with (kwargs["source_root"] / "company.sqlite3").open("ab") as stream:
                stream.write(b"changed after dependency resolution")
        return manifest

    monkeypatch.setattr(runner.operator, "run", altered)
    result = runner.run(write_plan(tmp_path), tmp_path / "run", repository=ROOT)
    assert [j["status"] for j in result["jobs"]] == ["COMPLETE", "FAILED", "NOT_RUN"]
    assert result["jobs"][1]["failure_stage"] == "VERIFY_PRIOR_OUTPUTS_AFTER_JOB"
    assert (tmp_path / "run/jobs/configuration").exists()  # retained, not declared complete


def test_private_hardlinked_input_and_aliased_destination_rejected(tmp_path):
    import os

    source = write_plan(tmp_path)
    os.link(source, tmp_path / "hardlink.json")
    with pytest.raises(CompanyStoreError, match="Private"):
        runner.run(source, tmp_path / "run", repository=ROOT)
    (tmp_path / "hardlink.json").unlink()
    target = tmp_path / "parent"
    target.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(target)
    with pytest.raises(CompanyStoreError, match="nonsymlink"):
        runner.run(source, alias / "run", repository=ROOT)
    assert not (target / "run").exists()
