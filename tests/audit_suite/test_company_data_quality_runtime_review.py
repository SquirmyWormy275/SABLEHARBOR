"""Independent checks of historical correction retries and later source versions."""

from copy import deepcopy

from enterprise.audit_suite import company_data_quality_runtime as runtime
from enterprise.audit_suite.inference import _json as decode
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_activity import ROOT
from tests.audit_suite.test_company_data_quality_runtime import (
    LATER,
    args,
    content,
    corrections,
    plan,
    rows,
    snapshot,
    view,
)


def test_historical_correction_retry_does_not_invalidate_later_transform(tmp_path):
    root = tmp_path / "quality"
    raw = encoded(rows())
    p = root, runtime.initialize(root, repository=ROOT, plan=plan(), raw_records=raw), raw
    request = args(p, "correct", "CORRECT", corrections(p), LATER)
    corrected = runtime.execute(root, **request)
    transformed = runtime.execute(root, **args(p, "transform", at=LATER))
    before = snapshot(p)
    assert runtime.execute(root, **request) == corrected
    assert snapshot(p) == before
    assert view(p)["revision"] == transformed["revision"] == 2
    assert view(p)["state"]["last_transform"]["command_id"] == "transform"


def test_second_correction_keeps_both_originals_and_requires_fresh_transform(tmp_path):
    root = tmp_path / "quality"
    raw = encoded(rows())
    p = root, runtime.initialize(root, repository=ROOT, plan=plan(), raw_records=raw), raw
    first = runtime.execute(root, **args(p, "first", "CORRECT", corrections(p), LATER))
    old_pin = first["outputs"][0]
    old_bytes = content(p, old_pin)
    old_rows = decode(old_bytes)
    replacement = deepcopy(old_rows[0])
    replacement["units"] = 6
    params = {
        "input_pin": old_pin,
        "replacements": [
            {
                "index": 0,
                "before_row_sha256": sha(encoded(old_rows[0])),
                "replacement": replacement,
            }
        ],
    }
    second = runtime.execute(root, **args(p, "second", "CORRECT", params, LATER))
    assert second["outputs"][0]["version"] == 3
    assert second["observation"]["prior_input_pin"] == old_pin
    assert view(p)["state"]["last_transform"] is None
    assert content(p, old_pin) == old_bytes
    assert content(p, p[1]["input_pin"]) == raw
    final = runtime.execute(root, **args(p, "final", at=LATER))
    assert decode(content(p, final["outputs"][1]))["accepted_rows_only_total"] == 24
