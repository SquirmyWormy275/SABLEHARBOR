"""Compose operating histories without rewriting the accepted business baseline."""

import copy
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

from enterprise.business.model import BusinessModel, fingerprint

from . import commercial, credit, matters, research, workforce


class OperatingModel(
    credit.CreditMixin,
    commercial.CommercialMixin,
    matters.MatterMixin,
    research.ResearchMixin,
    workforce.WorkforceMixin,
    BusinessModel,
):
    def __init__(self, inputs=None, operations_inputs=None):
        self.operations_inputs = copy.deepcopy(
            operations_inputs
            if operations_inputs is not None
            else {
                p.stem: json.loads(p.read_text())
                for p in sorted(Path(__file__).with_name("source").glob("*.json"))
            }
        )
        super().__init__(inputs)
        self.input_hash = fingerprint(
            {"business": self.inputs, "operations": self.operations_inputs}
        )

    def build(self):
        if self._built:
            return self
        for scenario, case in self.policy["cases"].items():
            self.scenario, self.case = scenario, case
            self.sequence = 0
            self.balances = defaultdict(lambda: defaultdict(D))
            self.invoices, self.payables, self.host_payables, self.lots = [], [], [], []
            self.invoice_ids, self.accepted, self.churned = set(), set(), set()
            self.contract_starts, self.work_done, self.asset_cost, self.asset_accum = {}, {}, {}, {}
            self.matter_started, self.certified, self.measurement_due = set(), set(), {}
            for module in (credit, commercial, matters, research, workforce):
                module.start_scenario(self)
            for month in range(1, 61):
                self.month = month
                self.settle()
                self.workforce()
                self.subscriptions()
                self.outcomes()
                self.product_outcomes()
                self.research()
                self.recovery()
                self.close()
            self.tables["invoices"].extend(self.invoices)
            self.tables["payables"].extend(self.payables)
            self.tables["recovery_lots"].extend(self.lots)
        self._built = True
        return self
