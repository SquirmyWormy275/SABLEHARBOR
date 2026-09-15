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
