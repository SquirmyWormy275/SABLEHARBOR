import json
from dataclasses import asdict
from pathlib import Path

import pytest

from enterprise.audit_suite.company_store import CompanyStoreError
from tests.audit_suite.test_company_activity import recipe
from tools.audit_suite import generate_company_activity as operator

ROOT = Path(__file__).resolve().parents[2]


def prepare(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path / "recipe.json"
    source.write_text(json.dumps(asdict(recipe())))
    source.chmod(0o600)
    return source


def test_operator_generates_private_sources_without_audit_or_grants(tmp_path):
    source = prepare(tmp_path)
    result = operator.run("mover", source, tmp_path / "result", repository=ROOT)
    assert result["counts"] == {"systems": 10, "versions": 20, "grants": 0, "collections": 0}
    assert (tmp_path / "result" / "RECIPE.json").read_bytes() == source.read_bytes()
    assert not list((tmp_path / "result").rglob("engagements.sqlite3"))
    assert all(not p.stat().st_mode & 0o077 for p in (tmp_path / "result").rglob("*"))
    with pytest.raises(CompanyStoreError, match="New private"):
        operator.run("mover", source, tmp_path / "result", repository=ROOT)


def test_bad_recipe_and_generator_failure_never_leave_destination(tmp_path, monkeypatch):
    source = prepare(tmp_path)
    bad = json.loads(source.read_text())
    bad["unexpected"] = "not accepted"
    source.write_text(json.dumps(bad))
    with pytest.raises(CompanyStoreError, match="Invalid explicit"):
        operator.run("mover", source, tmp_path / "bad", repository=ROOT)
    assert not (tmp_path / "bad").exists()
    source.write_text(json.dumps(asdict(recipe())))

    def fail(store, **kwargs):
        store.register_system("CO", "branch", "system", "owner")
        raise RuntimeError("injected partial generation")

    monkeypatch.setitem(operator.KINDS, "mover", (operator.TransferRecipe, fail))
    with pytest.raises(RuntimeError, match="partial generation"):
        operator.run("mover", source, tmp_path / "failed", repository=ROOT)
    assert not (tmp_path / "failed").exists()
    assert not list(tmp_path.glob(".company-activity-*"))


def test_public_or_aliased_recipe_denied_before_output(tmp_path):
    source = prepare(tmp_path)
    source.chmod(0o644)
    with pytest.raises(CompanyStoreError, match="Private regular"):
        operator.run("mover", source, tmp_path / "public", repository=ROOT)
    source.chmod(0o600)
    alias = tmp_path / "alias.json"
    alias.symlink_to(source)
    with pytest.raises(CompanyStoreError, match="aliases"):
        operator.run("mover", alias, tmp_path / "aliased", repository=ROOT)


@pytest.mark.parametrize("kind,versions", [("training", 29), ("backup", 51), ("change", 32)])
def test_nested_training_recipe_and_computed_backup_adapter(tmp_path, kind, versions):
    from tests.audit_suite.test_company_backup_activity import recipe as backup_recipe
    from tests.audit_suite.test_company_change_activity import recipe as change_recipe
    from tests.audit_suite.test_company_training_activity import recipe as training_recipe

    source = prepare(tmp_path)
    value = {"training": training_recipe, "backup": backup_recipe, "change": change_recipe}[kind]()
    source.write_text(json.dumps(asdict(value)))
    result = operator.run(kind, source, tmp_path / "result", repository=ROOT)
    assert result["counts"]["versions"] == versions
    assert result["counts"]["grants"] == result["counts"]["collections"] == 0
    import hashlib

    for name, expected in result["members"].items():
        assert hashlib.sha256((tmp_path / "result" / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize(
    "raw",
    [
        '{"company_id":"first","company_id":"second"}',
        '{"company_id":NaN}',
        '{"company_id":Infinity}',
    ],
)
def test_ambiguous_or_nonfinite_recipe_rejected_before_generation(tmp_path, monkeypatch, raw):
    source = prepare(tmp_path)
    source.write_text(raw)

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid JSON must never reach recipe construction")

    monkeypatch.setitem(operator.KINDS, "mover", (forbidden, forbidden))
    with pytest.raises(CompanyStoreError, match="Invalid explicit"):
        operator.run("mover", source, tmp_path / "result", repository=ROOT)
    assert not (tmp_path / "result").exists()


def test_training_manifest_pins_every_published_file(tmp_path):
    from tests.audit_suite.test_company_training_activity import recipe as training_recipe

    source = prepare(tmp_path)
    source.write_text(json.dumps(asdict(training_recipe())))
    result = operator.run("training", source, tmp_path / "result", repository=ROOT)
    published = {
        str(p.relative_to(tmp_path / "result"))
        for p in (tmp_path / "result").rglob("*")
        if p.is_file() and p.name != "MANIFEST.json"
    }
    assert "company/SOURCE_RECEIPT.json" in published
    assert set(result["members"]) == published


def test_recipe_growth_after_size_check_is_still_bounded(tmp_path, monkeypatch):
    source = prepare(tmp_path)
    original_open = operator.os.open

    def grow_before_open(path, flags, *args, **kwargs):
        if Path(path) == source:
            with source.open("ab") as stream:
                stream.write(b" " * operator.MAX_RECIPE_BYTES)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(operator.os, "open", grow_before_open)
    with pytest.raises(CompanyStoreError, match="bounded size"):
        operator.run("mover", source, tmp_path / "result", repository=ROOT)
    assert not (tmp_path / "result").exists()


def test_configuration_operator_reads_pinned_change_sources_without_mutation(tmp_path):
    import hashlib

    from tests.audit_suite.test_company_configuration_activity import inputs

    source_root, recipe_value, _ = inputs.__wrapped__(tmp_path)
    source = tmp_path / "configuration-recipe.json"
    source.write_text(json.dumps(asdict(recipe_value)))
    source.chmod(0o600)
    original = (source_root / "company.sqlite3").read_bytes()
    result = operator.run(
        "configuration",
        source,
        tmp_path / "configuration-output",
        repository=ROOT,
        source_root=source_root,
    )
    assert result["counts"] == {"systems": 6, "versions": 12, "grants": 0, "collections": 0}
    assert result["source_input"]["source_versions_sha256"] == recipe_value.source_versions_sha256
    assert (source_root / "company.sqlite3").read_bytes() == original
    for name, expected in result["members"].items():
        assert (
            hashlib.sha256((tmp_path / "configuration-output" / name).read_bytes()).hexdigest()
            == expected
        )
    with pytest.raises(CompanyStoreError, match="outside"):
        operator.run(
            "configuration",
            source,
            source_root / "nested-output",
            repository=ROOT,
            source_root=source_root,
        )
    assert not (source_root / "nested-output").exists()


def test_source_dependency_must_be_explicit_and_kind_specific(tmp_path):
    source = prepare(tmp_path)
    with pytest.raises(CompanyStoreError, match="explicit source root"):
        operator.run("configuration", source, tmp_path / "cfg", repository=ROOT)
    with pytest.raises(CompanyStoreError, match="only for configuration"):
        operator.run("mover", source, tmp_path / "mover", repository=ROOT, source_root=tmp_path)
    assert not (tmp_path / "cfg").exists() and not (tmp_path / "mover").exists()
