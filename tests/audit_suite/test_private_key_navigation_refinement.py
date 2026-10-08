"""Optional literal saved metadata over normal OWN source-bound Key stores."""

# ruff: noqa: F811
# Imported pytest fixture is intentionally named by the test parameters.
import hashlib
from copy import deepcopy

import pytest

from enterprise.audit_suite.instructor_key_views import validate_user
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_instructor_key_views import request, views  # noqa: F401


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_literal_facets_restore_exact_source_and_old_rows_unchanged(views):
    core, engine, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    before = engine.store.get(actor, eid)
    source_sha = sha(engine.company_store.path)
    old = request(core, args)
    saved_old = core.save(actor, eid, old)
    assert saved_old["user"] == old["user"]
    assert "source_filters" not in saved_old["user"]
    value = request(core, args, command_id="new-source-facets")
    value["user"]["source_filters"] = {"system": "SYS", "visibility": "FUTURE_UNAVAILABLE"}
    # Selected R1 remains exactly pinned outside the intentionally empty scope/filter.
    saved = core.save(actor, eid, value)
    restored = core.restore(
        actor,
        eid,
        saved["id"],
        {
            "expected_version": 1,
            "expected_engagement_revision": before["revision"],
            "expected_key_pin": saved["key_pin"],
        },
    )
    assert restored["navigation"] == value["user"]
    assert restored["navigation"]["source"] == old["user"]["source"]
    assert engine.store.get(actor, eid) == before
    assert sha(engine.company_store.path) == source_sha


def test_literal_archive_review_facets_and_hash_query(views):
    core, engine, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    before = engine.store.get(actor, eid)
    row = core._context(actor, eid, "ARCHIVE")["data"]["entries"][0]
    value = request(core, args, "ARCHIVE")
    value["user"]["query"] = row["raw_sha256"]
    value["user"]["review_facets"] = {k: row["review"][k] for k in ("causal_validation", "grading")}
    saved = core.save(actor, eid, value)
    assert saved["user"] == value["user"]
    assert core.save(actor, eid, value) == saved
    assert engine.store.get(actor, eid) == before


@pytest.mark.parametrize(
    "kind,field,bad",
    [
        ("BOUND", "source_filters", {"system": "foreign", "visibility": None}),
        ("BOUND", "source_filters", {"system": None, "visibility": "future"}),
        ("BOUND", "source_filters", {"system": None, "visibility": None, "owner": "inferred"}),
        ("BOUND", "source_filters", None),
        ("ARCHIVE", "review_facets", {"causal_validation": "CERTIFIED", "grading": None}),
        ("ARCHIVE", "review_facets", {"causal_validation": None, "grading": False}),
        (
            "ARCHIVE",
            "review_facets",
            {"causal_validation": None, "grading": None, "severity": "HIGH"},
        ),
    ],
)
def test_unknown_or_malformed_facets_refuse_without_private_or_formal_write(
    views, kind, field, bad
):
    core, engine, args = views
    actor, eid = args["instructor_id"], args["engagement_id"]
    before = engine.store.get(actor, eid)
    value = deepcopy(request(core, args, kind))
    value["user"][field] = bad
    with pytest.raises(DomainError):
        core.save(actor, eid, value)
    assert core.listing(actor, eid, kind)["views"] == []
    assert engine.store.get(actor, eid) == before


def test_legacy_shapes_remain_literal_without_new_defaults(views):
    core, _, args = views
    for kind in ("BOUND", "ARCHIVE"):
        user = request(core, args, kind)["user"]
        assert validate_user(kind, deepcopy(user)) == user
