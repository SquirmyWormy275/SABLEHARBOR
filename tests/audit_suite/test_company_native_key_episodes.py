"""Authoring boundaries; no fixtures, audit outcomes or runtime acceptance."""

import hashlib
import json
from copy import deepcopy

import pytest

from enterprise.audit_suite.company_native_key_episodes import (
    BRANCHES,
    Originals,
    digest,
    source_scene,
    task_facet,
)

A = BRANCHES["CLEAN"]
B = BRANCHES["MESSY"]


def original(
    system="method.authority",
    record="RULE",
    version=1,
    branch=A,
    doc=None,
    at="2027-01-01T00:00:00Z",
):
    raw = json.dumps(
        doc or {"status": "APPROVED", "scope_limit": "ONE_SELECTED_LOCAL_SCOPE"}, sort_keys=True
    ).encode()
    return {
        "company": "TEST-PRIVATE",
        "branch": branch,
        "system": system,
        "record": record,
        "version": version,
        "content": raw,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "event_at": at,
        "available_at": at,
        "imported_at": "2026-10-01T00:00:00Z",
    }


def holder(rows):
    return Originals(rows, [{k: r[k] for k in ("company", "branch", "system")} for r in rows])


def reference(row):
    return {k: v for k, v in row.items() if k != "content"}


def spec(systems=None):
    return {
        "id": "EPISODE-TEST",
        "title": "One exact declared decision",
        "cause_identity": {"decision": "RULE"},
        "control_ids": ["C1"],
        "systems": systems or ["method.authority", "method.operation", "method.population"],
        "fields": ["status", "scope_limit", "members", "decision"],
        "headline_fields": ["status", "decision"],
        "interpretation": "Rule, action and denominator are separate.",
        "unknowns": "Full enterprise authority remains unproved.",
    }


@pytest.mark.parametrize("version", [True, False, 0, -1, 1.0, "1"])
def test_strict_native_version(version):
    with pytest.raises(ValueError, match="Strict positive"):
        holder([original(version=version)])


def test_changed_original_bytes_rejected():
    r = original()
    r["content"] = b'{"status":"APPROVED"}'
    with pytest.raises(ValueError, match="pin changed"):
        holder([r])


def test_duplicate_native_version_rejected():
    r = original()
    with pytest.raises(ValueError, match="Distinct original"):
        holder([r, deepcopy(r)])


def test_unadmitted_role_excluded_and_scene_refused():
    r = original()
    o = Originals([r], [])
    assert len(o.unadmitted) == 1 and not o.ids
    with pytest.raises(ValueError, match="admitted physical"):
        source_scene(o, spec(), A)


def test_fully_repaired_role_substitute_does_not_establish_authority():
    r = original(system="method.meeting_note")
    o = holder([r])
    assert o.exact_reference(reference(r), A, systems={"method.authority"}) == (
        None,
        "WRONG_NATIVE_PHYSICAL_ROLE",
    )


def test_fully_repaired_foreign_branch_reference_refused():
    r = original(branch=B)
    o = holder([r])
    assert o.exact_reference(reference(r), A) == (None, "FOREIGN_BRANCH_NOT_AUTHORITY")


def test_hash_resealed_reference_not_original():
    r = original()
    o = holder([r])
    ref = reference(r)
    ref["sha256"] = "f" * 64
    assert o.exact_reference(ref, A)[0] is None


def test_future_publication_cannot_be_prior_input():
    r = original(at="2027-02-01T00:00:00Z")
    o = holder([r])
    assert o.exact_reference(reference(r), A, before="2027-01-01T00:00:00Z") == (
        None,
        "ORIGINAL_UNAVAILABLE_AT_OCCURRENCE",
    )


def test_original_namespace_alias_not_remapped():
    r = original()
    o = holder([r])
    ref = reference(r)
    ref["system_id"] = ref.pop("system")
    ref["record_id"] = ref.pop("record")
    assert o.exact_reference(ref, A) == (None, "UNTYPED_ORIGINAL_DECLARATION_NOT_AUTHORITY")


def test_clock_header_difference_refused():
    r = original()
    o = holder([r])
    ref = reference(r)
    ref["event_at"] = "2027-01-02T00:00:00Z"
    assert o.exact_reference(ref, A) == (None, "ORIGINAL_CLOCK_MISMATCH")


def test_all_members_preserved_in_one_typed_array_not_fanout():
    members = [{"id": str(i), "decision": "REMOVE"} for i in range(1695)]
    r = original(system="method.population", doc={"members": members, "status": "SCOPED"})
    o = holder([r])
    chapter = source_scene(o, spec(), A)
    f = next(o.facts[f] for f in chapter["native_fact_ids"] if o.facts[f]["locator"] == "/members")
    assert f["value"] == members and f["typed_value_sha256"] == digest(members)
    assert len(chapter["source_ids"]) == 1


def test_later_correction_does_not_replace_original():
    r = original(system="method.operation", record="STATE", doc={"status": "INVALID"})
    c = original(
        system="method.operation",
        record="STATE",
        version=2,
        at="2028-01-15T00:00:00Z",
        doc={"status": "CORRECTED"},
    )
    o = holder([r, c])
    s = source_scene(o, spec(), A)
    delta = next(x for x in s["dated_history_changes"] if x["locator"] == "/status")
    assert delta["prior_value"] == "INVALID" and delta["later_value"] == "CORRECTED"
    assert delta["later_does_not_replace_earlier_tested_state"] is True
    assert o.source(o.source_id(c))["period_classification"] == "POST_PERIOD"


def test_stored_query_never_runs(tmp_path):
    target = tmp_path / "must-not-exist"
    r = original(
        doc={
            "status": "APPROVED",
            "stored_query": f"__import__('pathlib').Path({str(target)!r}).touch()",
        }
    )
    source_scene(holder([r]), spec(), A)
    assert not target.exists()


def test_distinct_design_action_and_population_witnesses():
    rows = [
        original(),
        original(system="method.operation", record="ACTION", doc={"decision": "REFUSED"}),
        original(
            system="method.population", record="DUE", doc={"members": ["one"], "status": "SCOPED"}
        ),
    ]
    o = holder(rows)
    s = source_scene(o, spec(), A)
    out = []
    for kind in ("TOD", "IMPLEMENTATION", "TOE"):
        t = {
            "task_id": kind,
            "control_id": "C1",
            "batch": "B0",
            "metadata": {"kind": kind, "authored_instruction": "Test this exact attribute."},
            "contract": {
                "performed": "Selected context only.",
                "unperformed": "Full enterprise period is not established.",
            },
        }
        out.append(task_facet(o, t, [s]))
    assert len({x["distinct_witness_question"] for x in out}) == 3
    assert len({tuple(x["native_role_source_ids"]) for x in out}) == 3
    assert all(x["professional_qualified_owner_or_grade_acceptance"] == "NOT_ASSERTED" for x in out)


def test_exact_clause_keeps_source_status_hold():
    rows = [
        original(
            system="legal.provision_locator",
            doc={
                "detail": {
                    "provision": {"id": "45-CFR-160.101"},
                    "qualified_review_status": "OPEN_2027_PRIMARY_AND_FACT_RECHECK",
                    "applicability_status": "UNDETERMINED",
                },
                "2027_legal_text_verified": False,
                "source_complete": False,
            },
        ),
        original(
            system="legal.provision_locator",
            record="OTHER",
            doc={"detail": {"provision": {"id": "45-CFR-160.104"}}},
        ),
    ]
    o = holder(rows)
    sp = spec(["legal.provision_locator"])
    sp["fields"] = ["detail", "source_complete"]
    s = source_scene(o, sp, A)
    t = {
        "task_id": "TASK-CHECK-HIPAA:160.101",
        "control_id": "C1",
        "batch": "B0",
        "metadata": {
            "kind": "ADDITIONAL_DUTY",
            "authored_instruction": "Check authority context without recurring safeguard.",
        },
        "contract": {
            "performed": "Reference only.",
            "unperformed": "Qualified applicability remains open.",
        },
    }
    f = task_facet(o, t, [s])
    assert f["native_role_source_ids"] == [o.source_id(rows[0])]
    assert any(o.facts[x]["value"] is False for x in f["native_fact_ids"])
    assert f["professional_qualified_owner_or_grade_acceptance"] == "NOT_ASSERTED"


def test_gap_witness_cannot_prove_nonoccurrence():
    r = original()
    o = holder([r])
    s = source_scene(o, spec(), A)
    t = {
        "task_id": "TEST",
        "control_id": "C1",
        "batch": "B0",
        "metadata": {
            "kind": "ADDITIONAL_DUTY",
            "authored_instruction": "A specific hearing transcript and subpoena proceeding.",
        },
        "contract": {
            "performed": "Context only.",
            "unperformed": "Specific proceeding is unestablished.",
        },
    }
    f = task_facet(o, t, [s])
    assert f["gap_witness_is_not_proof_of_event_nonoccurrence"] is True
    assert not f["native_fact_ids"] and f["source_declared_gap_fact_ids"]


def test_control_free_scope_requires_explicit_exact_task():
    r = original()
    o = holder([r])
    sp = spec()
    sp["control_ids"] = []
    sp["scope_task_ids"] = ["EXACT-SCOPE"]
    s = source_scene(o, sp, A)
    t = {
        "task_id": "OTHER-SCOPE",
        "control_id": None,
        "batch": "B00",
        "metadata": {"kind": "SCOPE_DEPENDENCY"},
        "contract": {"performed": "Declared facts.", "unperformed": "Owner acceptance."},
    }
    with pytest.raises(ValueError, match="Concrete decision"):
        task_facet(o, t, [s])


def test_antecedent_event_and_later_publication_are_distinct():
    row = original(at="2026-12-30T00:00:00Z")
    row["available_at"] = "2027-01-03T00:00:00Z"
    originals = holder([row])
    source = originals.source(originals.source_id(row))
    assert source["native_event_period_classification"] == "ANTECEDENT"
    assert source["publication_period_classification"] == "IN_PERIOD"
    assert source["publication_date_is_not_the_operating_occurrence_date"] is True


def test_unknown_event_is_not_inferred_from_publication():
    row = original()
    row["event_at"] = None
    originals = holder([row])
    source = originals.source(originals.source_id(row))
    assert source["native_event_period_classification"] == "UNKNOWN_NATIVE_TIME"
    assert source["period_classification"] == "UNKNOWN_NATIVE_TIME"
