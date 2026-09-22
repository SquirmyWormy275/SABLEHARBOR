"""Source-level SHI market facts; tax sourcing and filing groups remain separate."""

import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

SOURCE = Path(__file__).with_name("source") / "receipt_markets.json"
CURRENT_SOURCE = (
    Path(__file__).resolve().parents[1] / "operations/source/current_company_2026_08.json"
)
EXTERNAL_ACCOUNTS = {"LEG_4000", "LEG_4010", "LEG_4020", "LEG_4050", "BIZ_REVENUE"}


def allocate(journal_rows, source=None):
    source = json.loads(SOURCE.read_text()) if source is None else source
    if (
        source["rules"]["SHI-SERVICE-MARKET"]["state"] != "CA"
        or source["rules"]["SHI-CRADLE-DESTINATION"]["state"] != "WV"
    ):
        raise ValueError("Receipt territory changed; renew source reconciliation")
    current = json.loads(CURRENT_SOURCE.read_text())
    august_facts = source["august_2026"]
    if (
        D(august_facts["total_shi_revenue_usd"]) != D(current["core_revenue_usd"])
        or D(august_facts["wv_cradle_materials_usd"]) != D(current["cradle"]["revenue_usd"])
        or D(august_facts["ca_services_usd"])
        != sum(D(group["revenue_usd"]) for group in current["commercial_groups"])
    ):
        raise ValueError("August market split differs from current operating source")
    output, selected = [], []
    identities = set()
    august = defaultdict(D)
    for row in journal_rows:
        if row["entity"] != "SHI" or int(row["month"]) == 0 or row["account_type"] != "revenue":
            continue
        year, month = int(row["year"]), int(row["month"])
        if not 2016 <= year <= 2031 or not 1 <= month <= 12:
            raise ValueError("Receipt period is outside the authored market scope")
        identity = (row["scenario"], row["entity"], row["journal_id"], str(row["line_no"]))
        if identity in identities:
            raise ValueError("Duplicate SHI revenue journal identity")
        identities.add(identity)
        amount = -D(row["signed_usd"])
        selected.append(amount)
        account = row["account"]
        base = {
            key: row[key]
            for key in (
                "scenario",
                "entity",
                "year",
                "month",
                "journal_id",
                "line_no",
                "account",
                "source_id",
            )
        }
        if account == "SHARED_REV":
            output.append(
                dict(
                    base,
                    market_state="N/A",
                    population="INTERCOMPANY_ALLOCATION",
                    rule_id="SHARED-RECIPIENT-PERIMETER-REQUIRED",
                    receipts_usd=str(amount),
                )
            )
            continue
        if account not in EXTERNAL_ACCOUNTS:
            raise ValueError("Unclassified SHI revenue account")
        if account == "BIZ_REVENUE" and year < 2027:
            raise ValueError("Conditional business receipt promoted before its period")
        if account == "LEG_4050" and (year, month) < (2026, 9):
            raise ValueError("Separate Cradle receipt contradicts historical aggregate scope")
        if (year, month) == (2026, 8) and account != "LEG_4000":
            raise ValueError("August receipt must decompose the retained single control")
        splits = []
        if int(row["year"]) == 2026 and int(row["month"]) == 8 and account == "LEG_4000":
            august[row["scenario"]] += amount
            if amount != D(source["august_2026"]["total_shi_revenue_usd"]):
                raise ValueError("August single retained revenue control changed")
            splits = [
                ("CA", D(source["august_2026"]["ca_services_usd"]), "SHI-AUGUST-SERVICES"),
                ("WV", D(source["august_2026"]["wv_cradle_materials_usd"]), "SHI-AUGUST-CRADLE"),
            ]
        else:
            cradle = account == "LEG_4050" or (
                account == "BIZ_REVENUE" and row.get("unit") == "project-cradle"
            )
            rule = "SHI-CRADLE-DESTINATION" if cradle else "SHI-SERVICE-MARKET"
            if account == "BIZ_REVENUE" and row.get("unit") not in {
                "project-cradle",
                "foundry-field",
                "atlas-meridian",
                "advisory",
            }:
                raise ValueError("New revenue-generating business requires market facts")
            splits = [(source["rules"][rule]["state"], amount, rule)]
        if sum(value for _, value, _ in splits) != amount:
            raise ValueError("Market allocation changes source revenue")
        output.extend(
            dict(
                base,
                market_state=state,
                population="EXTERNAL_CUSTOMER",
                rule_id=rule,
                receipts_usd=str(value),
            )
            for state, value, rule in splits
        )
    if any(value != D(source["august_2026"]["total_shi_revenue_usd"]) for value in august.values()):
        raise ValueError("Duplicate August aggregate")
    if sum(D(row["receipts_usd"]) for row in output) != sum(selected):
        raise ValueError("Incomplete source-to-market bridge")
    return output
