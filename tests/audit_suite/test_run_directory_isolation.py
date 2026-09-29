from types import SimpleNamespace

import pytest

from enterprise.audit_suite.generation import epoch_directory, run_directory
from enterprise.audit_suite.store import DomainError


@pytest.mark.parametrize("level", ["worlds", "engagement", "epoch"])
@pytest.mark.parametrize("dangling", [False, True])
def test_private_directory_alias_rejected_before_creating_or_reading_target(
    tmp_path, level, dangling
):
    base = tmp_path / "private"
    base.mkdir(mode=0o700)
    outside = tmp_path / "other-engagement"
    if not dangling:
        outside.mkdir()
        (outside / "private-answer.json").write_text("Other engagement only")
    engine = SimpleNamespace(store=SimpleNamespace(root=base))
    if level == "worlds":
        alias = base / "worlds"
    elif level == "engagement":
        (base / "worlds").mkdir()
        alias = base / "worlds" / "ENG-abcdef"
    else:
        alias = run_directory(engine, "ENG-abcdef") / "scope-00001"
    alias.symlink_to(outside, target_is_directory=True)
    before = sorted(p.relative_to(outside) for p in outside.rglob("*")) if outside.exists() else []
    with pytest.raises(DomainError, match="symlink|isolated|alias"):
        epoch_directory(engine, "ENG-abcdef", 1)
    assert outside.exists() is not dangling
    assert (
        sorted(p.relative_to(outside) for p in outside.rglob("*")) if outside.exists() else []
    ) == before


def test_epochs_are_distinct_real_directories_and_files_are_rejected(tmp_path):
    engine = SimpleNamespace(store=SimpleNamespace(root=tmp_path))
    root = run_directory(engine, "ENG-abcdef")
    first = epoch_directory(engine, "ENG-abcdef", 1)
    second = epoch_directory(engine, "ENG-abcdef", 2)
    assert first.parent == second.parent == root
    assert first.resolve() == first and second.resolve() == second and first != second
    assert epoch_directory(engine, "ENG-abcdef", 1) == first
    (root / "scope-00003").write_text("not a directory")
    with pytest.raises(DomainError):
        epoch_directory(engine, "ENG-abcdef", 3)
