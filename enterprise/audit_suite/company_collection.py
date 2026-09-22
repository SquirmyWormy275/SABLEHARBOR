"""Collect existing company originals through explicit trusted engagement bindings."""

from __future__ import annotations

from .store import DomainError, digest

# These native systems retain raw object/document bytes, not JSON envelopes.
# Text intake still inspects the exact bytes; unknown systems keep JSON validation.
_UNNAMED_TEXT_SYSTEMS = frozenset(
    {"privileged_object", "policy_document", "nonhuman_source", "copied_dataset"}
)


def binding(engine, state):
    if engine.company_store is None:
        raise DomainError("Company source connection is not configured", status=503)
    selected = engine.company_bindings.get(state["id"])
    if getattr(engine.company_store, "is_federated", False):
        from .company_store import CompanyStoreError

        try:
            engine.company_store.validate_binding(selected)
        except CompanyStoreError as exc:
            raise DomainError(
                "Company portfolio binding changed or unavailable", status=409
            ) from exc
    elif not isinstance(selected, dict) or set(selected) != {"company", "branch"}:
        raise DomainError("Company source binding is unavailable", status=404)
    frozen = state.get("company_source_binding")
    if frozen is not None and frozen != selected:
        raise DomainError("Company binding changed; explicit reconciliation required", status=409)
    return selected


def discover(engine, actor, engagement_id, system_id, *, after_record=None, limit=100):
    state = engine.store.get(actor, engagement_id)
    bound = binding(engine, state)
    from .company_store import CompanyStoreError

    try:
        return engine.company_store.list_records(
            actor,
            engagement_id,
            bound["company"],
            bound["branch"],
            system_id,
            as_of=state["simulated_at"],
            after_record=after_record,
            limit=limit,
        )
    except CompanyStoreError as exc:
        raise DomainError("Company source unavailable or request invalid", status=403) from exc


def collect(engine, state, payload, stamped, command_id):
    if set(payload) != {"system_id", "record_id", "version", "request_id"}:
        raise DomainError("Choose an existing source version and evidence request")
    request = next((r for r in state["requests"] if r["id"] == payload["request_id"]), None)
    if request is None or request["status"] not in {
        "ISSUED",
        "ACKNOWLEDGED",
        "IN_PROGRESS",
        "CLARIFICATION",
        "SUBMITTED",
    }:
        raise DomainError("Issue an evidence request before collecting company support")
    bound = binding(engine, state)
    from .company_store import CompanyStoreError

    actor = stamped["actor"]
    args = (
        actor,
        state["id"],
        bound["company"],
        bound["branch"],
        payload["system_id"],
        payload["record_id"],
    )
    kwargs = {"version": payload["version"], "as_of": state["simulated_at"]}
    try:
        record = engine.company_store.read_version(*args, **kwargs)
        identity = {
            key: record[key]
            for key in ("company", "branch", "system", "record", "version", "sha256")
        }
        for key in ("source_store_id", "source_system_alias", "registry_sha256"):
            if key in record:
                identity[key] = record[key]
        if any(
            row.get("source_identity") == identity for row in request.get("company_collections", [])
        ):
            return
        receipt = engine.company_store.collect(
            *args, **kwargs, command_id="COL-" + digest([state["id"], command_id])
        )
    except CompanyStoreError as exc:
        raise DomainError("Company source unavailable or request invalid", status=403) from exc
    # Source identifiers may contain colons or exceed filename limits together.
    # Keep their exact values in the receipt, independently of the download name.
    name = record["provenance"].get("name")
    if name is None:
        suffix = ".txt" if record["system"] in _UNNAMED_TEXT_SYSTEMS else ".json"
        name = "company-source-" + digest(identity) + suffix
    source = {"kind": "COLLECTED_COMPANY_SOURCE", "receipt": receipt, "origin": record["origin"]}
    manifest = engine.artifacts.retain_company(
        state["id"],
        name,
        record["content"],
        source=source,
        coverage={
            "request_id": request["id"],
            "control_id": request.get("control_id"),
            "professional_sufficiency": "NOT_ASSERTED",
        },
    )
    manifest.update(stamped)
    manifest.update(
        request_id=request["id"], version=record["version"], received_at=stamped["recorded_at"]
    )
    provenance = record["provenance"]
    if provenance.get("source_period_start") and provenance.get("source_period_end"):
        manifest["covered_period"] = (
            f"Source snapshot: {provenance['source_period_start']} – "
            f"{provenance['source_period_end']}"
        )
    state["artifacts"].append(manifest)
    request.setdefault("artifact_ids", []).append(manifest["id"])
    request["status"] = "SUBMITTED"
    request["unread"] = True
    request.setdefault("company_collections", []).append(
        {
            "artifact_id": manifest["id"],
            "source_identity": identity,
            "source_record": record["record"],
            "source_version": record["version"],
            "source_sha256": record["sha256"],
            "collection_command": receipt["command_id"],
            **stamped,
        }
    )


def activate(engine, state, payload, stamped):
    """Instructor starts a bound source investigation without generating evidence."""
    if payload or state["phase"] != "CONFIGURING":
        raise DomainError("Activate an ungenerated engagement with no additional payload")
    if state["artifacts"] or state["requests"] or state["configuration"].get("selections"):
        raise DomainError("Source activation cannot replace existing evidence or scenario plans")
    bound = binding(engine, state)
    if any(not control.get("owner_ids") for control in state["controls"]):
        raise DomainError("Resolve scoped control ownership before activation")
    state["company_source_binding"] = dict(bound)
    state["evidence_acquisition"] = "COMPANY_SOURCE_COLLECTION"
    state["phase"] = "READY"
    state["generation"] = {
        "state": "READY",
        "completed": 0,
        "errors": [],
        "stage": "Company source connection; no evidence generated",
    }
    state["clock"] = {"simulated_at": state["simulated_at"]}
