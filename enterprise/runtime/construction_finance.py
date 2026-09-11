"""Construction transaction reference and explicit budget-to-enterprise scope bridge.

No transaction in this reference is evidence that a vendor was engaged or paid.
Accepted-event fixtures exercise deposits, accruals, retention and in-service policy;
the September source has no such accepted construction transactions.
"""

from decimal import Decimal as D
from collections import defaultdict
from datetime import date


class ProjectLedger:
    def __init__(self, available_cash=0):
        self.balances = defaultdict(D, cash=D(str(available_cash)))
        self.authorized = D(0)
        self.committed = D(0)
        self.invoiced = D(0)
        self.in_service = None
        self.life_years = None
        self.events = []

    def apply(self, event):
        required = {
            "id",
            "type",
            "amount",
            "effective_on",
            "recorded_on",
            "authorized_by",
            "evidence_ref",
            "origin",
            "asset_class",
            "life_years",
        }
        if set(event) != required or any(e["id"] == event["id"] for e in self.events):
            raise ValueError("Invalid or duplicate accounting event")
        if (
            not event["authorized_by"]
            or not event["evidence_ref"]
            or event["origin"] != "SYNTHETIC_ACCEPTED_TEST_EVENT"
        ):
            raise ValueError(
                "Unapproved forecast is not a payable, asset acceptance or cash payment"
            )
        amount = D(str(event["amount"]))
        if not amount.is_finite() or amount < 0:
            raise ValueError("Invalid accounting amount")
        effective = date.fromisoformat(event["effective_on"])
        date.fromisoformat(event["recorded_on"])
        kind = event["type"]
        b = self.balances
        if kind == "AUTHORIZE":
            self.authorized += amount
        elif kind == "COMMIT":
            if self.committed + amount > self.authorized:
                raise ValueError("Commitment exceeds phase authority")
            self.committed += amount
        elif kind == "REFUNDABLE_DEPOSIT":
            if amount > b["cash"] or b["deposit"] + amount > self.committed:
                raise ValueError("Unfunded or uncommitted deposit")
            b["cash"] -= amount
            b["deposit"] += amount
        elif kind == "INVOICE":
            if self.invoiced + amount > self.committed:
                raise ValueError("Invoice exceeds accepted commitment")
            if event["asset_class"] not in {"CIP", "EXPENSE", "PREPAID"}:
                raise ValueError("Unknown invoice asset/cost class")
            self.invoiced += amount
            b[event["asset_class"].lower()] += amount
            b["payable"] += amount
        elif kind == "APPLY_DEPOSIT":
            if amount > min(b["deposit"], b["payable"]):
                raise ValueError("Invalid deposit application")
            b["deposit"] -= amount
            b["payable"] -= amount
        elif kind == "RETAIN":
            if amount > b["payable"]:
                raise ValueError("Retention exceeds payable")
            b["payable"] -= amount
            b["retention"] += amount
        elif kind == "RELEASE_RETENTION":
            if amount > b["retention"]:
                raise ValueError("Release exceeds retention")
            b["retention"] -= amount
            b["payable"] += amount
        elif kind == "PAY":
            if amount > min(b["cash"], b["payable"]):
                raise ValueError("Payment exceeds cash or accepted payable")
            b["payable"] -= amount
            b["cash"] -= amount
            b["paid"] += amount
        elif kind == "IN_SERVICE":
            if (
                event["asset_class"] == "LAND"
                or type(event["life_years"]) is not int
                or event["life_years"] <= 0
                or amount > b["cip"]
            ):
                raise ValueError(
                    "Land cannot be depreciated; in-service transfer requires accumulated CIP and a life"
                )
            if self.in_service:
                raise ValueError(
                    "Use a separate component ledger for each asset cohort"
                )
            b["cip"] -= amount
            b["ppe"] += amount
            self.in_service = effective
            self.life_years = event["life_years"]
        elif kind == "CANCEL_UNDELIVERED":
            if amount > self.committed - self.invoiced:
                raise ValueError("Cancellation cannot erase delivered/accrued costs")
            self.committed -= amount
        elif kind == "REFUND_DEPOSIT":
            if amount > b["deposit"]:
                raise ValueError("Refund exceeds remaining deposit")
            b["deposit"] -= amount
            b["cash"] += amount
        else:
            raise ValueError("Unsupported accounting event type")
        self.events.append(dict(event))

    def depreciation_at(self, as_of):
        if not self.in_service:
            return D(0)
        end = date.fromisoformat(as_of)
        months = max(
            0,
            (end.year - self.in_service.year) * 12 + end.month - self.in_service.month,
        )
        return min(
            self.balances["ppe"],
            self.balances["ppe"] * D(months) / D(self.life_years * 12),
        ).quantize(D(".01"))


def phase_reconciliation(data):
    """Every dollar of Phase I reconciles; unaccepted 2026 costs are not retro-booked."""
    from .planning import phase_cash

    a = data["capital"]["implementation_assumptions"]
    rows = []
    for scenario in a["scenarios"]:
        cash = phase_cash(a, scenario)
        before = sum(v for (y, m), v in cash.items() if y == 2026) - D(3000000)
        after = sum(v for (y, m), v in cash.items() if y >= 2027)
        row = dict(
            scenario=scenario,
            phase_i_envelope="15500000.00",
            land_non_cash_overlay="3000000.00",
            pre_2027_unaccepted_unrecognized_requests=str(before),
            conditional_post_2026_cip_requests=str(after),
            unspent_reserve="500000.00",
            actual_construction_commitment="0.00",
            actual_invoices="0.00",
            actual_paid="0.00",
            status="FORECAST_SCOPE_BRIDGE_NOT_PAYMENT_EVIDENCE",
        )
        if before + after + D(3000000) + D(500000) != D(row["phase_i_envelope"]):
            raise ValueError("Unreconciled facility budget")
        rows.append(row)
    return rows


def asset_forecast(data):
    """Owned acceptance sensitivity; separate from the uncommissioned world state."""
    a = data["capital"]["implementation_assumptions"]
    policy = a["technical_design"]["asset_policy"]
    buckets = data["capital"]["owned_site"]
    rows = []
    base = {
        "SITE": D(buckets["site_civil_security_usd"]),
        "SHELL": D(buckets["shell_support_building_usd"]),
        "UTILITY": D(buckets["utility_fiber_backbone_usd"]),
        "PLANT": D(buckets["initial_critical_plant_usd"]),
    }
    direct = sum(base.values())
    # $200k preliminary studies expensed; $500k contingency remains unspent.
    study_cost = next(p["cost"] for p in a["phases"] if p["id"] == "RT-STUDIES")
    indirect = (
        D(buckets["engineering_permitting_contingency_usd"])
        - D(study_cost)
        - D(policy["unspent_contingency"])
    )
    allocated = {
        k: (v + indirect * v / direct).quantize(D(".01")) for k, v in base.items()
    }
    allocated["PLANT"] += direct + indirect - sum(allocated.values())
    for scenario, s in a["scenarios"].items():
        service_year = 2029 + s["construction_delay_months"] // 12
        for year in range(2026, 2037):
            for kind, gross in allocated.items():
                life = policy[kind.lower() + "_life_years"]
                months = max(0, (year - service_year) * 12 + 11)
                depreciation = min(gross, gross * D(months) / D(life * 12)).quantize(
                    D(".01")
                )
                rows.append(
                    dict(
                        scenario=scenario,
                        year=year,
                        component=kind,
                        conditional_completed_cost=str(gross),
                        useful_life_years=life,
                        in_service_assumption=f"{service_year}-01-01",
                        cumulative_depreciation=str(depreciation),
                        conditional_net_book=str(
                            gross - depreciation if year >= service_year else D(0)
                        ),
                        actual_in_service=False,
                        state="HYPOTHETICAL_COMPLETION_NOT_ENTERPRISE_ACTUAL_PPE",
                    )
                )
    return rows


def commercial_cash_cases(data):
    """Negotiating sensitivities; deposits are assets, retained invoices are liabilities."""
    a = data["capital"]["implementation_assumptions"]
    policy = a["technical_design"]["asset_policy"]
    rows = []
    for phase in a["phases"]:
        if phase["id"] in {"RT-LAND", "RT-CONTINGENCY"}:
            continue
        cost = D(str(phase["cost"]))
        deposit = cost * D(str(policy["refundable_deposit_fraction"]))
        retention = cost * D(str(policy["invoice_retention_fraction"]))
        rows.append(
            dict(
                phase=phase["id"],
                contract_value=str(cost),
                deposit_asset=str(deposit),
                full_invoice_accrual=str(cost),
                retained_liability=str(retention),
                completion_cash_excluding_deposit=str(cost - deposit - retention),
                final_retention_cash=str(retention),
                total_cash_if_fully_accepted=str(cost),
                authorized_commitment="0",
                actual_invoice="0",
                actual_cash="0",
                state="ALTERNATIVE_DEPOSIT_RETENTION_TERMS_NOT_EXECUTED",
            )
        )
    return rows
