import json

import pytest

from tools.evidence.closeout import runtime_cases, sha, verify


def test_denied_disclosures_never_return_payload():
    cases = runtime_cases()
    assert all(row["passed"] for row in cases)
    disclosures = [row for row in cases if row["case_id"].startswith("ACCESS-")]
    assert len(disclosures) == 63
    denied = [row for row in disclosures if row["observed"]["authorization"] == "DENY"]
    assert len(denied) == 54
    assert all(row["observed"]["context"] == [] for row in denied)
    lifecycle = next(row for row in cases if row["case_id"] == "LIFECYCLE-HOLD-RESTORE")
    assert lifecycle["observed"]["restored"] == {}
    assert lifecycle["observed"]["records"]["held"]["payload"] == "synthetic held bytes"


def test_verifier_rejects_tampering_and_incomplete_population(tmp_path):
    record = tmp_path / "observations.json"
    record.write_text("{}")
    manifest = {"files": {record.name: sha(record)}, "dirty_review": False, "passed": True}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    assert verify(tmp_path) == manifest
    record.write_text('{"forged": true}')
    with pytest.raises(ValueError, match="hash mismatch"):
        verify(tmp_path)
    record.unlink()
    with pytest.raises(ValueError, match="population"):
        verify(tmp_path)


@pytest.mark.parametrize("dirty,passed", [(True, True), (False, False)])
def test_verifier_rejects_review_or_failed_evidence(tmp_path, dirty, passed):
    manifest = {"files": {}, "dirty_review": dirty, "passed": passed}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="cannot qualify"):
        verify(tmp_path)
