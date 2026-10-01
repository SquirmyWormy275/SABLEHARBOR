"""Forward carrying correction for identified mine costs; original cash is preserved."""

from collections import defaultdict
from decimal import Decimal as D

from enterprise.closeout.rwh_history import Q
from enterprise.closeout.rwh_history import build as history
from enterprise.closeout.support_inventory import step as support_step


def current_inventory_bridge(anchor):
    """Pure current-year carrying schedule from locked anchor and authored H2 history."""
    native_keys = set()
    for row in anchor:
        if row["entity"] != "RWH_PS":
            continue
        if int(row["year"]) != 2026:
            raise ValueError("Current mine anchor requires 2026 source period")
        key = (row["entity"], row["year"], row["journal_id"], row["account"])
        if key in native_keys:
            raise ValueError("Duplicate native mine anchor leg")
        native_keys.add(key)
    h = history()
    ending = D(h["ending_inventory_lb"])
    produced_h2 = D(h["source"]["produced_lb"])
    cash = (
        D(h["cash_inventory_usd"])
        + D(h["source"]["book_normal_production_indirect_usd"]) * ending / produced_h2
    )
    dda = (
        D("687500")
        + D(h["book_inventory_delta_usd"])
        - (cash - D(h["cash_inventory_usd"])).quantize(Q)
    )
    rate = (D("48000000") - D(h["book_dda_usd"])) / D("7820000")
    cash_cogs = (cash + D("27950000") + D("2125000")) * D("500000") / D("672400") / 12
    dda_cogs = (dda + D("547400") * rate) * D("500000") / D("672400") / 12
    rows = []
    support = D(0)
    elimination = D(0)
    units = D(125000)
    for month in range(1, 13):
        source = [r for r in anchor if r["entity"] == "RWH_PS" and int(r["month"]) == month]
        production = sum(
            D(r["signed_usd"]) for r in source if r["account"] == "1200" and D(r["signed_usd"]) > 0
        )
        taxes = sum(
            D(r["signed_usd"])
            for r in source
            if r["account"] == "5100" and r.get("description") == "production mineral taxes usd"
        )
        if production <= 0 or taxes <= 0:
            raise ValueError("Missing current mine production cost or tax population")
        opening_cash, opening_dda = cash + support, dda
        support_row = support_step(
            support, elimination, source, 2026, month, units + D(547400) / 12, D(500000) / 12
        )
        support = support_row["closing_legal"]
        elimination = support_row["closing_elimination"]
        units += D(47400) / 12
        cash += production + taxes - cash_cogs
        dda += D("547400") / 12 * rate - dda_cogs
        rows.append(
            dict(
                year=2026,
                month=month,
                opening_cash_inventory_usd=str(opening_cash.quantize(Q)),
                opening_dda_inventory_usd=str(opening_dda.quantize(Q)),
                corrected_cash_inventory_usd=str((cash + support).quantize(Q)),
                support_inventory_usd=str(support.quantize(Q)),
                consolidated_service_cost_inventory_usd=str(elimination.quantize(Q)),
                corrected_dda_inventory_usd=str(dda.quantize(Q)),
                corrected_cash_cost_cogs_usd=str(
                    (cash_cogs + support_row["legal_cogs"]).quantize(Q)
                ),
                corrected_dda_cogs_usd=str(dda_cogs.quantize(Q)),
            )
        )
    return rows


class RwhBook:
    def __init__(self, result, forecast_result, anchor):
        h = history()
        self.history = h
        self.rows = []
        self.entries = {}
        self.elimination_entries = {}
        self.open_cash = (
            D(h["source"]["book_normal_production_indirect_usd"])
            * D(h["ending_inventory_lb"])
            / D(h["source"]["produced_lb"])
        )
        self.open_dda = D(h["book_inventory_delta_usd"]) - self.open_cash.quantize(Q)
        self.open_accum = D(h["book_dda_usd"])
        self.open_equity = self.open_accum - self.open_cash.quantize(Q) - self.open_dda
        if any(r["source_id"].startswith("CO-RWH-BOOK-") for r in result["journal_rows"]):
            raise ValueError("Mine carrying provider requires original pre-correction books")
        current = {r["month"]: r for r in current_inventory_bridge(anchor)}
        native = defaultdict(list)
        for r in anchor:
            if r["entity"] == "RWH_PS" and int(r["month"]) > 0:
                for scenario in ["base", "downside", "expansion"]:
                    native[scenario, 2026, int(r["month"])].append(r)
        for r in forecast_result["journal_rows"]:
            if r["entity"] == "RWH_PS" and int(r["month"]) > 0:
                native[r["scenario"], int(r["year"]), int(r["month"])].append(r)
        physical = {
            (r["scenario"], int(r["year"]), int(r["month"])): r
            for r in forecast_result["datasets"]["inventory"]
        }
        old = defaultdict(D)
        old_close = {}
        # Each scenario is emitted as an ordered monthly legal journal.
        for r in result["journal_rows"]:
            if r["entity"] == "RWH" and r["account"] in {"1200", "1210"}:
                key = (r["scenario"], r["account"])
                old[key] += D(r["signed_usd"])
                old_close[r["scenario"], int(r["year"]), int(r["month"]), r["account"]] = old[key]
        rate26 = (D(48000000) - self.open_accum) / D(7820000)
        rate27 = ((D(48000000) - self.open_accum) - D(547400) * rate26 + D(9000000)) / D(7272600)
        for scenario in ["base", "downside", "expansion"]:
            support = D(0)
            support_elim = D(0)
            prior_support_elim = D(0)
            cash = D(5625000) + self.open_cash
            dda = D(687500) + self.open_dda
            units = D(125000)
            prior_cash_delta = self.open_cash.quantize(Q)
            prior_dda_delta = self.open_dda
            prior_accum_delta = self.open_accum
            new_accum_delta = self.open_accum
            annual_cash_cogs = (cash + D(27950000) + D(2125000)) * D(500000) / D(672400)
            annual_dda_cogs = (dda + D(547400) * rate26) * D(500000) / D(672400)
            for year in range(2026, 2032):
                for month in range(1, 13):
                    k = (scenario, year, month)
                    source = native[k]
                    production = sum(
                        D(r["signed_usd"])
                        for r in source
                        if r["account"] == "1200" and D(r["signed_usd"]) > 0
                    )
                    taxes = sum(
                        D(r["signed_usd"])
                        for r in source
                        if r["account"] == "5100"
                        and (
                            r.get("description") == "production mineral taxes usd"
                            or r.get("source_type") == "PRODUCTION_MINERAL_TAX"
                        )
                    )
                    total_dda = sum(
                        D(r["signed_usd"])
                        for r in source
                        if r["account"] == "1210" and D(r["signed_usd"]) > 0
                    )
                    legacy_dda = sum(
                        D(r["signed_usd"])
                        for r in source
                        if r["account"] == "1210"
                        and r["source_id"] in {"RW-DDA", "RW-LEGACY-PRODUCTION"}
                        and D(r["signed_usd"]) > 0
                    )
                    if year == 2026:
                        produced = D(547400) / D(12)
                        sold = D(500000) / D(12)
                        new_legacy = produced * rate26
                        cash_cogs = annual_cash_cogs / D(12)
                        dda_cogs = annual_dda_cogs / D(12)
                    else:
                        p = physical[k]
                        produced = D(str(p["produced_lb"]))
                        sold = D(str(p["sold_lb"]))
                        new_legacy = produced * rate27
                        available = units + produced
                        cash_cogs = (cash + production + taxes) * sold / available
                        dda_cogs = (dda + total_dda - legacy_dda + new_legacy) * sold / available
                    support_row = support_step(
                        support, support_elim, source, year, month, units + produced, sold
                    )
                    support = support_row["closing_legal"]
                    support_elim = support_row["closing_elimination"]
                    cash += production + taxes - cash_cogs
                    dda += total_dda - legacy_dda + new_legacy - dda_cogs
                    if year == 2026:
                        if (
                            abs(
                                (cash + support).quantize(Q)
                                - D(current[month]["corrected_cash_inventory_usd"])
                            )
                            > Q
                            or abs(
                                dda.quantize(Q) - D(current[month]["corrected_dda_inventory_usd"])
                            )
                            > Q
                        ):
                            raise ValueError("Current carrying helper differs from full provider")
                    units += produced - sold
                    new_accum_delta += new_legacy - legacy_dda
                    cash_delta = (cash + support).quantize(Q) - old_close[
                        scenario, year, month, "1200"
                    ]
                    dda_delta = dda.quantize(Q) - old_close[scenario, year, month, "1210"]
                    accum_delta = new_accum_delta.quantize(Q)
                    dc = cash_delta - prior_cash_delta
                    di = dda_delta - prior_dda_delta
                    dep = accum_delta - prior_accum_delta
                    self.entries[k] = [
                        ("1200", dc),
                        ("5100", -dc + support_row["fee_production_cost"].quantize(Q)),
                        ("5150", -support_row["fee_production_cost"].quantize(Q)),
                        ("1210", di),
                        ("5300", dep - di),
                        ("1490", -dep),
                    ]
                    elim_delta = support_elim.quantize(Q) - prior_support_elim
                    self.elimination_entries[k] = [("1200", elim_delta), ("5100", -elim_delta)]
                    prior_support_elim = support_elim.quantize(Q)
                    self.rows.append(
                        dict(
                            scenario=scenario,
                            year=year,
                            month=month,
                            entity="RWH",
                            production_lb=str(produced),
                            sales_lb=str(sold),
                            ending_inventory_lb=str(units),
                            production_cash_cost_usd=str(production),
                            production_mineral_tax_usd=str(taxes),
                            corrected_cash_cost_cogs_usd=str(
                                (cash_cogs + support_row["legal_cogs"]).quantize(Q)
                            ),
                            corrected_dda_cogs_usd=str(dda_cogs.quantize(Q)),
                            corrected_cash_inventory_usd=str((cash + support).quantize(Q)),
                            support_inventory_usd=str(support.quantize(Q)),
                            group_support_production_cost_usd=str(
                                support_row["group_production_cost"].quantize(Q)
                            ),
                            legal_support_production_cost_usd=str(
                                support_row["legal_production_cost"].quantize(Q)
                            ),
                            consolidated_service_cost_inventory_usd=str(support_elim.quantize(Q)),
                            corrected_dda_inventory_usd=str(dda.quantize(Q)),
                            accumulated_ppe_correction_usd=str(accum_delta),
                            cash_flow_change_usd="0",
                            method="2026retainedannualnormal-costallocation;2027forwardmonthlyweightedaverage",
                            origin="DATED_BOOK_COST_SUCCESSOR_NOT_TAX263A_DETERMINATION",
                        )
                    )
                    prior_cash_delta = cash_delta
                    prior_dda_delta = dda_delta
                    prior_accum_delta = accum_delta

    def post_opening(self, books):
        books.post(
            "RWH",
            2026,
            0,
            [
                ("1200", self.open_cash.quantize(Q)),
                ("1210", self.open_dda),
                ("1490", -self.open_accum),
                ("3100", self.open_equity),
            ],
            "CO-RWH-BOOK-OPENING",
            "H2normalcost inventory and productiveestate DDA; abnormal3mrepair expense retained; cashunchanged",
            kind="COMPANY_MINE_BOOK_CORRECTION",
        )

    def post_month(self, books, year, month):
        sid = f"CO-RWH-BOOK-{year}-{month}"
        if any(r["source_id"] == sid for r in books.rows):
            raise ValueError("Duplicate mine carrying correction")
        books.post(
            "RWH",
            year,
            month,
            self.entries[books.scenario, year, month],
            sid,
            "Normal production mineral tax absorbed into inventory; corrected source productiveestate DDA and carryforwards",
            kind="COMPANY_MINE_BOOK_CORRECTION",
        )
        books.post(
            "ELIM",
            year,
            month,
            self.elimination_entries[books.scenario, year, month],
            f"CO-RWH-BOOK-SERVICE-{year}-{month}",
            "Replace production fee embedded in inventory with platform provider cost; no new fee or cash",
            kind="COMPANY_MINE_BOOK_CORRECTION",
        )
