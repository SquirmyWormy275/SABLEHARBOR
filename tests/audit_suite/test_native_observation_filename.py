"""New transport filenames; native slot and record identities stay literal."""

import hashlib
import json
from pathlib import Path

import pytest

from enterprise.audit_suite import company_operating_depth_runtime as depth
from enterprise.audit_suite.artifacts import DomainError
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.source_library_audit import typed_content
from tests.audit_suite import test_company_operating_depth_runtime as prior_depth
from tests.audit_suite import test_company_operating_source_edition as prior_edition

OLD_ROWS = Path(
    "/home/kingoftheeast/SABLEHARBOR-source-edition-publication-integration-review-20261003/"
    "depth-observation-filename-counter-v1/EXACT_NATIVE_OBSERVATION_ROWS.json"
)
OLD_ROWS_SHA = "9e523ad063dfef3bbe1fc69bf338972be37f81aaed031163cc058542320ef437"


def expected_name(row, body):
    identity = [
        row["company"],
        row["branch"],
        row["system"],
        body["declaration_pin"]["record"],
        body["slot"]["slot_id"],
    ]
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest() + ".json"


def collect_observations(root, at):
    store = CompanyStore(root)
    with store._db() as db:
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM versions WHERE system=? ORDER BY company,branch,record,version",
                (depth.SYSTEM,),
            )
        ]
    assert rows
    names, identities = {}, {}
    for number, row in enumerate(rows):
        body = json.loads(row["content"])
        provenance = json.loads(row["provenance"])
        assert ":" in body["slot"]["slot_id"]
        assert row["record"] == body["declaration_pin"]["record"] + ":" + body["slot"]["slot_id"]
        assert provenance == {
            "source_reference": body["declaration_pin"]["record"],
            "name": expected_name(row, body),
            "content_type": "application/json",
            "qualification": depth.QUALIFICATION,
        }
        key = (row["company"], row["branch"], row["system"], row["record"])
        assert names.setdefault(provenance["name"], key) == key
        assert identities.setdefault(key, provenance["name"]) == provenance["name"]
        store.grant("OWN-NAME-AUDITOR", "OWN-NAME-AUDIT", *key[:3])
        receipt = store.collect(
            "OWN-NAME-AUDITOR",
            "OWN-NAME-AUDIT",
            *key,
            version=row["version"],
            as_of=at,
            command_id="OWN-NAME-COL-" + str(number),
        )
        actual = store.read_version(
            "OWN-NAME-AUDITOR",
            "OWN-NAME-AUDIT",
            *key,
            version=row["version"],
            as_of=at,
        )
        document, mime = typed_content(actual)
        assert (
            mime == "application/json" and document == body and actual["content"] == row["content"]
        )
        assert receipt["source"]["sha256"] == row["sha256"]
    return rows


def test_real_restore_return_and_failed_return_keep_literal_slot_and_collect(tmp_path):
    prior_depth.test_real_restore_return_capacity_and_age_criterion(tmp_path)
    rows = collect_observations(tmp_path / "business", "2028-01-17T00:00:00Z")
    assert len(rows) == 2
    assert {json.loads(r["content"])["observation"]["status"] for r in rows} == {
        "PASS_LOCAL_SERVICE_RETURN_CRITERION",
        "FAIL_LOCAL_RESTORE_NO_RETURN",
    }
    assert len({json.loads(r["provenance"])["name"] for r in rows}) == 1


def test_completed_source_edition_all_new_observations_have_distinct_safe_identity_names(
    tmp_path, monkeypatch
):
    owned = prior_edition.owned.__wrapped__(
        prior_depth.full_period.__wrapped__(tmp_path), tmp_path, monkeypatch
    )
    prior_edition.test_source_first_real_policy_retry_copy_restore_failure_and_late36(owned)
    rows = collect_observations(tmp_path / "edition/company", owned["plan"]["finish_at"])
    assert len({r["record"] for r in rows}) >= 3
    assert {json.loads(r["content"])["kind"] for r in rows} >= {"RESTORE", "POLICY", "RETRY"}


def test_preserved_old_colon_counter_remains_invalid_and_unmodified():
    if not OLD_ROWS.is_file():
        pytest.skip("Requires the preserved private historical observation counter")
    before = OLD_ROWS.stat()
    raw = OLD_ROWS.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == OLD_ROWS_SHA
    for item in json.loads(raw):
        row = dict(item["row"])
        row["content"] = bytes.fromhex(row.pop("content_hex"))
        row["provenance"] = json.loads(row["provenance"])
        with pytest.raises(DomainError, match="Invalid artifact filename"):
            typed_content(row)
    after = OLD_ROWS.stat()
    assert all(
        getattr(before, k) == getattr(after, k)
        for k in (
            "st_dev",
            "st_ino",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
            "st_mode",
            "st_nlink",
        )
    )
    assert hashlib.sha256(OLD_ROWS.read_bytes()).hexdigest() == OLD_ROWS_SHA
