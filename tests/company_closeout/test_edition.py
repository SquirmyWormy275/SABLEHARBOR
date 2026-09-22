import copy
import json
import subprocess

import pytest

from tools.company_closeout.edition import EditionError, archive, build, encoded, sha, verify


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    (root / "rows.csv").write_text("id,amount\nA,12\n")
    contract = {
        "schema_version": "1.0.0",
        "edition_id": "test",
        "version": "1.0.0",
        "status": "REVIEW_CANDIDATE",
        "scope": "One declared source table",
        "limitations": ["Synthetic, no external confirmation"],
        "allowed_joins": ["native id only"],
        "required_components": ["finance"],
        "components": [
            {
                "id": "finance",
                "fact_status": "NEWLY_AUTHORED_SYNTHETIC_HISTORY",
                "access_scope": "PUBLIC_SYNTHETIC",
                "population_definition": "One row, August synthetic activity",
                "units": ["USD"],
                "legal_entities": ["SHI"],
                "available_at": "2026-09-15T00:00:00Z",
                "members": [{"path": "rows.csv", "sha256": sha((root / "rows.csv").read_bytes())}],
            }
        ],
    }
    path = root / "contract.json"
    path.write_bytes(encoded(contract))
    return root, path, contract


def test_independent_import_and_reproducible_archive(source, tmp_path):
    root, path, _ = source
    first, second = tmp_path / "first", tmp_path / "second"
    build(root, path, first)
    build(root, path, second)
    assert verify(first) == {"result": "PASS", "members": 1, "components": 1}
    archive(first, tmp_path / "one.zip")
    archive(second, tmp_path / "two.zip")
    assert (tmp_path / "one.zip").read_bytes() == (tmp_path / "two.zip").read_bytes()


def test_wrong_source_revision_rejected(source, tmp_path):
    root, path, contract = source
    contract["source_commit_required"] = "0" * 40
    path.write_bytes(encoded(contract))
    with pytest.raises(EditionError, match="another source revision"):
        build(root, path, tmp_path / "edition")


def test_manifest_revision_cannot_override_pinned_source(source, tmp_path):
    root, path, contract = source
    contract["source_commit_required"] = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    path.write_bytes(encoded(contract))
    destination = tmp_path / "edition"
    build(root, path, destination)
    manifest_path = destination / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["source_commit"] = "0" * 40
    manifest_path.write_bytes(encoded(manifest))
    with pytest.raises(EditionError, match="source revision contradicts"):
        verify(destination)


@pytest.mark.parametrize(
    "fault", ["duplicate", "omitted", "future", "private", "traversal", "stale"]
)
def test_reject_invalid_input_before_publication(source, tmp_path, fault):
    root, path, contract = source
    if fault == "duplicate":
        contract["components"].append(copy.deepcopy(contract["components"][0]))
    elif fault == "omitted":
        contract["required_components"].append("people")
    elif fault == "future":
        contract["components"][0]["claims_known_on"] = "2026-08-31T23:59:59Z"
    elif fault == "private":
        contract["components"][0]["access_scope"] = "PRIVATE_ASSESSMENT"
    elif fault == "traversal":
        contract["components"][0]["members"][0]["path"] = "../rows.csv"
    elif fault == "stale":
        (root / "rows.csv").write_text("id,amount\nA,13\n")
    path.write_bytes(encoded(contract))
    with pytest.raises(EditionError):
        build(root, path, tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_reject_omitted_payload_after_packaging(source, tmp_path):
    root, path, _ = source
    result = tmp_path / "result"
    build(root, path, result)
    (result / "content/rows.csv").unlink()
    with pytest.raises(EditionError, match="Missing"):
        verify(result)


def test_manifest_resealing_does_not_hide_changed_contract_population(source, tmp_path):
    root, path, _ = source
    result = tmp_path / "result"
    build(root, path, result)
    manifest_path = result / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["members"] = []
    manifest_path.write_bytes(encoded(manifest))
    with pytest.raises(EditionError, match="population"):
        verify(result)


@pytest.mark.parametrize("extra", ["top-level", "nested", "symlink"])
def test_archive_rejects_unmanifested_or_linked_material(source, tmp_path, extra):
    root, path, _ = source
    result = tmp_path / "result"
    build(root, path, result)
    if extra == "symlink":
        (result / "leak").symlink_to(root / "rows.csv")
    elif extra == "nested":
        (result / "content/extra.txt").write_text("unmanifested")
    else:
        (result / "extra.txt").write_text("unmanifested")
    with pytest.raises(EditionError):
        archive(result, tmp_path / "unsafe.zip")
    assert not (tmp_path / "unsafe.zip").exists()


def test_accepted_claim_rejects_dirty_source(source, tmp_path):
    root, path, contract = source
    contract["status"] = "ACCEPTED_SCOPED_EDITION"
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    scope = dict(
        status="LOCKED_ON_REPOSITORY_ACCEPTANCE",
        adopted_sources=[dict(contract["components"][0]["members"][0], scope="Selected rows")],
        preserved_states=["Fictional failures remain failed"],
        work_packages=[dict(id=f"SH-C{i:02d}") for i in range(1, 11)],
    )
    (root / "scope.json").write_bytes(encoded(scope))
    scope_hash = sha((root / "scope.json").read_bytes())
    contract["components"][0]["members"].append(dict(path="scope.json", sha256=scope_hash))
    contract["source_commit_required"] = revision
    contract["acceptance_receipt"] = dict(
        source_commit=revision,
        merge_commit=revision,
        pr_number=166,
        pr_url="https://github.com/SquirmyWormy275/SABLEHARBOR/pull/166",
        accepted_at="2026-09-14T00:00:00Z",
        observed_at="2026-09-15T00:00:00Z",
        adoption_path="scope.json",
        adoption_sha256=scope_hash,
        **{k: scope[k] for k in ("adopted_sources", "preserved_states", "work_packages")},
    )
    path.write_bytes(encoded(contract))
    with pytest.raises(EditionError, match="clean"):
        build(root, path, tmp_path / "result")


@pytest.mark.parametrize(
    "key,value",
    [("status", "ACCEPTED_SCOPED_EDITION"), ("edition_id", "other"), ("component_count", 99)],
)
def test_receipt_cannot_promote_or_relabel_contract(source, tmp_path, key, value):
    root, path, _ = source
    result = tmp_path / "result"
    build(root, path, result)
    manifest_path = result / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest[key] = value
    manifest_path.write_bytes(encoded(manifest))
    with pytest.raises(EditionError, match="contradicts"):
        verify(result)
