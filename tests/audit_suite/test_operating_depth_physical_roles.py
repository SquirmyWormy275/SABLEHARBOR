"""Literal input roles over small, freshly appended fictional native sources.

The calendar shape under a production role is an OWN declaration, not a claim
that an existing production inventory contains this new local calendar.
"""

import json
import os
from copy import deepcopy

import pytest

from enterprise.audit_suite import company_operating_depth_runtime as depth
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from tests.audit_suite import test_company_operating_depth_runtime as prior


def native_state(store):
    with store._db() as db:
        return tuple(db.iterdump())


def proof(root, **fields):
    raw = json.dumps(fields, sort_keys=True, indent=2).encode()
    fd = os.open(root / "ROLE_PROOF.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def business(tmp_path):
    root = tmp_path / "business"
    root.mkdir(mode=0o700)
    return CompanyStore(root)


def alternate_inventory(store, role, *, release=None):
    _, definition = prior.setup_declaration(store, "RESTORE" if release else "IAM", release=release)
    with store._db() as db:
        row, document = depth.selected(db, definition["business_inventory_ref"], prior.AT)
    replacement = prior.original(store, role, "ROLE-INVENTORY", document)
    assert replacement["sha256"] == row["sha256"]
    definition["business_inventory_ref"] = replacement
    current = prior.original(store, "depth_definition", "ROLE-DEPTH", definition, at=prior.AT)
    return current, definition


def admission_and_registration(store, declaration, definition, permitted, role_kind):
    before = native_state(store)
    calls = [
        lambda: depth.declare(
            store, repository=prior.MAIN, declaration_pin=declaration, as_of=prior.AT
        ),
        lambda: depth.register_declaration(
            store,
            repository=prior.MAIN,
            business_inventory_pin=definition["business_inventory_ref"],
            retained_period_refs=[],
            runtime_id="ROLE-REGISTERED",
            actor_id="AS-P007",
            recorded_at=prior.AT,
            command_id="REGISTER-KNOWN-ROLES",
        ),
    ]
    if permitted:
        admitted = calls[0]()
        assert admitted["enterprise_completeness_established"] is False
        assert native_state(store) == before  # declare is a read-only census.
        registered = calls[1]()
        assert registered["system"] == "operating_depth_definition"
    else:
        for call in calls:
            with pytest.raises(CompanyStoreError, match="physical " + role_kind + " role"):
                call()
            assert native_state(store) == before
    return before


@pytest.mark.parametrize(
    "role,permitted",
    [
        ("business_inventory", True),
        ("person-access-history.account_system_inventory", False),
        ("unrelated_family", False),
        ("invented.business_inventory", False),
    ],
)
def test_inventory_literal_roles_and_no_append(tmp_path, role, permitted):
    store = business(tmp_path)
    declaration, definition = alternate_inventory(store, role)
    before = admission_and_registration(
        store, declaration, definition, permitted, "business inventory"
    )
    proof(
        tmp_path,
        input_role=role,
        permitted=permitted,
        identical_inventory_body=True,
        no_native_append_on_refusal=not permitted and native_state(store) == before,
        engineering_fixture_only=True,
    )


@pytest.mark.parametrize(
    "role,permitted",
    [
        ("site_release", True),
        ("transition.site_release", True),
        ("unrelated_family", False),
        ("invented.site_release", False),
    ],
)
def test_commissioning_literal_roles_and_no_append(tmp_path, role, permitted):
    store = business(tmp_path)
    document = dict(
        fictional_in_universe_operating_release=True,
        status="OPERATING_RECOVERY_SIMULATED",
    )
    original = prior.original(store, "site_release", "ORIGINAL-RELEASE", document, at=prior.START)
    replacement = prior.original(store, role, "ROLE-RELEASE", document, at=prior.START)
    assert replacement["sha256"] == original["sha256"]
    declaration, definition = alternate_inventory(store, "business_inventory", release=replacement)
    before = admission_and_registration(store, declaration, definition, permitted, "commissioning")
    proof(
        tmp_path,
        input_role=role,
        permitted=permitted,
        identical_release_body=True,
        no_native_append_on_refusal=not permitted and native_state(store) == before,
        engineering_fixture_only=True,
    )


def test_exclusion_reference_keeps_explicit_generic_documentary_scope(tmp_path):
    store = business(tmp_path)
    _, definition = prior.setup_declaration(store, "IAM")
    exclusion_source = prior.original(
        store,
        "specific_operating_decision",
        "EXCLUDED-SYSTEM-DECISION",
        {"decision": "Explicitly outside this local IAM followthrough calendar."},
    )
    exclusion = dict(
        system_id="excluded-service",
        reason="Outside the separately declared local operation scope.",
        source_ref=exclusion_source,
    )
    definition["exclusions"] = [exclusion]
    with store._db() as db:
        _, inventory = depth.selected(db, definition["business_inventory_ref"], prior.AT)
    inventory = deepcopy(inventory)
    inventory["systems"].append({"system": "excluded-service", "owner": "AS-P007"})
    inventory["operating_depth_calendar"]["exclusions"] = [exclusion]
    definition["business_inventory_ref"] = prior.original(
        store, "business_inventory", "EXCLUDED-INVENTORY", inventory
    )
    declaration = prior.original(
        store, "depth_definition", "EXCLUDED-DEPTH", definition, at=prior.AT
    )
    before = native_state(store)
    result = depth.declare(
        store, repository=prior.MAIN, declaration_pin=declaration, as_of=prior.AT
    )
    assert result["enterprise_completeness_established"] is False
    assert native_state(store) == before
    proof(tmp_path, exclusion_role=exclusion_source["system"], admitted=True, no_native_append=True)


@pytest.mark.parametrize(
    "role,permitted",
    [
        ("service_criterion", True),
        ("unrelated_family", False),
        ("invented.service_criterion", False),
        ("bcm.technical_objectives", False),
    ],
)
def test_genuine_restore_criterion_literal_roles_and_no_append(
    tmp_path, monkeypatch, role, permitted
):
    """Reuse the existing real copy/restore/read fixture, changing only source role."""
    original = prior.original
    restore_return = depth.restore_return
    seen = {}

    def source(store, system, record, document, **kwargs):
        reference = original(store, system, record, document, **kwargs)
        if system != "service_criterion":
            return reference
        alternate = original(store, role, "ROLE-RETURN-CRITERION", document, **kwargs)
        assert alternate["sha256"] == reference["sha256"]
        seen["source"] = alternate
        return alternate

    def checked_return(store, **kwargs):
        before = native_state(store)
        seen["entered_restore_return"] = True
        try:
            return restore_return(store, **kwargs)
        except CompanyStoreError as error:
            if permitted:
                # Preserve the prior genuine copied-file tamper refusal too.
                assert native_state(store) == before
                raise
            assert not permitted
            assert "physical service criterion role" in str(error)
            assert native_state(store) == before
            seen["no_native_append_on_refusal"] = True
            raise

    monkeypatch.setattr(prior, "original", source)
    monkeypatch.setattr(depth, "restore_return", checked_return)
    if permitted:
        prior.test_real_restore_return_capacity_and_age_criterion(tmp_path)
    else:
        with pytest.raises(CompanyStoreError, match="physical service criterion role"):
            prior.test_real_restore_return_capacity_and_age_criterion(tmp_path)
    assert seen["entered_restore_return"] and seen["source"]["system"] == role
    assert permitted or seen["no_native_append_on_refusal"]
    proof(
        tmp_path,
        input_role=role,
        permitted=permitted,
        identical_criterion_body=True,
        genuine_copy_restore_and_use_probe=True,
        no_native_append_on_refusal=seen.get("no_native_append_on_refusal", False),
        engineering_fixture_only=True,
    )
