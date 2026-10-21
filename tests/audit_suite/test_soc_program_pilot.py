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
