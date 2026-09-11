"""Preserved chart records and large publications retain narrow integrity boundaries."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def history_module():
    spec = importlib.util.spec_from_file_location(
        "j2_archive_history", ROOT / "scripts/organization_history.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safety_module():
    spec = importlib.util.spec_from_file_location(
        "j2_public_safety", ROOT / "scripts/check_public_safety.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verified_archive_filters_only_explicitly_rejected_review_rows():
    module = history_module()
    text = (ROOT / module.ARCHIVED_SOURCE).read_text()
    scanned = module.current_text(ROOT, module.ARCHIVED_SOURCE, text)
    assert "Daniel Mercer" in scanned
    for name in module.REJECTED.values():
        assert name not in scanned
    assert module.current_text(ROOT, "another/register.json", text) == text


def test_altered_archive_is_not_exempted(tmp_path):
    module = history_module()
    destination = tmp_path / module.ARCHIVED_SOURCE
    destination.parent.mkdir(parents=True)
    payload = (ROOT / module.ARCHIVED_SOURCE).read_bytes() + b"\n"
    destination.write_bytes(payload)
    with pytest.raises(ValueError, match="Archive checksum drift"):
        module.current_text(tmp_path, module.ARCHIVED_SOURCE, payload.decode())


def test_large_chart_allowances_match_only_the_reviewed_bytes():
    module = safety_module()
    assert module.MAX_BYTES == 10 * 1024 * 1024
    for relative in (
        "docs/organization/assets/current/Sable-Harbor-Organization-Charts.pdf",
        "docs/organization/history/v1.0.0/Sable-Harbor-Organization-Charts.pdf",
    ):
        path = ROOT / relative
        assert module.ALLOWED_LARGE_PUBLIC_ARTIFACTS[Path(relative)] == (
            path.stat().st_size,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    unknown = Path("docs/organization/history/unreviewed.pdf")
    assert unknown not in module.ALLOWED_LARGE_PUBLIC_ARTIFACTS


def test_large_publication_with_changed_bytes_is_rejected(tmp_path, monkeypatch):
    module = safety_module()
    relative = Path("docs/organization/history/v1.0.0/Sable-Harbor-Organization-Charts.pdf")
    payload = bytearray((ROOT / relative).read_bytes())
    payload[-1] ^= 1
    destination = tmp_path / relative
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "review_files", lambda: [relative])
    monkeypatch.setattr(sys, "argv", ["check_public_safety.py"])
    with pytest.raises(SystemExit, match="unapproved large file exceeds 10 MiB"):
        module.main()
