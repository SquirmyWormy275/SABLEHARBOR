"""Bounded person-level 2027 company affiliation and logical-access operations.

Planning positions are never workers. Source authoring is separate from any
engagement; real import times and fictional business event times stay distinct.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, _json, _time
from .fresh_identity_family_procedure import immutable_schema
from .fresh_sec003_procedure import read_only, require, sha, write
from .organization import snapshot
from .store import digest

SCHEMA = "SH_COMPANY_WORKFORCE_IDENTITY_2027_V1"
COMPANY = "SABLE-HARBOR-REFERENCE"
BRANCHES = {"A": "PERSON-ACCESS-2027-A", "B": "PERSON-ACCESS-2027-B"}
LEGACY = (
    "enterprise/generated/audit-suite/company-identity-period-2026-09-14/"
    "full-year-v1/company/company.sqlite3"
)
LEGACY_SHA = "8183a47f82d0e76c0a785d12a0b0d8113f65d666c0ad5284c9a6e2dc92290357"
CHANNELS = (
    "directory",
    "application",
    "local_account",
    "remote_access",
    "api_token",
    "application_session",
)
DELEGATES = {
    "AS-P003": "local legal record custodian",
    "AS-P006": "local affiliation record custodian",
    "AS-P007": "local identity provisioner",
    "AS-P008": "local access approver",
    "AS-P009": "local management quality reviewer",
    "AS-P013": "local contractor record custodian",
}
CONTRACTORS = (
    {
        "id": "SH-CW-001",
        "name": "Morgan Aster",
        "purpose": "identity connector maintenance",
        "start": "2027-02-01T09:00:00Z",
        "end": "2027-06-30T12:00:00Z",
        "sponsor": "P004",
    },
    {
        "id": "SH-CW-002",
        "name": "Casey Linden",
        "purpose": "recovery inventory reconciliation",
        "start": "2027-08-01T09:00:00Z",
        "end": "2027-11-30T12:00:00Z",
        "sponsor": "P007",
    },
)
SERVICES = ("SH-SVC-HR-SYNC", "SH-SVC-BACKUP", "SH-SVC-MONITOR")
CONFLICTS = (("billing-admin", "inventory-admin"), ("iam.approve", "iam.provision"))
REFERENCE_KEYS = (
    "company",
    "branch",
    "system",
    "record",
    "version",
    "sha256",
    "event_at",
    "available_at",
    "imported_at",
)


def instant(value):
    return datetime.fromisoformat(_time(value))


def after(value, seconds):
    return (instant(value) + timedelta(seconds=seconds)).isoformat()


def original_witness(row):
    """Bind exact original custody without exposing legacy mode labels."""
    return {
        "custody_status": "RESTRICTED_ARCHIVE_WITNESS_ONLY",
        "company": row["company"],
        "system": row["system"],
        "record": row["record"],
        "version": row["version"],
        "native_identity_sha256": digest(
            [row[k] for k in ("company", "branch", "system", "record", "version")]
        ),
        "event_at": row["event_at"],
        "available_at": row["available_at"],
        "content_sha256": row["sha256"],
    }


def canonical_basis(repository):
    value = snapshot(repository, as_of="2027-12-31")
    people = value["canonical_people"]
    require(
        len(people) == len({p["person_id"] for p in people}) == 52,
        "Canonical person membership differs",
    )
    require(
        Counter(p["status"] for p in people)
        == {
            "current_employee": 44,
            "current_nonemployee_director": 7,
            "former_employee": 1,
        },
        "Canon employment/director distinctions differ",
    )
    proposed = value["proposed_people"]
    require(
        len(proposed) == 15 and all(p["status"] == "PROPOSED_OFFICE_OCCUPANT" for p in proposed),
        "Proposed contact status differs",
    )
    # Narrow projection only: financial account maps and audit assignments are not sources.
    result = {
        "people": [
            {
                "person_id": p["person_id"],
                "name": p["name"],
                "status": p["status"],
                "titles": p["titles"],
                "joining_records": p["joining_records"],
                "sources": p["sources"],
            }
            for p in people
        ],
        "proposed": [
            {k: p[k] for k in ("person_id", "name", "title", "status", "org_role_id")}
            for p in proposed
        ],
        "source_sha256": value["source_sha256"],
        "planning_counts": {
            g: {k: r[k] for k in ("authorized", "occupied")}
            for g, r in json.loads(
                (Path(repository) / "enterprise/business/source/policy.json").read_text()
            )["workforce"].items()
        },
    }
    require(
        sum(r["authorized"] for r in result["planning_counts"].values()) == 591
        and sum(r["occupied"] for r in result["planning_counts"].values()) == 506,
        "Original planning counts differ",
    )
    return result


def legacy_basis(private_repository):
    path = Path(private_repository) / LEGACY
    require(sha(path) == LEGACY_SHA, "Original mover source pin differs")
    require(
        not any(Path(str(path) + s).exists() for s in ("-wal", "-shm", "-journal")),
        "Original mover source has sidecar",
    )
    with read_only(path) as db:
        rows = [
            dict(r)
            for r in db.execute("SELECT * FROM versions ORDER BY branch,system,record,version")
        ]
    require(len(rows) == 64, "Original mover history membership differs")
    for row in rows:
        require(
            hashlib.sha256(row["content"]).hexdigest() == row["sha256"],
            "Original mover content differs",
        )
        row["document"] = json.loads(row.pop("content"))
    return rows


class LocalRuntime:
    """Actual deterministic local ACL/lease state; contains no usable credentials."""

    def __init__(self):
        self.accounts = {}

    def install(
        self, account_id, subject, channel, rights, *, starts, ends, epoch=1, review_anchor=None
    ):
        require(channel in CHANNELS or channel == "legacy_application", "Unknown logical channel")
        self.accounts[account_id] = {
            "account_id": account_id,
            "subject_id": subject,
            "channel": channel,
            "rights": sorted(set(rights)),
            "active": True,
            "starts": _time(starts),
            "ends": _time(ends),
            "credential_epoch": epoch,
            "review_anchor": review_anchor,
        }
        return dict(self.accounts[account_id])

    def revoke(self, account_id):
        self.accounts[account_id]["active"] = False
        return dict(self.accounts[account_id])

    def permits(self, account_id, right, at, *, epoch=1):
        account = self.accounts.get(account_id)
        return bool(
            account
            and account["active"]
            and account["credential_epoch"] == epoch
            and instant(account["starts"]) <= instant(at) < instant(account["ends"])
            and right in account["rights"]
        )

    def read(self, account_id, right, at, original, *, epoch=1):
        allowed = self.permits(account_id, right, at, epoch=epoch)
        data = Path(original).read_bytes() if allowed else b""
        return {
            "account_id": account_id,
            "right": right,
            "decision_at": _time(at),
            "credential_epoch": epoch,
            "decision": "ALLOW" if allowed else "DENY",
            "returned_bytes": len(data),
            "returned_sha256": hashlib.sha256(data).hexdigest() if allowed else None,
        }

    def active(self, at):
        return [
            dict(a)
            for a in sorted(self.accounts.values(), key=lambda a: a["account_id"])
            if a["active"] and instant(a["starts"]) <= instant(at) < instant(a["ends"])
        ]


class Writer:
    def __init__(self, store, branch, *, initialized_at):
        self.store, self.branch, self.initialized_at = store, branch, initialized_at
        self.versions, self.records = {}, []

    def append(self, system, record, at, body, *, available=None, owner="AS-P007"):
        self.store.register_system(COMPANY, self.branch, system, owner)
        key = (system, record)
        version = self.versions.get(key, 0)
        payload = {"schema": "SH_COMPANY_PERSON_ACCESS_RECORD_V1", **body}
        ref = self.store.append_version(
            COMPANY,
            self.branch,
            system,
            record,
            expected_version=version,
            command_id="PERS-" + digest([self.branch, system, record, version + 1])[:60],
            event_at=at,
            available_at=available or at,
            content=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
            provenance={
                "source_reference": f"company://{COMPANY}/{self.branch}/{system}/{record}",
                "name": "person-access-" + digest(key)[:24] + ".json",
                "content_type": "application/json",
                "initialized_at": self.initialized_at,
                "qualification": "FICTIONAL_COMPANY_OPERATIONS_NO_REAL_EMPLOYMENT_OR_PHI",
            },
            origin="AUTHORED_TRAINING_SOURCE",
        )
        ref = {k: ref[k] for k in REFERENCE_KEYS}
        self.versions[key] = version + 1
        self.records.append({"native": ref, "body": payload})
        return ref

    def append_object(self, path):
        self.store.register_system(COMPANY, self.branch, "workspace_object", "AS-P007")
        return self.store.append_version(
            COMPANY,
            self.branch,
            "workspace_object",
            "CORPORATE-REFERENCE",
            expected_version=0,
            command_id="OBJ-" + self.branch,
            event_at="2027-01-01T02:55:00Z",
            available_at="2027-01-01T02:55:00Z",
            content=path.read_bytes(),
            provenance={
                "source_reference": f"company://{COMPANY}/{self.branch}/workspace_object/CORPORATE-REFERENCE",
                "name": "corporate-reference.txt",
                "content_type": "text/plain; charset=utf-8",
                "initialized_at": self.initialized_at,
                "qualification": "FICTIONAL_COMPANY_OPERATIONS_NO_REAL_EMPLOYMENT_OR_PHI",
            },
            origin="AUTHORED_TRAINING_SOURCE",
        )


def opening(w, basis):
    """Dated service authority does not appoint employees or populate forecasts."""
    authority = w.append(
        "company_authority",
        "SERVICE-ORDER-2027",
        "2027-01-01T00:15:00Z",
        {
            "issued_by": "P001",
            "management_acceptance": ["P001", "P002"],
            "purpose": "Maintain the named corporate shared-service identity boundary",
            "effective_from": "2027-01-01T00:30:00Z",
            "effective_to": "2028-01-01T00:00:00Z",
            "closing_record_authority_until": "2028-01-16T00:00:00Z",
            "closing_authority_scope": (
                "Retrospective reconciliation, review and expired-state "
                "maintenance; no operating access extension"
            ),
            "employment_appointments_made": False,
            "forecast_positions_are_operating_workers": False,
            "financial_or_physical_occupancy_change": False,
            "operating_access_ready_from": "2027-01-01T03:15:00Z",
            "earlier_operating_history": "NOT_ESTABLISHED_BY_THIS_REGISTER",
            "scope": (
                "Named registered company/affiliate people, separately accepted "
                "service delegates, "
                "explicit contractor relationships and owned nonhuman accounts only"
            ),
            "unmodeled_scope": (
                "Unnamed workers, other enterprise accounts, industrial operating"
                " systems, "
                "physical badges and unaccepted proposed office occupants"
            ),
            "original_planning_counts": basis["planning_counts"],
            "planning_count_basis": "Unchanged conditional forecast; not a worker/account census",
            "delegations": DELEGATES,
            "reserved_authority": (
                "No operating safety, corporate employment hire, external opinion or legal status"
            ),
        },
        owner="P001",
    )
    delegated = {}
    proposed = {p["person_id"]: p for p in basis["proposed"]}
    for person, capacity in DELEGATES.items():
        delegated[person] = w.append(
            "service_delegation",
            person,
            "2027-01-01T01:00:00Z",
            {
                "person_id": person,
                "name": proposed[person]["name"],
                "capacity": capacity,
                "issuer": "P001",
                "accepted_by": person,
                "authority": authority,
                "accepted_at": "2027-01-01T01:00:00Z",
                "effective_from": "2027-01-01T01:00:00Z",
                "effective_to": "2028-01-16T00:00:00Z",
                "operating_service_window_ends": "2028-01-01T00:00:00Z",
                "post_window_scope": "Closing records only; no operating permissions extended",
                "office_status": "PROPOSED_NOT_APPOINTED",
                "employment_status": "NOT_ESTABLISHED",
                "appointment_is_employment": False,
                "identity_basis": "Named source contact reconciled in the local reference registry",
            },
            owner="P001",
        )
    affiliations, subjects = {}, {}
    for p in basis["people"] + basis["proposed"]:
        pid, status = p["person_id"], p["status"]
        included = (
            status in {"current_employee", "current_nonemployee_director"} or pid in DELEGATES
        )
        kind = (
            "EMPLOYEE"
            if status == "current_employee"
            else "NONEMPLOYEE_DIRECTOR"
            if status == "current_nonemployee_director"
            else "SERVICE_DELEGATE"
            if pid in DELEGATES
            else "FORMER_EMPLOYEE"
            if status == "former_employee"
            else "PROPOSED_CONTACT"
        )
        reason = (
            "Accepted current employee source; shared-service assignment only"
            if kind == "EMPLOYEE"
            else "Current board affiliation; board portal only; no payroll/operating privilege"
            if kind == "NONEMPLOYEE_DIRECTOR"
            else "Separate dated local service delegation; office and employment remain unaccepted"
            if kind == "SERVICE_DELEGATE"
            else "Departed in 2024; historical revocation date is not established by this register"
            if kind == "FORMER_EMPLOYEE"
            else "Proposed contact without accepted service assignment or employment basis"
        )
        titles = [{"title": t["title"], "status": t["status"]} for t in p.get("titles", [])]
        if "title" in p:
            titles = [{"title": p["title"], "status": "PROPOSED_NOT_APPOINTED"}]
        affiliations[pid] = w.append(
            "affiliation_register",
            pid,
            "2027-01-01T02:00:00Z",
            {
                "person_id": pid,
                "name": p["name"],
                "source_status": status,
                "relationship_kind": kind,
                "source_titles": titles,
                "employment_start": None,
                "employment_start_basis": "Not supplied by display/appointment years",
                "joining_records": p.get("joining_records", []),
                "source_refs": p.get("sources", []),
                "employer_legal_entity": None,
                "payroll_basis": "Outside this service-eligibility register",
                "included_in_service_boundary": included,
                "inclusion_or_exclusion_reason": reason,
                "service_effective_from": "2027-01-01T03:00:00Z" if included else None,
                "service_effective_to": "2028-01-01T00:00:00Z" if included else None,
                "authority": delegated.get(pid, authority),
                "physical_workplace_assignment": None,
            },
            owner="AS-P006",
        )
        if included:
            subjects[pid] = {
                "kind": kind,
                "name": p["name"],
                "starts": "2027-01-01T03:00:00Z",
                "ends": "2028-01-01T00:00:00Z",
                "affiliation": affiliations[pid],
            }
    require(
        sum(p["kind"] == "EMPLOYEE" for p in subjects.values()) == 44,
        "Service delegation changed canonical employee count",
    )
    catalog = w.append(
        "entitlement_catalogue",
        "CORPORATE-LOGICAL",
        "2027-01-01T02:30:00Z",
        {
            "approved_by": "AS-P008",
            "reviewed_by": "AS-P009",
            "authority": authority,
            "duties": {
                "EMPLOYEE": ["workspace.read"],
                "NONEMPLOYEE_DIRECTOR": ["board.read"],
                "SERVICE_DELEGATE": ["workspace.read"],
                "CONTRACTOR": ["workspace.read"],
                "NONHUMAN_SERVICE": ["workspace.read"],
            },
            "individual_duties": {
                "AS-P007": ["iam.provision"],
                "AS-P008": ["iam.approve"],
                "AS-P009": ["review.perform"],
                "AS-P006": ["affiliation.record"],
                "AS-P013": ["contract.record"],
                "AS-P003": ["legal.record"],
            },
            "conflicting_rights": [list(pair) for pair in CONFLICTS],
            "local_mover_duties": {
                code: "Retained local application entitlement; original detailed business "
                "permission catalogue unavailable"
                for code in ("billing-admin", "inventory-admin")
            },
            "mover_duty_is_job_title_change": False,
            "channels": list(CHANNELS),
            "physical_channel_scope": "Not established here",
        },
        owner="AS-P008",
    )
    w.append(
        "account_system_inventory",
        "LOGICAL-SERVICE-BOUNDARY",
        "2027-01-01T02:45:00Z",
        {
            "systems": [
                {
                    "system": c,
                    "owner": "AS-P007",
                    "registration": "AUTHORITATIVE_FOR_DECLARED_LOCAL_SERVICE",
                    "independent_approver": "AS-P008",
                }
                for c in CHANNELS
            ]
            + [
                {
                    "system": "legacy_application",
                    "owner": "AS-P007",
                    "registration": "TWO_RETAINED_MOVER_APPLICATION_HISTORIES_ONLY",
                }
            ],
            "authority": authority,
            "catalogue": catalog,
            "other_estate_inventory": "UNESTABLISHED_NOT_INFERRED_FROM_EMPTY_EXPORT",
        },
        owner="AS-P007",
    )
    return authority, delegated, catalog, subjects, affiliations


def install_subject(
    w, runtime, subject, info, catalog, original, *, request_at, approval_at, issue_at
):
    rights = ["board.read"] if info["kind"] == "NONEMPLOYEE_DIRECTOR" else ["workspace.read"]
    rights += {
        "AS-P007": ["iam.provision"],
        "AS-P008": ["iam.approve"],
        "AS-P009": ["review.perform"],
        "AS-P006": ["affiliation.record"],
        "AS-P013": ["contract.record"],
        "AS-P003": ["legal.record"],
    }.get(subject, [])
    requester = "P002" if subject in DELEGATES else "AS-P006"
    approver = "P001" if subject in DELEGATES else "AS-P008"
    request = w.append(
        "access_requests",
        subject,
        request_at,
        {
            "subject_id": subject,
            "requested_by": requester,
            "affiliation": info["affiliation"],
            "catalogue": catalog,
            "requested_rights": sorted(rights),
            "channels": list(CHANNELS),
            "effective_from": issue_at,
            "effective_to": info["ends"],
        },
        owner="AS-P006",
    )
    approval = w.append(
        "access_approvals",
        subject,
        approval_at,
        {
            "subject_id": subject,
            "approved_by": approver,
            "provisioner": "AS-P007",
            "approved_at": approval_at,
            "request": request,
            "catalogue": catalog,
            "approved_rights": sorted(rights),
            "decision": "APPROVED",
            "effective_from": issue_at,
            "effective_to": info["ends"],
        },
        owner="AS-P008",
    )
    for channel in CHANNELS:
        account = runtime.install(
            subject + ":" + channel,
            subject,
            channel,
            rights,
            starts=issue_at,
            ends=info["ends"],
            review_anchor=subject,
        )
        ref = w.append(
            "account_" + channel,
            account["account_id"],
            issue_at,
            {
                "state": account,
                "approval": approval,
                "performed_by": "AS-P007",
            },
        )
        probe_at = after(issue_at, 60)
        w.append(
            "permission_activity",
            account["account_id"] + ":ISSUE",
            probe_at,
            {
                **runtime.read(account["account_id"], rights[0], probe_at, original),
                "account_state": ref,
                "object_sha256": sha(original),
                "object_bytes": original.stat().st_size,
                "performed_by": "AS-P007",
            },
        )
    return approval


def state_at(records, at):
    """Reconstruct closed-window account state rather than using final state."""
    latest = {}
    for r in records:
        if (
            not r["native"]["system"].startswith("account_")
            or "state" not in r["body"]
            or instant(r["native"]["available_at"]) >= instant(at)
        ):
            continue
        aid = r["body"]["state"]["account_id"]
        if aid not in latest or r["native"]["version"] > latest[aid]["native"]["version"]:
            latest[aid] = r
    return latest


def retain_movers(w, runtime, legacy, catalog, authority, original, side):
    source_branch = "year-clean" if side == "A" else "year-messy"
    selected = [r for r in legacy if r["branch"] == source_branch]
    for cause in ("MOVE-2027-Q1-001", "MOVE-2027-Q2-001"):
        hr = next(
            r
            for r in selected
            if r["system"] == "hr" and r["record"] == cause + "-hr" and r["version"] == 3
        )
        pid = hr["document"]["person_id"]
        auth = hr["document"]["transfer_authorization"]
        w.append(
            "duty_authorizations",
            cause,
            auth["approved_at"],
            {
                "subject_id": pid,
                "service_duties": [auth["add_right"]],
                "remove_duties": [auth["remove_right"]],
                "approved_by": auth["approved_by"],
                "requested_by": auth["requested_by"],
                "effective_at": auth["effective_at"],
                "catalogue": catalog,
                "company_authority": authority,
                "approval_id": auth["approval_id"],
                "canonical_job_title_changed": False,
                "source_content_sha256": hr["sha256"],
                "original_source_witness": original_witness(hr),
                "source_scope": "Retained local service duty history; not a personnel appointment",
                "approval_document_at_fact_time": "NOT_ESTABLISHED_BY_RESTRICTED_ORIGINAL",
            },
            available=hr["available_at"],
            owner="AS-P008",
        )
        for source in sorted(
            [r for r in selected if r["record"] == cause + "-application"],
            key=lambda r: r["version"],
        ):
            d = source["document"]
            at = source["event_at"]
            state = runtime.install(
                cause + ":application",
                pid,
                "legacy_application",
                d["rights"],
                starts=at,
                ends="2028-01-01T00:00:00Z",
                review_anchor=None if side == "B" and pid == "P014" else pid,
            )
            ref = w.append(
                "account_legacy_application",
                cause + ":application",
                at,
                {
                    "state": state,
                    "performed_by": d.get("performed_by", "AS-P007"),
                    "source_content_sha256": source["sha256"],
                    "original_source_witness": original_witness(source),
                    "source_event_at": source["event_at"],
                    "source_available_at": source["available_at"],
                    "duty_approval_id": d.get("authorization_id"),
                    "authorization_basis": (
                        "Retained local history; initial issue request unavailable in "
                        "original source"
                    )
                    if source["version"] == 1
                    else "Retained prior dated duty approval",
                    "review_mapping": "AWAITING_OWNER_MATCH"
                    if state["review_anchor"] is None
                    else "MATCHED_PERSON",
                    "employment_title_change": False,
                },
                available=source["available_at"],
            )
            probe_at = after(source["available_at"], 30)
            for right in ("billing-admin", "inventory-admin"):
                w.append(
                    "permission_activity",
                    cause + f":v{source['version']}:" + right,
                    probe_at,
                    {
                        **runtime.read(state["account_id"], right, probe_at, original),
                        "account_state": ref,
                        "object_sha256": sha(original),
                        "object_bytes": original.stat().st_size,
                        "performed_by": "AS-P007",
                    },
                )
        original_review = next(r for r in selected if r["record"] == cause + "-access_review")
        d = original_review["document"]
        w.append(
            "duty_followup",
            cause,
            original_review["event_at"],
            {
                "subject_id": pid,
                "reviewed_by": d["reviewed_by"],
                "observed_rights": d["observed_application_rights"],
                "authorized_rights": d["authorized_rights"],
                "remaining_rights": d["unapproved_remaining_rights"],
                "followup_status": d["followup_status"],
                "followup_owner": d.get("followup_owner"),
                "source_content_sha256": original_review["sha256"],
                "original_source_witness": original_witness(original_review),
                "removal_is_confirmed": not d["unapproved_remaining_rights"],
            },
            available=original_review["available_at"],
            owner="AS-P008",
        )


def contractors(w, runtime, subjects, authority, catalog, original, side):
    for c in CONTRACTORS:
        pid = c["id"]
        signed_at = after(c["start"], -7 * 86400)
        contract = w.append(
            "contractor_relationship",
            pid,
            signed_at,
            {
                "person_id": pid,
                "name": c["name"],
                "counterparty_accepted_by": pid,
                "company_accepted_by": "AS-P003",
                "sponsor": c["sponsor"],
                "purpose": c["purpose"],
                "starts": c["start"],
                "ends": c["end"],
                "company_authority": authority,
                "identity_basis": "Synthetic counterparty and local identity verification record",
                "employment_status": "NONEMPLOYEE_CONTRACTOR",
                "renewal": "REQUIRES_NEW_APPROVAL",
            },
            owner="AS-P013",
        )
        info = {
            "kind": "CONTRACTOR",
            "name": c["name"],
            "starts": c["start"],
            "ends": c["end"],
            "affiliation": contract,
        }
        subjects[pid] = info
        install_subject(
            w,
            runtime,
            pid,
            info,
            catalog,
            original,
            request_at=after(c["start"], -3600),
            approval_at=after(c["start"], -1800),
            issue_at=c["start"],
        )
        event = w.append(
            "relationship_events",
            pid + ":EXPIRY",
            c["end"],
            {
                "subject_id": pid,
                "kind": "CONTRACT_EXPIRED",
                "relationship": contract,
                "recorded_by": "AS-P013",
                "effective_at": c["end"],
                "renewal_authority": None,
                "removal_channels": list(CHANNELS),
                "notified_to": "AS-P007",
            },
            owner="AS-P013",
        )
        for channel in CHANNELS:
            aid = pid + ":" + channel
            if side == "B" and pid == "SH-CW-001" and channel == "application_session":
                runtime.accounts[aid]["ends"] = _time(after(c["end"], 3600))
                state = dict(runtime.accounts[aid])
                ack_at = after(c["end"], 3600)
            else:
                state = runtime.revoke(aid)
                ack_at = c["end"]
            ref = w.append(
                "account_" + channel,
                aid,
                c["end"],
                {
                    "state": state,
                    "relationship_event": event,
                    "performed_by": "AS-P007",
                    "invalidation_ack_due": after(c["end"], 300),
                    "invalidation_ack_at": ack_at if ack_at == c["end"] else None,
                    "connector_status": "INVALIDATION_ACKNOWLEDGED"
                    if ack_at == c["end"]
                    else "SESSION_CACHE_INVALIDATION_PENDING",
                },
            )
            probe_at = after(c["end"], 60)
            w.append(
                "permission_activity",
                aid + ":EXPIRY",
                probe_at,
                {
                    **runtime.read(aid, "workspace.read", probe_at, original),
                    "account_state": ref,
                    "object_sha256": sha(original),
                    "object_bytes": original.stat().st_size,
                    "performed_by": "AS-P007",
                },
            )
            if ack_at != c["end"]:
                corrected = runtime.revoke(aid)
                final_ref = w.append(
                    "account_" + channel,
                    aid,
                    ack_at,
                    {
                        "state": corrected,
                        "relationship_event": event,
                        "performed_by": "AS-P007",
                        "previous_account": ref,
                        "invalidation_ack_at": ack_at,
                    },
                )
                w.append(
                    "permission_activity",
                    aid + ":ACK",
                    after(ack_at, 60),
                    {
                        **runtime.read(aid, "workspace.read", after(ack_at, 60), original),
                        "account_state": final_ref,
                        "object_sha256": sha(original),
                        "object_bytes": original.stat().st_size,
                        "performed_by": "AS-P007",
                    },
                )


def nonhuman_services(w, runtime, subjects, authority, catalog, original, side):
    for pid in SERVICES:
        owned = w.append(
            "nonhuman_inventory",
            pid,
            "2027-01-01T03:05:00Z",
            {
                "identity_id": pid,
                "kind": "NONHUMAN_SERVICE",
                "owner": "AS-P007",
                "approved_by": "AS-P008",
                "purpose": {
                    "SH-SVC-HR-SYNC": "named affiliation sync",
                    "SH-SVC-BACKUP": "local reference object copy",
                    "SH-SVC-MONITOR": "local permission telemetry",
                }[pid],
                "company_authority": authority,
                "catalogue": catalog,
                "interactive_signin": "DISABLED",
                "logical_channels": ["api_token"],
                "credential_material": "INERT_VERSION_MARKER_ONLY",
                "scope": ["workspace.read"],
                "starts": "2027-01-01T03:15:00Z",
                "ends": "2028-01-01T00:00:00Z",
            },
            owner="AS-P007",
        )
        subjects[pid] = {
            "kind": "NONHUMAN_SERVICE",
            "name": pid,
            "starts": "2027-01-01T03:15:00Z",
            "ends": "2028-01-01T00:00:00Z",
            "affiliation": owned,
        }
        aid = pid + ":api_token"
        state = runtime.install(
            aid,
            pid,
            "api_token",
            ["workspace.read"],
            starts="2027-01-01T03:15:00Z",
            ends="2028-01-01T00:00:00Z",
            review_anchor=pid,
        )
        ref = w.append(
            "account_api_token",
            aid,
            "2027-01-01T03:15:00Z",
            {
                "state": state,
                "owner_authority": owned,
                "performed_by": "AS-P007",
            },
        )
        w.append(
            "permission_activity",
            aid + ":BASELINE",
            "2027-01-01T03:16:00Z",
            {
                **runtime.read(aid, "workspace.read", "2027-01-01T03:16:00Z", original),
                "account_state": ref,
                "object_sha256": sha(original),
                "object_bytes": original.stat().st_size,
                "performed_by": "AS-P007",
            },
        )
        runtime.accounts[aid]["credential_epoch"] = 2
        rotated = w.append(
            "account_api_token",
            aid,
            "2027-05-01T09:00:00Z",
            {
                "state": dict(runtime.accounts[aid]),
                "owner_authority": owned,
                "rotation_approved_by": "AS-P008",
                "performed_by": "AS-P007",
                "previous_account": ref,
                "retired_credential_epoch": 1,
            },
        )
        configured_epoch = 1 if side == "B" and pid == "SH-SVC-BACKUP" else 2
        for suffix, epoch in (("CONSUMER", configured_epoch), ("RETIRED", 1)):
            at = "2027-05-01T09:05:00Z"
            w.append(
                "permission_activity",
                aid + ":" + suffix,
                at,
                {
                    **runtime.read(aid, "workspace.read", at, original, epoch=epoch),
                    "account_state": rotated,
                    "object_sha256": sha(original),
                    "object_bytes": original.stat().st_size,
                    "performed_by": "AS-P007",
                    "consumer_configured_epoch": epoch,
                },
            )
        if configured_epoch == 1:
            w.append(
                "service_consumer_change",
                pid,
                "2027-05-02T09:00:00Z",
                {
                    "owner": "AS-P007",
                    "approved_by": "AS-P008",
                    "configured_epoch_before": 1,
                    "configured_epoch_after": 2,
                    "account_state": rotated,
                    "reason": "Consumer authentication did not follow credential rotation",
                },
            )
            w.append(
                "permission_activity",
                aid + ":CORRECTION",
                "2027-05-02T09:05:00Z",
                {
                    **runtime.read(
                        aid, "workspace.read", "2027-05-02T09:05:00Z", original, epoch=2
                    ),
                    "account_state": rotated,
                    "object_sha256": sha(original),
                    "object_bytes": original.stat().st_size,
                    "performed_by": "AS-P007",
                    "consumer_configured_epoch": 2,
                },
            )


def population_view(records, subjects, cutoff):
    latest = state_at(records, cutoff)
    accounts = [
        r
        for r in latest.values()
        if r["body"]["state"]["active"]
        and instant(r["body"]["state"]["starts"]) < instant(cutoff)
        and instant(cutoff) <= instant(r["body"]["state"]["ends"])
    ]
    expected = sorted(
        pid
        for pid, p in subjects.items()
        if instant(p["starts"]) < instant(cutoff) <= instant(p["ends"])
    )
    observed = sorted({r["body"]["state"]["subject_id"] for r in accounts})
    unmapped = sorted(
        {
            r["body"]["state"]["subject_id"]
            for r in accounts
            if r["body"]["state"]["review_anchor"] is None
        }
    )
    members = []
    for pid in expected:
        own = [r for r in accounts if r["body"]["state"]["subject_id"] == pid]
        if pid in unmapped:
            continue
        members.append(
            {
                "subject_id": pid,
                "relationship_kind": subjects[pid]["kind"],
                "accounts": [
                    {"source": r["native"], "state": r["body"]["state"]}
                    for r in sorted(own, key=lambda r: r["body"]["state"]["account_id"])
                ],
            }
        )
    return {
        "expected_subject_ids": expected,
        "account_subject_ids": observed,
        "unmatched_review_subject_ids": unmapped,
        "members": members,
        "account_population": [
            {"source": r["native"], "state": r["body"]["state"]}
            for r in sorted(accounts, key=lambda r: r["body"]["state"]["account_id"])
        ],
    }


def period_operations(w, subjects, legacy, side):
    source_branch = "year-clean" if side == "A" else "year-messy"
    for month in range(1, 13):
        cutoff = (
            datetime(2028, 1, 1, tzinfo=UTC)
            if month == 12
            else datetime(2027, month + 1, 1, tzinfo=UTC)
        )
        at = cutoff.isoformat()
        view = population_view(w.records, subjects, at)
        census = w.append(
            "denominator_snapshot",
            f"2027-{month:02}",
            at,
            {
                "cutoff_exclusive": at,
                "registered_subject_ids": view["expected_subject_ids"],
                "accounts": view["account_population"],
                "prepared_by": "AS-P007",
                "unmodeled_worker_population": (
                    "UNESTABLISHED; not inferred from forecast or this export"
                ),
                "worker_and_account_counts_are_identical": False,
            },
        )
        w.append(
            "monthly_reconciliation",
            f"2027-{month:02}",
            after(at, 300),
            {
                "denominator": census,
                "expected_subject_ids": view["expected_subject_ids"],
                "account_subject_ids": view["account_subject_ids"],
                "account_population_sha256": digest(view["account_population"]),
                "missing_account_subject_ids": sorted(
                    set(view["expected_subject_ids"]) - set(view["account_subject_ids"])
                ),
                "unmatched_review_subject_ids": view["unmatched_review_subject_ids"],
                "reviewed_by": "AS-P009",
                "status": "MAPPING_WORK_OPEN"
                if view["unmatched_review_subject_ids"]
                else "REGISTERED_SCOPE_RECONCILED",
                "scope": "Declared registered people and service identities only",
            },
            owner="AS-P009",
        )
        if month % 3:
            continue
        q = month // 3
        oldpop = next(
            r
            for r in legacy
            if r["branch"] == source_branch
            and r["system"] == "review_population"
            and r["record"] == f"PRIV-2027-Q{q}"
        )
        oldrecon = next(
            r
            for r in legacy
            if r["branch"] == source_branch
            and r["system"] == "review_reconciliation"
            and r["record"] == f"PRIV-2027-Q{q}"
        )
        population = w.append(
            "periodic_review_population",
            f"2027-Q{q}",
            after(at, 3600),
            {
                "period_start": datetime(2027, month - 2, 1, tzinfo=UTC).isoformat(),
                "period_end_exclusive": at,
                "denominator": census,
                "members": view["members"],
                "membership_sha256": digest(view["members"]),
                "exported_by": "AS-P007",
                "query": (
                    "All active registered accounts with resolved person/service review anchors"
                ),
                "retained_local_privileged_population": oldpop["document"]["members"],
                "retained_source_content_sha256": oldpop["sha256"],
                "retained_population_witness": original_witness(oldpop),
                "retained_reconciliation_witness": original_witness(oldrecon),
                "retained_local_review_missing_ids": oldrecon["document"]["missing_person_ids"],
                "retained_local_scope": (
                    "Two original local mover causes only; membership follows actual "
                    "account event windows"
                ),
            },
        )
        decisions = []
        for member in view["members"]:
            actual = sorted({right for a in member["accounts"] for right in a["state"]["rights"]})
            excess = [
                right
                for right in actual
                if right == "billing-admin" and "inventory-admin" in actual
            ]
            decisions.append(
                {
                    "subject_id": member["subject_id"],
                    "observed_rights": actual,
                    "remove_rights": excess,
                    "decision": "REMOVAL_REQUESTED" if excess else "RETAIN_SCOPED_DUTIES",
                    "removal_confirmation": None if excess else "NO_REMOVAL_REQUEST",
                }
            )
        reviewed = w.append(
            "periodic_review_decisions",
            f"2027-Q{q}",
            after(at, 4200),
            {
                "population": population,
                "population_sha256": digest(view["members"]),
                "decisions": decisions,
                "reviewed_by": "AS-P009",
                "period_end_exclusive": at,
                "missing_subject_ids": view["unmatched_review_subject_ids"],
                "review_status": "RECONCILIATION_OPEN"
                if view["unmatched_review_subject_ids"]
                or any(d["remove_rights"] for d in decisions)
                else "REGISTERED_SCOPE_REVIEW_RECORDED",
                "wider_estate_reviewed": False,
            },
            owner="AS-P009",
        )
        w.append(
            "review_followup",
            f"2027-Q{q}",
            after(at, 4500),
            {
                "review": reviewed,
                "population_sha256": digest(view["members"]),
                "assigned_to": "AS-P007",
                "recorded_by": "AS-P009",
                "person_mapping_work": view["unmatched_review_subject_ids"],
                "removal_work": [d for d in decisions if d["remove_rights"]],
                "status": "OPEN"
                if view["unmatched_review_subject_ids"]
                or any(d["remove_rights"] for d in decisions)
                else "NO_ACTION_REQUIRED_FOR_REGISTERED_SCOPE",
                "historical_reviews_replaced": False,
            },
            owner="AS-P009",
        )


def close_assignments(w, runtime, original, side):
    cutoff = "2028-01-01T00:00:00Z"
    for aid, state in sorted(runtime.accounts.items()):
        if not state["active"]:
            continue
        closed = runtime.revoke(aid)
        system = "account_" + state["channel"]
        ref = w.append(
            system,
            aid,
            cutoff,
            {
                "state": closed,
                "performed_by": "LOCAL-LEASE-ENGINE",
                "trigger": "ANNUAL_SERVICE_ASSIGNMENT_WINDOW_ENDED",
                "employment_termination": False,
            },
        )
        right = state["rights"][0]
        w.append(
            "permission_activity",
            aid + ":ANNUAL-EXPIRY",
            after(cutoff, 60),
            {
                **runtime.read(aid, right, after(cutoff, 60), original),
                "account_state": ref,
                "object_sha256": sha(original),
                "object_bytes": original.stat().st_size,
                "performed_by": "LOCAL-LEASE-ENGINE",
            },
        )
    if side == "B":
        maintenance = w.append(
            "company_authority",
            "POST-PERIOD-MAINTENANCE",
            "2028-01-15T09:30:00Z",
            {
                "issued_by": "P001",
                "independent_acceptance": "P002",
                "delegated_to": "AS-P007",
                "approved_by": "AS-P008",
                "effective_from": "2028-01-15T10:00:00Z",
                "effective_to": "2028-01-15T18:00:00Z",
                "scope": "Expired local ACL cleanup and review-mapping correction only",
                "employment_appointments_made": False,
                "previous_reviews_reperformed": False,
            },
            owner="P001",
        )
        for cause, pid in (("MOVE-2027-Q1-001", "P014"), ("MOVE-2027-Q2-001", "P015")):
            aid = cause + ":application"
            runtime.accounts[aid]["rights"] = ["inventory-admin"]
            runtime.accounts[aid]["review_anchor"] = pid
            corrected = w.append(
                "account_legacy_application",
                aid,
                "2028-01-15T12:00:00Z",
                {
                    "state": dict(runtime.accounts[aid]),
                    "performed_by": "AS-P007",
                    "authority": maintenance,
                    "post_period_cleanup": True,
                    "old_population_or_review_replaced": False,
                    "prior_removal_delay_preserved": True,
                },
            )
            w.append(
                "late_correction",
                cause,
                "2028-01-15T12:05:00Z",
                {
                    "subject_id": pid,
                    "account_state": corrected,
                    "reviewed_by": "AS-P008",
                    "status": "EXPIRED_STORED_ACL_AND_MAPPING_CORRECTED",
                    "operating_permission_reactivated": False,
                    "quarter_reviews_replaced": False,
                    "current_employee_status_changed": False,
                },
                owner="AS-P008",
            )


def author_family(store, basis, legacy, original, initialized):
    for side, branch in BRANCHES.items():
        writer = Writer(store, branch, initialized_at=initialized)
        runtime = LocalRuntime()
        authority, delegates, catalog, subjects, affiliations = opening(writer, basis)
        writer.append_object(original)
        for pid, info in sorted(subjects.items()):
            install_subject(
                writer,
                runtime,
                pid,
                info,
                catalog,
                original,
                request_at="2027-01-01T03:05:00Z",
                approval_at="2027-01-01T03:10:00Z",
                issue_at="2027-01-01T03:15:00Z",
            )
        retain_movers(writer, runtime, legacy, catalog, authority, original, side)
        contractors(writer, runtime, subjects, authority, catalog, original, side)
        nonhuman_services(writer, runtime, subjects, authority, catalog, original, side)
        period_operations(writer, subjects, legacy, side)
        close_assignments(writer, runtime, original, side)


def native_records(path):
    with read_only(path) as db:
        rows = [
            dict(r)
            for r in db.execute("SELECT * FROM versions ORDER BY branch,system,record,version")
        ]
    for row in rows:
        require(
            hashlib.sha256(row["content"]).hexdigest() == row["sha256"],
            "Native content SHA differs",
        )
        if row["system"] == "workspace_object":
            row["body"] = None
        else:
            row["body"] = json.loads(row["content"])
    return rows


def refs(value):
    if isinstance(value, dict):
        if {"company", "branch", "system", "record", "version", "sha256"} <= value.keys():
            yield value
        for child in value.values():
            yield from refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from refs(child)


def semantic_verify(rows, basis, legacy, original):
    keys = ("company", "branch", "system", "record", "version")
    lookup = {tuple(r[k] for k in keys): r for r in rows}
    require(len(lookup) == len(rows), "Duplicate native source member")
    legacy_lookup = {(r["branch"], r["system"], r["record"], r["version"]): r for r in legacy}
    summaries = {}
    for side, branch in BRANCHES.items():
        selected = [r for r in rows if r["branch"] == branch]
        require(
            len(selected) == (1695 if side == "A" else 1704),
            "Bounded source version membership differs",
        )
        sequences = {}
        for row in selected:
            sequences.setdefault((row["system"], row["record"]), []).append(row)
            require(
                instant(row["event_at"]) <= instant(row["available_at"]),
                "Invalid source availability",
            )
            document = row["body"] or {}
            for field in (
                "original_source_witness",
                "retained_population_witness",
                "retained_reconciliation_witness",
            ):
                if field not in document:
                    continue
                witness = document[field]
                matches = [
                    r
                    for r in legacy
                    if r["branch"] == ("year-clean" if side == "A" else "year-messy")
                    and original_witness(r) == witness
                ]
                require(len(matches) == 1, "Exact restricted original custody witness differs")
                require(
                    instant(matches[0]["available_at"]) <= instant(row["available_at"]),
                    "Original source custody becomes available after retained publication",
                )
                scalar = (
                    "source_content_sha256"
                    if field == "original_source_witness"
                    else "retained_source_content_sha256"
                    if field == "retained_population_witness"
                    else None
                )
                if scalar:
                    require(
                        document[scalar] == witness["content_sha256"],
                        "Original scalar SHA does not match exact custody witness",
                    )
            if "source_content_sha256" in document:
                require(
                    "original_source_witness" in document,
                    "Original scalar SHA lacks exact restricted custody witness",
                )
            if "retained_source_content_sha256" in document:
                require(
                    "retained_population_witness" in document
                    and "retained_reconciliation_witness" in document,
                    "Retained history lacks exact original custody witnesses",
                )
            for ref in refs(row["body"]):
                target = lookup.get(tuple(ref[k] for k in keys))
                require(
                    target and target["sha256"] == ref["sha256"],
                    "Native source reference custody differs",
                )
                require(
                    set(ref) == set(REFERENCE_KEYS)
                    and all(target[k] == ref[k] for k in REFERENCE_KEYS)
                    and target["branch"] == branch
                    and instant(target["available_at"]) <= instant(row["event_at"]),
                    "Future/cross-branch reference",
                )
        for sequence in sequences.values():
            require(
                [r["version"] for r in sequence] == list(range(1, len(sequence) + 1)),
                "Native immutable version sequence differs",
            )
            require(
                all(
                    instant(a["event_at"]) <= instant(b["event_at"])
                    for a, b in zip(sequence, sequence[1:], strict=False)
                ),
                "Correction backdates earlier operating version",
            )
        affiliations = [r for r in selected if r["system"] == "affiliation_register"]
        require(
            len(affiliations) == 67
            and {r["record"] for r in affiliations}
            == {p["person_id"] for p in basis["people"] + basis["proposed"]},
            "Exact affiliation person membership differs",
        )
        require(
            Counter(r["body"]["source_status"] for r in affiliations)
            == {
                "current_employee": 44,
                "current_nonemployee_director": 7,
                "former_employee": 1,
                "PROPOSED_OFFICE_OCCUPANT": 15,
            },
            "Employment/status count conflation",
        )
        for r in affiliations:
            pid = r["record"]
            d = r["body"]
            p = next(p for p in basis["people"] + basis["proposed"] if p["person_id"] == pid)
            expected_titles = [
                {"title": t["title"], "status": t["status"]} for t in p.get("titles", [])
            ]
            if "title" in p:
                expected_titles = [{"title": p["title"], "status": "PROPOSED_NOT_APPOINTED"}]
            require(
                d["name"] == p["name"]
                and d["source_status"] == p["status"]
                and d["source_titles"] == expected_titles
                and d["joining_records"] == p.get("joining_records", [])
                and d["source_refs"] == p.get("sources", [])
                and d["employment_start"] is None
                and d["employer_legal_entity"] is None
                and d["physical_workplace_assignment"] is None,
                "Original person/title/unknown employment distinctions changed",
            )
            if pid.startswith("AS-"):
                require(
                    d["source_status"] == "PROPOSED_OFFICE_OCCUPANT"
                    and all(t["status"] == "PROPOSED_NOT_APPOINTED" for t in d["source_titles"]),
                    "Proposed contact silently appointed",
                )
            require(
                d["included_in_service_boundary"]
                == (
                    d["source_status"] in {"current_employee", "current_nonemployee_director"}
                    or pid in DELEGATES
                ),
                "Person inclusion/exclusion basis differs",
            )

        def exact(system, record, version=1, selected=selected):
            matches = [
                r
                for r in selected
                if r["system"] == system and r["record"] == record and r["version"] == version
            ]
            require(len(matches) == 1, "Exact required operating record missing")
            return matches[0]

        order = exact("company_authority", "SERVICE-ORDER-2027")["body"]
        require(
            order["original_planning_counts"] == basis["planning_counts"]
            and order["employment_appointments_made"] is False
            and order["forecast_positions_are_operating_workers"] is False
            and order["financial_or_physical_occupancy_change"] is False,
            "Service order conflates planning, employment or operating occupancy",
        )
        require(
            order["issued_by"] == "P001"
            and order["management_acceptance"] == ["P001", "P002"]
            and order["effective_from"] == "2027-01-01T00:30:00Z"
            and order["effective_to"] == "2028-01-01T00:00:00Z"
            and order["closing_record_authority_until"] == "2028-01-16T00:00:00Z"
            and order["delegations"] == DELEGATES
            and order["operating_access_ready_from"] == "2027-01-01T03:15:00Z"
            and order["earlier_operating_history"] == "NOT_ESTABLISHED_BY_THIS_REGISTER",
            "Exact company authority operating/closing window differs",
        )
        require(
            order["scope"]
            == (
                "Named registered company/affiliate people, separately accepted service "
                "delegates, explicit contractor relationships and owned nonhuman accounts only"
            )
            and order["unmodeled_scope"]
            == (
                "Unnamed workers, other enterprise accounts, industrial operating systems, "
                "physical badges and unaccepted proposed office occupants"
            )
            and order["closing_authority_scope"]
            == (
                "Retrospective reconciliation, review and expired-state maintenance; "
                "no operating access extension"
            )
            and order["reserved_authority"]
            == "No operating safety, corporate employment hire, external opinion or legal status",
            "Exact company authority scope/reservations differ",
        )
        for person, capacity in DELEGATES.items():
            delegated = exact("service_delegation", person)
            d = delegated["body"]
            require(
                d["person_id"] == d["accepted_by"] == person
                and d["issuer"] == "P001"
                and d["capacity"] == capacity
                and d["accepted_at"] == d["effective_from"] == "2027-01-01T01:00:00Z"
                and d["effective_to"] == order["closing_record_authority_until"]
                and d["operating_service_window_ends"] == order["effective_to"]
                and d["post_window_scope"]
                == "Closing records only; no operating permissions extended"
                and d["office_status"] == "PROPOSED_NOT_APPOINTED"
                and d["employment_status"] == "NOT_ESTABLISHED"
                and d["appointment_is_employment"] is False
                and instant(order["effective_from"])
                <= instant(d["accepted_at"])
                < instant(order["effective_to"]),
                ("Delegation exceeds inherited authority or changes appointment/employment"),
            )
        catalogue = exact("entitlement_catalogue", "CORPORATE-LOGICAL")["body"]
        require(
            catalogue["conflicting_rights"] == [list(pair) for pair in CONFLICTS]
            and catalogue["mover_duty_is_job_title_change"] is False
            and catalogue["local_mover_duties"]
            == {
                code: "Retained local application entitlement; original detailed business "
                "permission catalogue unavailable"
                for code in ("billing-admin", "inventory-admin")
            },
            "Entitlement conflict or unavailable historical meaning reinterpreted",
        )

        for r in selected:
            d = r["body"]
            if d is None:
                continue

            def check_payload(value):
                if isinstance(value, dict):
                    forbidden = {
                        "task_id",
                        "control_id",
                        "expected_finding",
                        "expected_outcome",
                        "false_clean",
                        "rubric",
                        "answer_key",
                        "learner_answer",
                    }
                    require(
                        not forbidden.intersection(value),
                        "Audit task/answer labels exposed in company content",
                    )
                    for child in value.values():
                        check_payload(child)
                elif isinstance(value, list):
                    for child in value:
                        check_payload(child)

            check_payload(d)
            for field in (
                "performed_by",
                "requested_by",
                "approved_by",
                "reviewed_by",
                "recorded_by",
                "exported_by",
                "prepared_by",
                "company_accepted_by",
            ):
                if field not in d:
                    continue
                actor = d[field]
                require(
                    actor in {*DELEGATES, "P001", "P002", "LOCAL-LEASE-ENGINE"},
                    "Unknown company operation actor",
                )
                if actor in DELEGATES:
                    delegation = exact("service_delegation", actor)["body"]
                    require(
                        instant(delegation["effective_from"])
                        <= instant(r["event_at"])
                        < instant(delegation["effective_to"])
                        and delegation["accepted_by"] == actor
                        and delegation["office_status"] == "PROPOSED_NOT_APPOINTED"
                        and delegation["employment_status"] == "NOT_ESTABLISHED",
                        "Operation actor delegation unavailable or fabricated appointment",
                    )
                if actor == "LOCAL-LEASE-ENGINE":
                    require(
                        r["system"].startswith("account_") or r["system"] == "permission_activity",
                        "Automatic lease actor exceeds authority",
                    )
            if r["system"] == "access_approvals":
                d = r["body"]
                request = lookup[tuple(d["request"][k] for k in keys)]["body"]
                subject = next((p for p in affiliations if p["record"] == d["subject_id"]), None)
                expected_rights = (
                    ["board.read"]
                    if subject and subject["body"]["relationship_kind"] == "NONEMPLOYEE_DIRECTOR"
                    else ["workspace.read"]
                )
                expected_rights += {
                    "AS-P007": ["iam.provision"],
                    "AS-P008": ["iam.approve"],
                    "AS-P009": ["review.perform"],
                    "AS-P006": ["affiliation.record"],
                    "AS-P013": ["contract.record"],
                    "AS-P003": ["legal.record"],
                }.get(d["subject_id"], [])
                require(
                    d["approved_by"] != request["requested_by"]
                    and d["approved_by"] != d["provisioner"],
                    "Independent approval absent",
                )
                require(
                    d["approved_rights"] == request["requested_rights"]
                    and instant(d["approved_at"]) < instant(d["effective_from"]),
                    "Approval/right/effective chronology differs",
                )
                require(
                    d["decision"] == "APPROVED"
                    and d["subject_id"] == request["subject_id"]
                    and d["effective_from"] == request["effective_from"]
                    and d["effective_to"] == request["effective_to"]
                    and d["provisioner"] == "AS-P007"
                    and d["approved_by"] == ("P001" if d["subject_id"] in DELEGATES else "AS-P008"),
                    "Approval subject/authority/boundary differs",
                )
                require(
                    d["approved_rights"] == sorted(expected_rights)
                    and request["channels"] == list(CHANNELS),
                    "Approved entitlement differs from actual relationship/duty catalogue",
                )
            if r["system"].startswith("account_") and "state" in d:
                state = d["state"]
                require(
                    r["record"] == state["account_id"]
                    and r["system"] == "account_" + state["channel"]
                    and type(state["active"]) is bool
                    and state["rights"] == sorted(set(state["rights"])),
                    "Account inventory identity/state differs",
                )
                if "approval" in d:
                    approval = lookup[tuple(d["approval"][k] for k in keys)]["body"]
                    require(
                        state["subject_id"] == approval["subject_id"]
                        and state["rights"] == approval["approved_rights"]
                        and state["starts"] == _time(approval["effective_from"])
                        and state["ends"] == _time(approval["effective_to"]),
                        "Provisioned state does not match independent approved request",
                    )
                if d.get("invalidation_ack_at"):
                    require(
                        instant(d["invalidation_ack_at"]) <= instant(r["event_at"]),
                        "Acknowledgement known before its actual business event",
                    )
            if r["system"] == "permission_activity":
                d = r["body"]
                account = lookup[tuple(d["account_state"][k] for k in keys)]["body"]["state"]
                available_states = [
                    x
                    for x in selected
                    if x["system"].startswith("account_")
                    and x["body"] is not None
                    and "state" in x["body"]
                    and x["body"]["state"]["account_id"] == d["account_id"]
                    and instant(x["available_at"]) <= instant(d["decision_at"])
                ]
                latest = max(available_states, key=lambda x: x["version"])
                require(
                    latest["sha256"] == d["account_state"]["sha256"],
                    "Permission probe uses stale account state",
                )
                allowed = (
                    account["active"]
                    and account["credential_epoch"] == d["credential_epoch"]
                    and instant(account["starts"])
                    <= instant(d["decision_at"])
                    < instant(account["ends"])
                    and d["right"] in account["rights"]
                )
                require(
                    d["account_id"] == account["account_id"]
                    and d["decision_at"] == r["event_at"]
                    and d["object_sha256"] == sha(original)
                    and d["object_bytes"] == original.stat().st_size
                    and (d["decision"] == "ALLOW") == allowed,
                    "Permission decision contradicts actual state",
                )
                require(
                    d["returned_bytes"] == (original.stat().st_size if allowed else 0)
                    and d["returned_sha256"] == (sha(original) if allowed else None),
                    "Permission original byte/result custody differs",
                )
        source_branch = "year-clean" if side == "A" else "year-messy"
        for cause in ("MOVE-2027-Q1-001", "MOVE-2027-Q2-001"):
            for version in (1, 2):
                old = legacy_lookup[(source_branch, "application", cause + "-application", version)]
                current = exact("account_legacy_application", cause + ":application", version)
                require(
                    current["body"]["state"]["rights"] == old["document"]["rights"]
                    and current["event_at"] == old["event_at"]
                    and current["available_at"] == old["available_at"]
                    and current["body"]["source_content_sha256"] == old["sha256"],
                    "Retained mover application history changed",
                )
        # These are independent expected memberships based on actual recorded
        # relationship intervals, not the producer's population count.
        subjects = {
            r["record"]: {
                "kind": r["body"]["relationship_kind"],
                "starts": r["body"]["service_effective_from"],
                "ends": r["body"]["service_effective_to"],
            }
            for r in affiliations
            if r["body"]["included_in_service_boundary"]
        }
        for r in selected:
            if r["system"] == "contractor_relationship":
                d = r["body"]
                subjects[d["person_id"]] = {
                    "kind": "CONTRACTOR",
                    "starts": d["starts"],
                    "ends": d["ends"],
                }
            if r["system"] == "nonhuman_inventory":
                d = r["body"]
                subjects[d["identity_id"]] = {
                    "kind": "NONHUMAN_SERVICE",
                    "starts": d["starts"],
                    "ends": d["ends"],
                }
        projected = [
            {
                "native": {
                    k: r[k] for k in (*keys, "sha256", "event_at", "available_at", "imported_at")
                },
                "body": r["body"],
            }
            for r in selected
            if r["body"] is not None
        ]
        for month in range(1, 13):
            census_row = exact("denominator_snapshot", f"2027-{month:02}")
            census = census_row["body"]
            expected_cutoff = (
                datetime(2028, 1, 1, tzinfo=UTC)
                if month == 12
                else datetime(2027, month + 1, 1, tzinfo=UTC)
            )
            require(
                instant(census["cutoff_exclusive"]) == expected_cutoff
                and instant(census_row["event_at"]) == expected_cutoff,
                "Closed monthly window was truncated or moved",
            )
            view = population_view(projected, subjects, census["cutoff_exclusive"])
            require(
                census["registered_subject_ids"] == view["expected_subject_ids"]
                and census["accounts"] == view["account_population"],
                "Closed-period denominator/accounts differ",
            )
            recon = exact("monthly_reconciliation", f"2027-{month:02}")["body"]
            require(
                recon["denominator"]["sha256"] == census_row["sha256"]
                and recon["expected_subject_ids"] == view["expected_subject_ids"]
                and recon["account_subject_ids"] == view["account_subject_ids"]
                and recon["unmatched_review_subject_ids"] == view["unmatched_review_subject_ids"]
                and recon["missing_account_subject_ids"]
                == sorted(set(view["expected_subject_ids"]) - set(view["account_subject_ids"]))
                and recon["account_population_sha256"] == digest(view["account_population"])
                and recon["status"]
                == (
                    "MAPPING_WORK_OPEN"
                    if view["unmatched_review_subject_ids"]
                    else "REGISTERED_SCOPE_RECONCILED"
                ),
                "Monthly account reconciliation differs",
            )
            if month % 3:
                continue
            q = month // 3
            pop_row = exact("periodic_review_population", f"2027-Q{q}")
            pop = pop_row["body"]
            require(
                instant(pop["period_start"]) == datetime(2027, month - 2, 1, tzinfo=UTC)
                and instant(pop["period_end_exclusive"]) == expected_cutoff
                and instant(pop_row["event_at"]) == expected_cutoff + timedelta(hours=1)
                and pop["denominator"]["sha256"] == census_row["sha256"],
                "Quarterly period or exact denominator link differs",
            )
            require(
                pop["members"] == view["members"]
                and pop["membership_sha256"] == digest(view["members"]),
                "Quarterly exact member population differs",
            )
            old = legacy_lookup[(source_branch, "review_population", f"PRIV-2027-Q{q}", 1)]
            oldrecon = legacy_lookup[(source_branch, "review_reconciliation", f"PRIV-2027-Q{q}", 1)]
            require(
                pop["retained_local_privileged_population"] == old["document"]["members"]
                and pop["retained_source_content_sha256"] == old["sha256"]
                and pop["retained_local_review_missing_ids"]
                == oldrecon["document"]["missing_person_ids"],
                "Original privileged review history backfilled or altered",
            )
            reviewed = exact("periodic_review_decisions", f"2027-Q{q}")["body"]
            expected_decisions = []
            for member in view["members"]:
                rights = sorted(
                    {
                        right
                        for account in member["accounts"]
                        for right in account["state"]["rights"]
                    }
                )
                removed = (
                    ["billing-admin"] if {"billing-admin", "inventory-admin"} <= set(rights) else []
                )
                expected_decisions.append(
                    {
                        "subject_id": member["subject_id"],
                        "observed_rights": rights,
                        "remove_rights": removed,
                        "decision": "REMOVAL_REQUESTED" if removed else "RETAIN_SCOPED_DUTIES",
                        "removal_confirmation": None if removed else "NO_REMOVAL_REQUEST",
                    }
                )
            open_work = bool(
                view["unmatched_review_subject_ids"]
                or any(d["remove_rights"] for d in expected_decisions)
            )
            require(
                reviewed["population"]["sha256"] == pop_row["sha256"]
                and reviewed["decisions"] == expected_decisions
                and reviewed["population_sha256"] == digest(view["members"])
                and reviewed["missing_subject_ids"] == view["unmatched_review_subject_ids"]
                and reviewed["review_status"]
                == ("RECONCILIATION_OPEN" if open_work else "REGISTERED_SCOPE_REVIEW_RECORDED")
                and reviewed["wider_estate_reviewed"] is False,
                "Review decisions or claimed closure contradict actual member state",
            )
            followup = exact("review_followup", f"2027-Q{q}")["body"]
            require(
                followup["review"]["sha256"]
                == exact("periodic_review_decisions", f"2027-Q{q}")["sha256"]
                and followup["population_sha256"] == digest(view["members"])
                and followup["person_mapping_work"] == view["unmatched_review_subject_ids"]
                and followup["removal_work"]
                == [d for d in expected_decisions if d["remove_rights"]]
                and followup["status"]
                == ("OPEN" if open_work else "NO_ACTION_REQUIRED_FOR_REGISTERED_SCOPE")
                and followup["historical_reviews_replaced"] is False,
                "Management follow-up contradicts performed review",
            )
        eligible = {r["record"] for r in affiliations if r["body"]["included_in_service_boundary"]}
        expected_humans = eligible | {c["id"] for c in CONTRACTORS}
        require(
            {r["record"] for r in selected if r["system"] == "access_requests"} == expected_humans
            and {r["record"] for r in selected if r["system"] == "access_approvals"}
            == expected_humans,
            "Exact included-human request/approval census differs",
        )
        require(
            {r["record"] for r in selected if r["system"] == "nonhuman_inventory"} == set(SERVICES),
            "Owned service inventory membership differs",
        )
        for pid in expected_humans:
            for channel in CHANNELS:
                first = exact("account_" + channel, pid + ":" + channel)["body"]["state"]
                require(
                    first["subject_id"] == pid
                    and first["review_anchor"] == pid
                    and first["active"] is True,
                    "Human logical channel baseline missing or misassigned",
                )
        for c in CONTRACTORS:
            relationship = exact("contractor_relationship", c["id"])["body"]
            require(
                relationship["person_id"] == c["id"]
                and relationship["name"] == c["name"]
                and relationship["starts"] == c["start"]
                and relationship["ends"] == c["end"]
                and relationship["sponsor"] == c["sponsor"]
                and relationship["employment_status"] == "NONEMPLOYEE_CONTRACTOR"
                and relationship["counterparty_accepted_by"] == c["id"]
                and relationship["company_accepted_by"] == "AS-P003",
                "Contractor identity/term/acceptance basis differs",
            )
            expired = exact("relationship_events", c["id"] + ":EXPIRY")["body"]
            require(
                expired["kind"] == "CONTRACT_EXPIRED"
                and expired["effective_at"] == c["end"]
                and expired["renewal_authority"] is None
                and expired["removal_channels"] == list(CHANNELS),
                "Contractor expiry/removal channel history differs",
            )
        if side == "B":
            maintenance = exact("company_authority", "POST-PERIOD-MAINTENANCE")["body"]
            require(
                maintenance["issued_by"] == "P001"
                and maintenance["independent_acceptance"] == "P002"
                and maintenance["delegated_to"] == "AS-P007"
                and maintenance["approved_by"] == "AS-P008"
                and maintenance["effective_from"] == "2028-01-15T10:00:00Z"
                and maintenance["effective_to"] == "2028-01-15T18:00:00Z"
                and maintenance["employment_appointments_made"] is False
                and maintenance["previous_reviews_reperformed"] is False,
                "Exact post-period maintenance authority differs",
            )
            for cause, pid in (("MOVE-2027-Q1-001", "P014"), ("MOVE-2027-Q2-001", "P015")):
                corrected = exact("account_legacy_application", cause + ":application", 4)
                d = corrected["body"]
                require(
                    corrected["event_at"] == _time("2028-01-15T12:00:00Z")
                    and d["state"]["rights"] == ["inventory-admin"]
                    and d["state"]["review_anchor"] == pid
                    and d["state"]["active"] is False
                    and d["old_population_or_review_replaced"] is False,
                    "Late correction rewrites historical review or reactivates expired access",
                )
                closed = exact("late_correction", cause)["body"]
                require(
                    closed["quarter_reviews_replaced"] is False
                    and closed["operating_permission_reactivated"] is False
                    and closed["current_employee_status_changed"] is False,
                    "Late correction falsely backfills/changes employment history",
                )
        summaries[side] = {
            "native_versions": len(selected),
            "canonical_employees": 44,
            "nonemployee_directors": 7,
            "proposed_contacts": 15,
            "local_service_delegates_without_employment": 6,
            "modeled_contractors": 2,
            "owned_nonhuman_services": 3,
            "monthly_denominators": 12,
            "quarterly_reviews": 4,
            "wider_workforce_established": False,
        }
    return summaries


def schema_verify(path):
    """Validate the storage contract, including deletion/update protection."""
    immutable_schema(path)
    tables = {
        "systems": (
            "CREATE TABLE systems(company TEXT, branch TEXT, system TEXT, "
            "owner TEXT NOT NULL, PRIMARY KEY(company,branch,system))"
        ),
        "versions": (
            "CREATE TABLE versions(company TEXT, branch TEXT, system TEXT, "
            "record TEXT, version INTEGER, event_at TEXT, available_at TEXT "
            "NOT NULL, imported_at TEXT NOT NULL, origin TEXT NOT NULL, "
            "provenance TEXT NOT NULL, content BLOB NOT NULL, sha256 TEXT NOT"
            " NULL, command_id TEXT UNIQUE NOT NULL, input_digest TEXT NOT "
            "NULL, PRIMARY KEY(company,branch,system,record,version), FOREIGN"
            " KEY(company,branch,system) REFERENCES "
            "systems(company,branch,system))"
        ),
        "grants": (
            "CREATE TABLE grants(principal TEXT, engagement TEXT, company "
            "TEXT, branch TEXT, system TEXT, active INTEGER NOT NULL, PRIMARY"
            " KEY(principal,engagement,company,branch,system))"
        ),
        "access_events": (
            "CREATE TABLE access_events(id INTEGER PRIMARY KEY, principal "
            "TEXT, engagement TEXT, company TEXT, branch TEXT, system TEXT, "
            "active INTEGER, recorded_at TEXT)"
        ),
        "collections": (
            "CREATE TABLE collections(command_id TEXT PRIMARY KEY, "
            "input_digest TEXT NOT NULL, receipt TEXT NOT NULL)"
        ),
    }

    def normalize(v):
        return "".join(v.split()).lower()

    with read_only(path) as db:
        actual = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'"))
        require(
            set(actual) == set(tables)
            and all(normalize(actual[k]) == normalize(v) for k, v in tables.items()),
            "Exact CompanyStore table schema differs",
        )
        require(
            not db.execute("PRAGMA foreign_key_check").fetchall(),
            "Company source foreign-key integrity differs",
        )
        for table in ("grants", "access_events", "collections"):
            require(
                db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0,
                "Source authoring contains engagement access/collection journal",
            )
        require(
            not db.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall(),
            "Unexpected source view",
        )
        indices = list(db.execute("SELECT name,sql FROM sqlite_master WHERE type='index'"))
        require(
            {r[0] for r in indices}
            == {
                "sqlite_autoindex_systems_1",
                "sqlite_autoindex_versions_1",
                "sqlite_autoindex_versions_2",
                "sqlite_autoindex_grants_1",
                "sqlite_autoindex_collections_1",
            }
            and all(r[1] is None for r in indices),
            "Exact source indexes differ",
        )
        special_owners = {
            "company_authority": "P001",
            "service_delegation": "P001",
            "affiliation_register": "AS-P006",
            "entitlement_catalogue": "AS-P008",
            "access_requests": "AS-P006",
            "access_approvals": "AS-P008",
            "duty_authorizations": "AS-P008",
            "duty_followup": "AS-P008",
            "contractor_relationship": "AS-P013",
            "relationship_events": "AS-P013",
            "monthly_reconciliation": "AS-P009",
            "periodic_review_decisions": "AS-P009",
            "review_followup": "AS-P009",
            "late_correction": "AS-P008",
        }
        systems = [dict(r) for r in db.execute("SELECT * FROM systems")]
        versions = {
            (r[0], r[1], r[2]) for r in db.execute("SELECT company,branch,system FROM versions")
        }
        require(
            {(r["company"], r["branch"], r["system"]) for r in systems} == versions
            and all(r["owner"] == special_owners.get(r["system"], "AS-P007") for r in systems),
            "Exact registered source owner/membership differs",
        )


def private_inventory(destination):
    destination = Path(destination).absolute()
    require(
        not any(p.is_symlink() for p in [destination, *destination.parents]),
        "Private directory aliases forbidden",
    )
    inventory = {}
    for path in [destination, *destination.rglob("*")]:
        require(not path.is_symlink(), "Private source alias forbidden")
        stat = path.stat()
        if path.is_dir():
            require(stat.st_mode & 0o777 == 0o700, "Private source directory mode differs")
        else:
            require(
                path.is_file() and stat.st_mode & 0o777 == 0o600 and stat.st_nlink == 1,
                "Private independent regular file required",
            )
            require(
                not path.name.endswith(("-wal", "-shm", "-journal")), "Non-quiescent company source"
            )
            if path.name != "MANIFEST.json":
                inventory[str(path.relative_to(destination))] = sha(path)
    return inventory


def custody_contract(legacy, repository, private_repository):
    return {
        "schema": "SH_PRIVATE_RESTRICTED_ORIGINAL_CUSTODY_V1",
        "input_repository": str(Path(repository).absolute()),
        "input_private_repository": str(Path(private_repository).absolute()),
        "original_database_sha256": LEGACY_SHA,
        "admission_status": "RESTRICTED_NOT_PROJECTED_AUDITOR_ACCESS_NOT_ESTABLISHED",
        "records": [
            {
                "original_native_reference": {k: row[k] for k in REFERENCE_KEYS},
                "native_identity_sha256": original_witness(row)["native_identity_sha256"],
            }
            for row in legacy
        ],
    }


def limitation_contract():
    return [
        (
            "Declared named shared-service boundary only; forecast positions "
            "and wider workers remain unmodeled"
        ),
        (
            "Canonical source does not supply exact employment starts, "
            "payroll entities or accepted proposed offices"
        ),
        (
            "Original mover initial requests and historical former-employee "
            "revocation remain unavailable"
        ),
        (
            "Quarter-end reviews first become available after their closed "
            "window; later corrections do not replace them"
        ),
        (
            "No physical badge, industrial-system census, real deployment, "
            "legal acceptance or external opinion is asserted"
        ),
        (
            "First registered accounts are issued January 1 at 03:15 UTC; "
            "earlier operating access history is not established"
        ),
        (
            "Restricted original custody witnesses do not grant auditor "
            "source access or admit projected originals"
        ),
    ]


def create(destination, repository, private_repository):
    destination, repository, private_repository = map(
        lambda p: Path(p).absolute(), (destination, repository, private_repository)
    )
    require(not destination.exists(), "New isolated source destination required")
    require(
        destination.parent.is_dir() and not destination.parent.is_symlink(),
        "Existing private parent required",
    )
    require(destination.parent.stat().st_mode & 0o077 == 0, "Private parent required")
    initialized = datetime.now(UTC).isoformat()
    basis = canonical_basis(repository)
    legacy = legacy_basis(private_repository)
    destination.mkdir(mode=0o700)
    company_root = destination / "company"
    company_root.mkdir(mode=0o700)
    original = destination / "corporate-reference.txt"
    write(
        original,
        (
            b"Sable Harbor corporate reference workspace\nNamed shared-service "
            b"inventory and records.\nSynthetic company information; no real "
            b"customer data or PHI.\n"
        ),
    )
    write(destination / "IMPLEMENTATION.py", Path(__file__).read_bytes())
    write(destination / "BASIS.json", basis)
    write(
        destination / "ORIGINAL_CUSTODY.json",
        custody_contract(legacy, repository, private_repository),
    )
    store = CompanyStore(company_root)
    author_family(store, basis, legacy, original, initialized)
    rows = native_records(store.path)
    summary = semantic_verify(rows, basis, legacy, original)
    schema_verify(store.path)
    completed = datetime.now(UTC).isoformat()
    require(
        canonical_basis(repository) == basis and sha(private_repository / LEGACY) == LEGACY_SHA,
        "Original input changed during source creation",
    )
    systems = sorted({r["system"] for r in rows})
    write(
        destination / "RECEIPT.json",
        {
            "schema": SCHEMA,
            "company": COMPANY,
            "branches": BRANCHES,
            "initialized_at": initialized,
            "completed_at": completed,
            "fictional_business_period": {
                "start": "2027-01-01T00:00:00Z",
                "end_exclusive": "2028-01-01T00:00:00Z",
                "closing_record_cutoff": "2028-01-16T00:00:00Z",
            },
            "input_repository": str(repository),
            "input_private_repository": str(private_repository),
            "legacy_source": LEGACY,
            "legacy_sha256": LEGACY_SHA,
            "basis_sha256": sha(destination / "BASIS.json"),
            "native_versions": len(rows),
            "systems": systems,
            "summary": summary,
            "source_complete": False,
            "whole_period_operations_established": False,
            "registered_account_first_issue_at": "2027-01-01T03:15:00Z",
            "restricted_original_admission": "NOT_ADMITTED_OR_GRANTED_BY_THIS_SOURCE",
            "wider_workforce_established": False,
            "engagements_created": 0,
            "source_grants": 0,
            "audit_collections": 0,
            "limitations": limitation_contract(),
        },
    )
    write(
        destination / "MANIFEST.json", {"schema": SCHEMA, "files": private_inventory(destination)}
    )
    return verify(destination)


def verify(destination):
    destination = Path(destination).absolute()
    inventory = private_inventory(destination)
    manifest = json.loads((destination / "MANIFEST.json").read_bytes())
    require(
        set(manifest) == {"schema", "files"}
        and manifest["schema"] == SCHEMA
        and manifest["files"] == inventory,
        "Exact private source manifest differs",
    )
    require(
        set(manifest["files"])
        == {
            "company/company.sqlite3",
            "corporate-reference.txt",
            "IMPLEMENTATION.py",
            "BASIS.json",
            "ORIGINAL_CUSTODY.json",
            "RECEIPT.json",
        }
        and {str(p.relative_to(destination)) for p in destination.rglob("*") if p.is_dir()}
        == {"company"},
        "Exact private source file/directory roster differs",
    )
    receipt = json.loads((destination / "RECEIPT.json").read_bytes())
    require(
        set(receipt)
        == {
            "schema",
            "company",
            "branches",
            "initialized_at",
            "completed_at",
            "fictional_business_period",
            "input_repository",
            "input_private_repository",
            "legacy_source",
            "legacy_sha256",
            "basis_sha256",
            "native_versions",
            "systems",
            "summary",
            "source_complete",
            "whole_period_operations_established",
            "registered_account_first_issue_at",
            "restricted_original_admission",
            "wider_workforce_established",
            "engagements_created",
            "source_grants",
            "audit_collections",
            "limitations",
        },
        "Exact receipt key contract differs",
    )
    require(
        receipt["fictional_business_period"]
        == {
            "start": "2027-01-01T00:00:00Z",
            "end_exclusive": "2028-01-01T00:00:00Z",
            "closing_record_cutoff": "2028-01-16T00:00:00Z",
        }
        and receipt["legacy_source"] == LEGACY
        and receipt["legacy_sha256"] == LEGACY_SHA
        and receipt["limitations"] == limitation_contract()
        and receipt["whole_period_operations_established"] is False
        and receipt["registered_account_first_issue_at"] == "2027-01-01T03:15:00Z"
        and receipt["restricted_original_admission"] == "NOT_ADMITTED_OR_GRANTED_BY_THIS_SOURCE",
        "Exact receipt boundary, history or limitation claims differ",
    )
    for field in ("input_repository", "input_private_repository"):
        path = Path(receipt[field])
        require(
            path.is_absolute()
            and str(path.absolute()) == receipt[field]
            and not any(p.is_symlink() for p in [path, *path.parents]),
            "Exact ordinary input root required",
        )
    require(
        receipt["schema"] == SCHEMA
        and receipt["company"] == COMPANY
        and receipt["branches"] == BRANCHES,
        "Source scope/branch contract differs",
    )
    require(
        (destination / "IMPLEMENTATION.py").read_bytes() == Path(__file__).read_bytes(),
        "Source implementation pin differs",
    )
    require(
        receipt["source_complete"] is False
        and receipt["wider_workforce_established"] is False
        and receipt["engagements_created"]
        == receipt["source_grants"]
        == receipt["audit_collections"]
        == 0,
        "Source completeness/journal claim differs",
    )
    basis = json.loads((destination / "BASIS.json").read_bytes())
    require(
        sha(destination / "BASIS.json") == receipt["basis_sha256"]
        and canonical_basis(Path(receipt["input_repository"])) == basis,
        "Canonical source custody differs",
    )
    legacy = legacy_basis(Path(receipt["input_private_repository"]))
    require(
        json.loads((destination / "ORIGINAL_CUSTODY.json").read_bytes())
        == custody_contract(
            legacy, Path(receipt["input_repository"]), Path(receipt["input_private_repository"])
        ),
        "Exact private original tuple, lineage status or input root differs",
    )
    path = destination / "company/company.sqlite3"
    schema_verify(path)
    rows = native_records(path)
    require(
        len(rows) == receipt["native_versions"]
        and sorted({r["system"] for r in rows}) == receipt["systems"],
        "Exact native inventory differs",
    )
    require(
        all(r["company"] == COMPANY and r["branch"] in BRANCHES.values() for r in rows),
        "Unexpected company source member",
    )
    started, completed = instant(receipt["initialized_at"]), instant(receipt["completed_at"])
    require(started <= completed <= datetime.now(UTC), "Real source import clock invalid")
    for r in rows:
        require(
            started <= instant(r["imported_at"]) <= completed,
            "Actual source import outside authoring bounds",
        )
        provenance = json.loads(r["provenance"])
        expected_provenance = {
            "source_reference": f"company://{COMPANY}/{r['branch']}/{r['system']}/{r['record']}",
            "name": "corporate-reference.txt"
            if r["system"] == "workspace_object"
            else "person-access-" + digest([r["system"], r["record"]])[:24] + ".json",
            "content_type": "text/plain; charset=utf-8"
            if r["system"] == "workspace_object"
            else "application/json",
            "initialized_at": receipt["initialized_at"],
            "qualification": "FICTIONAL_COMPANY_OPERATIONS_NO_REAL_EMPLOYMENT_OR_PHI",
        }
        require(
            provenance == expected_provenance,
            "Exact typed authoring provenance/name contract differs",
        )
        require(
            r["input_digest"]
            == hashlib.sha256(
                _json(
                    [
                        [r[k] for k in ("company", "branch", "system", "record")],
                        r["version"] - 1,
                        r["event_at"],
                        r["available_at"],
                        r["origin"],
                        provenance,
                        r["sha256"],
                    ]
                ).encode()
            ).hexdigest(),
            "Supported source command input digest differs",
        )
        expected_command = (
            "OBJ-" + r["branch"]
            if r["system"] == "workspace_object"
            else "PERS-" + digest([r["branch"], r["system"], r["record"], r["version"]])[:60]
        )
        require(
            r["command_id"] == expected_command, "Native source append command identity differs"
        )
        require(
            r["origin"] == "AUTHORED_TRAINING_SOURCE"
            and provenance["initialized_at"] == receipt["initialized_at"]
            and provenance["source_reference"]
            == f"company://{COMPANY}/{r['branch']}/{r['system']}/{r['record']}"
            and provenance["qualification"]
            == "FICTIONAL_COMPANY_OPERATIONS_NO_REAL_EMPLOYMENT_OR_PHI",
            "Synthetic authoring provenance differs",
        )
        if r["system"] == "workspace_object":
            require(
                provenance["name"] == "corporate-reference.txt"
                and provenance["content_type"] == "text/plain; charset=utf-8"
                and r["content"] == (destination / "corporate-reference.txt").read_bytes(),
                "Typed native original workspace object differs",
            )
        else:
            require(
                provenance["name"].endswith(".json")
                and provenance["content_type"] == "application/json"
                and r["body"]["schema"] == "SH_COMPANY_PERSON_ACCESS_RECORD_V1",
                "Typed native JSON contract differs",
            )
    result = semantic_verify(rows, basis, legacy, destination / "corporate-reference.txt")
    require(result == receipt["summary"], "Native operation summary differs")
    return {
        "schema": SCHEMA,
        "verified": True,
        "manifest_sha256": sha(destination / "MANIFEST.json"),
        "company_sha256": sha(path),
        "native_versions": len(rows),
        "summary": result,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("create")
    run.add_argument("--destination", type=Path, required=True)
    run.add_argument("--repository", type=Path, required=True)
    run.add_argument("--private-repository", type=Path, required=True)
    check = commands.add_parser("verify")
    check.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = (
        create(args.destination, args.repository, args.private_repository)
        if args.command == "create"
        else verify(args.destination)
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
