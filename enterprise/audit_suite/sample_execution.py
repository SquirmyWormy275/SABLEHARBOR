"""Author-recorded sampled-item procedure traces, never automatic testing credit."""

from collections import Counter
from copy import deepcopy
from datetime import datetime, time
from zoneinfo import ZoneInfo

from . import populations
from .population_lifecycle import population, record, selection
from .store import DomainError, canonical, digest, identifier
from .workpaper_links import validate_task_ids

COMMANDS = {"sample.execution.record", "sample.execution.correct"}
FIELDS = {
    "task_id",
    "task_digest",
    "selection_id",
    "selection_digest",
    "population_id",
    "population_digest",
    "workpaper_id",
    "workpaper_version",
    "workpaper_digest",
    "purpose",
    "procedure",
    "items",
}
CORRECTION = {"predecessor_id", "predecessor_digest", "correction_rationale"}
STATUSES = {"OBSERVED", "EXCEPTION_RECORDED", "SUPPORT_UNAVAILABLE", "NOT_PERFORMED"}


def require(condition, message):
    if not condition:
        raise DomainError(message)


def text(value, label, maximum=4000):
    require(
        isinstance(value, str) and 0 < len(value.strip()) <= maximum, "Bounded required " + label
    )
    return value


def exact_hash(value, label):
    require(
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
        "Exact " + label + " SHA256 required",
    )
    return value


def boundary_time(value, scope, end=False):
    parsed = datetime.fromisoformat(value)
    if len(value) == 10:
        parsed = datetime.combine(
            parsed.date(), time.max if end else time.min, ZoneInfo(scope.get("timezone", "UTC"))
        )
    require(parsed.tzinfo is not None, "Explicit population/engagement time basis required")
    return parsed


def _lineage(state, row, obj, seen=None):
    seen = set() if seen is None else seen
    require(
        obj.id not in seen and len(seen) < 16, "Bounded acyclic population parent lineage required"
    )
    seen.add(obj.id)
    if not obj.parent_selection_digest:
        require(not row.get("parent_selection_id"), "Unexpected parent selection reference")
        return []
    parent_row = record(state, "selections", row.get("parent_selection_id"))
    parent_selection = selection(parent_row)
    parent_population_row = record(state, "populations", parent_selection.population_id)
    parent_population = population(parent_population_row)
    populations.validate_selection(parent_population, parent_selection)
    require(
        parent_selection.sha256 == obj.parent_selection_digest
        and parent_population.sha256 == obj.parent_population_digest,
        "Parent population/selection digest differs",
    )
    require(
        all(r.get(obj.parent_key) in parent_selection.all_ids for r in obj.rows),
        "Child item outside exact parent selection",
    )
    return [
        {
            "selection_id": parent_selection.id,
            "selection_digest": parent_selection.sha256,
            "population_id": parent_population.id,
            "population_digest": parent_population.sha256,
            "parent_key": obj.parent_key,
        }
    ] + _lineage(state, parent_population_row, parent_population, seen)


def handle(state, kind, payload, stamped, artifacts):
    """Only invoke inside Store's current learn/instruct CAS/replay transaction.

    The handler reads originals but mutates only sample_executions at final append.
    Locators/observations are author supplied, not machine-verified content matches.
    """
    require(kind in COMMANDS, "Unsupported sample execution command")
    require(state.get("phase") == "ACTIVE", "Sample execution requires an active engagement")
    expected = FIELDS | (CORRECTION if kind.endswith("correct") else set())
    require(
        isinstance(payload, dict) and set(payload) == expected,
        "Exact sample execution fields required",
    )
    require(
        len(state.get("sample_executions", [])) < 10000, "Sample execution history limit reached"
    )
    require(
        len(canonical(payload).encode()) <= 512 * 1024, "Sample execution payload exceeds512KiB"
    )
    p = deepcopy(payload)
    for field in ("task_id", "selection_id", "population_id", "workpaper_id"):
        text(p[field], field, 128)
    for field in ("task_digest", "selection_digest", "population_digest", "workpaper_digest"):
        exact_hash(p[field], field)
    text(p["purpose"], "purpose")
    text(p["procedure"], "procedure", 12000)
    task = record(state, "tasks", p["task_id"])
    validate_task_ids(state, task.get("control_id"), [task["id"]])
    require(
        task.get("applicability", "CURRENT_SCOPE") == "CURRENT_SCOPE",
        "Procedure requires current scope applicability",
    )
    require(
        task.get("scope_version", state.get("generation_epoch", 0))
        == state.get("generation_epoch", 0),
        "Procedure belongs to an earlier scope epoch",
    )
    require(digest(task) == p["task_digest"], "Procedure digest changed")
    pop_row = record(state, "populations", p["population_id"])
    require(
        pop_row.get("scope_reassessment") != "REQUIRED_FOR_REUSE",
        "Population requires explicit scope reassessment",
    )
    try:
        pop = population(pop_row)
        chosen = selection(record(state, "selections", p["selection_id"]))
        require(
            pop.id == p["population_id"] and chosen.id == p["selection_id"],
            "Immutable population/selection identity differs from API record",
        )
        populations.validate_selection(pop, chosen)
        lineage = _lineage(state, pop_row, pop)
    except (ValueError, TypeError, KeyError) as error:
        raise DomainError("Invalid immutable sample/population lineage") from error
    require(
        pop.sha256 == p["population_digest"] and chosen.sha256 == p["selection_digest"],
        "Exact population/selection digest differs",
    )
    scope = state["scope"]
    boundary = pop.scope["boundary_id"]
    require(
        boundary in scope.get("boundaries", []) and task.get("boundary_id") == boundary,
        "Sample and procedure must share a current explicit boundary",
    )
    require(
        boundary_time(scope["period_start"], scope)
        <= boundary_time(pop.scope["period_start"], pop.scope)
        and boundary_time(pop.scope["period_end"], pop.scope, True)
        <= boundary_time(scope["period_end"], scope, True),
        "Population period lies outside current engagement scope",
    )
    paper = record(state, "workpapers", p["workpaper_id"])
    require(
        paper.get("control_id") == task.get("control_id"),
        "Workpaper and procedure must share the scoped control",
    )
    require(type(p["workpaper_version"]) is int, "Exact integer workpaper version required")
    versions = [v for v in paper["versions"] if v["version"] == p["workpaper_version"]]
    require(len(versions) == 1, "Pinned workpaper version unavailable")
    version = versions[0]
    require(
        digest(version) == p["workpaper_digest"] and task["id"] in version.get("task_ids", []),
        "Pinned workpaper digest or explicit procedure link differs",
    )
    items = p["items"]
    require(
        isinstance(items, list) and 1 <= len(items) <= 500,
        "One to500 explicit sample items required",
    )
    ids = []
    verified = {}
    annotated = []
    total = 0
    source_rows = {r["id"]: r for r in pop.rows}
    for item in items:
        require(
            isinstance(item, dict)
            and set(item) == {"item_id", "observation", "status", "evidence"},
            "Exact sampled item fields required",
        )
        item_id = text(item["item_id"], "sample item ID", 256)
        require(
            item_id not in ids and item_id in chosen.all_ids,
            "Item must be a unique member of the exact selection",
        )
        ids.append(item_id)
        text(item["observation"], "item observation", 8000)
        require(
            isinstance(item["status"], str) and item["status"] in STATUSES,
            "Explicit author observation status required",
        )
        evidence = item["evidence"]
        require(
            isinstance(evidence, list) and len(evidence) <= 20,
            "At most20 explicit evidence references per item",
        )
        require(
            item["status"] in {"NOT_PERFORMED", "SUPPORT_UNAVAILABLE"} or evidence,
            "An observed item requires retained support",
        )
        refs = []
        for ref in evidence:
            require(
                isinstance(ref, dict) and set(ref) == {"artifact_id", "sha256", "locator"},
                "Exact evidence reference fields required",
            )
            text(ref["artifact_id"], "artifact ID", 128)
            exact_hash(ref["sha256"], "artifact")
            text(ref["locator"], "author supplied locator", 1000)
            artifact = record(state, "artifacts", ref["artifact_id"])
            require(
                artifact.get("status") == "AVAILABLE"
                and artifact.get("audience", "LEARNER") == "LEARNER"
                and artifact.get("engagement_id", state["id"]) == state["id"],
                "Evidence must be current authorized learner-visible retained content",
            )
            require(artifact["sha256"] == ref["sha256"], "Evidence SHA256 differs")
            if artifact["id"] not in verified:
                size = artifact.get("bytes")
                require(
                    type(size) is int and 0 <= size <= 16 * 1024 * 1024,
                    "Bounded evidence size required",
                )
                total += size
                require(
                    total <= 32 * 1024 * 1024 and len(verified) < 100,
                    "Bounded aggregate evidence required",
                )
                try:
                    artifacts.read(artifact)
                except (OSError, ValueError) as error:
                    raise DomainError("Retained evidence original unavailable") from error
                verified[artifact["id"]] = artifact["sha256"]
            require(ref not in refs, "Duplicate evidence locator")
            refs.append(ref)
        annotated.append(
            {
                **item,
                "item_digest": digest(source_rows[item_id]),
                "selection_basis": "TARGETED" if item_id in chosen.targeted_ids else "SAMPLED",
                "locator_validation": "AUTHOR_SUPPLIED_NOT_CONTENT_MATCH_VERIFIED",
            }
        )
    predecessor = None
    if kind.endswith("correct"):
        text(p["correction_rationale"], "correction rationale")
        exact_hash(p["predecessor_digest"], "predecessor")
        matches = [r for r in state.get("sample_executions", []) if r["id"] == p["predecessor_id"]]
        require(len(matches) == 1, "Correction predecessor unavailable")
        predecessor = matches[0]
        require(
            predecessor["scope_digest"] == digest(scope)
            and predecessor.get("company_source_binding") == state.get("company_source_binding")
            and predecessor.get("evidence_acquisition") == state.get("evidence_acquisition"),
            "Correction requires the original scope and company source context",
        )
        require(
            digest(predecessor) == p["predecessor_digest"], "Correction predecessor digest changed"
        )
        require(
            not any(
                r.get("predecessor_id") == predecessor["id"]
                for r in state.get("sample_executions", [])
            ),
            "Correction must reference latest trace revision",
        )
        for field in (
            "task_id",
            "selection_id",
            "selection_digest",
            "population_id",
            "population_digest",
        ):
            require(
                predecessor[field] == p[field],
                "Correction cannot replace original procedure/sample identity",
            )
        require(
            set(ids) == {i["item_id"] for i in predecessor["items"]},
            "Correction must preserve the exact sampled item set",
        )
    trace = {
        **p,
        "items": annotated,
        "id": identifier("SEXEC"),
        "revision": predecessor["revision"] + 1 if predecessor else 1,
        "predecessor_id": predecessor["id"] if predecessor else None,
        "scope_digest": digest(scope),
        "scope": deepcopy(scope),
        "company_source_binding": deepcopy(state.get("company_source_binding")),
        "evidence_acquisition": deepcopy(state.get("evidence_acquisition")),
        "parent_lineage": lineage,
        "population_status": pop.status,
        "selection_provisional": chosen.provisional,
        "assertion_origin": "AUTHOR_RECORDED_PROCEDURE_OBSERVATION",
        "independent_review": "NOT_PERFORMED",
        "automatic_testing_credit": False,
        **stamped,
    }
    state.setdefault("sample_executions", []).append(trace)


def _input_pins(state):
    """Read-only metadata projection; call AFTER authorization/audience projection.

    Digests use the exact Python state objects used by handle(), not browser JSON
    number serialization. This is not evidence readability or sufficiency review.
    """
    scope = state.get("scope", {})
    collections = ("tasks", "populations", "selections", "workpapers", "artifacts")
    for name in collections:
        _input_limit(
            len(state.get(name, [])) <= 20000, "Sample input projection collection bound exceeded"
        )
    counts = {name: Counter(row["id"] for row in state.get(name, [])) for name in collections}
    controls = {c["id"] for c in state.get("controls", [])}
    tasks = []
    for task in state.get("tasks", []):
        if (
            task.get("control_id") not in controls
            or task.get("boundary_id") not in scope.get("boundaries", [])
            or task.get("applicability", "CURRENT_SCOPE") != "CURRENT_SCOPE"
            or task.get("scope_version", state.get("generation_epoch", 0))
            != state.get("generation_epoch", 0)
            or counts["tasks"][task["id"]] != 1
        ):
            continue
        tasks.append(
            {
                "task_id": task["id"],
                "task_digest": digest(task),
                "control_id": task["control_id"],
                "boundary_id": task["boundary_id"],
            }
        )
    task_map = {t["task_id"]: t for t in tasks}
    pops = {}
    for row in state.get("populations", []):
        if row.get("scope_reassessment") == "REQUIRED_FOR_REUSE":
            continue
        try:
            obj = population(row)
            require(obj.id == row["id"], "Population API identity differs")
            require(
                counts["populations"][obj.id] == 1,
                "Ambiguous population identity",
            )
            require(
                obj.scope["boundary_id"] in scope.get("boundaries", []),
                "Population outside current scope",
            )
            require(
                boundary_time(scope["period_start"], scope)
                <= boundary_time(obj.scope["period_start"], obj.scope)
                and boundary_time(obj.scope["period_end"], obj.scope, True)
                <= boundary_time(scope["period_end"], scope, True),
                "Population outside current period",
            )
            _lineage(state, row, obj)
            pops[obj.id] = obj
        except (DomainError, ValueError, KeyError, TypeError):
            continue
    selections = []
    for row in state.get("selections", []):
        try:
            obj = selection(row)
            require(
                obj.id == row["id"] and counts["selections"][obj.id] == 1,
                "Ambiguous selection identity",
            )
            pop = pops[obj.population_id]
            populations.validate_selection(pop, obj)
            selections.append(
                {
                    "selection_id": obj.id,
                    "selection_digest": obj.sha256,
                    "population_id": pop.id,
                    "population_digest": pop.sha256,
                    "population_version": pop.version,
                    "population_status": pop.status,
                    "selection_provisional": obj.provisional,
                    "boundary_id": pop.scope["boundary_id"],
                    "sampling_unit": pop.scope["unit"],
                    "selected_item_count": len(obj.selected_ids),
                    "targeted_item_count": len(obj.targeted_ids),
                }
            )
        except (DomainError, ValueError, KeyError, TypeError):
            continue
    versions = []
    for paper in state.get("workpapers", []):
        if counts["workpapers"][paper["id"]] != 1:
            continue
        _input_limit(
            len(paper.get("versions", [])) <= 10000, "Workpaper version projection bound exceeded"
        )
        version_counts = Counter(v.get("version") for v in paper.get("versions", []))
        for version in paper.get("versions", []):
            if type(version.get("version")) is not int or version_counts[version["version"]] != 1:
                continue
            task_ids = [
                t
                for t in version.get("task_ids", [])
                if t in task_map and task_map[t]["control_id"] == paper.get("control_id")
            ]
            if task_ids:
                versions.append(
                    {
                        "workpaper_id": paper["id"],
                        "workpaper_version": version["version"],
                        "workpaper_digest": digest(version),
                        "task_ids": task_ids,
                        "control_id": paper["control_id"],
                    }
                )
                _input_limit(len(versions) <= 20000, "Workpaper input projection bound exceeded")
    evidence = []
    for artifact in state.get("artifacts", []):
        if (
            artifact.get("status") == "AVAILABLE"
            and artifact.get("audience", "LEARNER") == "LEARNER"
            and artifact.get("engagement_id", state["id"]) == state["id"]
            and type(artifact.get("bytes")) is int
            and 0 <= artifact["bytes"] <= 16 * 1024 * 1024
            and counts["artifacts"][artifact["id"]] == 1
        ):
            try:
                exact_hash(artifact.get("sha256"), "artifact")
            except DomainError:
                continue
            evidence.append(
                {
                    "artifact_id": artifact["id"],
                    "sha256": artifact["sha256"],
                    "bytes": artifact["bytes"],
                }
            )
    traces = state.get("sample_executions", [])
    _input_limit(len(traces) <= 10000, "Sample execution history projection bound exceeded")
    trace_counts = Counter(trace["id"] for trace in traces)
    superseded = {trace.get("predecessor_id") for trace in traces}
    selection_map = {row["selection_id"]: row for row in selections}
    correction_pins = []
    for trace in traces:
        selected = selection_map.get(trace.get("selection_id"))
        task = task_map.get(trace.get("task_id"))
        if (
            state.get("phase") != "ACTIVE"
            or trace_counts[trace["id"]] != 1
            or trace["id"] in superseded
            or trace.get("scope_digest") != digest(scope)
            or trace.get("company_source_binding") != state.get("company_source_binding")
            or trace.get("evidence_acquisition") != state.get("evidence_acquisition")
            or selected is None
            or task is None
            or task["boundary_id"] != selected["boundary_id"]
            or any(
                trace.get(field) != selected[field]
                for field in ("selection_digest", "population_id", "population_digest")
            )
        ):
            continue
        correction_pins.append({"execution_id": trace["id"], "predecessor_digest": digest(trace)})
    return {
        "engagement_id": state["id"],
        "engagement_revision": state.get("revision"),
        "status": "AVAILABLE" if state.get("phase") == "ACTIVE" else "ENGAGEMENT_NOT_ACTIVE",
        "tasks": tasks,
        "selections": selections,
        "workpaper_versions": versions,
        "artifacts": evidence,
        "correctable_executions": correction_pins,
        "validation": "CURRENT_VISIBLE_REFERENCE_METADATA_ONLY_ORIGINAL_BYTES_RECHECKED_ON_RECORD",
        "automatic_testing_credit": False,
    }


class _InputProjectionLimit(Exception):
    pass


def _input_limit(condition, message):
    if not condition:
        raise _InputProjectionLimit(message)


def input_pins(state):
    """Fail closed for this optional index without breaking authorized legacy reads.

    No partially built choices are returned after any limit or malformed-data error.
    The mutation handler independently retains all strict rejecting bounds.
    """
    try:
        return _input_pins(state)
    except _InputProjectionLimit:
        status = "INPUT_LIMIT_EXCEEDED"
    except (DomainError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        status = "INPUT_DATA_UNAVAILABLE"
    return {
        "engagement_id": state.get("id"),
        "engagement_revision": state.get("revision"),
        "status": status,
        "tasks": [],
        "selections": [],
        "workpaper_versions": [],
        "artifacts": [],
        "correctable_executions": [],
        "validation": "INPUT_INDEX_UNAVAILABLE_NO_PARTIAL_CHOICES_RETURNED",
        "automatic_testing_credit": False,
    }
