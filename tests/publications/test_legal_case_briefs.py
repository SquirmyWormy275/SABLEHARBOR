"""Briefs must retain their stated scope and detect source drift."""

import json

import pytest

from tools.legal_gaps import case_briefs


def test_five_scoped_briefs_and_publication():
    case_briefs.validate()
    records = json.loads((case_briefs.HERE / "source.json").read_text())["cases"]
    mixed = next(r for r in records if r["id"] == "SH-CASE-RECON-01")
    assert "Do not combine" in mixed["deliverable"]
    close = next(r for r in records if r["id"] == "SH-CASE-CLOSE-01")
    assert "ARU_GROUP" in close["period"] and "January 2027" in close["period"]
    assert "forecast" in close["limits"]


def test_changed_input_invalidates_brief(monkeypatch):
    real_sha = case_briefs.sha
    monkeypatch.setattr(
        case_briefs, "sha", lambda p: "0" * 64 if p.name == "source.json" else real_sha(p)
    )
    with pytest.raises(AssertionError, match="Stale brief input"):
        case_briefs.validate()


def test_validation_does_not_require_browser_runtime():
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.modules['playwright'] = None; "
            "from tools.legal_gaps.case_briefs import validate; validate()",
        ],
        cwd=case_briefs.ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
