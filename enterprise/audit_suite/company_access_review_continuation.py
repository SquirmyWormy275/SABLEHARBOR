"""Declared-subject next-quarter review from exact local removal operations."""

import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_access_remediation_activity import QUALIFICATION as REMOVAL_QUALIFICATION
from .company_access_remediation_activity import LocalEntitlements
from .company_lifecycle_activity import FIELDS, LifecycleSourceRef, read_inputs
from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .inference import _json as strict_json
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

CONTROL = "SH-IAM-007"
QUALIFICATION = "DECLARED_SUBJECT_LOCAL_REVIEW_CONTINUATION_NOT_WHOLE_QUARTER_OPERATION"
AccessReviewSourceRef = LifecycleSourceRef


@dataclass(frozen=True)
class ReviewContinuationSourceGroup:
    id: str
    source_store_id: str
    source_refs: tuple[AccessReviewSourceRef, ...]
    source_versions_sha256: str


@dataclass(frozen=True)
class AccessReviewContinuationRecipe:
    company_id: str
    branch_id: str
    campaign_id: str
    source_groups: tuple[ReviewContinuationSourceGroup, ...]
    period_start: str
    period_end_exclusive: str
    population_at: str
    decision_at: str
    reconciliation_at: str
    local_requirement_basis: str


def require(value, message):
    if not value:
        raise CompanyStoreError(message)


def instant(value):
    return datetime.fromisoformat(_time(value))


def names(value):
    require(
        isinstance(value, list)
        and len(value) <= 64
        and all(isinstance(v, str) and v for v in value)
        and len(value) == len(set(value)),
        "Distinct bounded native names required",
    )
    return set(value)


def pin(row):
    return {k: row[k] for k in FIELDS}


CHAIN = (
    ("entitlement_state", "APPLICATION", 1),
    ("removal_requests", "REQUEST", 1),
    ("permission_resolver", "RESOLVER", 1),
    ("execution_attempts", "EXECUTION", 1),
    ("entitlement_state", "APPLICATION", 2),
    ("validation_probes", "VALIDATION", 1),
    ("remediation_followup", "FOLLOWUP", 1),
    ("permission_resolver", "RESOLVER", 2),
    ("execution_attempts", "EXECUTION", 2),
    ("entitlement_state", "APPLICATION", 3),
    ("validation_probes", "VALIDATION", 2),
)


def prepare(repository, roots, recipe):
    for value in (recipe.company_id, recipe.branch_id, recipe.campaign_id):
        _id(value)
    group_ids = {"identity", "remediation_initial", "remediation_final"}
    require(
        isinstance(recipe.source_groups, tuple)
        and len(recipe.source_groups) == 3
        and all(isinstance(g, ReviewContinuationSourceGroup) for g in recipe.source_groups)
        and {g.id for g in recipe.source_groups} == group_ids
        and isinstance(roots, dict)
        and set(roots) == group_ids,
        "Three explicit native source groups required",
    )
    require(
        Path(roots["remediation_initial"]).resolve() == Path(roots["remediation_final"]).resolve()
        and Path(roots["identity"]).resolve() != Path(roots["remediation_initial"]).resolve(),
        "One original identity store and one separate removal store required",
    )
    require(
        isinstance(recipe.local_requirement_basis, str)
        and 1 <= len(recipe.local_requirement_basis.strip()) <= 2000,
        "Explicit bounded local review requirements required",
    )
    start, stop, exported, decided, reconciled = [
        instant(getattr(recipe, k))
        for k in (
            "period_start",
            "period_end_exclusive",
            "population_at",
            "decision_at",
            "reconciliation_at",
        )
    ]
    month = start.month + 3
    next_quarter = start.replace(year=start.year + (month > 12), month=(month - 1) % 12 + 1)
    require(
        start.month in (1, 4, 7, 10)
        and start.day == 1
        and (start.hour, start.minute, start.second, start.microsecond) == (0, 0, 0, 0)
        and stop == next_quarter
        and stop <= exported < decided < reconciled
        and reconciled <= stop + timedelta(days=7),
        "One UTC calendar quarter and dated post-period review sequence required",
    )
    groups, all_rows = {}, []
    for group in recipe.source_groups:
        _id(group.source_store_id)
        rows, digest = read_inputs(roots[group.id], group.source_refs)
        require(digest == group.source_versions_sha256, "Selected source metadata differs")
        require(
            len(rows) == (5 if group.id != "remediation_initial" else 6),
            "Exact five/six/five native group membership required",
        )
        require(
            len({(r["company"], r["branch"]) for r in rows}) == 1,
            "One native company and branch per group required",
        )
        for row in rows:
            require(
                row["company"] == recipe.company_id
                and row["branch"] != recipe.branch_id
                and row["origin"] == "AUTHORED_TRAINING_SOURCE"
                and row["event_at"] is not None
                and instant(row["event_at"]) <= instant(row["available_at"]) <= exported,
                "Known original availability and separate continuation branch required",
            )
            try:
                row["body"] = strict_json(row["content"])
            except (ValueError, UnicodeError) as exc:
                raise CompanyStoreError("Strict finite native JSON required") from exc
            require(isinstance(row["body"], dict), "Native source object required")
        groups[group.id] = (group, rows)
        all_rows.extend(rows)
    first_group, first_rows = groups["remediation_initial"]
    last_group, last_rows = groups["remediation_final"]
    require(
        first_group.source_store_id == last_group.source_store_id
        and first_rows[0]["branch"] == last_rows[0]["branch"],
        "Removal groups must retain same native branch and producer label",
    )
    parent_group, parent_rows = groups["identity"]
    parent = {r["system"]: r for r in parent_rows}
    require(
        set(parent)
        == {"review_population", "review_decisions", "review_reconciliation", "application", "hr"},
        "Exact prior review/application/HR roles required",
    )
    pop = parent["review_population"]["body"]
    decisions = parent["review_decisions"]["body"]
    recon = parent["review_reconciliation"]["body"]
    app, hr = parent["application"]["body"], parent["hr"]["body"]
    subject = app.get("person_id")
    require(
        isinstance(subject, str)
        and subject
        and hr.get("person_id") == subject
        and app.get("cause_id") == hr.get("cause_id"),
        "Same explicitly correlated subject required",
    )
    require(
        instant(pop.get("period_end_exclusive")) == start
        and instant(pop.get("period_start")) < start,
        "Continuation must follow exact parent review period",
    )
    for row in (parent["review_decisions"], parent["review_reconciliation"]):
        require(
            row["body"].get("control_id") == CONTROL
            and all(
                row["body"].get(k) == pop.get(k)
                for k in ("id", "period_start", "period_end_exclusive")
            )
            and row["body"].get("population_sha256") == parent["review_population"]["sha256"],
            "Exact prior review linkage required",
        )
    require(
        pop.get("control_id") == CONTROL
        and isinstance(pop.get("members"), list)
        and sha(encoded(pop["members"])) == pop.get("membership_sha256"),
        "Exact prior membership required",
    )
    query = pop.get("query")
    require(
        isinstance(query, dict)
        and query.get("system") == "application"
        and instant(query.get("as_of_exclusive")) == start,
        "Exact prior query cutoff required",
    )
    require(isinstance(decisions.get("decisions"), list), "Native review decisions required")
    members = [m for m in pop["members"] if isinstance(m, dict) and m.get("person_id") == subject]
    matches = [
        d for d in decisions["decisions"] if isinstance(d, dict) and d.get("person_id") == subject
    ]
    require(len(members) == len(matches) == 1, "One exact declared subject decision required")
    decision = matches[0]
    for value, keys in (
        (members[0], ("record", "version", "sha256")),
        (decision, ("source_record", "source_version", "source_sha256")),
    ):
        require(
            type(value.get(keys[1])) is int
            and [value.get(k) for k in keys]
            == [parent["application"][k] for k in ("record", "version", "sha256")],
            "Review must bind exact original application version",
        )
    auth = hr.get("transfer_authorization")
    require(isinstance(auth, dict), "Explicit original transfer authorization required")
    expected, removals, observed = (
        names(decision.get("authorized_rights")),
        names(decision.get("remove_rights")),
        names(app.get("rights")),
    )
    require(
        expected == {auth.get("add_right")}
        and removals == {auth.get("remove_right")}
        and observed == names(decision.get("observed_rights")) == names(members[0].get("rights"))
        and removals == observed - expected
        and decision.get("decision") == "REMOVE_EXCESS",
        "Exact original authorization and removal arithmetic required",
    )
    require(all(isinstance(m, dict) for m in pop["members"]), "Typed prior members required")
    missing = names(recon.get("missing_person_ids"))
    unsupported = {
        m.get("person_id")
        for m in pop["members"]
        if isinstance(m, dict) and m.get("person_id") != subject
    }
    require(
        all(isinstance(p, str) and p for p in unsupported),
        "Typed prior population identities required",
    )
    chain_index = {(r["system"], r["record"], r["version"]): r for r in first_rows + last_rows}
    require(set(chain_index) == set(CHAIN), "Complete eleven-original removal chain required")
    chain = [chain_index[key] for key in CHAIN]
    request = chain[1]["body"]
    owner, reviewer = request.get("owner_id"), request.get("operating_reviewer_id")
    require(decision.get("decision_by") == owner, "Original decision and removal owner must match")
    local = LocalEntitlements(subject, owner, reviewer, sorted(observed), sorted(removals))
    require(
        names(request.get("remove_rights")) == removals
        and names(request.get("authorized_rights")) == expected
        and request.get("requested_by") == owner,
        "Exact authorized removal request required",
    )
    require(
        all(instant(r["available_at"]) <= instant(chain[0]["event_at"]) for r in parent_rows),
        "Original parent support unavailable at removal baseline",
    )
    prior_review = [
        parent[k] for k in ("review_population", "review_decisions", "review_reconciliation")
    ]
    for earlier, later in zip(prior_review, prior_review[1:], strict=False):
        require(
            instant(earlier["available_at"]) <= instant(later["event_at"]),
            "Parent review predecessor unavailable",
        )
    require(
        instant(auth.get("approved_at"))
        <= instant(auth.get("effective_at"))
        <= instant(parent["hr"]["event_at"])
        < start
        and instant(parent["application"]["available_at"]) < start,
        "Parent authorization and application chronology invalid",
    )
    hr_links = recon.get("hr_sources")
    require(
        isinstance(hr_links, list)
        and any(
            isinstance(r, dict)
            and type(r.get("version")) is int
            and all(r.get(k) == parent["hr"][k] for k in ("record", "version", "sha256"))
            for r in hr_links
        ),
        "Parent reconciliation lacks exact HR original",
    )
    history = []
    for row in chain:
        body = row["body"]
        require(
            body.get("classification") == REMOVAL_QUALIFICATION
            and body.get("control_ids") == [CONTROL]
            and body.get("subject_person_id") == subject
            and body.get("owner_id") == owner
            and body.get("operating_reviewer_id") == reviewer
            and body.get("parent_campaign") == pop.get("id")
            and body.get("parent_branch") == parent_rows[0]["branch"]
            and body.get("source_versions_sha256") == parent_group.source_versions_sha256
            and body.get("source_store_id") == parent_group.source_store_id
            and all(
                body.get(k) == request.get(k)
                for k in ("campaign_id", "period_start", "period_end_exclusive")
            )
            and body.get("recorded_unresolved_population_ids") == recon.get("missing_person_ids"),
            "Exact qualified removal lineage required",
        )
        links = body.get("source_records")
        require(
            isinstance(links, list)
            and len(links) == 5
            and sorted(encoded({k: r.get(k) for k in FIELDS}) for r in links if isinstance(r, dict))
            == sorted(encoded(pin(r)) for r in parent_rows)
            and all(r.get("source_store_id") == parent_group.source_store_id for r in links),
            "Removal must retain exact five parent pins and producer label",
        )
        require(
            instant(body.get("period_start"))
            <= instant(row["event_at"])
            <= instant(row["available_at"])
            < instant(body.get("period_end_exclusive")),
            "Native removal event must lie within its declared activity period",
        )
        previous = body.get("previous_events")
        require(
            isinstance(previous, list)
            and len(previous) <= len(CHAIN)
            and all(
                isinstance(link, dict)
                and set(link) == {"system", "record", "version", "sha256"}
                and type(link["version"]) is int
                and link["version"] > 0
                and isinstance(link["sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", link["sha256"]) is not None
                for link in previous
            ),
            "Exact typed prior-event native pins required",
        )
        for link in previous:
            _id(link["system"])
            _id(link["record"])
        require(previous == history, "Complete exact prior-event chain required")
        for prior in chain[: len(history)]:
            require(
                instant(prior["available_at"]) <= instant(row["event_at"]),
                "Predecessor unavailable at dependent event",
            )
        history.append({k: row[k] for k in ("system", "record", "version", "sha256")})
    require(
        names(chain[0]["body"].get("rights")) == observed,
        "Exact original entitlement baseline required",
    )
    checks = []
    for resolver, execution, state, verification in (
        (chain[2], chain[3], chain[4], chain[5]),
        (chain[7], chain[8], chain[9], chain[10]),
    ):
        outcome = local.execute(owner, subject, sorted(removals), resolver["body"].get("mapping"))
        require(
            execution["body"].get("performed_by") == owner
            and all(encoded(execution["body"].get(k)) == encoded(v) for k, v in outcome.items()),
            "Native execution must match actual authorized local state transition",
        )
        require(
            names(state["body"].get("rights")) == local.rights, "Native resulting rights mismatch"
        )
        probe = local.verify(reviewer, sorted(expected))
        require(
            verification["body"].get("performed_by") == reviewer
            and all(encoded(verification["body"].get(k)) == encoded(v) for k, v in probe.items()),
            "Native verification must match independent local probes",
        )
        checks.append(probe)
    followup = chain[6]["body"]
    require(
        names(followup.get("open_rights")) == set(checks[0]["excess_rights"])
        and followup.get("recorded_by") == reviewer,
        "Followup must preserve original unresolved rights",
    )
    require(
        instant(chain[-1]["available_at"]) < stop,
        "Terminal local state must precede new review cutoff",
    )
    org = snapshot(repository, as_of=exported.date().isoformat())
    assignment = next(a for a in org["control_assignments"] if a["control_id"] == CONTROL)
    return (
        groups,
        all_rows,
        chain[-2],
        checks[-1],
        expected,
        subject,
        missing,
        unsupported,
        assignment,
        org["source_sha256"],
    )


def generate(destination, *, repository, source_roots, recipe: AccessReviewContinuationRecipe):
    destination, repository = Path(destination).absolute(), Path(repository)
    require(
        not destination.exists()
        and destination.parent.is_dir()
        and not destination.parent.stat().st_mode & 0o077
        and not any(p.is_symlink() for p in (destination, *destination.parents))
        and isinstance(source_roots, dict)
        and not any(
            destination.resolve().is_relative_to(Path(p).resolve()) for p in source_roots.values()
        ),
        "New private destination outside original stores required",
    )
    groups, rows, terminal, check, expected, subject, missing, unsupported, assignment, org_pins = (
        prepare(repository, source_roots, recipe)
    )
    owner, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    require(owner and reviewer and owner != reviewer, "Distinct scoped review actors required")
    pins = {
        **org_pins,
        **{
            name: sha((repository / name).read_bytes())
            for name in (
                "enterprise/audit_suite/company_access_review_continuation.py",
                "enterprise/audit_suite/company_access_remediation_activity.py",
                "enterprise/audit_suite/company_lifecycle_activity.py",
                "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
                "enterprise/audit_suite/inference.py",
                "enterprise/audit_suite/company_store.py",
                "enterprise/audit_suite/organization.py",
                "enterprise/audit_suite/operating_source_bridge.py",
                "enterprise/audit_suite/private_publication.py",
            )
        },
    }
    recipe_sha = sha(encoded(asdict(recipe)))
    provenance = {
        "control_ids": [CONTROL],
        "classification": QUALIFICATION,
        "source_sha256": pins,
        "recipe_sha256": recipe_sha,
        "scoped_assignment": assignment,
    }
    common = {
        "classification": QUALIFICATION,
        "control_id": CONTROL,
        "boundary_id": "corporate",
        "id": recipe.campaign_id,
        "period_start": _time(recipe.period_start),
        "period_end_exclusive": _time(recipe.period_end_exclusive),
        "source_groups": [
            {
                "id": g.id,
                "source_store_id": g.source_store_id,
                "source_refs": [pin(r) for r in rs],
                "source_versions_sha256": g.source_versions_sha256,
            }
            for g, rs in groups.values()
        ],
        "state_basis": (
            "EXACT_SELECTED_LOCAL_STATE_CARRIED_FORWARD_NO_INTERVENING_ACTIVITY_SUPPLIED"
        ),
        "population_scope": "DECLARED_SUBJECT_ONLY_NOT_WORKFORCE_CENSUS",
        "unresolved_parent_missing_person_ids": sorted(missing),
        "unsupported_prior_population_person_ids": sorted(unsupported),
        "whole_quarter_operation": "NOT_ESTABLISHED",
        "professional_assurance": "NOT_PERFORMED",
        "local_requirement_basis": recipe.local_requirement_basis,
    }
    with tempfile.TemporaryDirectory(
        prefix=".review-continuation-", dir=destination.parent
    ) as temporary:
        stage = Path(temporary)
        store = CompanyStore(stage)
        (stage / "upstream").mkdir(mode=0o700)
        for index, row in enumerate(rows):
            path = stage / "upstream" / f"{index:02d}.json"
            path.write_bytes(row["content"])
            path.chmod(0o600)
        records = []

        def emit(system, at, body):
            store.register_system(
                recipe.company_id,
                recipe.branch_id,
                system,
                reviewer if system == "review_reconciliation" else owner,
            )
            return store.append_version(
                recipe.company_id,
                recipe.branch_id,
                system,
                recipe.campaign_id,
                expected_version=0,
                command_id=sha(encoded([recipe_sha, system])),
                event_at=at,
                available_at=at,
                content=encoded({**common, **body}),
                provenance={
                    **provenance,
                    "name": system + ".json",
                    "source_reference": recipe.campaign_id,
                },
            )

        member = {
            "person_id": subject,
            "rights": check["observed_rights"],
            "state_source": pin(terminal),
        }
        pop = emit(
            "review_population",
            recipe.population_at,
            {
                "members": [member],
                "membership_sha256": sha(encoded([member])),
                "exported_by": owner,
                "query": {
                    "system": "EXPLICIT_LOCAL_REMOVAL_CONTINUATION",
                    "as_of_exclusive": _time(recipe.period_end_exclusive),
                    "subject_ids": [subject],
                },
            },
        )
        records.append(pop)
        rights = set(check["observed_rights"])
        excess = sorted(rights - expected)
        decision = {
            "person_id": subject,
            "observed_rights": sorted(rights),
            "authorized_rights": sorted(expected),
            "remove_rights": excess,
            "decision": (
                "UNRESOLVED_MISSING_AUTHORIZED"
                if expected - rights
                else "REMOVE_EXCESS"
                if excess
                else "RETAIN_AUTHORIZED"
            ),
            "decision_by": owner,
            "state_source": pin(terminal),
            "missing_authorized_rights": sorted(expected - rights),
        }
        decided = emit(
            "review_decisions",
            recipe.decision_at,
            {"population_sha256": pop["sha256"], "decisions": [decision]},
        )
        records.append(decided)
        records.append(
            emit(
                "review_reconciliation",
                recipe.reconciliation_at,
                {
                    "population_sha256": pop["sha256"],
                    "decisions_sha256": decided["sha256"],
                    "reviewed_by": reviewer,
                    "declared_subject_ids": [subject],
                    "export_person_ids": [subject],
                    "unresolved_person_ids": sorted(missing | unsupported),
                    "status": "UNRESOLVED_COHORT_LIMITATIONS"
                    if missing | unsupported
                    else "DECLARED_SUBJECT_RECONCILED",
                    "whole_review_closed": False,
                },
            )
        )
        for group, _original_rows in groups.values():
            require(
                read_inputs(source_roots[group.id], group.source_refs)[1]
                == group.source_versions_sha256,
                "Original inputs changed before publication",
            )
        require(
            all(sha((repository / name).read_bytes()) == value for name, value in pins.items()),
            "Implementation or scoped source pins changed before publication",
        )
        receipt = {
            "status": "DECLARED_SUBJECT_REVIEW_CREATED",
            "recipe": asdict(recipe),
            "recipe_sha256": recipe_sha,
            "source_sha256": pins,
            "records": records,
            "qualification": QUALIFICATION,
            "audit_created": False,
            "grants_created": False,
            "professional_assurance": "NOT_PERFORMED",
        }
        path = stage / "SOURCE_RECEIPT.json"
        path.write_bytes(encoded(receipt))
        path.chmod(0o600)
        publish(stage, destination)
    return receipt
