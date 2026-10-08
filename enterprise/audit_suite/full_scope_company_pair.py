"""One admitted company lifetime, two empty full-program workrooms.

Reviewed methods use ordinary retained originals in the same engagement.
No deployment, source generation, professional review or old-state import.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import stat
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from .company_store import _json, _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, discover_history, require
from .persistent_company_journey import (
    RUNTIME_SCHEMA,
    RUNTIME_VERDICT,
    PersistentAudit,
    PersistentCompany,
    write,
)
from .population_lifecycle import population, selection
from .source_library_audit import (
    BUSINESS_REFERENCE,
    file_sha,
    ordinary_copy,
    private_file,
    typed_content,
)
from .source_library_security_execution import (
    PROGRAM_SHA,
    adapter_gate,
    authored_instruction,
    command,
    plans,
)
from .source_library_security_execution import (
    TASKS as SECURITY_TASKS,
)
from .source_library_security_execution import (
    record_method as record_security,
)
from .source_library_security_methods import (
    analyze_continuity_timestamps,
    analyze_security_publishers,
    analyze_vulnerability,
)
from .source_privacy_execution import (
    TASKS as PRIVACY_TASKS,
)
from .source_privacy_execution import (
    record_findings as record_privacy_findings,
)
from .source_privacy_execution import (
    record_method as record_privacy,
)
from .source_privacy_methods import examine as examine_privacy
from .store import digest

INITIAL = "2027-12-31T09:00:00Z"
MODES = ("CLEAN", "MESSY")
PAIR_SCHEMA = "SH_ROOT_FULL_SCOPE_COMPANY_PAIR_REVIEW_V1"
PAIR_VERDICT = "PASS_SHARED_COMPANY_FULL_PROGRAM_PAIR_ORCHESTRATION"
BINDING_SCHEMA = "SH_RETAINED_COMPANY_AUDIT_WORKROOM_BINDING_V1"
GENERAL_METHOD_SCHEMA = "SH_ROOT_COLLECTED_COMPANY_BATCH_METHOD_REVIEW_V1"
GENERAL_METHOD_VERDICT = "PASS_COLLECTED_COMPANY_BATCH_METHOD_SELECTED_BOUNDARY"
SCOPE = {
    "programs": ["SOC2", "HIPAA"],
    "report_type": "Type 2",
    "period_start": "2027-01-01",
    "period_end": "2027-12-31",
    "fieldwork_start": "2027-12-31",
    "timezone": "UTC",
    "boundaries": ["corporate"],
    "soc2_categories": ["Security", "Availability", "Confidentiality"],
    "hipaa_scenario": "FICTIONAL_BUSINESS_ASSOCIATE_SUBCONTRACTOR_SIMULATED_EPHI",
}
LEGAL_TASKS = (
    "TASK-SH-LEG-001-corporate-TOE",
    "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.300",
    "TASK-SH-LEG-001-corporate-CHECK-HIPAA:160.304",
)
METHOD_GATES = {
    "security": (
        "SH_ROOT_COLLECTED_SECURITY_METHOD_REVIEW_V1",
        "PASS_COLLECTED_BYTES_BOUNDED_SECURITY_METHOD",
        "source_library_security_methods.py",
        "security_module_sha256",
        tuple(SECURITY_TASKS.values()),
    ),
    "privacy": (
        "SH_PRIVACY_METHOD_INDEPENDENT_REVIEW_V2",
        "PASS_COLLECTED_BYTES_BOUNDED_PRIVACY_METHOD",
        "source_privacy_methods.py",
        "privacy_module_sha256",
        tuple(PRIVACY_TASKS.values()),
    ),
    "legal": (
        "SH_ROOT_COLLECTED_LEGAL_METHOD_REVIEW_V1",
        "PASS_COLLECTED_BYTES_BOUNDED_LEGAL_METHOD",
        "source_legal_intake_methods.py",
        "legal_module_sha256",
        LEGAL_TASKS,
    ),
}


@dataclass(frozen=True)
class PinnedReview:
    path: Path
    sha256: str

    def read(self):
        private_file(self.path)
        require(file_sha(self.path) == self.sha256, "Independent review pin changed")
        data = json.loads(self.path.read_bytes())
        require(isinstance(data, dict), "Structured independent review required")
        return data


def dependencies():
    names = (
        "source_library_security_execution.py",
        "source_library_security_methods.py",
        "source_privacy_execution.py",
        "source_privacy_methods.py",
        "source_legal_intake_methods.py",
        "legal_intake_selected_method_plan_v1.json",
        "source_library_audit.py",
        "persistent_company_journey.py",
        "fresh_sec003_procedure.py",
        "engine.py",
        "company_store.py",
        "store.py",
        "artifacts.py",
        "population_lifecycle.py",
        "workpaper_links.py",
        "company_collection.py",
        "sample_execution.py",
    )
    return {name: file_sha(Path(__file__).with_name(name)) for name in names}


def independent_method_gate(batch, gate):
    require(batch in METHOD_GATES, "Unknown reviewed method batch")
    schema, verdict, filename, field, tasks = METHOD_GATES[batch]
    review = gate.read()
    require(
        review.get("schema") == schema
        and review.get("verdict") == verdict
        and review.get("source_execution_authorized") is True
        and review.get(field) == file_sha(Path(__file__).with_name(filename)),
        "Exact independently reviewed method implementation required",
    )
    # The historical privacy gate binds the pure method, without a task vector.
    # These six fixed wrappers are additionally bound by the orchestration gate.
    if batch != "privacy":
        require(
            review.get("selected_task_ids") == list(tasks),
            "Independent method review task vector differs",
        )
    return {"path": str(gate.path), "sha256": gate.sha256, "task_ids": list(tasks)}


def route_vector(routes_by_mode):
    return {
        mode: sorted((asdict(route) for route in routes), key=lambda r: r["system"])
        for mode, routes in sorted(routes_by_mode.items())
    }


def _pair_scope(fieldwork_start):
    require(type(fieldwork_start) is str, "Explicit ISO fieldwork date required")
    try:
        fieldwork = date.fromisoformat(fieldwork_start)
    except ValueError:
        require(False, "Explicit ISO fieldwork date required")
    require(
        fieldwork.isoformat() == fieldwork_start
        and fieldwork >= date.fromisoformat(SCOPE["period_start"])
        and (fieldwork - date.fromisoformat(SCOPE["period_end"])).days <= 3660,
        "Fieldwork date must preserve normal approved period chronology",
    )
    return {**json.loads(_json(SCOPE)), "fieldwork_start": fieldwork_start}


def require_pair_gate(gate, pins, routes_by_mode, *, expected_scope=None):
    selected = SCOPE if expected_scope is None else expected_scope
    require(
        type(selected) is dict
        and set(selected) == set(SCOPE)
        and _json(selected) == _json(_pair_scope(selected["fieldwork_start"])),
        "Only the explicitly selected fieldwork date may change approved scope",
    )
    review = gate.read()
    require(
        review.get("schema") == PAIR_SCHEMA
        and review.get("verdict") == PAIR_VERDICT
        and review.get("source_execution_authorized") is True
        and review.get("orchestration_module_sha256") == file_sha(Path(__file__))
        and review.get("dependency_module_sha256") == dependencies()
        and review.get("accepted_baseline_pins") == pins
        and review.get("program_pack_sha256") == PROGRAM_SHA
        and review.get("route_vector") == route_vector(routes_by_mode)
        and _json(review.get("scope")) == _json(selected),
        "Independent full-pair acceptance with exact source/dependency pins required",
    )


def control_for(state, task_id):
    matches = [task for task in state["tasks"] if task["id"] == task_id]
    require(len(matches) == 1, "Exact authored task unavailable")
    return matches[0]["control_id"]


def documentary_population_attribution(state, rows):
    """Separate the audited subject period from supporting document dates.

    This population contains examined documentary attributes, not operating
    occurrences. A January close or an antecedent design can support a 2027
    examination without changing its actual native dates. The collected-byte
    task method must separately establish relevance, cadence and sufficiency.
    """
    scope = state["scope"]
    require(scope.get("timezone") == "UTC", "Explicit UTC documentary scope required")
    start, end = scope["period_start"], scope["period_end"]
    require(isinstance(start, str) and isinstance(end, str), "Explicit audit period required")
    first = _time(start + "T00:00:00+00:00" if len(start) == 10 else start)
    last = _time(end + "T23:59:59.999999+00:00" if len(end) == 10 else end)
    require(first <= last, "Ordered documentary audit attribution period required")
    originals = []
    for row in rows:
        source = row["source"]
        event = _time(source["event_at"]) if source["event_at"] is not None else None
        relation = (
            "NO_NATIVE_OCCURRENCE_CLOCK"
            if event is None
            else "ANTECEDENT_DOCUMENT"
            if event < first
            else "POST_PERIOD_DOCUMENT"
            if event > last
            else "DOCUMENT_CREATED_IN_AUDIT_PERIOD"
        )
        originals.append(
            {
                "artifact_id": row["artifact_id"],
                "native_source": {k: source[k] for k in CLOCK_ID},
                "document_creation_relative_to_audit_period": relation,
            }
        )
    require(
        originals and any(r["native_source"]["event_at"] for r in originals),
        "Actual documentary originals and source dates required",
    )
    return {
        "kind": "SELECTED_DOCUMENTARY_EXAMINATION_ATTRIBUTES_NOT_CONTROL_OCCURRENCES",
        "audit_attribution_period": {"start": start, "end": end, "timezone": "UTC"},
        "audit_attribution_instants": {"start": first, "end": last},
        "original_native_document_dates": originals,
        "native_dates_or_receipt_clocks_changed": False,
        "document_date_establishes_operating_period_or_cadence": False,
        "enterprise_or_full_period_denominator_established": False,
        "attribution_basis": "Current audited subject period only. The exact task method's "
        "performed and unperformed facets determine relevance and actual control occurrence "
        "dates. Before/after-period documents never automatically become operating events.",
    }


def record_documentary_items(
    room, task_id, rows, observations, *, performed, unperformed, result, disposition=None
):
    """Record a genuine selected examination; no generic full-task answer."""
    require(rows and observations, "Actual selected originals and observations required")
    disposition = disposition or {
        "status": "IN_PROGRESS",
        "conclusion": "LIMITATION",
        "rationale": "Actual selected documentary examination remains partial. " + unperformed,
    }
    state, auditor, engagement = room.state(), room.auditor, room.engagement
    control = control_for(state, task_id)
    require(len({o["id"] for o in observations}) == len(observations), "Distinct observed items")
    attribution = documentary_population_attribution(state, rows)
    state = command(
        room.engine,
        auditor,
        engagement,
        "population.import",
        {
            "artifact_id": rows[0]["artifact_id"],
            "title": "Selected documentary examination attributes " + task_id,
            "rows": [{"id": o["id"]} for o in observations],
            "scope": {
                "boundary_id": "corporate",
                "unit": "selected documentary examination attributes, not operating occurrences",
                "timezone": "UTC",
                "period_start": attribution["audit_attribution_instants"]["start"],
                "period_end": attribution["audit_attribution_instants"]["end"],
            },
            "source": {
                "source_id": "ordinary-collected:" + task_id,
                "query": "Actual clock-bound discovery; exact retained native versions",
                "completeness_representation": "Selected documentary attributes only; "
                "audit period is subject attribution, not document creation or occurrence period. "
                "Original source dates remain in the linked workpaper. Operating-event, "
                "enterprise/full-year completeness and qualified acceptance unestablished",
                "excluded_ids": [],
            },
        },
    )
    state = command(
        room.engine,
        auditor,
        engagement,
        "population.assess",
        {
            "population_id": state["populations"][-1]["id"],
            "status": "READY_FOR_PURPOSE",
            "purpose": performed,
            "rationale": "Ready for this bounded examination. " + unperformed,
            "observable_artifact_ids": [r["artifact_id"] for r in rows],
        },
    )
    pop = state["populations"][-1]
    state = command(
        room.engine,
        auditor,
        engagement,
        "population.select",
        {
            "population_id": pop["id"],
            "method": "ENTIRE",
            "purpose": performed,
            "rationale": "Entire observed selected subpopulation; no full-period extrapolation",
        },
    )
    chosen = state["selections"][-1]
    paper = {
        "task_id": task_id,
        "authored_instruction": authored_instruction(state, task_id),
        "performed": performed,
        "unperformed": unperformed,
        "observations": observations,
        "examination": result,
        "source_custody": [{k: r["source"][k] for k in CLOCK_ID} for r in rows],
        "documentary_population_attribution": attribution,
        "conclusion": disposition["conclusion"],
        "independent_review": "PENDING_RESERVED_REVIEWER",
    }
    state = command(
        room.engine,
        auditor,
        engagement,
        "workpaper.add",
        {
            "title": "Actual retained-source examination " + task_id,
            "control_id": control,
            "task_ids": [task_id],
            "text": json.dumps(paper, sort_keys=True),
            "objective": performed,
            "procedures": performed,
            "evidence_ids": [r["artifact_id"] for r in rows],
            "conclusion": disposition["conclusion"],
        },
    )
    wp = state["workpapers"][-1]
    executions = []
    groups, current, citations = [], [], 0
    for observed in observations:
        require(len(observed["evidence"]) <= 20, "Selected observation citation bound exceeded")
        if current and (len(current) == 20 or citations + len(observed["evidence"]) > 100):
            groups.append(current)
            current, citations = [], 0
        current.append(observed)
        citations += len(observed["evidence"])
    if current:
        groups.append(current)
    for group in groups:
        items = []
        for observed in group:
            refs = observed["evidence"]
            require(len(refs) <= 20, "Selected observation citation bound exceeded")
            facts = json.dumps(observed["facts"], sort_keys=True)
            if len(facts) > 3900:
                facts = json.dumps(
                    {
                        "item_id": observed["id"],
                        "performed": performed,
                        "full_observation": "Exact linked workpaper item",
                    },
                    sort_keys=True,
                )
            items.append(
                {
                    "item_id": observed["id"],
                    "observation": facts,
                    "status": observed["status"],
                    "evidence": refs,
                }
            )
        state = command(
            room.engine,
            auditor,
            engagement,
            "sample.execution.record",
            {
                "task_id": task_id,
                "task_digest": digest(next(t for t in state["tasks"] if t["id"] == task_id)),
                "population_id": pop["id"],
                "population_digest": population(pop).sha256,
                "selection_id": chosen["id"],
                "selection_digest": selection(chosen).sha256,
                "workpaper_id": wp["id"],
                "workpaper_version": 1,
                "workpaper_digest": digest(wp["versions"][0]),
                "purpose": performed,
                "procedure": performed + " Unperformed: " + unperformed,
                "items": items,
            },
        )
        executions.append(state["sample_executions"][-1]["id"])
    command(
        room.engine,
        auditor,
        engagement,
        "task.update",
        {
            "task_id": task_id,
            **disposition,
        },
    )
    return {
        "task_id": task_id,
        "population_id": pop["id"],
        "selection_id": chosen["id"],
        "workpaper_id": wp["id"],
        "sample_execution_ids": executions,
    }


def legal_batch(room, rows, root):
    from .source_legal_intake_methods import examine

    result = examine(rows, as_of=room.state()["simulated_at"])
    planpath = Path(__file__).with_name("legal_intake_selected_method_plan_v1.json")
    plan = json.loads(planpath.read_bytes())
    filters = (
        None,
        {"legal_matter_classification", "regulatory_response_playbook"},
        {"legal_inbound_message", "legal_inbound_attachment"},
    )
    links = []
    for task, systems in zip(plan["selected_tasks"], filters, strict=True):
        relevant = [r for r in rows if systems is None or r["logical_system"] in systems]
        require(relevant, "Selected legal facet originals unavailable")
        observed = []
        for row in relevant:
            source = row["source"]
            related = [
                d
                for d in result["documentary_discrepancies"]
                if all(d["source"][k] == source[k] for k in NATIVE_ID)
            ]
            observed.append(
                {
                    "id": f"{source['system']}/{source['record']}/v{source['version']}",
                    "facts": {
                        "business_document": row["document"],
                        "discrepancies": related,
                        "actual_regulator_assistance_or_legal_approval": False,
                    },
                    "status": "EXCEPTION_RECORDED" if related else "OBSERVED",
                    "evidence": [
                        {
                            "artifact_id": row["artifact_id"],
                            "sha256": row["artifact_sha256"],
                            "locator": "Exact collected legal original " + source["record"],
                        }
                    ],
                }
            )
        links.append(
            record_documentary_items(
                room,
                task["task_id"],
                relevant,
                observed,
                performed="; ".join(task["proposed_performed_facets"]),
                unperformed="; ".join(task["unperformed_facets"]),
                result=result,
            )
        )
    write(root / "EXAMINATION.json", result)
    return links


class BoundWorkroom:
    """Only this workroom's performer can acquire and append its own fieldwork."""

    def __init__(self, pair, mode, session, binding):
        self.pair, self.mode, self.session, self.binding = pair, mode, session, binding
        self.engine, self.engagement = session.engine, session.engagement
        self.operator = session.identities["operator"]
        self.auditor = session.identities["auditor"]
        self.reviewer = session.identities["reviewer"]
        self.root = Path(binding["audit_root"]).parent

    def state(self):
        self.pair.check()
        state, _ = self.session._context(self.engine, self.auditor, self.engagement)
        require(
            self.engine.company_store is self.pair.world.store
            and self.engine.company_bindings.get(self.engagement)
            == {"company": self.binding["company"], "branch": self.binding["branch"]}
            and state["mode"] == self.mode
            and len(state["tasks"]) == 409
            and _json(state["scope"]) == _json(self.binding["scope"])
            and _json({k: state["scope"][k] for k in SCOPE})
            == _json(
                {
                    **self.pair.expected_scope,
                    "programs": sorted(self.pair.expected_scope["programs"]),
                }
            )
            and _time(self.binding["initial_simulated_at"])[:10]
            == self.pair.expected_scope["fieldwork_start"]
            and _time(state["simulated_at"])
            >= _time(self.binding["initial_simulated_at"]),
            "Actual shared-company workroom binding changed",
        )
        return state

    def _authorize(self, systems, *, active):
        with self.pair.world.verified_sources():
            self._authorize_verified(systems, active=active)

    def _authorize_verified(self, systems, *, active):
        self.session._context(self.engine, self.auditor, self.engagement)
        require(
            all(
                (self.binding["company"], self.binding["branch"], system) in self.session.routes
                for system in systems
            ),
            "Unreviewed source route",
        )
        for system in systems:
            key = (self.binding["company"], self.binding["branch"], system)
            require(key in self.session.routes, "Unreviewed source route")
            self.session.store.grant(self.auditor, self.engagement, *key, active=active)
            self.session.access_log.append(
                {
                    "operator_id": self.operator,
                    "principal_id": self.auditor,
                    "reviewer_id": self.reviewer,
                    "engagement_id": self.engagement,
                    "company": key[0],
                    "branch": key[1],
                    "system": key[2],
                    "active": active,
                    "recorded_at": datetime.now(UTC).isoformat(),
                }
            )

    def _retained(self, row, artifacts, *, cutoff, collection_clock):
        key = tuple(row[k] for k in NATIVE_ID)
        matches = [
            a
            for a in artifacts
            if a["source"].get("kind") == "COLLECTED_COMPANY_SOURCE"
            and tuple(a["source"]["receipt"]["source"][k] for k in NATIVE_ID) == key
        ]
        require(len(matches) <= 1, "Ambiguous repeated retained native original")
        if not matches:
            return None
        artifact = matches[0]
        receipt = artifact["source"]["receipt"]
        raw = self.engine.artifacts.read(artifact)
        require(
            type(receipt["source"]["version"]) is int
            and receipt["source"]["version"] > 0
            and type(receipt["content_bytes"]) is int
            and receipt["content_bytes"] > 0
            and _time(receipt["source"]["imported_at"])
            <= _time(receipt["collected_at"])
            <= _time(datetime.now(UTC).isoformat())
            and all(receipt["source"][k] == row[k] for k in CLOCK_ID)
            and receipt["source"]["provenance"] == row["provenance"]
            and receipt["engagement_id"] == self.engagement
            and receipt["principal_id"] == self.auditor
            and _time(row["available_at"]) <= _time(cutoff)
            and _time(row["available_at"])
            <= _time(receipt["simulated_as_of"])
            <= _time(collection_clock)
            and (
                row["event_at"] is None
                or _time(row["event_at"]) <= min(_time(cutoff), _time(receipt["simulated_as_of"]))
            )
            and raw == row["content"]
            and hashlib.sha256(raw).hexdigest() == artifact["sha256"] == row["sha256"]
            and len(raw) == receipt["content_bytes"],
            "Same-engagement retained original does not match discovered custody/bytes",
        )
        document, mime = typed_content({**receipt["source"], "content": raw})
        route = self.session.routes[tuple(row[k] for k in NATIVE_ID[:3])]
        return {
            "source": receipt["source"],
            "receipt": receipt,
            "content": raw,
            "retained_bytes": raw,
            "logical_family": route.family,
            "logical_system": route.logical_system,
            "artifact_id": artifact["id"],
            "artifact_sha256": artifact["sha256"],
            "document": document,
            "content_type": mime,
            "discovered_as_of": cutoff,
        }

    def acquire(self, *, systems, control_id, purpose, as_of=None):
        """Ordinary PBC/discovery/collection; reuse only exact originals held here."""
        systems = tuple(systems)
        require(systems and len(set(systems)) == len(systems), "Distinct native systems required")
        state = self.state()
        require(control_id in {c["id"] for c in state["controls"]}, "Scoped control unavailable")
        cutoff = _time(as_of if as_of is not None else state["simulated_at"])
        require(cutoff <= _time(state["simulated_at"]), "Acquisition exceeds actual workroom clock")
        self._authorize(systems, active=True)
        try:
            self.session._context(self.engine, self.auditor, self.engagement)
            with self.pair.world.verified_sources():
                rows, _ = discover_history(
                    self.session.store,
                    self.auditor,
                    self.engagement,
                    self.binding["company"],
                    self.binding["branch"],
                    as_of=cutoff,
                    systems=systems,
                )
            rows = [{**row, "discovered_as_of": cutoff} for row in rows]
            state = command(
                self.engine,
                self.auditor,
                self.engagement,
                "pbc.create",
                {
                    "title": "Company original request " + control_id,
                    "purpose": purpose,
                    "control_id": control_id,
                    "person_id": "AS-P007",
                    "boundary_id": "corporate",
                },
            )
            request = state["requests"][-1]["id"]
            command(
                self.engine, self.auditor, self.engagement, "pbc.issue", {"request_id": request}
            )
            artifacts = self.state()["artifacts"]
            retained = []
            for row in rows:
                existing = self._retained(
                    row, artifacts, cutoff=cutoff, collection_clock=state["simulated_at"]
                )
                if existing is not None:
                    retained.append(existing)
                    continue
                revision = self.engine.store.get(self.auditor, self.engagement)["revision"]
                with self.pair.world.verified_sources():
                    item = self.session.collect(
                        self.engine,
                        self.auditor,
                        self.engagement,
                        request,
                        row,
                        command_id=f"pair-collect-{revision}",
                    )
                current = self.engine.store.get(self.auditor, self.engagement)
                artifact = next(a for a in current["artifacts"] if a["id"] == item["artifact_id"])
                item["content"] = self.engine.artifacts.read(artifact)
                item["retained_bytes"] = item["content"]
                retained.append(item)
                artifacts.append(artifact)
            write(
                self.root / f"ACQUISITION-{request}.json",
                {
                    "engagement_id": self.engagement,
                    "request_id": request,
                    "purpose": purpose,
                    "systems": list(systems),
                    "actual_workroom_clock": state["simulated_at"],
                    "discovery_cutoff": cutoff,
                    "retained_artifact_ids": [r["artifact_id"] for r in retained],
                    "source_references": [
                        {k: r["source"][k] for k in BUSINESS_REFERENCE} for r in retained
                    ],
                    "reuse_basis": "EXACT_ALREADY_RETAINED_ORIGINAL_IN_THIS_ENGAGEMENT_ONLY",
                },
            )
            return retained
        finally:
            self._authorize(systems, active=False)
            self.session.check_unchanged()

    def _checked_rows(self, rows):
        require(
            rows and len({r["artifact_id"] for r in rows}) == len(rows),
            "Distinct actual retained originals required",
        )
        state = self.state()
        artifacts = {a["id"]: a for a in state["artifacts"]}
        for item in rows:
            require(item["artifact_id"] in artifacts, "Foreign or invented retained artifact")
            artifact = artifacts[item["artifact_id"]]
            require(
                artifact["source"].get("kind") == "COLLECTED_COMPANY_SOURCE",
                "Company-native original required",
            )
            receipt = artifact["source"]["receipt"]
            source = receipt["source"]
            route = self.session.routes.get(tuple(source[k] for k in NATIVE_ID[:3]))
            raw = self.engine.artifacts.read(artifact)
            require(
                type(source["version"]) is int
                and source["version"] > 0
                and type(receipt["content_bytes"]) is int
                and receipt["content_bytes"] > 0
                and _time(source["imported_at"])
                <= _time(receipt["collected_at"])
                <= _time(datetime.now(UTC).isoformat())
                and route is not None
                and _json(receipt) == _json(item["receipt"])
                and _json(source) == _json(item["source"])
                and receipt["engagement_id"] == self.engagement
                and receipt["principal_id"] == self.auditor
                and item["logical_family"] == route.family
                and item["logical_system"] == route.logical_system
                and raw == item["content"] == item["retained_bytes"]
                and hashlib.sha256(raw).hexdigest()
                == artifact["sha256"]
                == item["artifact_sha256"]
                == source["sha256"]
                and len(raw) == receipt["content_bytes"]
                and _time(source["available_at"])
                <= _time(receipt["simulated_as_of"])
                <= _time(state["simulated_at"])
                and (
                    source["event_at"] is None
                    or _time(source["event_at"]) <= _time(receipt["simulated_as_of"])
                ),
                "Retained method input differs from actual workroom original/clock/route",
            )
            item["document"], item["content_type"] = typed_content({**source, "content": raw})
        return state

    def append_reviewed_batch(self, *, batch, review, rows, method=None):
        """Run exact reviewed code against fresh originals; append ordinary records."""
        state = self._checked_rows(rows)
        if method is None:
            approval = independent_method_gate(batch, review)
            task_ids = approval["task_ids"]
        else:
            approval, task_ids = self._general_method_gate(method, review)
        require(
            set(task_ids) <= {t["id"] for t in state["tasks"]},
            "Reviewed batch includes unavailable tasks",
        )
        require(
            all(
                t.get("control_id") in {c["id"] for c in state["controls"]}
                and t["kind"] != "SCOPE_DEPENDENCY"
                for t in state["tasks"]
                if t["id"] in task_ids
            ),
            "Scope dependency tasks require the separate dedicated examination contract",
        )
        require(
            all(
                t["status"] == "NOT_STARTED" and t["conclusion"] == "NOT_RUN"
                for t in state["tasks"]
                if t["id"] in task_ids
            ),
            "A reviewed batch cannot overwrite previous task work",
        )
        root = self.root / f"BATCH-{batch}"
        require(
            not root.exists() and "/" not in batch and batch not in {".", ".."},
            "Distinct reviewed batch destination required",
        )
        root.mkdir(mode=0o700)
        write(
            root / "PLAN.json",
            {
                "schema": "SH_BOUND_COMPANY_BATCH_EXECUTION_PLAN_V1",
                "batch": batch,
                "review": approval,
                "task_ids": task_ids,
                "authored_instructions": {
                    task: authored_instruction(state, task) for task in task_ids
                },
                "ordinary_retained_artifact_ids": [r["artifact_id"] for r in rows],
                "simulated_at": state["simulated_at"],
                "cached_prior_outcomes_used": False,
            },
        )
        if method is not None:
            checkpoint = self.pair.world.checkpoint_sha256
            inspections = method(rows, as_of=state["simulated_at"], scratch_root=root)
            require(
                _json(self.state()) == _json(state)
                and self.pair.world.checkpoint_sha256 == checkpoint,
                "Pure reviewed method changed audit state or company history before append",
            )
            require(
                isinstance(inspections, list) and [i["task_id"] for i in inspections] == task_ids,
                "Exact reviewed task inspection vector required",
            )
            self._checked_rows(rows)
            for inspection in inspections:
                self._validate_inspection(
                    rows, inspection, approval["task_contracts"][inspection["task_id"]]
                )
            links = [self._append_inspection(rows, inspection) for inspection in inspections]
            dispositions = {
                i["task_id"]: {k: i["disposition"][k] for k in ("status", "conclusion")}
                for i in inspections
            }
        elif batch == "security":
            selected_plans = plans()
            analyses = {
                "SEC003": analyze_vulnerability,
                "SEC005": analyze_security_publishers,
                "BCM003": analyze_continuity_timestamps,
            }
            links = [
                record_security(
                    self.engine,
                    self.auditor,
                    self.engagement,
                    rows,
                    label,
                    analyses[label](rows, selected_plans[label]),
                    selected_plans[label],
                    root,
                )
                for label in SECURITY_TASKS
            ]
        elif batch == "privacy":
            result = examine_privacy(rows, as_of=state["simulated_at"])
            write(root / "EXAMINATION.json", result)
            links = [
                record_privacy(
                    self.engine,
                    self.auditor,
                    self.engagement,
                    rows,
                    result,
                    label,
                    root,
                )
                for label in PRIVACY_TASKS
            ]
            record_privacy_findings(self.engine, self.auditor, self.engagement, rows, result)
        else:
            links = legal_batch(self, rows, root)
        if method is None:
            dispositions = {
                task: {"status": "IN_PROGRESS", "conclusion": "LIMITATION"} for task in task_ids
            }
        self._verify_batch_append(state, dispositions)
        write(
            root / "RECEIPT.json",
            {
                "schema": "SH_BOUND_COMPANY_BATCH_EXECUTION_RECEIPT_V1",
                "batch": batch,
                "engagement_id": self.engagement,
                "mode": self.mode,
                "task_ids": task_ids,
                "links": links,
                "review": approval,
                "actual_simulated_at": self.state()["simulated_at"],
                "professional_review_performed": False,
                "task_dispositions": dispositions,
                "broader_enterprise_or_annual_credit": False,
            },
        )
        return links

    def _general_method_gate(self, method, gate):
        review = gate.read()
        filename = Path(inspect.getsourcefile(method) or "").absolute()
        require(
            filename.is_relative_to(self.pair.repository)
            and filename.suffix == ".py"
            and not any(p.is_symlink() for p in [filename, *filename.parents]),
            "Reviewed repository-native method required",
        )
        task_ids = review.get("selected_task_ids")
        dependency_pins = review.get("dependency_module_sha256")
        require(
            review.get("schema") == GENERAL_METHOD_SCHEMA
            and review.get("verdict") == GENERAL_METHOD_VERDICT
            and review.get("source_execution_authorized") is True
            and review.get("method_module_sha256") == file_sha(filename)
            and review.get("method_callable") == method.__module__ + "." + method.__qualname__
            and isinstance(task_ids, list)
            and task_ids
            and len(set(task_ids)) == len(task_ids),
            "Exact independently reviewed collected-byte batch method required",
        )
        require(
            isinstance(dependency_pins, dict), "Explicit reviewed method dependency pins required"
        )
        for name, pin in dependency_pins.items():
            require(
                isinstance(name, str)
                and Path(name).name == name
                and name.endswith(".py")
                and file_sha(Path(__file__).with_name(name)) == pin,
                "Reviewed method dependency implementation changed",
            )
        contracts = review.get("task_contracts")
        require(
            isinstance(contracts, dict) and set(contracts) == set(task_ids),
            "Independent review must bind exact per-task facets and dispositions",
        )
        for contract in contracts.values():
            require(
                set(contract) == {"performed", "unperformed", "allowed_dispositions"}
                and all(
                    isinstance(contract[k], str) and contract[k].strip()
                    for k in ("performed", "unperformed")
                )
                and isinstance(contract["allowed_dispositions"], list)
                and contract["allowed_dispositions"],
                "Exact task-specific performed/unperformed attributes required",
            )
            for disposition in contract["allowed_dispositions"]:
                require(
                    set(disposition) == {"status", "conclusion"}
                    and disposition["status"] in {"IN_PROGRESS", "COMPLETE"}
                    and disposition["conclusion"] in {"LIMITATION", "FAIL"},
                    "Reviewed bounded task disposition required; professional PASS is excluded",
                )
        return {
            "path": str(gate.path),
            "sha256": gate.sha256,
            "task_ids": task_ids,
            "task_contracts": contracts,
            "dependency_module_sha256": dependency_pins,
        }, task_ids

    def _validate_inspection(self, rows, inspection, contract):
        require(
            set(inspection)
            == {
                "task_id",
                "artifact_ids",
                "observations",
                "performed",
                "unperformed",
                "result",
                "disposition",
            },
            "Exact bounded task inspection fields required",
        )
        ids = inspection["artifact_ids"]
        require(
            isinstance(ids, list)
            and ids
            and len(set(ids)) == len(ids)
            and set(ids) <= {r["artifact_id"] for r in rows},
            "Task inspection must cite its actually retained originals",
        )
        require(
            all(inspection[k] == contract[k] for k in ("performed", "unperformed")),
            "Actual task facets differ from independently reviewed attributes",
        )
        disposition = inspection["disposition"]
        require(
            set(disposition) == {"status", "conclusion", "rationale"}
            and {k: disposition[k] for k in ("status", "conclusion")}
            in contract["allowed_dispositions"]
            and isinstance(disposition["rationale"], str)
            and disposition["rationale"].strip(),
            "Actual task disposition is not independently authorized",
        )
        retained = [r for r in rows if r["artifact_id"] in ids]
        require(
            any(r["source"]["event_at"] is not None for r in retained),
            "Actual selected source event bounds required before append",
        )
        documentary_population_attribution(self.state(), retained)
        require(
            isinstance(inspection["observations"], list)
            and inspection["observations"]
            and len({o["id"] for o in inspection["observations"]})
            == len(inspection["observations"]),
            "Distinct task-specific observations required",
        )
        _json(inspection)
        for observed in inspection["observations"]:
            require(
                set(observed) == {"id", "facts", "status", "evidence"}
                and isinstance(observed["id"], str)
                and 0 < len(observed["id"]) <= 128
                and observed["status"] in {"OBSERVED", "EXCEPTION_RECORDED", "SUPPORT_UNAVAILABLE"}
                and isinstance(observed["evidence"], list)
                and 0 < len(observed["evidence"]) <= 20,
                "Actual task observation and evidence required",
            )
            for evidence in observed["evidence"]:
                require(
                    set(evidence) == {"artifact_id", "sha256", "locator"}
                    and isinstance(evidence["locator"], str)
                    and evidence["locator"].strip(),
                    "Explicit exact observed source locator required before append",
                )
                matching = [r for r in retained if r["artifact_id"] == evidence["artifact_id"]]
                require(
                    len(matching) == 1 and evidence["sha256"] == matching[0]["artifact_sha256"],
                    "Observation evidence must be a task-cited exact collected original",
                )
        require(inspection["observations"], "Each task requires its own observations")

    def _append_inspection(self, rows, inspection):
        retained = [r for r in rows if r["artifact_id"] in inspection["artifact_ids"]]
        return record_documentary_items(
            self,
            inspection["task_id"],
            retained,
            inspection["observations"],
            performed=inspection["performed"],
            unperformed=inspection["unperformed"],
            result=inspection["result"],
            disposition=inspection["disposition"],
        )

    def _verify_batch_append(self, before, dispositions):
        after = self.state()
        require(not before["reviews"] and not after["reviews"], "Reserved reviewer remains unused")
        require(
            before["artifacts"] == after["artifacts"]
            and before["scope"] == after["scope"]
            and before["simulated_at"] == after["simulated_at"],
            "Batch cannot replace originals, scope or actual clock",
        )
        for field in (
            "workpapers",
            "populations",
            "selections",
            "sample_executions",
            "findings",
            "requests",
        ):
            require(
                _json(after[field][: len(before[field])]) == _json(before[field]),
                "Existing fieldwork history changed: " + field,
            )
        require(
            _json(before["controls"]) == _json(after["controls"]),
            "Reviewed batch cannot alter the authored scoped controls",
        )
        old = {t["id"]: t for t in before["tasks"]}
        for task in after["tasks"]:
            if task["id"] not in dispositions:
                require(task == old[task["id"]], "Unselected task changed")
            else:
                require(
                    all(task[k] == dispositions[task["id"]][k] for k in ("status", "conclusion")),
                    "Actual task disposition differs from independently reviewed execution",
                )
                require(
                    _json(task["history"][: len(old[task["id"]]["history"])])
                    == _json(old[task["id"]]["history"]),
                    "Existing task history changed",
                )
                permitted = {
                    "status",
                    "conclusion",
                    "rationale",
                    "history",
                    "actor",
                    "simulated_at",
                    "recorded_at",
                }
                require(
                    all(
                        _json(task.get(k)) == _json(value)
                        for k, value in old[task["id"]].items()
                        if k not in permitted
                    ),
                    "Reviewed task's authored identity or instruction changed",
                )
        require(
            {
                task
                for paper in after["workpapers"][len(before["workpapers"]) :]
                for task in paper["versions"][-1]["task_ids"]
            }
            == set(dispositions),
            "Every selected task requires its own appended workpaper",
        )
        self.session.check_unchanged()


class FullScopePair:
    """Company initialization precedes every workroom; neither inherits old work."""

    def __init__(self, *, expected_fieldwork_start=SCOPE["fieldwork_start"]):
        _pair_scope(expected_fieldwork_start)
        self.expected_fieldwork_start = expected_fieldwork_start

    @property
    def expected_scope(self):
        return _pair_scope(self.expected_fieldwork_start)

    @classmethod
    def initialize(
        cls,
        *,
        accepted,
        repository,
        program_pack,
        routes_by_mode,
        destination,
        operator_id,
        adapter_review=None,
        runtime_review=None,
        pair_review=None,
        engineering_only=False,
    ):
        require(
            type(engineering_only) is bool and set(routes_by_mode) == set(MODES),
            "Explicit engineering boundary and two exact modes required",
        )
        repository, program_pack = Path(repository).absolute(), Path(program_pack).absolute()
        pins = accepted.verify()
        require(
            file_sha(program_pack) == PROGRAM_SHA, "Exact complete authored program pack required"
        )
        for routes in routes_by_mode.values():
            require(
                routes and len({(r.company, r.branch) for r in routes}) == 1,
                "One declared native company/branch per mode required",
            )
        require(
            len({(routes[0].company, routes[0].branch) for routes in routes_by_mode.values()}) == 2,
            "Clean and messy workrooms require distinct native company branches",
        )
        if not engineering_only:
            require(
                adapter_review and runtime_review and pair_review,
                "Source adapter runtime and orchestration acceptance required",
            )
            adapter_gate(adapter_review.path, adapter_review.sha256, pins)
            runtime = runtime_review.read()
            require(
                runtime.get("schema") == RUNTIME_SCHEMA
                and runtime.get("verdict") == RUNTIME_VERDICT
                and runtime.get("source_execution_authorized") is True
                and runtime.get("runtime_module_sha256")
                == file_sha(Path(__file__).with_name("persistent_company_journey.py"))
                and runtime.get("adapter_module_sha256")
                == file_sha(Path(__file__).with_name("source_library_audit.py"))
                and runtime.get("accepted_baseline_pins") == pins,
                "Current separately accepted runtime/source composition required",
            )
            require_pair_gate(pair_review, pins, routes_by_mode)
        destination = Path(destination).absolute()
        require(
            not destination.exists()
            and not any(p.is_symlink() for p in [destination, *destination.parents])
            and stat.S_IMODE(destination.parent.stat().st_mode) == 0o700,
            "New private ordinary pair destination required",
        )
        destination.mkdir(mode=0o700)
        ordinary_copy(program_pack, destination / "program-pack.json")
        world = PersistentCompany.initialize(
            accepted,
            destination / "company",
            operator_id=operator_id,
            engineering_only=engineering_only,
        )
        if not engineering_only:
            world.accept_runtime(runtime_review.path, runtime_review.sha256)
        pair = cls()
        pair.world, pair.root, pair.repository = world, destination, repository
        pair.program_pack = destination / "program-pack.json"
        pair.pins, pair.engineering_only = pins, engineering_only
        pair.adapter_review, pair.pair_review = adapter_review, pair_review
        pair.routes_by_mode, pair.rooms = routes_by_mode, {}
        write(
            destination / "PAIR_START.json",
            {
                "schema": "SH_SHARED_COMPANY_FULL_PROGRAM_PAIR_START_V1",
                "accepted_baseline_pins": pins,
                "company_root": str(world.root),
                "company_checkpoint_sha256": world.checkpoint_sha256,
                "company_initialization_sha256": file_sha(world.root / "INITIALIZATION.json"),
                "route_vector": route_vector(routes_by_mode),
                "scope": SCOPE,
                "program_pack_sha256": PROGRAM_SHA,
                "source_quality_is_enterprise_completeness": False,
                "company_created_before_audit": True,
                "engineering_only": engineering_only,
            },
        )
        for mode in MODES:
            root = destination / mode
            root.mkdir(mode=0o700)
            session = PersistentAudit(world, routes_by_mode[mode])
            engine, state, identities = session.create(
                repository=repository,
                audit_root=root / "audit-state",
                program_pack=pair.program_pack,
                payload={
                    "command_id": "full-scope-fresh-create-" + mode,
                    "title": "Company-native full-scope audit workroom " + mode,
                    "discipline": "IT",
                    "mode": mode,
                    "configuration": {"selections": []},
                    "scope": json.loads(json.dumps(SCOPE)),
                },
            )
            require(
                len(state["tasks"]) == 409 and _time(state["simulated_at"]) == _time(INITIAL),
                "All 409 authored tasks and genuine initial December clock required",
            )
            require(not state["sample_executions"], "No inherited sample executions")
            scope_ids = [t["id"] for t in state["tasks"] if t["kind"] == "SCOPE_DEPENDENCY"]
            require(len(scope_ids) == 2, "Two separate scope dependency tasks required")
            write(
                root / "TASK_ACCOUNTING_AT_BIRTH.json",
                {
                    "schema": "SH_FULL_SCOPE_PAIR_TASK_ACCOUNTING_AT_BIRTH_V1",
                    "all_task_ids": [t["id"] for t in state["tasks"]],
                    "scope_dependency_task_ids": scope_ids,
                    "control_task_count": 407,
                    "selected_reusable_method_task_count": 12,
                    "prior_identity_method_port_candidates": 30,
                    "new_control_clause_method_candidates": 365,
                    "fieldwork_performed_at_birth": 0,
                    "scope_dependency_batch_writer_support": "SEPARATE_CONTRACT_REQUIRED",
                },
            )
            company, branch = routes_by_mode[mode][0].company, routes_by_mode[mode][0].branch
            binding = {
                "schema": BINDING_SCHEMA,
                "company_root": str(world.root),
                "company_initialization_sha256": file_sha(world.root / "INITIALIZATION.json"),
                "accepted_baseline_pins": pins,
                "audit_root": str(engine.store.root),
                "engagement_id": state["id"],
                "company": company,
                "branch": branch,
                "identities": session.identities,
                "company_operator_id": world.operator.principal,
                "program_pack": {"path": str(pair.program_pack), "sha256": PROGRAM_SHA},
                "task_count": len(state["tasks"]),
                "mode": mode,
                "initial_simulated_at": state["simulated_at"],
                "scope": state["scope"],
                "zero_workroom_counts": identities["zero_workroom_counts"],
            }
            write(root / "BINDING.json", binding)
            command(engine, identities["operator"], state["id"], "company.activate", {})
            command(engine, identities["auditor"], state["id"], "kickoff.start", {})
            pair.rooms[mode] = BoundWorkroom(pair, mode, session, binding)
        pair.check()
        return pair

    def check(self):
        require(self.world.verify_accepted_pins() == self.pins, "Accepted baseline changed")
        require(file_sha(self.program_pack) == PROGRAM_SHA, "Retained program pack changed")
        self.world.require_runtime()
        if not self.engineering_only:
            adapter_gate(self.adapter_review.path, self.adapter_review.sha256, self.pins)
            require_pair_gate(
                self.pair_review,
                self.pins,
                self.routes_by_mode,
                expected_scope=self.expected_scope,
            )
