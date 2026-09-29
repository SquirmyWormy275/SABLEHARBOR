"""One adjacent declared-subject review after a verified local continuation."""

import tempfile
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path

from . import company_access_review_continuation as prior
from .company_lifecycle_activity import read_inputs
from .company_store import CompanyStore, _id, _time
from .inference import _json
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish

QUALIFICATION = "ADJACENT_DECLARED_SUBJECT_REVIEW_NOT_WHOLE_QUARTER_OPERATION"


@dataclass(frozen=True)
class AccessReviewSuccessorRecipe:
    prior_recipe: prior.AccessReviewContinuationRecipe
    prior_review: prior.ReviewContinuationSourceGroup
    company_id: str
    branch_id: str
    campaign_id: str
    period_start: str
    period_end_exclusive: str
    population_at: str
    decision_at: str
    reconciliation_at: str
    local_requirement_basis: str


def _common(recipe, groups, missing, unsupported, qualification):
    return {
        "classification": qualification,
        "control_id": prior.CONTROL,
        "boundary_id": "corporate",
        "id": recipe.campaign_id,
        "period_start": _time(recipe.period_start),
        "period_end_exclusive": _time(recipe.period_end_exclusive),
        "source_groups": [
            {
                "id": g.id,
                "source_store_id": g.source_store_id,
                "source_refs": [prior.pin(r) for r in rows],
                "source_versions_sha256": g.source_versions_sha256,
            }
            for g, rows in groups.values()
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


def _bodies(recipe, common, terminal, check, expected, subject, missing, unsupported, assignment):
    owner = assignment["primary_person_id"]
    reviewer = assignment["operating_reviewer_person_id"]
    prior.require(
        owner and reviewer and owner != reviewer, "Distinct scoped review actors required"
    )
    member = {
        "person_id": subject,
        "rights": check["observed_rights"],
        "state_source": prior.pin(terminal),
    }
    population = {
        **common,
        "members": [member],
        "membership_sha256": sha(encoded([member])),
        "exported_by": owner,
        "query": {
            "system": "EXPLICIT_LOCAL_REMOVAL_CONTINUATION",
            "as_of_exclusive": _time(recipe.period_end_exclusive),
            "subject_ids": [subject],
        },
    }
    rights = set(check["observed_rights"])
    excess = sorted(rights - expected)
    decision = {
        "person_id": subject,
        "observed_rights": sorted(rights),
        "authorized_rights": sorted(expected),
        "remove_rights": excess,
        "decision": "UNRESOLVED_MISSING_AUTHORIZED"
        if expected - rights
        else "REMOVE_EXCESS"
        if excess
        else "RETAIN_AUTHORIZED",
        "decision_by": owner,
        "state_source": prior.pin(terminal),
        "missing_authorized_rights": sorted(expected - rights),
    }
    decisions = {**common, "population_sha256": sha(encoded(population)), "decisions": [decision]}
    reconciliation = {
        **common,
        "population_sha256": sha(encoded(population)),
        "decisions_sha256": sha(encoded(decisions)),
        "reviewed_by": reviewer,
        "declared_subject_ids": [subject],
        "export_person_ids": [subject],
        "unresolved_person_ids": sorted(missing | unsupported),
        "status": "UNRESOLVED_COHORT_LIMITATIONS"
        if missing | unsupported
        else "DECLARED_SUBJECT_RECONCILED",
        "whole_review_closed": False,
    }
    return {
        "review_population": population,
        "review_decisions": decisions,
        "review_reconciliation": reconciliation,
    }


def prepare(repository, source_roots, recipe):
    prior.require(
        isinstance(recipe, AccessReviewSuccessorRecipe)
        and isinstance(recipe.prior_recipe, prior.AccessReviewContinuationRecipe)
        and isinstance(recipe.prior_review, prior.ReviewContinuationSourceGroup),
        "Typed successor recipe required",
    )
    for value in (recipe.company_id, recipe.branch_id, recipe.campaign_id):
        _id(value)
    prior.require(
        isinstance(source_roots, dict)
        and set(source_roots)
        == {"identity", "remediation_initial", "remediation_final", "prior_review"},
        "Four exact source roots required",
    )
    prior.require(
        recipe.company_id == recipe.prior_recipe.company_id
        and recipe.branch_id != recipe.prior_recipe.branch_id
        and recipe.campaign_id != recipe.prior_recipe.campaign_id,
        "Distinct same-company successor identity required",
    )
    prior.require(
        isinstance(recipe.local_requirement_basis, str)
        and 1 <= len(recipe.local_requirement_basis.strip()) <= 2000,
        "Explicit local continuation basis required",
    )
    prior.require(
        Path(source_roots["prior_review"]).resolve()
        not in {
            Path(source_roots[k]).resolve()
            for k in ("identity", "remediation_initial", "remediation_final")
        },
        "Separate prior review original store required",
    )
    start, stop, exported, decided, reconciled = [
        prior.instant(getattr(recipe, k))
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
    prior.require(
        start == prior.instant(recipe.prior_recipe.period_end_exclusive)
        and start.month in (1, 4, 7, 10)
        and start.day == 1
        and (start.hour, start.minute, start.second, start.microsecond) == (0, 0, 0, 0)
        and stop == next_quarter
        and stop <= exported < decided < reconciled
        and reconciled <= stop + timedelta(days=7),
        "Exactly adjacent quarter with post-period review required",
    )
    original_roots = {k: v for k, v in source_roots.items() if k != "prior_review"}
    prepared = prior.prepare(repository, original_roots, recipe.prior_recipe)
    (
        groups,
        originals,
        terminal,
        check,
        expected,
        subject,
        missing,
        unsupported,
        assignment,
        org_pins,
    ) = prepared
    g = recipe.prior_review
    _id(g.source_store_id)
    prior.require(
        g.id == "prior_review" and isinstance(g.source_refs, tuple) and len(g.source_refs) == 3,
        "Exactly three prior review native refs required",
    )
    rows, digest = read_inputs(source_roots["prior_review"], g.source_refs)
    prior.require(digest == g.source_versions_sha256, "Prior review metadata differs")
    common = _common(recipe.prior_recipe, groups, missing, unsupported, prior.QUALIFICATION)
    bodies = _bodies(
        recipe.prior_recipe,
        common,
        terminal,
        check,
        expected,
        subject,
        missing,
        unsupported,
        assignment,
    )
    prior.require({r["system"] for r in rows} == set(bodies), "Exact prior review systems required")
    times = dict(
        zip(
            bodies,
            (
                recipe.prior_recipe.population_at,
                recipe.prior_recipe.decision_at,
                recipe.prior_recipe.reconciliation_at,
            ),
            strict=True,
        )
    )
    recipe_sha = sha(encoded(asdict(recipe.prior_recipe)))
    for row in rows:
        prior.require(
            row["company"] == recipe.company_id
            and row["branch"] == recipe.prior_recipe.branch_id
            and row["record"] == recipe.prior_recipe.campaign_id
            and type(row["version"]) is int
            and row["version"] == 1,
            "Exact prior review native identity required",
        )
        body = _json(row["content"])
        prior.require(
            encoded(body) == encoded(bodies[row["system"]]),
            "Prior review must match recomputed original-chain rights and unresolved scope",
        )
        prior.require(
            row["event_at"] == _time(times[row["system"]])
            and row["available_at"] == row["event_at"]
            and prior.instant(row["available_at"]) < stop,
            "Prior review exact chronology required",
        )
        provenance = _json(row["provenance"])
        prior.require(
            row["origin"] == "AUTHORED_TRAINING_SOURCE"
            and provenance.get("source_reference") == recipe.prior_recipe.campaign_id
            and provenance.get("name") == row["system"] + ".json"
            and provenance.get("recipe_sha256") == recipe_sha
            and provenance.get("classification") == prior.QUALIFICATION
            and encoded(provenance.get("scoped_assignment")) == encoded(assignment)
            and provenance.get("control_ids") == [prior.CONTROL],
            "Prior review attributed recipe and scoped actors required",
        )
    current = snapshot(repository, as_of=exported.date().isoformat())
    current_assignment = next(
        a for a in current["control_assignments"] if a["control_id"] == prior.CONTROL
    )
    return prepared, rows, current_assignment, {**org_pins, **current["source_sha256"]}


def generate(destination, *, repository, source_roots, recipe: AccessReviewSuccessorRecipe):
    destination, repository = Path(destination).absolute(), Path(repository).absolute()
    prior.require(
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
    prepared, rows, assignment, org_pins = prepare(repository, source_roots, recipe)
    groups, originals, terminal, check, expected, subject, missing, unsupported, _, _ = prepared
    code_names = (
        "company_access_review_successor.py",
        "company_access_review_continuation.py",
        "company_access_remediation_activity.py",
        "company_lifecycle_activity.py",
        "company_store.py",
        "inference.py",
        "operating_source_bridge.py",
        "organization.py",
        "private_publication.py",
    )
    pins = {
        **org_pins,
        **{
            "enterprise/audit_suite/" + n: sha(
                (repository / "enterprise/audit_suite" / n).read_bytes()
            )
            for n in code_names
        },
    }
    recipe_sha = sha(encoded(asdict(recipe)))
    common = _common(recipe, groups, missing, unsupported, QUALIFICATION)
    common["predecessor_review"] = {
        "source_store_id": recipe.prior_review.source_store_id,
        "source_versions_sha256": recipe.prior_review.source_versions_sha256,
        "source_refs": [prior.pin(r) for r in rows],
        "period_start": _time(recipe.prior_recipe.period_start),
        "period_end_exclusive": _time(recipe.prior_recipe.period_end_exclusive),
    }
    bodies = _bodies(
        recipe, common, terminal, check, expected, subject, missing, unsupported, assignment
    )
    times = (recipe.population_at, recipe.decision_at, recipe.reconciliation_at)
    with tempfile.TemporaryDirectory(prefix=".review-successor-", dir=destination.parent) as temp:
        stage = Path(temp)
        store = CompanyStore(stage)
        (stage / "upstream").mkdir(mode=0o700)
        for index, row in enumerate([*originals, *rows]):
            p = stage / "upstream" / f"{index:02d}.json"
            p.write_bytes(row["content"])
            p.chmod(0o600)
        records = []
        for (system, body), at in zip(bodies.items(), times, strict=True):
            owner = (
                assignment["operating_reviewer_person_id"]
                if system == "review_reconciliation"
                else assignment["primary_person_id"]
            )
            store.register_system(recipe.company_id, recipe.branch_id, system, owner)
            records.append(
                store.append_version(
                    recipe.company_id,
                    recipe.branch_id,
                    system,
                    recipe.campaign_id,
                    expected_version=0,
                    command_id=sha(encoded([recipe_sha, system])),
                    event_at=at,
                    available_at=at,
                    content=encoded(body),
                    provenance={
                        "control_ids": [prior.CONTROL],
                        "classification": QUALIFICATION,
                        "source_sha256": pins,
                        "recipe_sha256": recipe_sha,
                        "scoped_assignment": assignment,
                        "name": system + ".json",
                        "source_reference": recipe.campaign_id,
                    },
                )
            )
        for g in (*recipe.prior_recipe.source_groups, recipe.prior_review):
            prior.require(
                read_inputs(source_roots[g.id], g.source_refs)[1] == g.source_versions_sha256,
                "Original inputs changed before publication",
            )
        prior.require(
            all(sha((repository / name).read_bytes()) == value for name, value in pins.items()),
            "Implementation or scoped sources changed before publication",
        )
        receipt = {
            "status": "ADJACENT_DECLARED_SUBJECT_REVIEW_CREATED",
            "recipe": asdict(recipe),
            "recipe_sha256": recipe_sha,
            "source_sha256": pins,
            "records": records,
            "qualification": QUALIFICATION,
            "audit_created": False,
            "grants_created": False,
            "professional_assurance": "NOT_PERFORMED",
        }
        p = stage / "SOURCE_RECEIPT.json"
        p.write_bytes(encoded(receipt))
        p.chmod(0o600)
        publish(stage, destination)
    return receipt
