"""Commercial consequences are exercised against the real credit and journal code."""

import copy
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

import pytest

from enterprise.business.model import BusinessModel, load_inputs
from enterprise.operations import commercial, credit


class CommercialHarness(credit.CreditMixin, commercial.CommercialMixin, BusinessModel):
    def __init__(self, config=None, inputs=None, capacity_multiplier="1"):
        super().__init__(inputs)
        source = Path(commercial.__file__).with_name("source")
        self.operations_inputs = {
            name: json.loads((source / f"{name}.json").read_text())
            for name in ("commercial", "credit")
        }
        if config is not None:
            self.operations_inputs["commercial"] = copy.deepcopy(config)
        self.capacity_multiplier = D(capacity_multiplier)

    def build(self):
        if self._built:
            return self
        for scenario, case in self.policy["cases"].items():
            self.scenario, self.case = scenario, case
            self.sequence = 0
            self.balances = defaultdict(lambda: defaultdict(D))
            self.invoices, self.payables, self.host_payables, self.lots = [], [], [], []
            self.invoice_ids, self.accepted, self.churned = set(), set(), set()
            self.contract_starts = {}
            credit.start_scenario(self)
            commercial.start_scenario(self)
            for month in range(1, 61):
                self.month = month
                self.capacity = defaultdict(
                    D,
                    {
                        "foundry-field": D(16640) * self.capacity_multiplier,
                        "atlas-meridian": D(3744) * self.capacity_multiplier,
                    },
                )
                self.settle()
                self.subscriptions()
                self.close()
            self.tables["invoices"].extend(self.invoices)
            self.tables["payables"].extend(self.payables)
        self._built = True
        return self


@pytest.fixture(scope="module")
def model():
    return CommercialHarness().build()


def select(model, table, **fields):
    return [r for r in model.tables[table] if all(r.get(k) == v for k, v in fields.items())]


def test_all_cases_reconcile(model):
    assert commercial.validate(model)["status"] == "PASS"
    assert credit.validate(model)["status"] == "PASS"
    by_journal = defaultdict(D)
    for row in model.tables["journal"]:
        by_journal[row["scenario"], row["journal_id"]] += D(row["signed_usd"])
    assert all(v == 0 for v in by_journal.values())


def test_loss_prevents_activation_and_billing(model):
    for scenario in ("base", "downside"):
        assert not select(model, "contract_versions", scenario=scenario, contract_id="FF-038")
        assert not [
            r
            for r in select(model, "invoices", scenario=scenario)
            if r["source_id"].startswith("FF-038-")
        ]
        changes = select(model, "commercial_changes", scenario=scenario, change_id="SYN-AMEND-038")
        assert len(changes) == 1 and changes[0]["status"] == "NOT_APPLICABLE_CLOSED"
    assert select(model, "contract_versions", scenario="expansion", contract_id="FF-038")


def test_pipeline_hold_preserves_unactivated_population(model):
    assert not select(model, "contract_versions", scenario="downside", contract_id="ATL-LIC-012")
    assert {
        r["status"]
        for r in select(
            model, "commercial_pipeline", scenario="downside", contract_id="ATL-LIC-012"
        )
    } == {"HELD"}


def test_amendment_before_delayed_activation_is_not_lost(model):
    changes = select(model, "commercial_changes", scenario="base", change_id="SYN-AMEND-037")
    assert changes[0]["status"] == "HELD_PENDING_ACTIVATION"
    assert changes[0]["month_index"] == 8
    applied = [r for r in changes if r["status"] == "APPLIED"]
    assert len(applied) == 1
    assert applied[0]["applied_month"] == 9
    assert applied[0]["original_effective_month"] == 8
    version = select(
        model, "contract_versions", scenario="base", contract_id="FF-037", reason="EXPANSION"
    )[0]
    assert version["approval_id"] == "SYN-CUSTOMER-APPROVAL-037"


def test_expansion_changes_invoice_and_future_recognition(model):
    invoice = select(model, "invoices", scenario="base", source_id="FF-001-SYN-AMEND-001")[0]
    assert D(invoice["amount_usd"]) == 70000  # Seven remaining months, including June.
    june = select(
        model,
        "commercial_deferred_rollforward",
        scenario="base",
        contract_id="FF-001",
        month_index=6,
    )[0]
    assert D(june["recognized_usd"]) == 125000
    assert D(june["billings_usd"]) == 70000


def test_contraction_reduces_unearned_service_and_rate(model):
    august = select(
        model,
        "commercial_deferred_rollforward",
        scenario="base",
        contract_id="FF-003",
        month_index=8,
    )[0]
    assert D(august["credits_usd"]) == 145000
    assert D(august["recognized_usd"]) == 116000
    assert D(august["closing_usd"]) == 464000


def test_cancellation_stops_service_and_reverses_remaining_deferral(model):
    september = select(
        model,
        "commercial_deferred_rollforward",
        scenario="base",
        contract_id="FF-004",
        month_index=9,
    )[0]
    assert D(september["credits_usd"]) == 640000
    assert D(september["recognized_usd"]) == 0
    assert D(september["closing_usd"]) == 0
    assert not [
        r
        for r in select(
            model, "events", scenario="base", source_id="FF-004", kind="SUBSCRIPTION_SERVICE"
        )
        if r["month_index"] >= 9
    ]


def test_incident_backlog_drives_credit_and_renewal_loss(model):
    incidents = select(model, "service_incidents", scenario="base", incident_id="SYN-INC-FF-001")
    assert incidents[0]["sla_breached"] is True
    assert D(incidents[0]["remaining_hours"]) > 0
    assert incidents[-1]["status"] == "RESOLVED"
    renewal = select(model, "commercial_renewals", scenario="base", contract_id="FF-001")[0]
    assert renewal["decision"] == "DECLINED" and renewal["cause"] == "SERVICE_BREACH"
    credit_rows = [
        r for r in select(model, "credit_notes", scenario="base") if "SYN-INC-FF-001" in str(r)
    ]
    assert len(credit_rows) == 1


def test_more_capacity_resolves_incident_and_preserves_renewal():
    strong = CommercialHarness(capacity_multiplier="3").build()
    assert not select(strong, "service_incidents", scenario="base", incident_id="SYN-INC-FF-001")[
        0
    ]["sla_breached"]
    assert (
        select(strong, "commercial_renewals", scenario="base", contract_id="FF-001")[0]["decision"]
        == "RENEWED"
    )


def test_shared_capacity_prevents_deployment_when_incident_uses_pool():
    source = Path(commercial.__file__).with_name("source") / "commercial.json"
    config = json.loads(source.read_text())
    config["incidents"][0]["start_month"] = 9
    config["incidents"][0]["required_hours"] = "9000"
    result = CommercialHarness(config=config).build()
    held = select(
        result, "commercial_pipeline", scenario="base", contract_id="FF-037", month_index=9
    )[0]
    assert held["status"] == "CAPACITY_HELD"
    assert not select(
        result, "contract_versions", scenario="base", contract_id="FF-037", applied_month=9
    )
    assert select(
        result, "commercial_changes", scenario="base", change_id="SYN-AMEND-037", status="APPLIED"
    )


def test_contract_amendments_do_not_mutate_baseline(model):
    assert model.inputs["contracts"] == load_inputs()["contracts"]
    before = len(model.tables["journal"])
    assert model.build() is model
    assert len(model.tables["journal"]) == before


def test_capacity_and_tickets_reconcile(model):
    for row in model.tables["commercial_capacity"]:
        tickets = select(
            model,
            "commercial_service_tickets",
            scenario=row["scenario"],
            month_index=row["month_index"],
            unit=row["unit"],
        )
        assert sum((D(r["served_hours"]) for r in tickets), D(0)) == D(row["routine_served_hours"])
        assert sum((D(r["required_hours"]) for r in tickets), D(0)) == D(
            row["routine_required_hours"]
        )


@pytest.mark.parametrize("case", ["arr", "deferred", "capacity"])
def test_exported_reconciliations_detect_tampering(model, case):
    table, key = {
        "arr": ("commercial_arr_bridge", "closing_arr_usd"),
        "deferred": ("commercial_deferred_rollforward", "closing_usd"),
        "capacity": ("commercial_capacity", "unused_hours"),
    }[case]
    row = model.tables[table][0]
    old = row[key]
    try:
        row[key] = str(D(old) + 1)
        with pytest.raises(ValueError):
            commercial.validate(model)
    finally:
        row[key] = old


def test_missing_approval_is_rejected():
    config = CommercialHarness().operations_inputs["commercial"]
    config["changes"][0]["approval_id"] = ""
    with pytest.raises(ValueError, match="approval"):
        CommercialHarness(config=config).build()


def test_excess_shared_capacity_is_rejected():
    config = CommercialHarness().operations_inputs["commercial"]
    config["service_capacity_fraction"] = "0.30"
    with pytest.raises(ValueError, match="Atlas outcome capacity"):
        CommercialHarness(config=config).build()


def test_zero_price_original_term_can_expand_and_receive_earned_credit():
    inputs = load_inputs()
    inputs["contracts"][0]["monthly_subscription_usd"] = 0
    config = CommercialHarness().operations_inputs["commercial"]
    config["changes"][0]["effective_month"] = 1
    config["incidents"][0]["start_month"] = 2
    result = CommercialHarness(inputs=inputs, config=config).build()
    assert commercial.validate(result)["status"] == "PASS"
    assert not select(result, "invoices", scenario="base", source_id="FF-001-TERM-0")
    assert select(result, "invoices", scenario="base", source_id="FF-001-SYN-AMEND-001")
    assert [
        r for r in select(result, "credit_notes", scenario="base") if "SYN-INC-FF-001" in str(r)
    ]


def test_duplicate_monthly_population_is_rejected(model):
    original = model.tables["commercial_arr_bridge"][1]
    try:
        model.tables["commercial_arr_bridge"][1] = dict(model.tables["commercial_arr_bridge"][0])
        with pytest.raises(ValueError, match="incomplete or duplicated"):
            commercial.validate(model)
    finally:
        model.tables["commercial_arr_bridge"][1] = original
