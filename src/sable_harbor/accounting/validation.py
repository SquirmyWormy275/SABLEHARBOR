from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session, selectinload

from sable_harbor.core.database import required_schema_head
from sable_harbor.provenance.models import GenerationRun
from sable_harbor.provenance.service import run_context

from .models import AccountingBook, EntryState, FiscalPeriod, JournalEntry


class FinancialIntegrityError(ValueError):
    pass


@dataclass(frozen=True)
class ControlResult:
    code: str
    passed: bool
    observed: str
    details: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "status": "PASS" if self.passed else "FAIL",
            "observed": self.observed,
            "details": self.details,
        }


@dataclass(frozen=True)
class ValidationReport:
    generation_run_id: str
    controls: tuple[ControlResult, ...]

    @property
    def passed(self) -> bool:
        return all(control.passed for control in self.controls)

    def require_pass(self) -> None:
        failures = [control for control in self.controls if not control.passed]
        if failures:
            raise FinancialIntegrityError(
                "Financial integrity validation failed: "
                + "; ".join(f"{item.code}: {item.details}" for item in failures)
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "generation_run_id": self.generation_run_id,
            "status": "PASS" if self.passed else "FAIL",
            "control_count": len(self.controls),
            "controls": [control.as_dict() for control in self.controls],
        }


def journal_integrity_violations(session: Session, run: GenerationRun) -> list[str]:
    """Return journal-level violations for one owning run, including cutoff ownership."""
    failures: list[str] = []
    entries = session.scalars(
        select(JournalEntry)
        .where(JournalEntry.generation_run_id == run.id)
        .options(selectinload(JournalEntry.lines))
    ).all()
    for entry in entries:
        if entry.state is not EntryState.POSTED:
            failures.append(f"journal {entry.id} is not posted")
            continue
        period = session.get(FiscalPeriod, entry.period_id)
        book = session.get(AccountingBook, entry.book_id)
        if period is None or book is None or period.book_id != entry.book_id:
            failures.append(f"journal {entry.id} has an incompatible book/period")
            continue
        if not period.starts_on <= entry.entry_date <= period.ends_on:
            failures.append(f"journal {entry.id} falls outside its fiscal period")
        if run.profile == "synthetic_common" and (
            run.synthetic_calibration_through is None
            or entry.entry_date > run.synthetic_calibration_through
        ):
            failures.append(
                f"shared synthetic calibration journal {entry.id} is after its persisted cutoff"
            )
        if run.shared_synthetic_calibration_run_id is not None and (
            run.forecast_from is None or entry.entry_date < run.forecast_from
        ):
            failures.append(
                f"scenario journal {entry.id} is before the persisted forecast boundary"
            )
        debit = sum((line.debit for line in entry.lines), Decimal(0))
        credit = sum((line.credit for line in entry.lines), Decimal(0))
        if not entry.lines or debit <= 0 or debit != credit:
            failures.append(f"journal {entry.id} is not independently balanced and nonzero")
        for line in entry.lines:
            if line.debit < 0 or line.credit < 0 or bool(line.debit) == bool(line.credit):
                failures.append(f"journal line {line.id} has invalid debit/credit")
            if line.functional_amount != line.debit - line.credit:
                failures.append(f"journal line {line.id} has invalid functional amount")
            if line.reporting_amount != line.functional_amount:
                failures.append(f"journal line {line.id} has invalid reporting amount")
            if line.transaction_currency != book.currency:
                failures.append(f"journal line {line.id} has unsupported FX treatment")
    return failures


def assert_run_ready_for_completion(session: Session, run: GenerationRun) -> None:
    """Reject a lifecycle transition that would freeze invalid accounting evidence."""
    session.flush()
    if run.status != "RUNNING" or run.completed_at is not None:
        raise FinancialIntegrityError(
            f"Generation run {run.id!r} is not in a completable RUNNING state"
        )
    if run.shared_synthetic_calibration_run_id is not None:
        calibration_run = session.get(GenerationRun, run.shared_synthetic_calibration_run_id)
        if calibration_run is None or calibration_run.status != "COMPLETED":
            raise FinancialIntegrityError(
                "Referenced shared synthetic calibration run must be completed"
            )
        if calibration_run.synthetic_calibration_dataset_id != run.synthetic_calibration_dataset_id:
            raise FinancialIntegrityError(
                "Referenced shared synthetic calibration run is dataset-incompatible"
            )
    failures = journal_integrity_violations(session, run)
    if failures:
        raise FinancialIntegrityError("; ".join(failures[:20]))


def validate_financial_integrity(session: Session, generation_run_id: str) -> ValidationReport:
    """Run read-only, selected-context controls used by CLI and release producers."""
    context = run_context(session, generation_run_id)
    run = session.get(GenerationRun, context.generation_run_id)
    if run is None:
        raise FinancialIntegrityError(f"Unknown generation run {generation_run_id!r}")
    controls: list[ControlResult] = []
    requires_complete_operational_population = run.profile in {
        "standard",
        "stress",
        "full_history",
    }

    schema_matches = run.schema_head == required_schema_head()
    controls.append(
        ControlResult(
            "RUN_SCHEMA_COMPATIBLE",
            schema_matches,
            str(run.schema_head),
            f"persisted schema must equal required head {required_schema_head()}",
        )
    )
    journal_count = (
        session.scalar(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.generation_run_id.in_(context.included_run_ids)
            )
        )
        or 0
    )
    controls.append(
        ControlResult(
            "JOURNAL_POPULATION_NONEMPTY",
            journal_count > 0,
            str(journal_count),
            "selected run context must contain accounting journals",
        )
    )
    journal_failures: list[str] = []
    for owner_id in context.included_run_ids:
        owner = session.get(GenerationRun, owner_id)
        if owner is None or owner.status != "COMPLETED":
            journal_failures.append(f"included run {owner_id} is missing or incomplete")
        else:
            journal_failures.extend(journal_integrity_violations(session, owner))
    controls.append(
        ControlResult(
            "JOURNALS_INDEPENDENTLY_VALID",
            not journal_failures,
            str(len(journal_failures)),
            "; ".join(journal_failures[:10]) or "all journals pass posting invariants",
        )
    )

    from .models import ScenarioValue

    marker_count = (
        session.scalar(
            select(func.count(ScenarioValue.id)).where(
                ScenarioValue.generation_run_id == context.generation_run_id,
                ScenarioValue.metric_code == "run_marker",
            )
        )
        or 0
    )
    controls.append(
        ControlResult(
            "RUN_MARKER_EXACTLY_ONE",
            marker_count == 1,
            str(marker_count),
            "selected run must carry exactly one lifecycle marker",
        )
    )

    if session.bind is None:
        raise FinancialIntegrityError("Validation session is not bound to a database")
    null_owned: list[str] = []
    database_inspector = inspect(session.bind)
    for table_name in database_inspector.get_table_names():
        columns = {column["name"] for column in database_inspector.get_columns(table_name)}
        if "generation_run_id" not in columns:
            continue
        null_count = (
            session.scalar(
                text(f'SELECT COUNT(*) FROM "{table_name}" WHERE generation_run_id IS NULL')
            )
            or 0
        )
        if null_count:
            null_owned.append(f"{table_name}={null_count}")
    controls.append(
        ControlResult(
            "GENERATION_OWNERSHIP_COMPLETE",
            not null_owned,
            str(len(null_owned)),
            ", ".join(null_owned) or "all generated records have an owning run",
        )
    )

    from sable_harbor.reporting_queries import run_named_query, single_run_named_queries
    from sable_harbor.reports.statements import monthly_statements, statement_snapshot

    query_failures: list[str] = []
    query_names = single_run_named_queries()
    for query_name in query_names:
        try:
            run_named_query(session, query_name, generation_run_id)
        except Exception as error:  # pragma: no cover - backend-specific diagnostic path
            query_failures.append(f"{query_name}: {error}")
    controls.append(
        ControlResult(
            "NAMED_QUERIES_EXECUTE",
            not query_failures,
            str(len(query_names) - len(query_failures)),
            (
                "; ".join(query_failures)
                or "all single-run named queries execute in selected context; "
                "scenario_variance requires two explicit compatible runs"
            ),
        )
    )
    exposure = run_named_query(session, "ar_ap_exposure_reconciliation", generation_run_id)
    exposure_failures = [
        str(row["ledger"])
        for row in exposure
        if abs(Decimal(row["reconciliation_difference"])) > Decimal("0.0001")
    ]
    controls.append(
        ControlResult(
            "AR_AP_RECONCILE_TO_GL",
            not exposure_failures
            and (bool(exposure) or not requires_complete_operational_population),
            str(len(exposure)),
            (
                "unreconciled ledgers: " + ", ".join(exposure_failures)
                if exposure_failures
                else (
                    "document and disclosed source-event exposure bridges to the GL"
                    if exposure
                    else "not applicable to this reduced generation profile"
                )
            ),
        )
    )
    intercompany = run_named_query(session, "intercompany_mismatch_elimination", generation_run_id)
    intercompany_failures = [
        f"{row['entity_a']}/{row['entity_b']}/{row['period']}"
        for row in intercompany
        if abs(Decimal(row["total_mismatch"])) > Decimal("0.0001")
    ]
    controls.append(
        ControlResult(
            "INTERCOMPANY_RECIPROCAL_MATCH",
            not intercompany_failures
            and (bool(intercompany) or not requires_complete_operational_population),
            str(len(intercompany)),
            (
                "mismatched pairs: " + ", ".join(intercompany_failures)
                if intercompany_failures
                else (
                    "reciprocal AR/AP and revenue/expense positions match"
                    if intercompany
                    else "not applicable to this reduced generation profile"
                )
            ),
        )
    )
    debt = run_named_query(session, "debt_covenant_calculation", generation_run_id)
    negative_debt = [
        str(row["facility_number"])
        for row in debt
        if Decimal(row["principal_outstanding"]) < 0 or Decimal(row["availability"]) < 0
    ]
    controls.append(
        ControlResult(
            "DEBT_SCHEDULE_NONNEGATIVE",
            bool(debt) and not negative_debt,
            str(len(debt)),
            ", ".join(negative_debt) or "no facility is over-repaid or overdrawn",
        )
    )
    snapshot = statement_snapshot(session, generation_run_id)
    monthly = monthly_statements(session, generation_run_id)
    statement_failures = [
        str(row["period"])
        for row in monthly
        if abs(Decimal(row["balance_sheet_difference"])) > Decimal("0.0001")
    ]
    final_difference = abs(Decimal(snapshot["balance_sheet_difference"]))
    statements_pass = final_difference <= Decimal("0.0001") and not statement_failures
    controls.append(
        ControlResult(
            "STATEMENTS_BALANCE",
            statements_pass,
            str(snapshot["balance_sheet_difference"]),
            (
                "unbalanced periods: " + ", ".join(statement_failures)
                if statement_failures
                else "monthly and final balance sheets reconcile"
            ),
        )
    )
    report = ValidationReport(context.generation_run_id, tuple(controls))
    report.require_pass()
    return report
