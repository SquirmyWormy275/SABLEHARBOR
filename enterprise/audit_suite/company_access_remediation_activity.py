"""Local IAM007 decision execution and distinct operating verification, not assurance."""

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_lifecycle_activity import FIELDS, read_inputs
from .company_lifecycle_activity import LifecycleSourceRef as AccessRemediationSourceRef
from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

CONTROL = "SH-IAM-007"
QUALIFICATION = "LOCAL_ACCESS_REMEDIATION_CONTINUATION_NOT_CANON_EMPLOYMENT_OR_DEPLOYMENT"


@dataclass(frozen=True)
class AccessRemediationRecipe:
    company_id: str
    source_store_id: str
    source_refs: tuple[AccessRemediationSourceRef, ...]
    source_versions_sha256: str
    branch_ids: tuple[str, str]
    campaign_id: str
    subject_person_id: str
    input_at: str
    request_at: str
    execute_at: str
    verify_at: str
    escalate_at: str
    correction_at: str
    closeout_at: str
    local_requirement_basis: str


def _rights(value):
    if (
        not isinstance(value, list)
        or not value
        or len(value) > 32
        or any(not isinstance(r, str) or not r for r in value)
        or len(set(value)) != len(value)
    ):
        raise CompanyStoreError("Bounded distinct explicit permission names required")
    return set(value)


class LocalEntitlements:
    """Data-only authorization state; no host permissions, tokens or external systems."""

    def __init__(self, subject, owner, reviewer, observed, removals):
        for value in (subject, owner, reviewer):
            _id(value)
        if owner == reviewer:
            raise CompanyStoreError("Distinct operating verifier required")
        self.subject, self.owner, self.reviewer = subject, owner, reviewer
        self.rights = _rights(observed)
        self.removals = _rights(removals)
        if not self.removals <= self.rights:
            raise CompanyStoreError("Removal request exceeds observed rights")

    def execute(self, actor, subject, requested, mapping):
        requested = _rights(requested)
        if actor != self.owner or subject != self.subject or requested != self.removals:
            raise CompanyStoreError("Only exact owner-authorized subject and removal allowed")
        if not isinstance(mapping, dict) or any(
            k != v or k not in self.removals for k, v in mapping.items()
        ):
            raise CompanyStoreError("Permission resolver cannot redirect or broaden authority")
        before = sorted(self.rights)
        missing = sorted(requested - set(mapping))
        if not missing:
            self.rights -= requested
        return {
            "before_rights": before,
            "after_rights": sorted(self.rights),
            "removed_rights": sorted(set(before) - self.rights),
            "unresolved_permissions": missing,
            "status": "UNRESOLVED_PERMISSION_MAPPING" if missing else "APPLIED_OR_ALREADY_ABSENT",
        }

    def verify(self, actor, expected):
        if actor != self.reviewer:
            raise CompanyStoreError("Distinct designated operating verifier required")
        expected = _rights(expected)
        return {
            "observed_rights": sorted(self.rights),
            "expected_rights": sorted(expected),
            "excess_rights": sorted(self.rights - expected),
            "missing_authorized_rights": sorted(expected - self.rights),
            "removed_permission_probes": {
                r: ("ALLOW" if r in self.rights else "DENY") for r in sorted(self.removals)
            },
            "verification_basis": "ACTUAL_LOCAL_AUTHORIZATION_STATE_NOT_EXECUTOR_STATUS_TEXT",
        }


def _prepare(repository, source_root, recipe):
    for value in (
        recipe.company_id,
        recipe.source_store_id,
        recipe.campaign_id,
        recipe.subject_person_id,
    ):
        _id(value)
    if (
        not isinstance(recipe.branch_ids, tuple)
        or len(recipe.branch_ids) != 2
        or len(set(recipe.branch_ids)) != 2
    ):
        raise CompanyStoreError("Two distinct qualified continuation branches required")
    for branch in recipe.branch_ids:
        _id(branch)
    if (
        not isinstance(recipe.local_requirement_basis, str)
        or not 1 <= len(recipe.local_requirement_basis.strip()) <= 2000
    ):
        raise CompanyStoreError("Explicit bounded local requirement basis required")
    names = (
        "input_at",
        "request_at",
        "execute_at",
        "verify_at",
        "escalate_at",
        "correction_at",
        "closeout_at",
    )
    times = [datetime.fromisoformat(_time(getattr(recipe, k))) for k in names]
    if any(a >= b for a, b in zip(times, times[1:], strict=False)) or times[-1] - times[
        0
    ] > timedelta(days=31):
        raise CompanyStoreError("Ordered continuation window at most31 days required")
    originals, pin = read_inputs(source_root, recipe.source_refs)
    if pin != recipe.source_versions_sha256 or len(originals) != 5:
        raise CompanyStoreError(
            "Five exactly pinned original review/HR/application records required"
        )
    if (
        len({(r["company"], r["branch"]) for r in originals}) != 1
        or originals[0]["company"] != recipe.company_id
    ):
        raise CompanyStoreError("One original company branch required")
    if originals[0]["branch"] in recipe.branch_ids:
        raise CompanyStoreError("Continuation cannot reuse original branch identity")
    native = {}
    for row in originals:
        if (
            row["origin"] != "AUTHORED_TRAINING_SOURCE"
            or row["event_at"] is None
            or datetime.fromisoformat(_time(row["event_at"])) > times[0]
            or datetime.fromisoformat(_time(row["available_at"])) > times[0]
        ):
            raise CompanyStoreError("Known available original source instants required")
        body = json.loads(row["content"])
        if not isinstance(body, dict) or row["system"] in native:
            raise CompanyStoreError("One exact native object per source role required")
        native[row["system"]] = (row, body)
    if set(native) != {
        "review_population",
        "review_decisions",
        "review_reconciliation",
        "application",
        "hr",
    }:
        raise CompanyStoreError(
            "Explicit review population/decision/reconciliation/application/HR sources required"
        )
    pop_row, pop = native["review_population"]
    decision_row, decisions = native["review_decisions"]
    recon_row, recon = native["review_reconciliation"]
    app_row, app = native["application"]
    hr_row, hr = native["hr"]
    for row, body in (
        native[k] for k in ("review_population", "review_decisions", "review_reconciliation")
    ):
        if body.get("control_id") != CONTROL or any(
            body.get(k) != pop.get(k) for k in ("id", "period_start", "period_end_exclusive")
        ):
            raise CompanyStoreError("Exact same native review campaign and period required")
        cutoff = datetime.fromisoformat(_time(pop["period_end_exclusive"]))
        if (
            datetime.fromisoformat(_time(row["event_at"])) < cutoff
            or datetime.fromisoformat(_time(row["available_at"])) < cutoff
        ):
            raise CompanyStoreError("Review event cannot precede declared cutoff")
    if datetime.fromisoformat(_time(pop.get("period_start"))) >= cutoff:
        raise CompanyStoreError("Native review period must increase")
    review_times = [
        datetime.fromisoformat(_time(r["event_at"])) for r in (pop_row, decision_row, recon_row)
    ]
    if review_times != sorted(review_times):
        raise CompanyStoreError("Native population decision reconciliation chronology invalid")
    if any(
        datetime.fromisoformat(_time(prior["available_at"]))
        > datetime.fromisoformat(_time(following["event_at"]))
        for prior, following in ((pop_row, decision_row), (decision_row, recon_row))
    ):
        raise CompanyStoreError("Native predecessor must be available before dependent review")
    if not isinstance(pop.get("members"), list) or sha(encoded(pop["members"])) != pop.get(
        "membership_sha256"
    ):
        raise CompanyStoreError("Exact review membership hash required")
    if (
        decisions.get("population_sha256") != pop_row["sha256"]
        or recon.get("population_sha256") != pop_row["sha256"]
    ):
        raise CompanyStoreError("Review records must reference exact original population")
    if (
        app.get("person_id") != recipe.subject_person_id
        or hr.get("person_id") != recipe.subject_person_id
        or app.get("cause_id") != hr.get("cause_id")
    ):
        raise CompanyStoreError("Same explicit subject and original causal record required")
    if any(datetime.fromisoformat(_time(r["available_at"])) >= cutoff for r in (app_row, hr_row)):
        raise CompanyStoreError("Original supporting state must precede review cutoff")
    query = pop.get("query")
    if (
        not isinstance(query, dict)
        or query.get("system") != "application"
        or _time(query.get("as_of_exclusive")) != _time(pop["period_end_exclusive"])
    ):
        raise CompanyStoreError("Population query must match exact application cutoff")
    if not isinstance(decisions.get("decisions"), list):
        raise CompanyStoreError("Explicit native decisions required")
    members = [
        m
        for m in pop["members"]
        if isinstance(m, dict) and m.get("person_id") == recipe.subject_person_id
    ]
    matches = [
        d
        for d in decisions.get("decisions", [])
        if isinstance(d, dict) and d.get("person_id") == recipe.subject_person_id
    ]
    if len(members) != 1 or len(matches) != 1:
        raise CompanyStoreError("One exact reviewed subject decision required")
    member, decision = members[0], matches[0]
    for value, keys in (
        (member, ("record", "version", "sha256")),
        (decision, ("source_record", "source_version", "source_sha256")),
    ):
        if type(value.get(keys[1])) is not int or [value.get(k) for k in keys] != [
            app_row[k] for k in ("record", "version", "sha256")
        ]:
            raise CompanyStoreError("Review subject must bind exact native application version")
    observed = _rights(app.get("rights"))
    removed = _rights(decision.get("remove_rights"))
    expected = _rights(decision.get("authorized_rights"))
    if (
        _rights(member.get("rights")) != observed
        or _rights(decision.get("observed_rights")) != observed
        or removed != observed - expected
        or decision.get("decision") != "REMOVE_EXCESS"
        or decision.get("removal_confirmation") != "NOT_YET_PERFORMED"
    ):
        raise CompanyStoreError("Exact outstanding removal and rights arithmetic required")
    authorization = hr.get("transfer_authorization")
    if (
        not isinstance(authorization, dict)
        or expected != {authorization.get("add_right")}
        or removed != {authorization.get("remove_right")}
    ):
        raise CompanyStoreError(
            "Explicit original local transfer authorization must support removal"
        )
    approved = datetime.fromisoformat(_time(authorization.get("approved_at")))
    effective = datetime.fromisoformat(_time(authorization.get("effective_at")))
    if not approved <= effective <= datetime.fromisoformat(_time(hr_row["event_at"])) < cutoff:
        raise CompanyStoreError("Original transfer authorization chronology is inconsistent")
    if datetime.fromisoformat(_time(app_row["event_at"])) >= cutoff:
        raise CompanyStoreError("Original application event must precede cutoff")
    hr_refs = recon.get("hr_sources", [])
    if not isinstance(hr_refs, list):
        raise CompanyStoreError("Explicit native HR references required")
    if not any(
        isinstance(r, dict)
        and type(r.get("version")) is int
        and all(r.get(k) == hr_row[k] for k in ("record", "version", "sha256"))
        for r in hr_refs
    ):
        raise CompanyStoreError("Reconciliation lacks exact selected HR source")
    missing = recon.get("missing_person_ids")
    if not isinstance(missing, list) or any(not isinstance(p, str) for p in missing):
        raise CompanyStoreError("Explicit recorded population limitation required")
    org = snapshot(repository, as_of=times[0].date().isoformat())
    assignment = next(a for a in org["control_assignments"] if a["control_id"] == CONTROL)
    owner, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    if owner == reviewer or decision.get("decision_by") != owner:
        raise CompanyStoreError("Scoped owner decision and distinct operating verifier required")
    pins = dict(org["source_sha256"])
    for name in (
        "enterprise/audit_suite/company_access_remediation_activity.py",
        "enterprise/audit_suite/company_lifecycle_activity.py",
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "docs/governance/ENTERPRISE_SUPPORT_SERVICES_AND_INDEPENDENCE.md",
    ):
        pins[name] = sha((repository / name).read_bytes())
    return originals, pin, native, decision, assignment, pins, times


def generate_pair(destination, *, repository, source_root, recipe: AccessRemediationRecipe):
    destination, repository = Path(destination).absolute(), Path(repository)
    if (
        destination.exists()
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or any(p.is_symlink() for p in (destination, *destination.parents))
        or destination.resolve().is_relative_to(Path(source_root).resolve())
    ):
        raise CompanyStoreError("New private continuation outside original source required")
    originals, pin, native, decision, assignment, pins, times = _prepare(
        repository, source_root, recipe
    )
    owner, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    start, request, execute, verify, escalate, correction, closeout = times
    refs = [
        {k: r[k] for k in FIELDS} | {"source_store_id": recipe.source_store_id} for r in originals
    ]
    common = {
        "classification": QUALIFICATION,
        "control_ids": [CONTROL],
        "boundary_id": "corporate",
        "campaign_id": recipe.campaign_id,
        "subject_person_id": recipe.subject_person_id,
        "source_records": refs,
        "source_versions_sha256": pin,
        "source_store_id": recipe.source_store_id,
        "parent_branch": originals[0]["branch"],
        "parent_campaign": native["review_population"][1]["id"],
        "owner_id": owner,
        "operating_reviewer_id": reviewer,
        "assignment_status": assignment["status"],
        "independent_assurance_contact_id": assignment["reviewer_person_id"],
        "independent_assurance": "NOT_PERFORMED",
        "supersession": "NONE_RETAINED_HISTORICAL_REVIEWS_NOT_REINTERPRETED",
        "recorded_unresolved_population_ids": native["review_reconciliation"][1][
            "missing_person_ids"
        ],
        "population_completeness": "NOT_ESTABLISHED_OR_REMEDIATED_BY_THIS_SLICE",
        "period_start": start.isoformat(),
        "period_end_exclusive": (closeout + timedelta(seconds=1)).isoformat(),
        "local_requirement_basis": recipe.local_requirement_basis,
        "runtime": "DATA_ONLY_LOCAL_ENTITLEMENTS_NO_HOST_OR_VENDOR_ACCESS",
    }
    recipe_pin = sha(encoded(asdict(recipe)))
    records = []
    with tempfile.TemporaryDirectory(
        prefix=".access-remediation-", dir=destination.parent
    ) as temporary:
        stage = Path(temporary)
        store = CompanyStore(stage)
        upstream = stage / "upstream"
        upstream.mkdir(mode=0o700)
        files = {}
        for i, row in enumerate(originals):
            p = upstream / f"{i:02d}.json"
            p.write_bytes(row["content"])
            p.chmod(0o600)
            files[str(p.relative_to(stage))] = row["sha256"]
        for index, branch in enumerate(recipe.branch_ids):
            for system in (
                "removal_requests",
                "permission_resolver",
                "entitlement_state",
                "execution_attempts",
                "validation_probes",
                "remediation_followup",
            ):
                store.register_system(
                    recipe.company_id,
                    branch,
                    system,
                    reviewer if system in ("validation_probes", "remediation_followup") else owner,
                )
            history = []
            versions = {}

            def add(
                system, record, when, body, *, versions=versions, branch=branch, history=history
            ):
                prior = versions.get((system, record), 0)
                row = store.append_version(
                    recipe.company_id,
                    branch,
                    system,
                    record,
                    expected_version=prior,
                    command_id="AR-"
                    + sha(encoded([recipe_pin, branch, system, record, prior + 1])),
                    event_at=when.isoformat(),
                    available_at=when.isoformat(),
                    content=encoded({**common, **body, "previous_events": list(history)}),
                    provenance={
                        "name": record + ".json",
                        "source_reference": record,
                        "control_ids": [CONTROL],
                        "classification": QUALIFICATION,
                        "source_sha256": pins,
                        "recipe_sha256": recipe_pin,
                    },
                )
                records.append(row)
                versions[system, record] = prior + 1
                history.append({k: row[k] for k in ("system", "record", "version", "sha256")})

            rights = decision["observed_rights"]
            removals = decision["remove_rights"]
            expected = decision["authorized_rights"]
            local = LocalEntitlements(recipe.subject_person_id, owner, reviewer, rights, removals)
            add(
                "entitlement_state",
                "APPLICATION",
                start,
                {
                    "rights": sorted(local.rights),
                    "state_origin": "EXACT_SELECTED_APPLICATION_PAYLOAD_BASELINE",
                },
            )
            add(
                "removal_requests",
                "REQUEST",
                request,
                {
                    "requested_by": owner,
                    "remove_rights": removals,
                    "authorized_rights": expected,
                    "authority": "EXPLICIT_RETAINED_LOCAL_OWNER_DECISION_NOT_CORPORATE_DELEGATION",
                },
            )
            mapping = {r: r for r in removals}
            if index == 1:
                mapping.pop(sorted(mapping)[0])
            add(
                "permission_resolver",
                "RESOLVER",
                request,
                {"mapping": mapping, "mapping_purpose": "LOCAL_EXECUTOR_PERMISSION_NAME_LOOKUP"},
            )
            result = local.execute(owner, recipe.subject_person_id, removals, mapping)
            add("execution_attempts", "EXECUTION", execute, {**result, "performed_by": owner})
            add(
                "entitlement_state",
                "APPLICATION",
                execute,
                {"rights": sorted(local.rights), "execution_status": result["status"]},
            )
            check = local.verify(reviewer, expected)
            add("validation_probes", "VALIDATION", verify, {**check, "performed_by": reviewer})
            add(
                "remediation_followup",
                "FOLLOWUP",
                escalate,
                {
                    "open_rights": check["excess_rights"],
                    "recorded_by": reviewer,
                    "status": "CORRECTION_REQUESTED"
                    if check["excess_rights"]
                    else "NO_FURTHER_REMOVAL_REQUIRED",
                    "unresolved_population_separate": True,
                },
            )
            mapping = {r: r for r in removals}
            add(
                "permission_resolver",
                "RESOLVER",
                correction,
                {
                    "mapping": mapping,
                    "change_basis": "CORRECTED_LOOKUP"
                    if check["excess_rights"]
                    else "REAFFIRMED_NO_CHANGE",
                },
            )
            result = local.execute(owner, recipe.subject_person_id, removals, mapping)
            add(
                "execution_attempts",
                "EXECUTION",
                correction,
                {**result, "performed_by": owner, "prior_attempt_preserved": True},
            )
            add(
                "entitlement_state",
                "APPLICATION",
                correction,
                {"rights": sorted(local.rights), "execution_status": result["status"]},
            )
            add(
                "validation_probes",
                "VALIDATION",
                closeout,
                {
                    **local.verify(reviewer, expected),
                    "performed_by": reviewer,
                    "scope": "LOCAL_REMOVAL_CHECK_ONLY_NOT_WHOLE_REVIEW_CLOSURE",
                },
            )
        if read_inputs(source_root, recipe.source_refs)[1] != pin:
            raise CompanyStoreError("Selected original sources changed during continuation")
        receipt = {
            "status": "LOCAL_ACCESS_REMEDIATION_CREATED",
            "recipe": asdict(recipe),
            "recipe_sha256": recipe_pin,
            "source_sha256": pins,
            "source_versions_sha256": pin,
            "source_metadata": [{k: v for k, v in r.items() if k != "content"} for r in originals],
            "upstream_files": files,
            "records": records,
            "assignment": assignment,
            "qualification": QUALIFICATION,
            "audit_created": False,
            "grants_created": False,
            "old_quarterly_sources_unchanged": True,
            "population_completeness": "NOT_ESTABLISHED",
            "professional_validation": "NOT_PERFORMED",
        }
        p = stage / "SOURCE_RECEIPT.json"
        p.write_bytes(encoded(receipt))
        p.chmod(0o600)
        publish(stage, destination)
    return receipt
