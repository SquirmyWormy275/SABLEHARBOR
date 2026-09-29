"""Quarterly privileged-access reviews over an explicit pre-audit mover inventory."""

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .company_activity import TransferRecipe, generate_pair
from .company_store import CompanyStore, CompanyStoreError, _time
from .operating_source_bridge import encoded, sha
from .organization import snapshot


@dataclass(frozen=True)
class PeriodRecipe:
    company_id: str
    clean_branch: str
    messy_branch: str
    period_start: str
    period_end_exclusive: str
    movers: tuple[TransferRecipe, ...]
    omitted_population_employee: str
    privilege_basis: str


def _quarters(recipe):
    start = datetime.fromisoformat(_time(recipe.period_start))
    end = datetime.fromisoformat(_time(recipe.period_end_exclusive))
    if any(
        t.month not in {1, 4, 7, 10}
        or t.day != 1
        or any((t.hour, t.minute, t.second, t.microsecond))
        for t in (start, end)
    ):
        raise CompanyStoreError("Complete UTC calendar-quarter boundaries required")
    if not start < end or (end - start).days > 732:
        raise CompanyStoreError("Bounded period of at most two years required")
    quarters = []
    cursor = start
    while cursor < end:
        stop = (
            cursor.replace(year=cursor.year + 1, month=1)
            if cursor.month == 10
            else cursor.replace(month=cursor.month + 3)
        )
        quarters.append((cursor, stop))
        cursor = stop
    return quarters


def generate_period(store: CompanyStore, *, repository: Path, recipe: PeriodRecipe):
    """Stage the complete plan before appending to a new dedicated company store.

    Each mover is a distinct employee. Quarterly scope is the explicitly declared
    privileged-account inventory only, not a company-wide employee census.
    """
    quarters = _quarters(recipe)
    if not isinstance(recipe.movers, tuple) or not 2 <= len(recipe.movers) <= 24:
        raise CompanyStoreError("Two to24 explicit distinct-employee mover causes required")
    if not isinstance(recipe.privilege_basis, str) or not recipe.privilege_basis.strip():
        raise CompanyStoreError("Explicit fictional privileged-rights classification required")
    people, causes = set(), set()
    for mover in recipe.movers:
        if (mover.company_id, mover.clean_branch, mover.messy_branch) != (
            recipe.company_id,
            recipe.clean_branch,
            recipe.messy_branch,
        ):
            raise CompanyStoreError("Mover branch scope differs from period scope")
        when = datetime.fromisoformat(_time(mover.effective_at))
        if not quarters[0][0] + timedelta(days=1) <= when < quarters[-1][1] - timedelta(minutes=10):
            raise CompanyStoreError("Initial and reconciliation records must fit source period")
        if mover.employee_id in people or mover.event_id in causes:
            raise CompanyStoreError(
                "Distinct employees and causal IDs required; chained movers need a separate adapter"
            )
        people.add(mover.employee_id)
        causes.add(mover.event_id)
    if recipe.omitted_population_employee not in people:
        raise CompanyStoreError(
            "Missing-population condition must target an actual declared employee"
        )
    org = snapshot(repository, as_of=quarters[0][0].date().isoformat())
    assignment = next(a for a in org["control_assignments"] if a["control_id"] == "SH-IAM-007")
    owner, reviewer = assignment["primary_person_id"], assignment["operating_reviewer_person_id"]
    pins = dict(org["source_sha256"])
    for p in [
        "enterprise/ccf/assurance/design_data/control_procedures.json",
        "enterprise/audit_suite/company_activity.py",
        "enterprise/audit_suite/company_activity_period.py",
    ]:
        pins[p] = sha((repository / p).read_bytes())
    recipe_hash = sha(encoded(asdict(recipe)))
    with tempfile.TemporaryDirectory(prefix="company-period-") as temp:
        staged = CompanyStore(Path(temp))
        for mover in sorted(recipe.movers, key=lambda m: _time(m.effective_at)):
            generate_pair(staged, repository=repository, recipe=mover)
        for branch in (recipe.clean_branch, recipe.messy_branch):
            for system in ["review_population", "review_decisions", "review_reconciliation"]:
                staged.register_system(
                    recipe.company_id,
                    branch,
                    system,
                    reviewer if system == "review_reconciliation" else owner,
                )
            for start, stop in quarters:
                cutoff = _time(stop.isoformat())
                with staged._db() as db:
                    raw = db.execute(
                        "SELECT * FROM versions WHERE company=? AND branch=? "
                        "AND system IN ('hr','application') AND available_at<? "
                        "ORDER BY system,record,version",
                        (recipe.company_id, branch, cutoff),
                    ).fetchall()
                latest = {}
                for r in raw:
                    latest[r["system"], r["record"]] = dict(r)
                applications = [r for r in latest.values() if r["system"] == "application"]
                members = []
                for row in applications:
                    content = json.loads(row["content"])
                    if (
                        branch == recipe.messy_branch
                        and content["person_id"] == recipe.omitted_population_employee
                    ):
                        continue
                    members.append(
                        {
                            "person_id": content["person_id"],
                            "record": row["record"],
                            "version": row["version"],
                            "sha256": row["sha256"],
                            "rights": content["rights"],
                            "cause_id": content["cause_id"],
                        }
                    )
                hr_rows = {
                    json.loads(r["content"])["person_id"]: json.loads(r["content"])
                    for r in latest.values()
                    if r["system"] == "hr"
                }
                decisions = []
                for m in members:
                    hr = hr_rows[m["person_id"]]
                    authorization = hr.get("transfer_authorization")
                    expected = [authorization["add_right"]] if authorization else m["rights"]
                    excess = sorted(set(m["rights"]) - set(expected))
                    decisions.append(
                        {
                            "person_id": m["person_id"],
                            "source_record": m["record"],
                            "source_version": m["version"],
                            "source_sha256": m["sha256"],
                            "observed_rights": m["rights"],
                            "authorized_rights": expected,
                            "decision": "REMOVE_EXCESS" if excess else "RETAIN_AUTHORIZED",
                            "remove_rights": excess,
                            "decision_by": owner,
                            "removal_confirmation": "NOT_YET_PERFORMED"
                            if excess
                            else "NOT_REQUIRED",
                        }
                    )
                missing = sorted(set(hr_rows) - {m["person_id"] for m in members})
                quarter_id = f"PRIV-{start.year}-Q{(start.month - 1) // 3 + 1}"
                common = {
                    "id": quarter_id,
                    "control_id": "SH-IAM-007",
                    "origin": "FICTIONAL_OPERATIONAL_SCENARIO_NOT_CANON_PERSONNEL_CHANGE",
                    "period_start": start.isoformat(),
                    "period_end_exclusive": stop.isoformat(),
                    "declared_employee_ids": sorted(people),
                    "privilege_classification_basis": recipe.privilege_basis,
                    "scope_limit": "Declared application accounts from these mover causes only",
                    "frequency_basis": (
                        "SH-IAM-007 quarterly privileged review; "
                        "no ordinary-rights cadence inferred"
                    ),
                }
                population = {
                    **common,
                    "members": members,
                    "query": {
                        "system": "application",
                        "as_of_exclusive": cutoff,
                        "excluded_person_ids": [recipe.omitted_population_employee]
                        if branch == recipe.messy_branch
                        else [],
                    },
                    "exported_by": owner,
                    "membership_sha256": sha(encoded(members)),
                }
                review = {
                    **common,
                    "population_sha256": sha(encoded(population)),
                    "decisions": decisions,
                }
                reconciliation = {
                    **common,
                    "reviewed_by": reviewer,
                    "population_sha256": sha(encoded(population)),
                    "hr_sources": [
                        {"record": r["record"], "version": r["version"], "sha256": r["sha256"]}
                        for r in latest.values()
                        if r["system"] == "hr"
                    ],
                    "hr_visible_person_ids": sorted(hr_rows),
                    "export_person_ids": sorted(m["person_id"] for m in members),
                    "missing_person_ids": missing,
                    "status": "REEXPORT_REQUESTED" if missing else "COUNTS_RECONCILED",
                    "limits": (
                        "Count reconciliation implies neither independent assurance "
                        "nor removal confirmation"
                    ),
                }
                for index, (system, content) in enumerate(
                    [
                        ("review_population", population),
                        ("review_decisions", review),
                        ("review_reconciliation", reconciliation),
                    ],
                    start=1,
                ):
                    when = (stop + timedelta(minutes=index)).isoformat()
                    staged.append_version(
                        recipe.company_id,
                        branch,
                        system,
                        quarter_id,
                        expected_version=0,
                        command_id="PER-"
                        + sha(encoded([recipe.company_id, branch, system, quarter_id])),
                        event_at=when,
                        available_at=when,
                        content=encoded(content),
                        provenance={
                            "source_reference": quarter_id,
                            "source_sha256": pins,
                            "recipe_sha256": recipe_hash,
                            "assignment_status": assignment["status"],
                        },
                    )
        with staged._db() as db:
            systems = [dict(r) for r in db.execute("SELECT * FROM systems")]
            records = [dict(r) for r in db.execute("SELECT * FROM versions ORDER BY rowid")]
    # Existing unrelated branch data is rejected, never silently folded into a census.
    with store._db() as db:
        allowed = {
            (r["company"], r["branch"], r["system"], r["record"], r["version"]) for r in records
        }
        for row in db.execute("SELECT * FROM versions"):
            if (
                tuple(row[k] for k in ["company", "branch", "system", "record", "version"])
                not in allowed
            ):
                raise CompanyStoreError(
                    "Dedicated empty or exact-replay company source store required"
                )
    for s in systems:
        store.register_system(s["company"], s["branch"], s["system"], s["owner"])
    receipts = []
    for r in records:
        receipts.append(
            store.append_version(
                r["company"],
                r["branch"],
                r["system"],
                r["record"],
                expected_version=r["version"] - 1,
                command_id=r["command_id"],
                event_at=r["event_at"],
                available_at=r["available_at"],
                content=r["content"],
                provenance=json.loads(r["provenance"]),
                origin=r["origin"],
            )
        )
    return {
        "recipe_sha256": recipe_hash,
        "source_sha256": pins,
        "quarters": len(quarters),
        "mover_causes": len(recipe.movers),
        "source_versions": len(receipts),
        "receipts": receipts,
        "grants_created": False,
        "audits_created": False,
        "professional_validation": "UNVALIDATED",
        "gaps": [
            "SH-IAM-004 leaver/session/token/remote-access lifecycle not implemented here.",
            "Retention expiry is not modeled; immutable originals remain retained.",
            "Full enterprise accounts and independent removal retests remain outside this slice.",
        ],
    }
