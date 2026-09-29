import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_activity_operator import prepare
from tools.audit_suite import generate_company_activity as operator


def test_risk_cli_consumes_exact_grouped_sources_and_preserves_inputs(tmp_path, capsys):
    from tests.audit_suite.test_company_risk_assessment_activity import inputs

    roots, recipe = inputs.__wrapped__(tmp_path)
    before = {key: (root / "company.sqlite3").read_bytes() for key, root in roots.items()}
    source_map = tmp_path / "roots.json"
    source_map.write_text(json.dumps({key: str(root) for key, root in roots.items()}))
    source_map.chmod(0o600)
    path = tmp_path / "risk.json"
    raw = json.dumps(asdict(recipe)).encode()
    path.write_bytes(raw)
    path.chmod(0o600)
    output = tmp_path / "risk-output"
    operator.main(
        [
            "risk-assessment",
            "--recipe",
            str(path),
            "--destination",
            str(output),
            "--source-roots",
            str(source_map),
        ]
    )
    status = json.loads(capsys.readouterr().out)
    assert status["counts"] == {"systems": 12, "versions": 20, "grants": 0, "collections": 0}
    manifest = json.loads((output / "MANIFEST.json").read_text())
    assert set(manifest["source_inputs"]) == set(roots)
    assert (output / "RECIPE.json").read_bytes() == raw
    for group in recipe.source_groups:
        assert manifest["source_inputs"][group.id] == {
            "root": str(roots[group.id]),
            "source_store_id": group.source_store_id,
            "source_versions_sha256": group.source_versions_sha256,
        }
    for name, pin in manifest["members"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == pin
    for key, root in roots.items():
        assert (root / "company.sqlite3").read_bytes() == before[key]
    wrong = {**roots, "change": roots["log"]}
    with pytest.raises(CompanyStoreError):
        operator.run(
            "risk-assessment",
            path,
            tmp_path / "invalid-map",
            repository=Path(__file__).resolve().parents[2],
            source_roots=wrong,
        )
    assert not (tmp_path / "invalid-map").exists()


def test_explicit_private_group_map_and_contract_conflicts(tmp_path):
    recipe = prepare(tmp_path)
    roots_file = tmp_path / "roots.json"
    roots_file.write_text(json.dumps({"incident": str(tmp_path / "source")}))
    roots_file.chmod(0o600)
    roots = operator.load_source_roots(roots_file)
    assert roots == {"incident": tmp_path / "source"}
    for kind, kwargs in [
        ("risk-assessment", {}),
        ("mover", {"source_roots": roots}),
        ("risk-assessment", {"source_roots": roots, "source_root": tmp_path}),
    ]:
        with pytest.raises(CompanyStoreError):
            operator.run(kind, recipe, tmp_path / "output", repository=tmp_path, **kwargs)
        assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "raw",
    [
        '{"incident":"/a","incident":"/b"}',
        '{"incident":NaN}',
        '{"incident":"relative"}',
        "[]",
        "{}",
    ],
)
def test_ambiguous_or_implicit_root_maps_are_rejected(tmp_path, raw):
    tmp_path.chmod(0o700)
    path = tmp_path / "roots.json"
    path.write_text(raw)
    path.chmod(0o600)
    with pytest.raises(CompanyStoreError):
        operator.load_source_roots(path)


def test_root_map_privacy_and_alias_rejected(tmp_path):
    tmp_path.chmod(0o700)
    path = tmp_path / "roots.json"
    path.write_text(json.dumps({"incident": str(tmp_path)}))
    path.chmod(0o644)
    with pytest.raises(CompanyStoreError):
        operator.load_source_roots(path)
    path.chmod(0o600)
    alias = tmp_path / "alias.json"
    alias.symlink_to(path)
    with pytest.raises(CompanyStoreError):
        operator.load_source_roots(alias)


def test_private_recipe_becoming_public_during_open_is_rejected(tmp_path, monkeypatch):
    recipe = prepare(tmp_path)
    original = operator.os.open

    def changed(path, *args, **kwargs):
        if Path(path) == recipe:
            recipe.chmod(0o644)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(operator.os, "open", changed)
    with pytest.raises(CompanyStoreError):
        operator.run("mover", recipe, tmp_path / "output", repository=tmp_path)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("kind", sorted(operator.SOURCE_KINDS | operator.MULTI_SOURCE_KINDS))
def test_normalized_source_overlap_rejected_before_recipe_read_or_staging(
    tmp_path, monkeypatch, kind
):
    tmp_path.chmod(0o700)
    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    sibling = tmp_path / "sibling"
    sibling.mkdir(mode=0o700)
    database = source / "company.sqlite3"
    database.write_bytes(b"unchanged original source sentinel")
    database.chmod(0o600)
    recipe = tmp_path / "recipe.json"
    recipe.write_text("{}")
    recipe.chmod(0o600)
    destination = sibling / ".." / "source" / "nested-output"
    before = source.stat().st_mtime_ns

    def forbidden(*args, **kwargs):
        pytest.fail("Source overlap must be rejected before recipe parsing or staging")

    monkeypatch.setattr(operator, "_private_bytes", forbidden)
    monkeypatch.setattr(operator.tempfile, "TemporaryDirectory", forbidden)
    arguments = (
        {"source_roots": {"input": source}}
        if kind in operator.MULTI_SOURCE_KINDS
        else {"source_root": source}
    )
    with pytest.raises(CompanyStoreError, match="outside"):
        operator.run(kind, recipe, destination, repository=tmp_path, **arguments)
    assert source.stat().st_mtime_ns == before
    assert list(source.iterdir()) == [database]
    assert database.read_bytes() == b"unchanged original source sentinel"
