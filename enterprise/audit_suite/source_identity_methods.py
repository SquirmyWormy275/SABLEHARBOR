"""Selected identity examinations over ordinary collected company originals.

Native coordinates and collection receipts remain intact. Business routing only
chooses a recorded role; it does not manufacture authority or a population. No
company database, historical audit, authoring recipe or instructor Key is an
input to the pure examination. The Engine adapter reads existing collected
artifacts and checks their ordinary source collection journal.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .company_collection import binding
from .company_store import _time
from .fresh_sec003_procedure import CLOCK_ID, NATIVE_ID, require
from .inference import _json
from .source_library_audit import private_file
from .store import digest

BUSINESS_ID = tuple(k for k in CLOCK_ID if k != "imported_at")
COMPONENTS = {
    "identity-history": "identity",
    "lifecycle-history": "lifecycle",
    "nonhuman-history": "nonhuman",
    "iam005-human": "human",
    "iam005-service": "service",
    "iam005emergency": "emergency",
    "person-access-history": "workforce",
    "common-duty": "context",
    "common-support": "context",
    "phi": "context",
    "bcm": "context",
    "sec005operated": "context",
    "baseline-lifecycle": "baseline_worker",
    "emergencyreplay": "context",
    "physicalsite": "physical",
    "training-history": "training",
    "critical_role": "critical",
    "ppl002": "screening",
    "eth001conduct": "conduct",
    "supplementalops": "supplemental",
}
CHANNELS = {
    "directory_account",
    "application_account",
    "application_session",
    "api_token",
    "remote_session",
    "physical_badge",
}
TEXT_ROLES = {
    ("iam005-human", "local_object"),
    ("iam005-service", "local_object"),
    ("person-access-history", "workspace_object"),
}
CONTRACT_PATH = Path(__file__).with_name("source_identity_method_contracts_v1.json")
CONTRACT_SHA256 = "7a4cd7792bfc0700381bd76241a029e9bf72c178cf136dcce09a67ac7887a46b"


def authored_contracts():
    raw = CONTRACT_PATH.read_bytes()
    require(
        hashlib.sha256(raw).hexdigest() == CONTRACT_SHA256, "Authored task contract pin differs"
    )
    contracts = _json(raw)
    require(
        contracts["schema"] == "SH_COLLECTED_IDENTITY_METHOD_CONTRACTS_V1"
        and len(contracts["selected_task_ids"]) == 30
        and len(set(contracts["selected_task_ids"])) == 30
        and set(contracts["selected_task_ids"]) == set(contracts["tasks"]),
        "Exact reviewed selected task contract required",
    )
    return contracts


def custody(row):
    return {k: row["source"][k] for k in CLOCK_ID}


def identity(source):
    return tuple(source[k] for k in NATIVE_ID)


def tokens(value, label):
    require(
        isinstance(value, list)
        and all(isinstance(x, str) and x for x in value)
        and len(value) == len(set(value)),
        "Distinct explicit " + label + " required",
    )
    return set(value)


def count(value, label):
    require(type(value) is int and value >= 0, "Strict nonnegative " + label + " required")
    return value


def flag(value, label):
    require(type(value) is bool, "Strict Boolean " + label + " required")
    return value


def references(value, path="$"):
    if isinstance(value, dict):
        if set(NATIVE_ID) <= value.keys():
            yield path, value
        else:
            for name, child in value.items():
                yield from references(child, path + "." + name)
    elif isinstance(value, list):
        for number, child in enumerate(value):
            yield from references(child, f"{path}[{number}]")


class History:
    def __init__(self, records, as_of):
        self.as_of, self.rows, self.index, self.joins = _time(as_of), [], {}, []
        for record in records:
            source, receipt = record["source"], record["receipt"]
            require(set(CLOCK_ID) <= source.keys(), "Exact native identity and clocks required")
            require(
                type(source["version"]) is int
                and source["version"] > 0
                and all(isinstance(source[k], str) and source[k] for k in NATIVE_ID[:-1]),
                "Strict native identity/version required",
            )
            require(
                source["event_at"] is not None
                and _time(source["event_at"]) <= _time(source["available_at"]) <= self.as_of
                and _time(source["imported_at"]) <= _time(datetime.now(UTC).isoformat()),
                "Selected source chronology exceeds examination boundary",
            )
            raw = record.get("retained_bytes", record.get("content"))
            require(isinstance(raw, bytes), "Actual retained original bytes required")
            require(
                all(receipt["source"].get(k) == source[k] for k in CLOCK_ID)
                and type(receipt["source"].get("version")) is int
                and type(receipt.get("content_bytes")) is int
                and receipt["content_bytes"] == len(raw)
                and all(
                    isinstance(receipt.get(k), str) and receipt[k]
                    for k in ("engagement_id", "principal_id", "command_id")
                )
                and _time(source["available_at"]) <= _time(receipt["simulated_as_of"]) <= self.as_of
                and _time(source["imported_at"])
                <= _time(receipt["collected_at"])
                <= _time(datetime.now(UTC).isoformat()),
                "Ordinary collected receipt identity/count/clocks differ",
            )
            require(
                hashlib.sha256(raw).hexdigest() == source["sha256"] == record["artifact_sha256"],
                "Retained original hash differs",
            )
            family, role = source["system"].split(".", 1)
            require(
                family in COMPONENTS
                and record.get("logical_family") == family
                and record.get("logical_system") == role,
                "Selected role differs from actual native system",
            )
            media = record.get(
                "content_type", receipt["source"].get("provenance", {}).get("content_type")
            )
            if (family, role) in TEXT_ROLES:
                require(
                    media in {"text/plain", "text/plain; charset=utf-8"},
                    "Typed local object bytes required",
                )
                raw.decode("utf-8")
                document = None
            else:
                require(media == "application/json", "Typed selected business JSON required")
                document = _json(raw)
                require(
                    isinstance(document, dict), "Structured selected business document required"
                )
            key = identity(source)
            require(key not in self.index, "Duplicate collected native version")
            row = {
                **{k: v for k, v in record.items() if k != "document"},
                "retained_bytes": raw,
                "document": document,
                "component": COMPONENTS[family],
                "content_bytes": len(raw),
            }
            self.rows.append(row)
            self.index[key] = row
        require(self.rows, "Collected selected identity originals required")
        require(
            len({(r["source"]["company"], r["source"]["branch"]) for r in self.rows}) == 1
            and len(
                {(r["receipt"]["engagement_id"], r["receipt"]["principal_id"]) for r in self.rows}
            )
            == 1,
            "One actually collected company branch, engagement and principal required",
        )
        for row in self.rows:
            for path, ref in references(row["document"]):
                target, state = self.resolve(row, ref)
                self.joins.append(
                    {
                        "from": custody(row),
                        "path": path,
                        "reference": ref,
                        "state": state,
                        "to": custody(target) if target else None,
                    }
                )

    def selected(self, component, role=None):
        return [
            r
            for r in self.rows
            if r["component"] == component and (role is None or r["logical_system"] == role)
        ]

    def exact(self, component, role, record, version=1):
        rows = [
            r
            for r in self.selected(component, role)
            if r["source"]["record"] == record and r["source"]["version"] == version
        ]
        if not rows:
            raise MissingOriginal(f"{component}/{role}/{record}/v{version}")
        require(len(rows) == 1, "Ambiguous selected native role")
        return rows[0]

    def resolve(self, row, ref):
        if ref.get("status") == "RESTRICTED_UNREGISTERED_DEPENDENCY":
            require(
                set(NATIVE_ID) <= ref.keys()
                and type(ref["version"]) is int
                and ref["version"] > 0
                and ref.get("event_at") is None
                and isinstance(ref.get("custody_id"), str)
                and ref["custody_id"]
                and "sha256" not in ref,
                "Exact restricted dependency witness required",
            )
            _time(ref["available_at"])
            return None, "RESTRICTED_UNREGISTERED_DEPENDENCY_NOT_NATIVE_AUTHORITY"
        require(
            isinstance(ref, dict)
            and set(BUSINESS_ID) <= ref.keys()
            and type(ref["version"]) is int
            and ref["version"] > 0,
            "Strict native business pointer required",
        )
        if (ref["company"], ref["branch"]) != (row["source"]["company"], row["source"]["branch"]):
            return None, "OUTSIDE_COLLECTED_BRANCH_AUTHORITY"
        target = self.index.get(identity(ref))
        if target is None:
            return None, "ORIGINAL_NOT_COLLECTED"
        fields = CLOCK_ID if "imported_at" in ref else BUSINESS_ID
        require(
            all(ref[k] == target["source"][k] for k in fields),
            "Native pointer hash or clocks differ",
        )
        if _time(target["source"]["available_at"]) > _time(row["source"]["event_at"]):
            return target, "SOURCE_UNAVAILABLE_AT_RECORDED_OCCURRENCE"
        return target, "EXACT_AVAILABLE_NATIVE_JOIN"


class MissingOriginal(ValueError):
    """An absent original is an explicit procedure limit, not event nonoccurrence."""


def workforce_context(history):
    rows = history.selected("workforce", "affiliation_register")
    if not rows:
        raise MissingOriginal("collected affiliation register")
    observed = {}
    for row in rows:
        d = row["document"]
        require(
            isinstance(d.get("person_id"), str) and d["person_id"],
            "Recorded person identity required",
        )
        require(d["person_id"] not in observed, "Affiliation version needs explicit disposition")
        flag(d["included_in_service_boundary"], "service eligibility")
        require(isinstance(d["source_titles"], list), "Recorded title/status pairs required")
        observed[d["person_id"]] = {
            "relationship": d["relationship_kind"],
            "source_status": d["source_status"],
            "service_eligible": d["included_in_service_boundary"],
            "titles": d["source_titles"],
            "source": custody(row),
        }
    kinds = Counter(x["relationship"] for x in observed.values())
    canonical = sorted(
        k
        for k, d in observed.items()
        if d["relationship"]
        in {
            "EMPLOYEE",
            "NONEMPLOYEE_DIRECTOR",
            "FORMER_EMPLOYEE",
        }
    )
    return {
        "people": observed,
        "canonical_people": canonical,
        "recorded_relationship_counts": dict(kinds),
        "proposed_office_contacts": sorted(
            k for k, d in observed.items() if d["source_status"] == "PROPOSED_OFFICE_OCCUPANT"
        ),
        "source_boundary": "SELECTED_SERVICE_AFFILIATION_REGISTER_NOT_ENTERPRISE_EMPLOYMENT_CENSUS",
        "appointments_or_planning_positions_inferred": False,
    }


def mover_attributes(history):
    rows = history.selected("identity")
    applied = [r for r in rows if r["logical_system"] == "hr" and r["source"]["version"] == 3]
    if not applied:
        raise MissingOriginal("applied mover HR originals")
    result = []
    for row in applied:
        d, cause = row["document"], row["document"]["cause_id"]
        auth = d["transfer_authorization"]
        prior = history.exact("identity", "hr", cause + "-hr", 2)
        pending = prior["document"]["pending_transfer"]
        approval_prior = (
            pending["approval_id"] == auth["approval_id"]
            and _time(auth["approved_at"]) < _time(auth["effective_at"])
            and _time(prior["source"]["available_at"]) <= _time(auth["effective_at"])
        )
        attributes = []
        for role, field, addition, removal in (
            ("directory", "groups", "add_right", "remove_right"),
            ("application", "rights", "add_right", "remove_right"),
            ("site_access", "sites", "add_site", "remove_site"),
        ):
            before = history.exact("identity", role, cause + "-" + role, 1)
            after = history.exact("identity", role, cause + "-" + role, 2)
            expected = (tokens(before["document"][field], "prior " + field) - {auth[removal]}) | {
                auth[addition]
            }
            observed = tokens(after["document"][field], "effective " + field)
            attributes.append(
                {
                    "role": role,
                    "expected": sorted(expected),
                    "observed": sorted(observed),
                    "excess": sorted(observed - expected),
                    "missing": sorted(expected - observed),
                    "subject_and_authorization_match": after["document"]["person_id"]
                    == d["person_id"]
                    and after["document"]["authorization_id"] == auth["approval_id"],
                    "provisioned_after_effective": _time(auth["effective_at"])
                    <= _time(after["source"]["event_at"]),
                    "before": custody(before),
                    "after": custody(after),
                }
            )
        review = history.exact("identity", "access_review", cause + "-access_review")
        excess = next(a["excess"] for a in attributes if a["role"] == "application")
        review_matches = excess == sorted(
            tokens(review["document"]["unapproved_remaining_rights"], "reviewed excess rights")
        )
        result.append(
            {
                "id": cause,
                "person_id": d["person_id"],
                "recorded_local_role": d["role"],
                "corporate_job_title_changed_by_this_examination": False,
                "approval": auth,
                "prior_approval_supported": approval_prior,
                "attributes": attributes,
                "review": custody(review),
                "review_reconciliation_matches": review_matches,
                "reviewer_distinct": review["document"]["reviewed_by"] != auth["approved_by"],
                "review_followup": review["document"]["followup_status"],
                "exception": not approval_prior
                or not review_matches
                or any(
                    a["excess"]
                    or a["missing"]
                    or not a["subject_and_authorization_match"]
                    or not a["provisioned_after_effective"]
                    for a in attributes
                ),
            }
        )
    return result


def quarterly_reviews(history):
    result = []
    for q, cutoff in enumerate(("2027-04-01", "2027-07-01", "2027-10-01", "2028-01-01"), 1):
        cutoff = _time(cutoff + "T00:00:00Z")
        record = f"PRIV-2027-Q{q}"
        if history.as_of < cutoff:
            result.append({"id": record, "cutoff": cutoff, "state": "NOT_YET_DUE_RIGHT_CENSORED"})
            continue
        try:
            population = history.exact("identity", "review_population", record)
            decisions = history.exact("identity", "review_decisions", record)
            reconciliation = history.exact("identity", "review_reconciliation", record)
        except MissingOriginal as error:
            result.append(
                {
                    "id": record,
                    "cutoff": cutoff,
                    "state": "SUPPORT_UNAVAILABLE",
                    "missing_original": str(error),
                }
            )
            continue
        latest = {}
        for row in history.selected("identity", "application"):
            if _time(row["source"]["available_at"]) >= cutoff:
                continue
            person = row["document"]["person_id"]
            if (
                person not in latest
                or row["source"]["version"] > latest[person]["source"]["version"]
            ):
                latest[person] = row
        p, decisions_doc, r = (
            population["document"],
            decisions["document"],
            reconciliation["document"],
        )
        declared = tokens(p["declared_employee_ids"], "declared quarterly subjects")
        supplied = [m["person_id"] for m in p["members"]]
        require(len(supplied) == len(set(supplied)), "Duplicate supplied quarterly subject")
        require(set(latest) <= declared, "Actual accounts exceed the declared local review cohort")
        member_matches = []
        for member in p["members"]:
            require(
                type(member["version"]) is int and member["version"] > 0,
                "Strict positive quarterly member version required",
            )
            tokens(member["rights"], "quarterly member rights")
            account = latest.get(member["person_id"])
            member_matches.append(
                {
                    "person_id": member["person_id"],
                    "actual_account_join": account is not None
                    and all(
                        member[k] == account["source"][k] for k in ("record", "version", "sha256")
                    )
                    and member["rights"] == account["document"]["rights"],
                }
            )
        hashes_match = (
            digest(p["members"]) == p["membership_sha256"]
            and decisions_doc["population_sha256"]
            == population["source"]["sha256"]
            == r["population_sha256"]
        )
        missing = sorted(set(latest) - set(supplied))
        seen = [d["person_id"] for d in decisions_doc["decisions"]]
        require(len(seen) == len(set(seen)), "Duplicate actual review decision subject")
        excess, decision_tests = [], []
        for decision in decisions_doc["decisions"]:
            account = latest.get(decision["person_id"])
            if account is None:
                decision_tests.append(
                    {"person_id": decision["person_id"], "actual_account_available": False}
                )
                continue
            auth = history.exact("identity", "hr", account["document"]["cause_id"] + "-hr", 3)[
                "document"
            ]["transfer_authorization"]
            observed = tokens(account["document"]["rights"], "actual account rights")
            expected = {auth["add_right"]}
            extra = sorted(observed - expected)
            if extra:
                excess.append({"person_id": decision["person_id"], "rights": extra})
            decision_tests.append(
                {
                    "person_id": decision["person_id"],
                    "actual_account_available": True,
                    "observed_rights_match": decision["observed_rights"]
                    == account["document"]["rights"],
                    "authorized_rights_match": tokens(
                        decision["authorized_rights"], "review authorization"
                    )
                    == expected,
                    "removal_decision_matches": sorted(
                        tokens(decision["remove_rights"], "review removal")
                    )
                    == extra,
                    "removal_confirmation": decision["removal_confirmation"],
                    "removal_implementation_proved_by_this_record": False,
                }
            )
        contradiction = (
            not hashes_match
            or any(not x["actual_account_join"] for x in member_matches)
            or tokens(r["missing_person_ids"], "declared missing subjects") != set(missing)
            or set(seen) != set(supplied)
            or any(
                not x.get("actual_account_available")
                or not x.get("observed_rights_match")
                or not x.get("authorized_rights_match")
                or not x.get("removal_decision_matches")
                for x in decision_tests
            )
        )
        result.append(
            {
                "id": record,
                "cutoff": cutoff,
                "state": "OBSERVED_WITH_EXCEPTION"
                if missing or excess or contradiction
                else "OBSERVED_SELECTED_COHORT",
                "expected_people": sorted(latest),
                "supplied_people": sorted(supplied),
                "missing_people": missing,
                "excess": excess,
                "member_tests": member_matches,
                "decision_tests": decision_tests,
                "contradiction": contradiction,
                "population": custody(population),
                "decisions": custody(decisions),
                "reconciliation": custody(reconciliation),
                "retrospective_review_is_contemporaneous_execution": False,
            }
        )
    return result


def worker_lifecycle(history):
    def get(role, record):
        return history.exact("lifecycle", role, record)

    request_row, create_row = get("worker_requests", "REQUEST"), get("identity_events", "CREATE")
    approval_row, provision_row = (
        get("access_approvals", "APPROVAL"),
        get("identity_events", "PROVISION"),
    )
    catalogue = get("access_approvals", "LOCAL-CATALOG")["document"]
    checkpoint_row, final_row = (
        get("access_reconciliation", "CHECKPOINT"),
        get("access_reconciliation", "FINAL-PROBES"),
    )
    revoke_row = get("revocation_events", "EXPIRY-REVOCATION")
    request, create, approval, provision = (
        r["document"] for r in (request_row, create_row, approval_row, provision_row)
    )
    checkpoint, final, revocation = (r["document"] for r in (checkpoint_row, final_row, revoke_row))
    requested = flag(request["approved"], "worker request approval")
    approved = flag(approval["approved"], "access approval")
    grant = tokens(provision["entitlement_diff"]["after"], "provisioned rights")
    allowed = tokens(approval["rights"], "approved rights")
    require(
        set(checkpoint["probes"]) == set(final["probes"]) == set(revocation["after"]) == CHANNELS,
        "All six actual selected channel states required",
    )
    require(
        all(
            x in {"ALLOW", "DENY"}
            for x in [*checkpoint["probes"].values(), *final["probes"].values()]
        ),
        "Explicit channel probe decisions required",
    )
    for value in revocation["after"].values():
        flag(value, "revocation channel state")
    active = sorted(k for k, value in checkpoint["probes"].items() if value == "ALLOW")
    final_active = sorted(k for k, value in final["probes"].items() if value == "ALLOW")
    preissue = _time(request["recorded_at"]) < _time(create["recorded_at"]) and _time(
        approval["recorded_at"]
    ) < _time(provision["recorded_at"])
    conflicts = [
        pair
        for pair in catalogue["conflicting_rights"]
        if tokens(pair, "conflicting rights") <= grant
    ]
    return {
        "id": request["subject_id"],
        "sponsor": request["sponsor_person_id"],
        "proofing": request["proofing_check"],
        "actual_identity_documents_validated": False,
        "request_creation_join": create["request_id"] == request["request_id"]
        and create["created_identity"] == request["subject_id"],
        "prior_approval": requested and approved and preissue,
        "reviewer_distinct": approval["reviewer_id"] != approval["provisioner_id"],
        "approved": sorted(allowed),
        "granted": sorted(grant),
        "excess_grants": sorted(grant - allowed),
        "conflicts": conflicts,
        "expiry": request["expires_at"],
        "checkpoint_active_channels": active,
        "final_active_channels": final_active,
        "actual_probe_and_revocation_state_match": active
        == sorted(k for k, value in revocation["after"].items() if value),
        "correction_delay_seconds": (
            datetime.fromisoformat(_time(final["recorded_at"]))
            - datetime.fromisoformat(_time(request["expires_at"]))
        ).total_seconds(),
        "checkpoint": custody(checkpoint_row),
        "final": custody(final_row),
        "historical_expiry_failure_closed_by_later_correction": False,
    }


def nonhuman_identity(history):
    inventory = history.exact("nonhuman", "identity_inventory", "IDENTITY")
    attempts = []
    for row in history.selected("nonhuman", "copy_attempts"):
        d = row["document"]
        if "status" in d:
            require(
                d["status"] in {"COPIED", "AUTHORIZATION_DENIED"}, "Recorded copy outcome required"
            )
            require(
                type(d["configured_version"]) is int
                and d["configured_version"] > 0
                and type(d["current_credential_version"]) is int
                and d["current_credential_version"] > 0,
                "Strict inert credential epochs required",
            )
            n = count(d["copied_bytes"], "copy byte count")
            match = d["configured_version"] == d["current_credential_version"]
            output_matches = n == 0 and d["output_ref"] is None
            if d["status"] == "COPIED":
                target, state = history.resolve(row, d["output_ref"])
                output_matches = (
                    target is not None
                    and target["logical_family"] == "nonhuman-history"
                    and target["logical_system"] == "copied_dataset"
                )
                output_matches = (
                    output_matches
                    and target["source"]["sha256"] == d["output_sha256"] == d["input_sha256"]
                    and target["content_bytes"] == n
                )
            else:
                state = "NO_RECORDED_OUTPUT"
            attempts.append(
                {
                    "id": row["source"]["record"],
                    "source": custody(row),
                    "status": d["status"],
                    "configured_version": d["configured_version"],
                    "active_version": d["current_credential_version"],
                    "credential_outcome_matches": (d["status"] == "COPIED") == match,
                    "copied_bytes": n,
                    "output_original_matches": bool(output_matches),
                    "output_join_state": state,
                    "live_credential_or_production_copy_reperformed": False,
                }
            )
        else:
            attempts.append(
                {
                    "id": row["source"]["record"],
                    "source": custody(row),
                    "operation": d["operation"],
                    "authorization": d["authorization"],
                    "forbidden_operation_denied_without_output": d["authorization"] == "DENY"
                    and d["output_ref"] is None,
                }
            )
    if not attempts:
        raise MissingOriginal("selected service copy/denial histories")
    return {
        "inventory": inventory["document"],
        "inventory_source": custody(inventory),
        "attempts": attempts,
    }


def local_object_access(history):
    human = history.exact("human", "local_object", "LOCAL-IAM005-TRACE-OBJECT")
    service = history.exact("service", "local_object", "LOCAL-IAM005-TRACE-OBJECT")
    require(
        human["retained_bytes"] == service["retained_bytes"],
        "Separate human/service objects differ",
    )
    reads, reviews = [], []
    for component, role in (("human", "human_access"), ("service", "service_access")):
        for row in history.selected(component, role):
            d = row["document"]
            if "read_bytes" not in d:
                continue
            n = count(d["read_bytes"], "local read bytes")
            require(
                d["result"] in {"AUTHORIZED", "DENIED"}, "Recorded local access result required"
            )
            match = n == 0 and d["read_sha256"] is None
            if d["result"] == "AUTHORIZED":
                match = (
                    n == human["content_bytes"] and d["read_sha256"] == human["source"]["sha256"]
                )
            reads.append(
                {
                    "component": component,
                    "id": row["source"]["record"],
                    "source": custody(row),
                    "result": d["result"],
                    "bytes": n,
                    "exact_object_or_empty_denial_matches": match,
                }
            )
        review = history.exact(component, component + "_review", "REVIEW-01")
        d = review["document"]
        claimed = flag(d["review_timely"], "local review timeliness")
        timely = _time(review["source"]["event_at"]) <= _time(d["review_due_at"])
        reviews.append(
            {
                "component": component,
                "source": custody(review),
                "timely": timely,
                "recorded_timeliness_matches": timely == claimed,
                "reviewer_distinct": d["reviewer_id"] != d["operator_id"],
                "open_exception": d["open_timing_exception_id"],
                "live_corporate_boundary_or_credential_test": False,
            }
        )
    if not reads:
        raise MissingOriginal("local same-object read/denial histories")
    return {
        "object_sources": [custody(human), custody(service)],
        "reads": reads,
        "reviews": reviews,
    }


def emergency_access(history):
    approval = history.exact("emergency", "emergency_authority", "APPROVE-EMERGENCY-EXERCISE-01")
    review = history.exact("emergency", "access_review", "REVIEW-ACCESS-01")
    approver, reviewer = (
        r["document"]["actor_person_or_inert_identity_id"] for r in (approval, review)
    )
    decisions = [
        {"id": r["source"]["record"], "source": custody(r), "decision": r["document"]["decision"]}
        for r in history.selected("emergency")
        if r["logical_system"] in {"access_decision", "service_activity"}
    ]
    return {
        "approved_by": approver,
        "reviewed_by": reviewer,
        "self_review": approver == reviewer,
        "approval": custody(approval),
        "review": custody(review),
        "decisions": decisions,
        "open_exceptions": [
            custody(r)
            for r in history.selected("emergency", "exception_register")
            if r["document"]["decision"] == "OPEN"
        ],
        "marker_establishes_actual_ephi_or_restored_permission_state": False,
        "later_review_closes_prior_exception_automatically": False,
    }


GROUP_METHODS = {
    "workforce": workforce_context,
    "movers": mover_attributes,
    "quarters": quarterly_reviews,
    "worker": worker_lifecycle,
    "nonhuman": nonhuman_identity,
    "local": local_object_access,
    "emergency": emergency_access,
}
CONTROL_GROUPS = {
    1: ("workforce", "worker", "nonhuman"),
    2: ("worker", "movers", "local"),
    3: ("movers",),
    4: ("worker",),
    5: ("local", "emergency"),
    6: ("nonhuman", "local"),
    7: ("quarters", "movers"),
}
GROUP_COMPONENTS = {
    "workforce": {"workforce"},
    "movers": {"identity"},
    "quarters": {"identity"},
    "worker": {"lifecycle"},
    "nonhuman": {"nonhuman"},
    "local": {"human", "service"},
    "emergency": {"emergency", "context"},
}
PERFORMED = {
    1: (
        "Reconcile collected affiliation identities and recorded service eligibility "
        "separately from proposed offices; trace the selected worker request, identity "
        "correlation and pre-issue approval; inspect the separately owned inert service "
        "inventory."
    ),
    2: (
        "Compare selected prior approval, actual provisioned rights and local conflict "
        "catalogue; trace the mover's effective directory/application/site rights; "
        "compare actual retained same-object read and denial byte counts."
    ),
    3: (
        "For every collected applied mover, join prior HR authorization and effective "
        "dates to before/after directory, application and site-access originals; "
        "recalculate obsolete/excess/missing rights and compare the recorded access "
        "review."
    ),
    4: (
        "Trace the selected fixed-term worker's expiry, actual six-channel revocation "
        "state and checkpoint probes; preserve surviving application sessions and "
        "compare later final probes without retroactive closure."
    ),
    5: (
        "Inspect the two separately collected local object originals, recorded "
        "authorized reads and empty denials, review due time and distinct actors; trace "
        "selected approved emergency-marker decisions, self-review and open exception "
        "records."
    ),
    6: (
        "Reconcile the selected inert nonhuman identity/owner record, recorded consumer "
        "and current credential epochs, successful copy output original byte/hash "
        "counts, denied outputs and forbidden operations; inspect the local service "
        "review separately."
    ),
    7: (
        "For each closed selected quarter, derive latest actual application accounts "
        "before its exclusive cutoff; join supplied members to exact native versions, "
        "recalculate membership and triple hashes, omissions/excess rights, removal "
        "decisions and separately retained mover failure."
    ),
}
UNPERFORMED = {
    1: (
        "Enterprise hiring authority, actual proofing documents, complete "
        "workforce/contractor/service employment denominator, and initial creation "
        "requests for the two historical mover subjects remain unproved."
    ),
    2: (
        "Full corporate job-duty entitlements, each corporate trust boundary and "
        "conflict matrix, deployment/key protection and actual system-wide permission "
        "enforcement remain unperformed."
    ),
    3: (
        "Whole-enterprise mover denominator, every connected corporate system, approved "
        "enterprise delegations and remediation closure beyond the actual selected "
        "histories remain unproved; local application duties do not change canonical "
        "job titles."
    ),
    4: (
        "Whole-enterprise leaver/transfer/expiry denominator, P008's initial revocation "
        "and every real system/session/token/badge integration remain unproved; later "
        "correction does not establish timely historical expiry."
    ),
    5: (
        "Full corporate privileged population, vault/approval architecture, actual ePHI "
        "application usability and restored permissions/sessions across recovery remain "
        "unperformed; marker and local-object history is bounded."
    ),
    6: (
        "Whole-enterprise workload/service identities and usable secret/deployment "
        "inventory, actual production copy or credential protection, and enterprise "
        "ownership-change census remain unproved."
    ),
    7: (
        "Full privileged enterprise population and every system/cadence, actual "
        "corporate independent review authority and completed remediation validation "
        "remain unproved; source reconciliation and later corrections are not "
        "retrospective assurance."
    ),
}


def examine(records, *, as_of):
    history = History(records, as_of)
    groups = {}
    for name, method in GROUP_METHODS.items():
        try:
            groups[name] = {"state": "EXAMINED_SELECTED_ORIGINALS", "result": method(history)}
        except MissingOriginal as error:
            groups[name] = {"state": "SUPPORT_UNAVAILABLE", "missing_original": str(error)}
    return {
        "as_of": history.as_of,
        "groups": groups,
        "native_joins": history.joins,
        "source_population": [custody(r) for r in history.rows],
        "enterprise_population_complete": False,
        "professional_acceptance": "NOT_ASSERTED",
    }


def implementation_exception(number, groups):
    def got(name):
        return groups[name].get("result")

    if number == 3 and got("movers") is not None:
        return any(m["exception"] for m in got("movers"))
    if number == 4 and got("worker") is not None:
        return (
            bool(got("worker")["checkpoint_active_channels"])
            or not got("worker")["actual_probe_and_revocation_state_match"]
        )
    if number == 6 and got("nonhuman") is not None:
        return any(
            a.get("status") == "AUTHORIZATION_DENIED"
            or a.get("credential_outcome_matches") is False
            or a.get("output_original_matches") is False
            or a.get("forbidden_operation_denied_without_output") is False
            for a in got("nonhuman")["attempts"]
        )
    if number == 7 and got("quarters") is not None:
        return any(q["state"] == "OBSERVED_WITH_EXCEPTION" for q in got("quarters"))
    return False


def retained_inputs(engine, auditor, engagement, artifact_ids):
    """Read real workroom originals; no caller-supplied body, actor or future cutoff."""
    state = engine.store.get(auditor, engagement)
    bound = binding(engine, state)
    require(
        state.get("company_source_binding") == bound
        and state.get("evidence_acquisition") == "COMPANY_SOURCE_COLLECTION",
        "Activated bound company-source workroom required",
    )
    with engine.store.connect() as db:
        principal = db.execute("SELECT roles FROM principals WHERE id=?", (auditor,)).fetchone()
        member = db.execute(
            "SELECT permission FROM members WHERE principal=? AND engagement=?",
            (auditor, engagement),
        ).fetchone()
        require(
            principal is not None
            and json.loads(principal[0]) == ["learner"]
            and member is not None
            and member[0] == "learn",
            "Actual independent audit performer required",
        )
    require(
        isinstance(artifact_ids, list)
        and artifact_ids
        and all(isinstance(a, str) and a for a in artifact_ids)
        and len(artifact_ids) == len(set(artifact_ids)),
        "Distinct selected collected artifact IDs required",
    )
    available = {a["id"]: a for a in state["artifacts"]}
    rows = []
    for aid in artifact_ids:
        require(aid in available, "Collected artifact belongs to another workroom")
        artifact = available[aid]
        require(
            artifact["status"] == "AVAILABLE"
            and artifact["source"].get("kind") == "COLLECTED_COMPANY_SOURCE",
            "Available ordinary collected company original required",
        )
        receipt = artifact["source"]["receipt"]
        source = receipt["source"]
        require(
            receipt["engagement_id"] == engagement
            and receipt["principal_id"] == auditor
            and all(source[k] == bound[k] for k in bound),
            "Actual receipt workroom/performer/branch differs",
        )
        private_file(engine.artifacts.root / artifact["sha256"])
        raw = engine.artifacts.read(artifact)
        with engine.company_store._db() as db:
            saved = db.execute(
                "SELECT receipt FROM collections WHERE command_id=?", (receipt["command_id"],)
            ).fetchone()
            require(
                saved is not None and json.loads(saved[0]) == receipt,
                "Actual ordinary company collection journal differs",
            )
        family, role = source["system"].split(".", 1)
        rows.append(
            {
                "source": source,
                "receipt": receipt,
                "artifact_id": aid,
                "artifact_sha256": artifact["sha256"],
                "retained_bytes": raw,
                "content_type": source["provenance"].get("content_type"),
                "logical_family": family,
                "logical_system": role,
            }
        )
    require(
        engine.store.get(auditor, engagement)["revision"] == state["revision"],
        "Engagement changed during original read",
    )
    History(rows, state["simulated_at"])
    return rows


def task_contracts():
    """Fixed strings and permitted bounded dispositions for independent review."""
    outputs = {}
    for task_id, task in authored_contracts()["tasks"].items():
        number = int(task["control_id"][-3:])
        kind = task["kind"]
        suffixes = {
            "TOD": (
                "Selected documentary design attributes are compared to the exact "
                "authored procedure."
            ),
            "IMPLEMENTATION": (
                "Selected dated implementation steps and their failures are examined separately."
            ),
            "TOE": (
                "Closed due windows and failed/corrected selected occurrences are retained "
                "separately."
            ),
            "ADDITIONAL_DUTY": "The additional source clause is examined separately: "
            + task["authored_instruction"],
        }
        kind_limits = {
            "TOD": (
                "The actual effective enterprise policy/procedure and full design acceptance "
                "remain unproved."
            ),
            "IMPLEMENTATION": (
                "Uncollected steps, external enforcement and full authored procedure acceptance "
                "remain unproved."
            ),
            "TOE": (
                "Complete period denominators, independent full-period selection and timely "
                "performance across every due occurrence remain unproved."
            ),
            "ADDITIONAL_DUTY": (
                "Full satisfaction of this additional requirement is not asserted; mapped control "
                "existence provides no requirement credit."
            ),
        }
        performed = PERFORMED[number] + " " + suffixes[kind]
        unperformed = (
            UNPERFORMED[number]
            + " "
            + kind_limits[kind]
            + " Missing originals and unfinished due windows are itemized in the result "
            "and do not establish event nonoccurrence."
        )
        allowed = [{"status": "IN_PROGRESS", "conclusion": "LIMITATION"}]
        if kind == "TOD" or kind == "IMPLEMENTATION" and number != 5:
            allowed.append({"status": "COMPLETE", "conclusion": "LIMITATION"})
        if kind == "IMPLEMENTATION" and number in {3, 4, 6, 7}:
            allowed.append({"status": "COMPLETE", "conclusion": "FAIL"})
        outputs[task_id] = {
            "performed": performed,
            "unperformed": unperformed,
            "allowed_dispositions": allowed,
        }
    return outputs


def inspections(records, *, as_of, scratch_root=None):
    """Reviewed batch callback: one explicit inspection per exact selected task."""
    del scratch_root  # Documentary examinations do not execute stored scripts.
    history = History(records, as_of)
    result = examine(records, as_of=as_of)
    contracts = authored_contracts()
    reviewed = task_contracts()
    outputs = []
    for task_id in contracts["selected_task_ids"]:
        task = contracts["tasks"][task_id]
        number = int(task["control_id"][-3:])
        chosen = CONTROL_GROUPS[number]
        if task_id.endswith("CC6.2"):
            chosen = tuple(dict.fromkeys((*chosen, "workforce")))
        groups = {name: result["groups"][name] for name in chosen}
        components = set().union(*(GROUP_COMPONENTS[g] for g in chosen))
        selected = [r for r in history.rows if r["component"] in components]
        missing = [name for name in chosen if groups[name]["state"] == "SUPPORT_UNAVAILABLE"]
        if "quarters" in groups and groups["quarters"].get("result") is not None:
            if any(
                q["state"] in {"SUPPORT_UNAVAILABLE", "NOT_YET_DUE_RIGHT_CENSORED"}
                for q in groups["quarters"]["result"]
            ):
                missing.append("closed quarterly windows")
        status, conclusion = "IN_PROGRESS", "LIMITATION"
        if not missing and task["kind"] == "TOD":
            status = "COMPLETE"
        elif not missing and task["kind"] == "IMPLEMENTATION" and number != 5:
            status = "COMPLETE"
            if implementation_exception(number, result["groups"]):
                conclusion = "FAIL"
        observations = []
        for row in selected:
            facts = {
                "native": custody(row),
                "actual_role": row["logical_system"],
                "component": row["component"],
                "task_id": task_id,
            }
            exception = False
            if row["component"] == "identity":
                movers = result["groups"]["movers"].get("result", [])
                match = next(
                    (m for m in movers if row["source"]["record"].startswith(m["id"])), None
                )
                quarter = next(
                    (
                        q
                        for q in result["groups"]["quarters"].get("result", [])
                        if q["id"] == row["source"]["record"]
                    ),
                    None,
                )
                if match:
                    attrs = [a for a in match["attributes"] if a["role"] == row["logical_system"]]
                    facts["mover_recalculation"] = attrs or {
                        k: match[k]
                        for k in (
                            "prior_approval_supported",
                            "reviewer_distinct",
                            "review_followup",
                        )
                    }
                    exception = row["source"]["version"] == 2 and any(
                        a["excess"] or a["missing"] for a in attrs
                    )
                if quarter:
                    facts["quarter_recalculation"] = quarter
                    exception = quarter["state"] == "OBSERVED_WITH_EXCEPTION"
            elif row["component"] == "lifecycle":
                facts["worker_recalculation"] = result["groups"]["worker"]
                exception = row["source"]["record"] in {"CHECKPOINT", "EXPIRY-REVOCATION"} and bool(
                    result["groups"]["worker"].get("result", {}).get("checkpoint_active_channels")
                )
            elif row["component"] == "nonhuman":
                match = next(
                    (
                        a
                        for a in result["groups"]["nonhuman"].get("result", {}).get("attempts", [])
                        if a["id"] == row["source"]["record"]
                    ),
                    None,
                )
                facts["service_recalculation"] = match or {
                    "recorded_role_document": row["document"]
                }
                exception = bool(match and match.get("status") == "AUTHORIZATION_DENIED")
            elif row["component"] in {"human", "service"}:
                local = result["groups"]["local"].get("result", {})
                match = next(
                    (
                        a
                        for a in local.get("reads", [])
                        if a["component"] == row["component"] and a["id"] == row["source"]["record"]
                    ),
                    None,
                )
                review = next(
                    (a for a in local.get("reviews", []) if a["component"] == row["component"]),
                    None,
                )
                facts["local_attribute_test"] = (
                    match or review or {"original_role": row["logical_system"]}
                )
                exception = (
                    row["source"]["record"] == "REVIEW-01"
                    and review is not None
                    and not review["timely"]
                )
            elif row["component"] == "emergency":
                facts["recorded_decision"] = row["document"].get("decision")
                facts["recorded_actor"] = row["document"].get("actor_person_or_inert_identity_id")
                exception = (
                    row["logical_system"] == "exception_register"
                    or row["logical_system"] == "access_review"
                    and result["groups"]["emergency"].get("result", {}).get("self_review", False)
                )
            elif row["component"] == "workforce":
                facts["recorded_affiliation_context"] = row["document"]
            observations.append(
                {
                    "id": "/".join(str(row["source"][k]) for k in NATIVE_ID),
                    "facts": facts,
                    "status": "EXCEPTION_RECORDED" if exception else "OBSERVED",
                    "evidence": [
                        {
                            "artifact_id": row["artifact_id"],
                            "sha256": row["artifact_sha256"],
                            "locator": "$; named source attributes and recalculations"
                            if row["document"] is not None
                            else "Native whole object bytes",
                        }
                    ],
                }
            )
        performed = reviewed[task_id]["performed"]
        unperformed = reviewed[task_id]["unperformed"]
        outputs.append(
            {
                "task_id": task_id,
                "artifact_ids": [r["artifact_id"] for r in selected],
                "observations": observations,
                "performed": performed,
                "unperformed": unperformed,
                "result": {
                    "selected_groups": groups,
                    "authored_task": task,
                    "missing_selected_inputs": missing,
                    "native_join_limits": [
                        j
                        for j in result["native_joins"]
                        if j["state"] != "EXACT_AVAILABLE_NATIVE_JOIN"
                    ],
                    "selected_scope_only": True,
                    "old_audit_outcomes_used": False,
                },
                "disposition": {
                    "status": status,
                    "conclusion": conclusion,
                    "rationale": "Selected original examination; "
                    + (
                        "observed implementation failure is preserved. "
                        if conclusion == "FAIL"
                        else "broader authored clauses remain limited. "
                    )
                    + unperformed,
                },
            }
        )
    return outputs
