"""Explicit source lineage and declared-period observations, never audit acceptance."""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .company_collection import binding
from .company_source_census import instant
from .explanation_binding import _private, _write
from .inference import _json
from .operating_source_bridge import encoded, sha
from .portfolio_explanation import capture, validate_capture_authority
from .private_publication import publish
from .store import DomainError, digest
from .temporal_workflow import bound

NATIVE = ("company", "branch", "system", "record", "version", "sha256")
REF_KEYS = {*NATIVE, "id", "source_store_id", "source_system_alias", "registry_sha256"}
ROLE_NATIVE = {
    "POPULATION": ("review_population", "members"),
    "DECISIONS": ("review_decisions", "decisions"),
    "RECONCILIATION": ("review_reconciliation", "hr_sources"),
}
ROLES = set(ROLE_NATIVE)


def require(condition, message):
    if not condition:
        raise DomainError(message)


def utc(value):
    result = instant(value)
    require(isinstance(value, str) and "T" in value, "Explicit UTC instant required")
    require(
        datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset().total_seconds() == 0,
        "UTC half-open intervals required",
    )
    return result


def analyze(plan, sources, bodies, scope):
    """Pure typed observations over already verified selected sources."""
    index = {r["id"]: r for r in sources}
    edges = []
    for adapter in plan["adapters"]:
        require(
            isinstance(adapter, dict)
            and set(adapter)
            == {"kind", "source_ref_id", "target_component_id", "producer_label_expected"},
            "Exact dependency adapter required",
        )
        require(
            adapter["kind"] in ("LOG_UPSTREAM", "CFG_UPSTREAM"), "Unsupported dependency adapter"
        )
        require(adapter["source_ref_id"] in index, "Adapter source must be explicitly selected")
        require(
            all(
                isinstance(adapter[k], str) and adapter[k]
                for k in ("target_component_id", "producer_label_expected")
            ),
            "Explicit producer routing required",
        )
        source = index[adapter["source_ref_id"]]
        body = bodies[source["id"]]
        if adapter["kind"] == "LOG_UPSTREAM":
            event = body.get("event", {})
            links = [("event.upstream", event.get("upstream"))] if isinstance(event, dict) else []
        else:
            links = [
                (k, body[k]) for k in ("build", "configuration_source", "release") if k in body
            ]
        require(
            links and all(isinstance(v, dict) for _, v in links), "Adapter lacks typed native links"
        )
        for locator, link in links:
            fields = (
                NATIVE
                if adapter["kind"] == "LOG_UPSTREAM"
                else ("company_id", "branch_id", "system_id", "record_id", "version", "sha256")
            )
            require(all(k in link for k in (*fields, "source_store_id")), "Incomplete native link")
            target = dict(zip(NATIVE, (link[k] for k in fields), strict=True))
            require(
                type(target["version"]) is int
                and target["version"] > 0
                and all(isinstance(target[k], str) and target[k] for k in NATIVE if k != "version")
                and len(target["sha256"]) == 64
                and all(c in "0123456789abcdef" for c in target["sha256"])
                and isinstance(link["source_store_id"], str)
                and bool(link["source_store_id"]),
                "Native link requires typed identifiers, positive integer version and SHA256",
            )
            candidates = [
                r
                for r in sources
                if r["source_store_id"] == adapter["target_component_id"]
                and all(r[k] == target[k] for k in NATIVE[:-1])
            ]
            status = "MISSING_SELECTED_TARGET"
            if link["source_store_id"] != adapter["producer_label_expected"]:
                status = "PRODUCER_LABEL_MISMATCH"
            elif len(candidates) > 1:
                status = "AMBIGUOUS_SELECTED_TARGET"
            elif candidates:
                status = (
                    "EXACT_MATCH"
                    if candidates[0]["sha256"] == target["sha256"]
                    else "DIGEST_MISMATCH"
                )
            timing = "NOT_RESOLVED"
            if status == "EXACT_MATCH":
                timing = (
                    "SUPPORT_AVAILABLE_BY_RECORD_AVAILABILITY"
                    if instant(candidates[0]["available_at"]) <= instant(source["available_at"])
                    else "LATER_SUPPORT"
                )
            edges.append(
                {
                    "source_ref_id": source["id"],
                    "locator": locator,
                    "target": target,
                    "target_component_id": adapter["target_component_id"],
                    "native_producer_label": link["source_store_id"],
                    "status": status,
                    "selected_target_ids": [r["id"] for r in candidates],
                    "timing": timing,
                    "causal_assertion": "NOT_INFERRED_FROM_REFERENCE",
                }
            )
    periods = []
    start = instant(bound(scope["period_start"], timezone=scope.get("timezone", "UTC")))
    end = instant(
        bound(scope["period_end"], inclusive_end=True, timezone=scope.get("timezone", "UTC"))
    )
    for contract in plan["period_contracts"]:
        require(
            isinstance(contract, dict)
            and set(contract)
            == {
                "control_id",
                "boundary_id",
                "inventory_ref_id",
                "expected_slots",
                "sources",
                "basis",
            },
            "Exact period contract required",
        )
        require(
            contract["basis"] == "EXPLICIT_LOCAL_REFERENCE_PLAN", "Authored local basis required"
        )
        require(contract["inventory_ref_id"] in index, "Selected inventory reference required")
        inventory_source = index[contract["inventory_ref_id"]]
        inventory_body = bodies[contract["inventory_ref_id"]]
        require(
            contract["control_id"] == "SH-IAM-007"
            and inventory_body.get("control_id") == contract["control_id"]
            and inventory_source["system"] == "review_population"
            and inventory_body.get("boundary_id", contract["boundary_id"])
            == contract["boundary_id"],
            "Native IAM inventory control/system/boundary mismatch",
        )
        inventory = inventory_body.get("declared_employee_ids")
        require(
            isinstance(inventory, list)
            and all(isinstance(i, str) and i for i in inventory)
            and len(set(inventory)) == len(inventory),
            "Typed declared local inventory required",
        )
        require(
            isinstance(contract["sources"], list) and len(contract["sources"]) <= 64,
            "Bounded period sources required",
        )
        observations, used = [], set()
        for link in contract["sources"]:
            require(
                isinstance(link, dict)
                and set(link) == {"source_ref_id", "role"}
                and isinstance(link["role"], str)
                and link["role"] in ROLES
                and link["source_ref_id"] in index,
                "Exact selected period role required",
            )
            require(link["source_ref_id"] not in used, "Duplicate or relabeled period source")
            used.add(link["source_ref_id"])
            source = index[link["source_ref_id"]]
            body = bodies[link["source_ref_id"]]
            system, field = ROLE_NATIVE[link["role"]]
            require(
                source["system"] == system
                and isinstance(body.get(field), list)
                and all(
                    source[k] == inventory_source[k]
                    for k in ("source_store_id", "company", "branch")
                )
                and body.get("boundary_id", contract["boundary_id"]) == contract["boundary_id"],
                "Native IAM role schema/branch/boundary mismatch",
            )
            require(
                body.get("control_id") == contract["control_id"], "Native period control mismatch"
            )
            inventory_status = (
                "MATCHES_DECLARED_LOCAL_INVENTORY"
                if body.get("declared_employee_ids") == inventory
                else "INVENTORY_DIFFERS"
            )
            a, b = body.get("period_start"), body.get("period_end_exclusive")
            if a is None or b is None:
                observations.append(
                    {**link, "status": "UNDATED", "inventory_status": inventory_status}
                )
                continue
            require(utc(a) < utc(b), "Native half-open period must be ordered")
            observations.append(
                {
                    **link,
                    "status": "DECLARED_WINDOW_ONLY",
                    "start": a,
                    "end": b,
                    "inventory_status": inventory_status,
                }
            )
        slots, prior, ids = [], None, set()
        require(
            isinstance(contract["expected_slots"], list)
            and 1 <= len(contract["expected_slots"]) <= 24,
            "One to24 explicit expected slots required",
        )
        for slot in contract["expected_slots"]:
            require(
                isinstance(slot, dict)
                and set(slot) == {"id", "start", "end"}
                and isinstance(slot["id"], str)
                and slot["id"]
                and slot["id"] not in ids,
                "Distinct exact period slots required",
            )
            a, b = utc(slot["start"]), utc(slot["end"])
            require(
                start <= a < b <= end and (prior is None or a >= prior),
                "Ordered nonoverlapping slots within audit period required",
            )
            ids.add(slot["id"])
            prior = b
            matches = [
                o
                for o in observations
                if o["status"] == "DECLARED_WINDOW_ONLY"
                and utc(o["start"]) == a
                and utc(o["end"]) == b
            ]
            slots.append(
                {
                    **slot,
                    "roles": {
                        role: {
                            "status": (
                                "REQUIRED_ROLE_PRESENT"
                                if any(
                                    o["role"] == role
                                    and o["inventory_status"] == "MATCHES_DECLARED_LOCAL_INVENTORY"
                                    for o in matches
                                )
                                else "ROLE_PRESENT_INVENTORY_DIFFERS"
                                if any(o["role"] == role for o in matches)
                                else "MISSING_SELECTED_SUPPORT"
                            ),
                            "source_ref_ids": [
                                o["source_ref_id"] for o in matches if o["role"] == role
                            ],
                        }
                        for role in sorted(ROLES)
                    },
                }
            )
        gaps, cursor = [], start
        for slot in slots:
            if utc(slot["start"]) > cursor:
                gaps.append(
                    {
                        "start": cursor.isoformat(),
                        "end": utc(slot["start"]).isoformat(),
                        "status": "NO_EXPECTED_SLOT_AUTHORED",
                    }
                )
            cursor = utc(slot["end"])
        if cursor < end:
            gaps.append(
                {
                    "start": cursor.isoformat(),
                    "end": end.isoformat(),
                    "status": "NO_EXPECTED_SLOT_AUTHORED",
                }
            )
        for observation in observations:
            observation["slot_alignment"] = (
                "EXACT_EXPECTED_SLOT"
                if observation["status"] == "DECLARED_WINDOW_ONLY"
                and any(
                    utc(observation["start"]) == utc(slot["start"])
                    and utc(observation["end"]) == utc(slot["end"])
                    for slot in slots
                )
                else "UNDATED_OR_CONFLICTING_PERIOD"
            )
        periods.append(
            {
                "control_id": contract["control_id"],
                "boundary_id": contract["boundary_id"],
                "basis": contract["basis"],
                "declared_inventory": inventory,
                "inventory_scope": "LOCAL_DECLARED_SUBSET_NOT_ENTERPRISE_POPULATION",
                "observations": observations,
                "slots": slots,
                "unplanned_intervals": gaps,
                "boundary_basis": "AUTHORED_SCOPE_ASSOCIATION_UNLESS_NATIVE_BOUNDARY_PRESENT",
                "operating_period_coverage": "NOT_ESTABLISHED",
            }
        )
    return {
        "dependencies": edges,
        "period_support": periods,
        "coherent_operating_year": "NOT_ESTABLISHED",
        "control_effectiveness": "NOT_ASSESSED",
        "population_acceptance": "NOT_PERFORMED",
        "limits": [
            "Missing selected support does not establish nonexistent company evidence.",
            "Matching references and declared windows do not establish execution or sufficiency.",
            "Component snapshots are independent; no global atomic source snapshot.",
            "This report neither imports populations nor selects samples nor records test work.",
        ],
    }


def _check_current(engine, actor, eid, original, report):
    current = engine.store.get(actor, eid)
    require(
        current["revision"] == original["revision"]
        and current["scope"] == original["scope"]
        and binding(engine, current) == report["company_binding"],
        "Audit context changed",
    )
    validate_capture_authority(engine, report)


def reconcile(engine, actor_id, engagement_id, plan):
    required = {"registry_sha256", "scope_sha256", "source_refs", "adapters", "period_contracts"}
    optional = {"iam_review_contracts", "access_remediation_contracts"}
    require(
        isinstance(plan, dict) and required <= set(plan) <= required | optional,
        "Exact reconciliation plan required",
    )
    require(getattr(engine.company_store, "is_federated", False), "Explicit portfolio required")
    plan = json.loads(encoded(plan))
    state = engine.store.get(actor_id, engagement_id)
    company = dict(binding(engine, state))
    require(
        company["registry_sha256"] == plan["registry_sha256"]
        and digest(state["scope"]) == plan["scope_sha256"],
        "Pinned scope/registry differs",
    )
    refs = plan["source_refs"]
    require(
        isinstance(refs, list) and 1 <= len(refs) <= 64,
        "One to64 explicit source references required",
    )
    require(
        all(
            isinstance(r, dict)
            and set(r) == REF_KEYS
            and isinstance(r["id"], str)
            and r["id"]
            and all(isinstance(r[k], str) and r[k] for k in REF_KEYS - {"version"})
            and type(r["version"]) is int
            and r["version"] > 0
            for r in refs
        ),
        "Exact typed source references required",
    )
    require(
        len({r["id"] for r in refs}) == len(refs)
        and len({tuple(r[k] for k in ("source_store_id", *NATIVE[:-1])) for r in refs})
        == len(refs),
        "Duplicate source identity or label",
    )
    require(
        isinstance(plan["adapters"], list)
        and len(plan["adapters"]) <= 64
        and isinstance(plan["period_contracts"], list)
        and len(plan["period_contracts"]) <= 16,
        "Bounded adapter and period lists required",
    )
    controls = {c["id"] for c in state["controls"]}
    for contract in plan["period_contracts"]:
        require(
            isinstance(contract, dict)
            and isinstance(contract.get("control_id"), str)
            and contract.get("control_id") in controls
            and contract.get("boundary_id") in state["scope"]["boundaries"],
            "Period contract outside assigned scope",
        )
    sources, files, components = capture(
        engine,
        state=state,
        bound=company,
        refs=refs,
        actor=actor_id,
        operator=actor_id,
        clock=state["simulated_at"],
        operator_clock=state["simulated_at"],
    )
    bodies = {}
    for source in sources:
        try:
            body = _json(files[source["path"]])
        except (ValueError, UnicodeError, RecursionError) as error:
            raise DomainError("Selected adapter input must be strict finite native JSON") from error
        require(isinstance(body, dict), "Selected native JSON object required")
        bodies[source["id"]] = body
    result = analyze(plan, sources, bodies, state["scope"])
    if "iam_review_contracts" in plan:
        from .iam_review_reconciliation import checks

        require("SH-IAM-007" in controls, "IAM review contracts outside assigned controls")
        result["iam_review_reconciliation"] = checks(
            plan["iam_review_contracts"], sources, bodies, state["scope"]
        )
    if "access_remediation_contracts" in plan:
        from .access_remediation_reconciliation import analyze as analyze_remediation

        require("SH-IAM-007" in controls, "Access remediation contracts outside assigned controls")
        result["access_remediation_reconciliation"] = analyze_remediation(
            plan["access_remediation_contracts"], sources, bodies, state["scope"]
        )
    result.update(
        schema="SOURCE_DEPENDENCY_PERIOD_REPORT_V1",
        snapshot_isolation="PER_COMPONENT_NOT_GLOBAL",
        created_at=datetime.now(UTC).isoformat(),
        engagement={"id": engagement_id, "revision": state["revision"], "scope": state["scope"]},
        company_binding=company,
        source_operator_id=actor_id,
        audited_actor_id=actor_id,
        sources=[
            {
                **{k: v for k, v in r.items() if k != "path"},
                "native_qualifiers": {
                    k: bodies[r["id"]][k]
                    for k in (
                        "classification",
                        "origin",
                        "policy_status",
                        "scope_limit",
                        "deployment_status",
                        "service_status",
                        "coverage_limit",
                    )
                    if k in bodies[r["id"]]
                },
            }
            for r in sources
        ],
        component_snapshots=components,
        plan_sha256=digest(plan),
    )
    _check_current(engine, actor_id, engagement_id, state, result)
    return result


def _analysis_source_pins(plan):
    """Maintained analysis source files, not loaded-binary or full dependency attestation."""
    names = ["source_dependency_reconciliation.py", "inference.py"]
    if "iam_review_contracts" in plan or "access_remediation_contracts" in plan:
        names.append("iam_review_reconciliation.py")
    if "access_remediation_contracts" in plan:
        names.append("access_remediation_reconciliation.py")
    return {name: sha((Path(__file__).parent / name).read_bytes()) for name in names}


def write_report(engine, actor_id, engagement_id, plan, *, output):
    plan = json.loads(encoded(plan))
    output = Path(output).absolute()
    _private(output.parent)
    require(not output.exists() and not output.is_symlink(), "New private output required")
    inputs = [
        engine.store.root,
        *[Path(c["root"]) for c in engine.company_store._manifest["components"].values()],
    ]
    require(
        not any(output.resolve().is_relative_to(p.resolve()) for p in inputs),
        "Output must be outside original audit/source stores",
    )
    analysis_pins = _analysis_source_pins(plan)
    report = reconcile(engine, actor_id, engagement_id, plan)
    with tempfile.TemporaryDirectory(
        prefix=".source-reconciliation-", dir=output.parent
    ) as directory:
        stage = Path(directory)
        values = {"REPORT.json": encoded(report), "PLAN.json": encoded(plan)}
        for name, raw in values.items():
            _write(stage / name, raw)
        manifest = {
            "files": {name: sha(raw) for name, raw in values.items()},
            "module_sha256": analysis_pins["source_dependency_reconciliation.py"],
            "analysis_modules_sha256": analysis_pins,
            "analysis_pin_scope": "MAINTAINED_SOURCE_FILES_NOT_LOADED_BINARY_ATTESTATION",
            "plan_sha256": digest(plan),
        }
        _write(stage / "MANIFEST.json", encoded(manifest))
        _check_current(engine, actor_id, engagement_id, report["engagement"], report)
        require(
            _analysis_source_pins(plan) == analysis_pins, "Analysis source changed during report"
        )
        publish(stage, output)
    return {"path": str(output), "manifest_sha256": sha(encoded(manifest))}
