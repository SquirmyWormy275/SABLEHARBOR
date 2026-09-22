"""Reperform statutory sources and feed finite cash requests into the native model."""

import json
from collections import defaultdict
from decimal import Decimal as D

from industrial.planning import enterprise, forecast

from .aru_tax_workpapers import build as aru_build
from .industrial_tax import IndustrialTax
from .industrial_tax_assets import build as assets_build
from .industrial_tax_future import FutureIndustrialTax
from .industrial_tax_settlement import build as settlement_build
from .parent_tax import ParentTax
from .rwh_book import RwhBook
from .rwh_tax_workpapers import build as mine_build
from .state_apportionment import build as factors_build
from .statutory_current import build as current_build
from .statutory_deferred import build as deferred_build
from .statutory_deferred import opening as opening_build
from .statutory_posting import StatutoryPosting


def build(output, fin, op, legacy, operating, policy, adjustment):
    """Solve the bounded tax/payment feedback; fail rather than publish unconverged cash."""
    anchor = enterprise.load_anchor()
    iterations = []
    prior_plan = None
    state_paid = {}
    interest_deductions = {}
    from .rot_penalties import RotPenalties

    adjustment.rot_penalties = RotPenalties()
    for iteration in range(1, 9):
        adjustment.parent_tax = None
        adjustment.statutory_tax = None
        adjustment.industrial_tax = None
        adjustment.future_industrial_tax = None
        adjustment.rwh_book = None

        def books():
            return enterprise.build(
                output / "enterprise",
                forecast_result=fin,
                legacy_result=legacy,
                source=policy,
                core_provider=operating,
                adjustment_provider=adjustment,
            )

        seed = books()
        adjustment.industrial_tax = IndustrialTax(seed)
        adjustment.future_industrial_tax = FutureIndustrialTax(seed)
        adjustment.rwh_book = RwhBook(seed, fin, anchor)
        before = books()
        parent = ParentTax(before, legacy, operating, state_cash_paid=state_paid)
        assets = assets_build(fin)
        mine = mine_build(before, adjustment.rwh_book, assets, fin, interest_deductions)
        aru = aru_build(before["journal_rows"], fin)
        factors = factors_build(before, fin, anchor)
        current = current_build(parent, aru, mine, factors, before["journal_rows"], state_paid)
        deferred = deferred_build(before, parent, mine, assets, current, factors)
        opening = opening_build(
            parent,
            mine,
            assets,
            current,
            adjustment.rwh_book.history,
            adjustment.historical_rot.bridge["utility_accrued_rot_usd"],
        )
        settlement = settlement_build(before["journal_rows"], fin)
        posting = StatutoryPosting(before, parent, current, deferred, opening, settlement)
        # The native cash model posts whole dollars. Compare exactly at that boundary,
        # retaining four-decimal tax computations in the underlying workpapers.
        plan = {
            "annual": {k: str(D(v).quantize(D(1))) for k, v in posting.annual_override.items()},
            "monthly": {k: str(D(v).quantize(D(1))) for k, v in posting.payment_override.items()},
        }
        plan_delta = (
            max(
                (
                    abs(D(value) - D(prior_plan[population][key]))
                    for population, values in plan.items()
                    for key, value in values.items()
                ),
                default=D(0),
            )
            if prior_plan is not None
            else None
        )
        iterations.append(
            {
                "maximum_cash_plan_change_usd": str(plan_delta)
                if plan_delta is not None
                else "N/A",
                "iteration": iteration,
                "converged": plan == prior_plan,
                "annual_current_usd": str(sum(map(D, plan["annual"].values()))),
                "requested_cash_usd": str(sum(map(D, plan["monthly"].values()))),
            }
        )
        next_state_paid = defaultdict(D)
        if prior_plan is not None:
            adjustment.statutory_tax = posting
            successor = books()
            for row in posting.payment_rows:
                if row["jurisdiction"] != "US":
                    next_state_paid[row["scenario"], row["taxpayer"], row["year"]] += D(
                        row["paid_usd"]
                    )
        next_interest_deductions = {
            (r["scenario"], r["year"]): D(r["interest_deducted_usd"])
            for r in current["federal"]
            if r["taxpayer"] == "PS"
        }
        converged = (
            plan == prior_plan
            and dict(next_state_paid) == state_paid
            and next_interest_deductions == interest_deductions
        )
        iterations[-1]["converged"] = converged
        iterations[-1]["maximum_state_deduction_change_usd"] = str(
            max(
                (
                    abs(next_state_paid.get(k, D(0)) - state_paid.get(k, D(0)))
                    for k in set(next_state_paid) | set(state_paid)
                ),
                default=D(0),
            )
        )
        iterations[-1]["maximum_interest_deduction_change_usd"] = str(
            max(
                (
                    abs(next_interest_deductions.get(k, D(0)) - interest_deductions.get(k, D(0)))
                    for k in set(next_interest_deductions) | set(interest_deductions)
                ),
                default=D(0),
            )
        )
        (output / "statutory_iteration_progress.json").write_text(
            json.dumps(iterations, indent=2) + "\n"
        )
        iterations[-1]["interest_deductions_stable"] = (
            next_interest_deductions == interest_deductions
        )
        print(f"Statutory cash iteration {iteration}: converged={converged}", flush=True)
        iterations[-1]["settled_state_deductions_stable"] = dict(next_state_paid) == state_paid
        if converged:
            from .statutory_replay import verify as verify_statutory

            replay = verify_statutory(posting, successor["journal_rows"])
            from .statutory_reconciliation import verify as reconcile_statutory

            reconciliation = reconcile_statutory(
                successor["journal_rows"], parent.rows, current, deferred, opening, settlement
            )
            penalty_check = adjustment.rot_penalties.verify(successor["journal_rows"])
            workpapers = dict(
                implementation_replay=replay,
                independent_reconciliation=reconciliation,
                rot_penalty_reconciliation=penalty_check,
                rot_penalty_monthly=adjustment.rot_penalties.rows,
                rot_penalty_opening=adjustment.rot_penalties.opening,
                rot_penalty_cutoff=adjustment.rot_penalties.cutoff,
                rot_historical_cutoff=adjustment.rot_penalties.historical_cutoff,
                rot_current_receipt_duties=adjustment.rot_penalties.current_cutoff,
                current=current,
                deferred=deferred,
                opening=opening,
                assets=assets,
                mine=mine,
                aru=aru,
                factors=factors,
                settlement=settlement,
                iterations=iterations,
                reviewed_native_journal=before["journal_rows"],
            )
            export(output, workpapers, posting)
            return fin, successor, parent, workpapers
        prior_plan = plan
        state_paid = dict(next_state_paid)
        interest_deductions = next_interest_deductions
        fin = forecast.build(
            output / "industrial/forecast",
            operating_rows=op["operating_rows"],
            statutory_current_override=plan["annual"],
            statutory_payment_override=plan["monthly"],
        )
    raise ValueError("Statutory cash/payment feedback did not converge in eight iterations")


def serializable(value):
    if isinstance(value, dict):
        return {
            "/".join(map(str, k)) if isinstance(k, tuple) else str(k): serializable(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return str(value) if isinstance(value, D) else value


def export(output, workpapers, posting):
    """Keep computations, native settlement evidence and requested cash distinct."""
    for name, value in workpapers.items():
        (output / f"statutory_{name}.json").write_text(
            json.dumps(serializable(value), indent=2) + "\n"
        )
        if isinstance(value, list):
            enterprise.write_csv(output / f"statutory_{name}.csv", value)
        elif isinstance(value, dict):
            for population, rows in value.items():
                if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                    enterprise.write_csv(output / f"statutory_{name}_{population}.csv", rows)
    enterprise.write_csv(output / "statutory_payment_allocations.csv", posting.payment_rows)
    (output / "statutory_requested_cash.json").write_text(
        json.dumps(
            {
                "annual_current": posting.annual_override,
                "monthly_requested_cash": posting.payment_override,
                "state": "CONDITIONAL_REQUESTS_ACTUAL_SETTLEMENT_SEPARATE",
                "interim_method": "Estimated annual statutory provision allocated monthly; future inputs remain conditional",
            },
            indent=2,
        )
        + "\n"
    )
