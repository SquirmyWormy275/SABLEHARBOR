"""Selectable work retains original duties and adds only selected candidate links."""

import copy
import itertools

import pytest

from enterprise.ccf.operations import selection


@pytest.fixture
def reference(monkeypatch):
    ids = ["SH-IAM-004", "SH-AIM-001", "SH-CFG-003"]
    controls = [
        dict(
            control_id=cid,
            native_owner_role_id="ROLE",
            base_procedure="Execute " + cid,
            base_test="Independently test " + cid,
            base_evidence=["Original records"],
            population_rule="Independent complete population",
            boundary_rule="Local execution",
        )
        for cid in ids
    ]
    actions = [
        dict(
            id=aid,
            control_ids=cids,
            requirement_ids=reqs,
            procedure="Perform " + aid,
            acceptance_test="Inspect " + aid,
            evidence_required=["Dated record"],
            dependencies=["QUALIFIED-REVIEW"],
            work_type="ASSESSMENT_ONLY" if not cids else "ENHANCE_EXISTING_CONTROL",
        )
        for aid, cids, reqs in [
            ("SHARED", [ids[0]], ["SOC2:CC6.1", "ISO27001:A.5.1", "ISO42001:A.6.1"]),
            ("ISO", [ids[1]], ["ISO42001:A.6.2"]),
            ("C5", [ids[2]], ["C5:OPS-01"]),
            ("CONTEXT", [], ["ISO27001:PREP-DOCUMENT-CONTEXT"]),
        ]
    ]
    baseline = []
    for boundary in ("corporate", "reno"):
        baseline.append(
            dict(
                id=f"COLLECT:{ids[0]}:{boundary}",
                control_id=ids[0],
                boundary_id=boundary,
                owner_role_id="ROLE",
                trigger="On event",
                proposed_source_system="Source",
                required_records=["Original records"],
                procedure=controls[0]["base_procedure"],
                baseline_test=controls[0]["base_test"],
                population="Independent complete population",
                boundary_test="Local execution",
                added_steps=[
                    dict(
                        action_id="SHARED",
                        requirement_ids=["SOC2:CC6.1"],
                        procedure="Perform SHARED",
                        test="Inspect SHARED",
                    )
                ],
            )
        )
    variants = {
        "baseline": {"SHARED": ["SOC2:CC6.1"]},
        "iso27001": {
            "SHARED": ["SOC2:CC6.1", "ISO27001:A.5.1"],
            "CONTEXT": ["ISO27001:PREP-DOCUMENT-CONTEXT"],
        },
        "iso42001": {"SHARED": ["SOC2:CC6.1", "ISO42001:A.6.1"], "ISO": ["ISO42001:A.6.2"]},
        "c5": {"SHARED": ["SOC2:CC6.1"], "C5": ["C5:OPS-01"]},
    }
    comparisons = {
        name: dict(reused_control_ids=[ids[0]], additional_candidate_control_ids=extra)
        for name, extra in [
            ("baseline", []),
            ("iso27001", []),
            ("iso42001", [ids[1]]),
            ("c5", [ids[2]]),
        ]
    }
    designs = [
        dict(
            control_id=cid,
            native_trigger="On change",
            proposed_system_of_record="Authored source",
            requirement_ids=(
                ["SOC2:CC6.1", "ISO27001:A.5.1", "ISO42001:A.6.1"]
                if i == 0
                else ["ISO42001:A.6.2"]
                if i == 1
                else ["C5:OPS-01"]
            ),
        )
        for i, cid in enumerate(ids)
    ]
    monkeypatch.setattr(selection, "review_packet", lambda native: dict(controls=designs))
    return dict(
        evidence_checklist=baseline,
        canonical_controls=controls,
        canonical_actions=actions,
        variant_action_requirements=variants,
        variant_comparisons=comparisons,
    )


@pytest.mark.parametrize(
    "targets", [list(t) for n in range(4) for t in itertools.combinations(selection.VARIANTS, n)]
)
def test_every_subset_keeps_baseline_and_filters_links(reference, targets):
    original = copy.deepcopy(reference)
    result = selection.plans(reference, targets, native={})
    expected_controls = 1 + ("ISO42001" in targets) + ("C5" in targets)
    assert len(result) == expected_controls * 2
    base = result["COLLECT:SH-IAM-004:reno"]
    assert base["procedure"] == "Execute SH-IAM-004"
    assert base["criteria"]["BASE"] == "Independently test SH-IAM-004"
    assert base["criteria"]["SHARED"] == "Inspect SHARED"
    assert "SOC2:CC6.1" in base["criterion_requirement_ids"]["SHARED"]
    assert all(p["extension_targets"] == sorted(targets) for p in result.values())
    for p in result.values():
        assert p["mapping_acceptance"] == "NOT_ASSERTED"
        assert p["requirement_link_authority"] == "CANDIDATE_MAPPING_NOT_ACCEPTED"
        assert all(
            r.split(":")[0] in ["SOC2", "HIPAA", *targets] for r in p["selected_requirement_ids"]
        )
        assert len(p["additional_procedures"]) == len(
            {s["action_id"] for s in p["additional_procedures"]}
        )
    assert bool(base["assessment_prerequisites"]) == ("ISO27001" in targets)
    assert "CONTEXT" not in base["criteria"]  # No invented control mapping.
    assert reference == original


def test_combined_union_does_not_repeat_shared_control_or_action(reference):
    targets = list(selection.VARIANTS)
    full = selection.plans(reference, targets, native={})
    singles = [selection.plans(reference, [t], native={}) for t in targets]
    assert set(full) == set().union(*(set(s) for s in singles))
    for key, p in full.items():
        assert set(p["criteria"]) == set().union(
            *(set(s[key]["criteria"]) for s in singles if key in s)
        )
    assert full == selection.plans(reference, targets[::-1], native={})


@pytest.mark.parametrize("targets", [["ISO27001", "ISO27001"], ["ISO270001"], [None], "C5", None])
def test_invalid_target_selection_is_rejected(reference, targets):
    with pytest.raises(ValueError, match="distinct"):
        selection.plans(reference, targets, native={})


@pytest.mark.parametrize(
    "fault",
    [
        "missing_control",
        "missing_action",
        "dropped_baseline",
        "foreign_link",
        "procedure_drift",
        "duplicate",
    ],
)
def test_inconsistent_inventory_cannot_hide_work(reference, fault):
    if fault == "missing_control":
        reference["canonical_controls"].pop()
    elif fault == "missing_action":
        reference["canonical_actions"].pop()
    elif fault == "dropped_baseline":
        reference["variant_comparisons"]["iso27001"]["reused_control_ids"] = []
    elif fault == "foreign_link":
        reference["variant_action_requirements"]["baseline"]["SHARED"] = ["UNSELECTED:X"]
    elif fault == "procedure_drift":
        reference["canonical_controls"][0]["base_test"] = "Auto-pass"
    else:
        reference["canonical_actions"].append(reference["canonical_actions"][0])
    with pytest.raises(ValueError):
        selection.plans(reference, list(selection.VARIANTS), native={})
