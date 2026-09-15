import json
from dataclasses import asdict
from pathlib import Path

import pytest

from enterprise.audit_suite.company_activity_plan_sources import resolve_source
from enterprise.audit_suite.company_lifecycle_activity import (
    FIELDS,
    LifecycleSourceRef,
    read_inputs,
)
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import sha
from tests.audit_suite.test_company_activity import recipe
from tools.audit_suite.generate_company_activity import run

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def source(tmp_path):
    tmp_path.chmod(0o700)
    config = tmp_path / "recipe.json"
    config.write_text(json.dumps(asdict(recipe())))
    config.chmod(0o600)
    output = tmp_path / "producer"
    run("mover", config, output, repository=ROOT)
    import sqlite3

    root = output / "company"
    with sqlite3.connect((root / "company.sqlite3").as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = [
            dict(r)
            for r in db.execute(
                "select * from versions where branch='activity-clean' "
                "and ((system='hr' and version=3) or "
                "(system='directory' and version=2)) order by system"
            )
        ]
    refs = tuple(LifecycleSourceRef(**{k: r[k] for k in FIELDS}) for r in rows)
    _, pin = read_inputs(root, refs)
    return dict(
        source_root=root,
        source_manifest_path=output / "MANIFEST.json",
        expected_manifest_sha256=sha((output / "MANIFEST.json").read_bytes()),
        binding={
            "source_store_id": "EXPLICIT-CALLER-LABEL",
            "expected_records": [asdict(r) for r in refs],
            "expected_selected_metadata_sha256": pin,
        },
        consumed_at="2027-05-01T00:00:00Z",
        destination=tmp_path / "consumer",
    )


def test_actual_producer_exact_selection_no_creation_and_label_not_inferred(source):
    originals = {
        p: sha(p.read_bytes())
        for p in source["source_manifest_path"].parent.rglob("*")
        if p.is_file()
    }
    result = resolve_source(**source)
    assert len(result["source_refs"]) == 2
    assert (
        result["source_versions_sha256"] == source["binding"]["expected_selected_metadata_sha256"]
    )
    assert result["receipt"]["source_store_id"] == "EXPLICIT-CALLER-LABEL"
    assert result["receipt"]["coherent_operating_year"] == "NOT_ESTABLISHED"
    assert not source["destination"].exists()
    assert all(sha(p.read_bytes()) == h for p, h in originals.items())
    source["destination"].mkdir(mode=0o700)
    assert resolve_source(**source)["source_versions_sha256"] == result["source_versions_sha256"]


@pytest.mark.parametrize(
    "fault",
    [
        "nativehash",
        "metadata",
        "manifest",
        "future",
        "bool",
        "duplicate",
        "label",
        "root",
        "contained",
        "alias",
    ],
)
def test_bad_exact_inputs_rejected_without_output(source, tmp_path, fault):
    if fault == "nativehash":
        source["binding"]["expected_records"][0]["sha256"] = "0" * 64
    elif fault == "metadata":
        source["binding"]["expected_selected_metadata_sha256"] = "0" * 64
    elif fault == "manifest":
        source["expected_manifest_sha256"] = "0" * 64
    elif fault == "future":
        source["consumed_at"] = "2027-01-01T00:00:00Z"
    elif fault == "bool":
        source["binding"]["expected_records"][0]["version"] = True
    elif fault == "duplicate":
        source["binding"]["expected_records"][1] = source["binding"]["expected_records"][0]
    elif fault == "label":
        source["binding"]["source_store_id"] = ""
    elif fault == "root":
        source["source_root"] = source["source_manifest_path"].parent
    elif fault == "contained":
        source["destination"] = source["source_root"] / "nested"
    else:
        alias = tmp_path / "alias"
        alias.symlink_to(source["source_root"], target_is_directory=True)
        source["source_root"] = alias
    with pytest.raises(CompanyStoreError):
        resolve_source(**source)
    assert not source["destination"].exists()


def test_member_tamper_and_during_read_manifest_change_fail(source, monkeypatch):
    from enterprise.audit_suite import company_activity_plan_sources as module

    original = module.read_inputs

    def mutate(*args):
        result = original(*args)
        with source["source_manifest_path"].open("ab") as stream:
            stream.write(b" ")
        return result

    monkeypatch.setattr(module, "read_inputs", mutate)
    with pytest.raises(CompanyStoreError, match="manifest pin"):
        resolve_source(**source)
    assert not source["destination"].exists()


def test_completed_member_tamper_not_hidden_by_unchanged_manifest(source):
    with (source["source_manifest_path"].parent / "RECIPE.json").open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(CompanyStoreError, match="member pin"):
        resolve_source(**source)


def test_existing_output_cannot_contain_original_source_job(source):
    source["destination"] = source["source_manifest_path"].parent.parent
    with pytest.raises(CompanyStoreError, match="outside source job"):
        resolve_source(**source)
