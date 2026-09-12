"""Select source-backed candidate duties without accepting mappings or duplicating controls."""

import copy

from enterprise.ccf.assurance.completion import review_packet
from enterprise.ccf.registry import compile_registry, digest

from . import testing

VARIANTS = {"ISO27001": "iso27001", "ISO42001": "iso42001", "C5": "c5"}


def indexed(rows, key):
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate selection inventory identifier")
    return result


def plans(reference, targets, native=None):
    """Return immutable-store-compatible plans; empty targets retain the baseline.

    Assessment-only actions without candidate controls remain explicit global
    prerequisites. They are never silently assigned an invented control route.
    """
    if (
        not isinstance(targets, list)
        or not all(isinstance(t, str) and t in VARIANTS for t in targets)
        or len(set(targets)) != len(targets)
    ):
        raise ValueError("Use distinct ISO27001, ISO42001 or C5 extension targets")
    targets = sorted(targets)
    frameworks = ["SOC2", "HIPAA", *targets]
    baseline = reference["evidence_checklist"]
    indexed(baseline, "id")
    base_ids = {r["control_id"] for r in baseline}
    boundaries = sorted({r["boundary_id"] for r in baseline})
    if not base_ids or not boundaries:
        raise ValueError("Baseline controls and boundaries required")
    if (
        len(baseline) != len(base_ids) * len(boundaries)
        or {(r["control_id"], r["boundary_id"]) for r in baseline}
        != {(cid, boundary) for cid in base_ids for boundary in boundaries}
        or any(r["id"] != f"COLLECT:{r['control_id']}:{r['boundary_id']}" for r in baseline)
    ):
        raise ValueError("Baseline boundary coverage is incomplete")
    selected_controls = set(base_ids)
    links = {}
    variants = ["baseline", *(VARIANTS[t] for t in targets)]
    for variant in variants:
        comparison = reference["variant_comparisons"][variant]
        if set(comparison["reused_control_ids"]) != base_ids:
            raise ValueError("Selection does not preserve baseline controls")
        selected_controls.update(comparison["additional_candidate_control_ids"])
        for aid, reqs in reference["variant_action_requirements"][variant].items():
            links.setdefault(aid, set()).update(reqs)
    actions = indexed(reference["canonical_actions"], "id")
    controls = indexed(reference["canonical_controls"], "control_id")
    if not set(links) <= set(actions) or not selected_controls <= set(controls):
        raise ValueError("Selected action or control missing from canonical inventory")
    for aid, reqs in links.items():
        if not reqs or not reqs <= set(actions[aid]["requirement_ids"]):
            raise ValueError("Selected requirement links differ from canonical action")
        if any(r.split(":", 1)[0] not in frameworks for r in reqs):
            raise ValueError("Unselected framework requirement leaked into selection")
        if not set(actions[aid]["control_ids"]) <= selected_controls:
            raise ValueError("Selected action has an unselected candidate control")
    designs = indexed(
        review_packet(native if native is not None else compile_registry())["controls"],
        "control_id",
    )
    if not selected_controls <= set(designs):
        raise ValueError("Selected control has no authored design metadata")
    global_actions = []
    per_control = {cid: [] for cid in selected_controls}
    for aid in sorted(links):
        action = actions[aid]
        selected = dict(copy.deepcopy(action), requirement_ids=sorted(links[aid]))
        if not action["control_ids"]:
            global_actions.append(selected)
        for cid in action["control_ids"]:
            per_control[cid].append(
                dict(
                    action_id=aid,
                    requirement_ids=sorted(links[aid]),
                    procedure=action["procedure"],
                    test=action["acceptance_test"],
                    evidence_required=copy.deepcopy(action["evidence_required"]),
                    dependencies=copy.deepcopy(action["dependencies"]),
                    work_type=action["work_type"],
                )
            )
    rows = []
    original = {(r["control_id"], r["boundary_id"]): r for r in baseline}
    for cid in sorted(selected_controls):
        c, d = controls[cid], designs[cid]
        if "base_design_digest" in c and c["base_design_digest"] != d.get("design_digest"):
            raise ValueError("Authored design changed since the reference assessment")
        for boundary in boundaries:
            if (cid, boundary) in original:
                row = copy.deepcopy(original[cid, boundary])
                if (
                    row["procedure"] != c["base_procedure"]
                    or row["baseline_test"] != c["base_test"]
                ):
                    raise ValueError("Canonical procedure differs from retained baseline")
                existing = {s["action_id"]: s for s in row["added_steps"]}
                selected = {s["action_id"]: s for s in per_control[cid]}
                for aid, step in existing.items():
                    if (
                        aid not in selected
                        or any(step[k] != selected[aid][k] for k in ("procedure", "test"))
                        or not set(step["requirement_ids"]) <= set(selected[aid]["requirement_ids"])
                    ):
                        raise ValueError("Selection dropped or changed a baseline duty")
            else:
                row = dict(
                    id=f"COLLECT:{cid}:{boundary}",
                    control_id=cid,
                    boundary_id=boundary,
                    owner_role_id=c["native_owner_role_id"],
                    trigger=d["native_trigger"],
                    proposed_source_system=d["proposed_system_of_record"],
                    required_records=c["base_evidence"],
                    procedure=c["base_procedure"],
                    baseline_test=c["base_test"],
                    population=c["population_rule"],
                    boundary_test=c["boundary_rule"],
                )
            row["added_steps"] = copy.deepcopy(per_control[cid])
            rows.append(row)
    result = testing.plans(dict(evidence_checklist=rows))
    for p in result.values():
        cid = p["control_id"]
        base_requirements = sorted(
            r for r in designs[cid]["requirement_ids"] if r.split(":", 1)[0] in frameworks
        )
        criterion_links = {"BASE": base_requirements}
        criterion_links.update({s["action_id"]: s["requirement_ids"] for s in per_control[cid]})
        p.update(
            reference_digest=digest(reference),
            is_baseline_control=cid in base_ids,
            selected_frameworks=frameworks,
            extension_targets=targets,
            criterion_requirement_ids=criterion_links,
            selected_requirement_ids=sorted({r for reqs in criterion_links.values() for r in reqs}),
            requirement_link_authority="CANDIDATE_MAPPING_NOT_ACCEPTED",
            assessment_prerequisites=copy.deepcopy(global_actions),
        )
    return result
