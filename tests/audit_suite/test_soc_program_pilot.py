"""Portable pilot reads Git-delivered originals and keeps answers out of setup."""

import copy

import pytest

from tools.audit_suite import soc_program_pilot as pilot


def test_portable_template_is_source_bound_and_blind():
    submission = pilot.template()
    assert submission["schema"] == pilot.SCHEMA
    assert {h: len(submission["source_inventory"][h]) for h in pilot.HISTORIES} == {
        "history-01": 39,
        "history-02": 55,
    }
    assert all(
        value is None
        for history in submission["histories"].values()
        for task in history.values()
        for value in task["observations"].values()
    )
    assert all(
        "expected" not in row
        for records in submission["source_inventory"].values()
        for row in records
    )


def test_submission_rejects_tampered_inventory_and_unfinished_answers():
    _, selected = pilot.load_source()
    submission = pilot.template()
    submission["prepared_by"] = "auditor"
    with pytest.raises(ValueError, match="incomplete observations"):
        pilot.validate_submission(submission, selected)
    tampered = copy.deepcopy(submission)
    tampered["source_inventory"]["history-01"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="inventory changed"):
        pilot.validate_submission(tampered, selected)


def test_extended_edition_cannot_carry_a_changed_selected_record(tmp_path):
    import hashlib
    import json
    import shutil

    from tools.audit_suite import company_record_delivery as delivery

    consumer = tmp_path / "company-records"
    shutil.copytree(pilot.SOURCE_ROOT, consumer)
    manifest_path = consumer / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["snapshot"]["authored_extensions"]
    _, selected = pilot.load_source(consumer)
    row = next(r for r in manifest["records"] if r["path"] == sorted(selected)[0])
    member = consumer / row["path"]
    content = member.read_bytes().replace(b"{", b'{"changed":true,', 1)
    member.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    row.update(bytes=len(content), source_bytes=len(content), sha256=digest, source_sha256=digest)
    manifest_path.write_bytes(delivery.encoded(manifest))
    delivery.verify(consumer)
    with pytest.raises(ValueError, match="differ from the pinned edition"):
        pilot.load_source(consumer)
