"""Normally emitted source pointers and fresh native clock joins, without audit outcomes."""

from copy import deepcopy

import pytest

from enterprise.audit_suite import company_operating_depth_runtime as depth
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite import test_company_operating_depth_runtime as source


def emitter(monkeypatch, width, fault=None, iam_fault=False):
    original = source.original

    def transform(store, value):
        if type(value) is dict:
            if set(value) == depth.PIN:
                result = deepcopy(value)
                if width != 6:
                    with store._db() as db:
                        row, _ = depth.selected(db, result, "2028-01-16T13:00:00.000000+00:00")
                    for field in (
                        "event_at",
                        "available_at",
                        *(["imported_at"] if width == 9 else []),
                    ):
                        result[field] = row[field]
                return result
            return {k: transform(store, v) for k, v in value.items()}
        if type(value) is list:
            return [transform(store, v) for v in value]
        return value

    def append(store, system, record, body, *args, **kwargs):
        body = deepcopy(body)
        if body.get("schema") == "SH_COMPANY_PERSON_ACCESS_RECORD_V1":
            body = transform(store, body)
            if iam_fault and system == "periodic_review_population":
                body["members"][0]["accounts"][0]["source"]["event_at"] = "2027-01-02T00:00:00Z"
            # These new OWN records are emitted normally with their newly constructed
            # pointer shape; their membership digest is computed before emission.
            if "members" in body:
                body["membership_sha256"] = sha(encoded(body["members"]))
            if "population" in body:
                with store._db() as db:
                    _, population = depth.selected(
                        db, depth.pin(body["population"]), "2028-01-16T13:00:00.000000+00:00"
                    )
                body["population_sha256"] = population["membership_sha256"]
            if fault and system == "monthly_reconciliation" and record == "2027-01":
                key, value = fault
                if key == "DELETE":
                    del body["denominator"][value]
                else:
                    body["denominator"][key] = value
        return original(store, system, record, body, *args, **kwargs)

    monkeypatch.setattr(source, "original", append)


@pytest.mark.parametrize("width", [6, 8, 9])
def test_all_36_source_joins_preserve_known_pointer_shapes_and_bytes(tmp_path, monkeypatch, width):
    emitter(monkeypatch, width)
    store, refs, _ = source.full_period.__wrapped__(tmp_path)
    before = store.path.read_bytes()
    view = depth.person_period_joins(store, references=refs, as_of="2028-01-16T13:00:00Z")
    assert len(view["monthly"]) == 12 and len(view["quarterly"]) == 4
    assert view["complete_registered_2027_period_join"] is True
    assert view["new_population_or_quarter_review_authored"] is False
    assert view["unnamed_other_estate"] == "NOT_ESTABLISHED_BY_REGISTERED_PERSON_SOURCE"
    assert store.path.read_bytes() == before


@pytest.mark.parametrize(
    "width,fault",
    [
        (8, ("event_at", "2027-02-02T00:00:00Z")),
        (8, ("available_at", "2027-02-02T00:00:00Z")),
        (8, ("event_at", True)),
        (8, ("DELETE", "available_at")),
        (8, ("unknown", "not admitted")),
        (8, ("branch", "FOREIGN")),
        (9, ("imported_at", "2025-01-01T00:00:00Z")),
    ],
)
def test_resealed_parent_with_wrong_native_clock_or_shape_refuses_without_write(
    tmp_path, monkeypatch, width, fault
):
    emitter(monkeypatch, width, fault)
    store, refs, _ = source.full_period.__wrapped__(tmp_path)
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError):
        depth.person_period_joins(store, references=refs, as_of="2028-01-16T13:00:00Z")
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("width", [6, 8, 9])
def test_native_account_and_decision_clocks_join_before_local_removal(tmp_path, monkeypatch, width):
    emitter(monkeypatch, width)
    owned = source.iam.__wrapped__(tmp_path)
    store, declaration, *_ = owned
    result = depth.access_followup(store, **source.access_args(owned))
    before = store.path.read_bytes()
    assert depth.access_followup(store, **source.access_args(owned)) == result
    assert store.path.read_bytes() == before
    observation = depth.inspect(store, declaration_pin=declaration, as_of=source.AT)["slots"][0][
        "history"
    ][0]["observation"]
    assert observation["status"] == "REQUESTED_LOCAL_REMOVALS_VERIFIED"
    assert observation["after_states"]["P014:application"]["rights"] == ["inventory-admin"]
    assert observation["old_population_or_review_replaced"] is False
    assert observation["all_rights_authorized"] == "NOT_ESTABLISHED_BY_REMOVAL_ONLY"


def test_account_embedded_clock_mismatch_refuses_before_any_followthrough(tmp_path, monkeypatch):
    emitter(monkeypatch, 8, iam_fault=True)
    owned = source.iam.__wrapped__(tmp_path)
    store, *_ = owned
    before = store.path.read_bytes()
    with pytest.raises(CompanyStoreError, match="Embedded native reference clock differs"):
        depth.access_followup(store, **source.access_args(owned))
    assert store.path.read_bytes() == before
