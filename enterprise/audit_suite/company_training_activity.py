"""Paired local training operations; no audit input, employment assertion or rubric."""

import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError, _id, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot
from .private_publication import publish


@dataclass(frozen=True)
class TrainingMember:
    person_id: str
    role_id: str


@dataclass(frozen=True)
class TrainingCourse:
    course_id: str
    title: str
    role_ids: tuple[str, ...]


@dataclass(frozen=True)
class TrainingRecipe:
    company_id: str
    on_time_branch: str
    late_branch: str
    cycle_id: str
    period_start: str
    period_end_exclusive: str
    due_at: str
    followup_at: str
    late_completed_at: str
    cohort: tuple[TrainingMember, ...]
    courses: tuple[TrainingCourse, ...]
    late_person_id: str
    late_course_id: str
    local_requirement_basis: str


def generate_pair(destination: Path, *, repository: Path, recipe: TrainingRecipe):
    """Stage and publish into a NEW private directory; existing stores fail closed."""
    destination = Path(destination).absolute()
    if (
        any(p.is_symlink() for p in (destination, *destination.parents))
        or not destination.parent.is_dir()
        or destination.parent.stat().st_mode & 0o077
        or destination.exists()
    ):
        raise CompanyStoreError("New training store under existing private parent required")
    for value in (recipe.company_id, recipe.on_time_branch, recipe.late_branch, recipe.cycle_id):
        _id(value)
    if recipe.on_time_branch == recipe.late_branch:
        raise CompanyStoreError("Distinct local branches required")
    start, end, due, followup, late = [
        datetime.fromisoformat(_time(v))
        for v in (
            recipe.period_start,
            recipe.period_end_exclusive,
            recipe.due_at,
            recipe.followup_at,
            recipe.late_completed_at,
        )
    ]
    checkpoint = due + timedelta(hours=1)
    closeout = late + timedelta(hours=1)
    if not start + timedelta(days=3) < due < checkpoint < followup < late < closeout < end:
        raise CompanyStoreError(
            "Assignment, due, monitoring, follow-up and late completion must fit period"
        )
    if (end - start).days > 93:
        raise CompanyStoreError("This adapter covers one bounded cycle, at most93 days")
    if (
        not isinstance(recipe.cohort, tuple)
        or not 2 <= len(recipe.cohort) <= 24
        or not isinstance(recipe.courses, tuple)
        or not 1 <= len(recipe.courses) <= 8
        or not isinstance(recipe.local_requirement_basis, str)
        or not recipe.local_requirement_basis.strip()
        or len(recipe.local_requirement_basis) > 2000
    ):
        raise CompanyStoreError(
            "Explicit bounded cohort, courses and local requirement basis required"
        )
    org = snapshot(repository, as_of=start.date().isoformat())
    people = {p["person_id"]: p for p in org["canonical_people"] + org["proposed_people"]}
    assignments = {a["control_id"]: a for a in org["control_assignments"]}
    owner = assignments["SH-TRN-001"]["primary_person_id"]
    monitor = assignments["SH-TRN-002"]["primary_person_id"]
    roster_owner = assignments["SH-PPL-001"]["primary_person_id"]
    if any(p not in people for p in (owner, monitor, roster_owner)):
        raise CompanyStoreError("Current scoped training and roster owners required")
    members = []
    seen = set()
    for member in recipe.cohort:
        person = people.get(member.person_id)
        if (
            person is None
            or member.person_id in seen
            or person.get("org_role_id") != member.role_id
            or person.get("status")
            in {"former_employee", "historical_employee_current_status_unconfirmed"}
        ):
            raise CompanyStoreError(
                "Distinct existing people with exact snapshot role IDs required"
            )
        seen.add(member.person_id)
        members.append(
            {
                "person_id": member.person_id,
                "role_id": member.role_id,
                "snapshot_status": person["status"],
                "role_basis": "SCOPED_SNAPSHOT_NOT_EMPLOYMENT_HISTORY",
            }
        )
    roles = {m.role_id for m in recipe.cohort}
    if len(roles) < 2:
        raise CompanyStoreError("At least two scoped roles required")
    course_ids = set()
    for course in recipe.courses:
        _id(course.course_id)
        if (
            course.course_id in course_ids
            or not isinstance(course.title, str)
            or not course.title.strip()
            or len(course.title) > 240
            or not isinstance(course.role_ids, tuple)
            or not course.role_ids
            or len(course.role_ids) != len(set(course.role_ids))
            or not set(course.role_ids) <= roles
        ):
            raise CompanyStoreError(
                "Distinct local courses with actual cohort role requirements required"
            )
        course_ids.add(course.course_id)
    targets = [(m, c) for m in recipe.cohort for c in recipe.courses if m.role_id in c.role_ids]
    if {m.person_id for m, c in targets} != seen or (
        recipe.late_person_id,
        recipe.late_course_id,
    ) not in {(m.person_id, c.course_id) for m, c in targets}:
        raise CompanyStoreError(
            "Every cohort member needs an assignment and late target must be assigned"
        )
    pins = dict(org["source_sha256"])
    for p in (
        "docs/controls/COMMON_CONTROL_CATALOG_v0.1.md",
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/audit_suite/company_training_activity.py",
    ):
        pins[p] = sha((repository / p).read_bytes())
    recipe_pin = sha(encoded(asdict(recipe)))
    common = {
        "cycle_id": recipe.cycle_id,
        "boundary_id": "corporate",
        "period_start": start.isoformat(),
        "period_end_exclusive": end.isoformat(),
        "origin": "LOCAL_SYNTHETIC_TRAINING_EXERCISE_NOT_EMPLOYMENT_FACT",
        "policy_status": "LOCAL_COURSE_RULES_NOT_ACCEPTED_ENTERPRISE_POLICY",
        "appointment_status": "SNAPSHOT_CONTACTS_NO_ACCEPTANCE_OR_EMPLOYMENT_ASSERTION",
        "scope_limit": "EXPLICIT_LOCAL_COHORT_ONLY_NOT_ENTERPRISE_WORKFORCE_CENSUS",
        "local_requirement_basis": recipe.local_requirement_basis,
    }
    receipts = []
    with tempfile.TemporaryDirectory(prefix="training-stage-", dir=destination.parent) as temp:
        store = CompanyStore(Path(temp))
        for branch in (recipe.on_time_branch, recipe.late_branch):
            owners = {
                "training_roster": roster_owner,
                "training_matrix": owner,
                "training_assignments": owner,
                "training_completions": owner,
                "training_monitoring": monitor,
                "training_followup": monitor,
            }
            for system, person in owners.items():
                store.register_system(recipe.company_id, branch, system, person)
            records = {}

            def emit(system, record_id, when, body, control_ids, branch=branch, records=records):
                value = {
                    **common,
                    "record_id": record_id,
                    "recorded_at": when.isoformat(),
                    "control_ids": control_ids,
                    **body,
                }
                content = encoded(value)
                result = store.append_version(
                    recipe.company_id,
                    branch,
                    system,
                    record_id,
                    expected_version=0,
                    command_id="TRN-" + sha(encoded([recipe_pin, branch, system, record_id])),
                    event_at=when.isoformat(),
                    available_at=when.isoformat(),
                    content=content,
                    origin="AUTHORED_TRAINING_SOURCE",
                    provenance={
                        "recipe_sha256": recipe_pin,
                        "source_sha256": pins,
                        "organization_snapshot_digest": org["snapshot_digest"],
                        "source_reference": recipe.cycle_id,
                        "control_ids": control_ids,
                        "classification": "LOCAL_SYNTHETIC_TRAINING_NOT_REAL_COMPLETION",
                        "assignment_status": assignments[control_ids[0]]["status"],
                    },
                )
                records[system, record_id] = {
                    "system": system,
                    "record": record_id,
                    "version": 1,
                    "sha256": sha(content),
                    "available_at": when.isoformat(),
                }
                receipts.append(result)
                return records[system, record_id]

            roster = emit(
                "training_roster",
                "ROSTER-" + recipe.cycle_id,
                start,
                {"members": members, "cohort_count": len(members), "custodian": roster_owner},
                ["SH-TRN-001", "SH-TRN-002"],
            )
            matrix = emit(
                "training_matrix",
                "MATRIX-" + recipe.cycle_id,
                start,
                {
                    "courses": [asdict(c) for c in recipe.courses],
                    "due_at": due.isoformat(),
                    "required_worker_class": "EXPLICIT_LOCAL_EXERCISE_PARTICIPANTS",
                    "approved_by": owner,
                    "approval_basis": "LOCAL_EXERCISE_ONLY",
                    "roster_source": roster,
                },
                ["SH-TRN-001"],
            )
            assigned = []
            completed = []
            for member, course in targets:
                rid = recipe.cycle_id + "-" + member.person_id + "-" + course.course_id
                assignment = emit(
                    "training_assignments",
                    rid,
                    start + timedelta(days=1),
                    {
                        "person_id": member.person_id,
                        "role_id": member.role_id,
                        "course_id": course.course_id,
                        "due_at": due.isoformat(),
                        "matrix_source": matrix,
                        "roster_source": roster,
                    },
                    ["SH-TRN-001", "SH-TRN-002"],
                )
                assigned.append((member, course, assignment))
                completion_time = (
                    late
                    if branch == recipe.late_branch
                    and (member.person_id, course.course_id)
                    == (recipe.late_person_id, recipe.late_course_id)
                    else due - timedelta(days=1)
                )
                completion = emit(
                    "training_completions",
                    rid,
                    completion_time,
                    {
                        "person_id": member.person_id,
                        "course_id": course.course_id,
                        "completed_at": completion_time.isoformat(),
                        "assignment_source": assignment,
                    },
                    ["SH-TRN-002"],
                )
                completed.append((member.person_id, course.course_id, completion_time, completion))
            for index, when in enumerate((checkpoint, closeout), 1):
                observed = [(p, c, t, ref) for p, c, t, ref in completed if t <= when]
                done = {(p, c) for p, c, t, ref in observed}
                overdue = [
                    {"person_id": m.person_id, "course_id": c.course_id, "assignment_source": ref}
                    for m, c, ref in assigned
                    if (m.person_id, c.course_id) not in done
                ]
                report = emit(
                    "training_monitoring",
                    f"MONITOR-{recipe.cycle_id}-{index}",
                    when,
                    {
                        "as_of": when.isoformat(),
                        "cohort_source": roster,
                        "matrix_source": matrix,
                        "assignment_sources": [ref for m, c, ref in assigned],
                        "completion_sources": [ref for p, c, t, ref in observed],
                        "assigned_count": len(assigned),
                        "completion_count": len(observed),
                        "overdue_count": len(overdue),
                        "overdue": overdue,
                        "late_completed_count": sum(t > due for p, c, t, ref in observed),
                        "reconciliation_basis": (
                            "Roster role-to-course requirements joined to assignments "
                            "and available completion records"
                        ),
                    },
                    ["SH-TRN-002"],
                )
                if index == 1 and overdue:
                    emit(
                        "training_followup",
                        "FOLLOWUP-" + recipe.cycle_id,
                        followup,
                        {
                            "monitoring_source": report,
                            "recipients": overdue,
                            "sent_by": monitor,
                            "requested_action": (
                                "Complete the assigned local course "
                                "and provide the completion record"
                            ),
                            "followup_due_at": late.isoformat(),
                        },
                        ["SH-TRN-002"],
                    )
        result = {
            "status": "LOCAL_TRAINING_SOURCE_PAIR_CREATED",
            "recipe_sha256": recipe_pin,
            "source_sha256": pins,
            "cohort_count": len(members),
            "assignments_per_branch": len(targets),
            "source_versions": len(receipts),
            "receipts": receipts,
            "grants_created": False,
            "audits_created": False,
            "professional_validation": "UNVALIDATED",
            "limits": [
                "One explicit local cycle, not full-year enterprise training completeness.",
                "No accepted policy, actual employment or real completion asserted.",
                "Overdue monitoring and late completion are source facts, not audit findings.",
            ],
        }
        path = Path(temp) / "SOURCE_RECEIPT.json"
        path.write_bytes(encoded(result))
        path.chmod(0o600)
        publish(Path(temp), destination)
    return result
