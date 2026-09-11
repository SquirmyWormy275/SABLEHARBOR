"""The preserved chart register is hash-gated history, not a broad name exemption."""

from __future__ import annotations

import importlib.util
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
