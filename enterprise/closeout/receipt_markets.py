"""Source-level SHI market facts; tax sourcing and filing groups remain separate."""

import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

SOURCE = Path(__file__).with_name("source") / "receipt_markets.json"
EXTERNAL_ACCOUNTS = {"LEG_4000", "LEG_4010", "LEG_4020", "LEG_4050", "BIZ_REVENUE"}


def allocate(journal_rows, source=None):
    source = json.loads(SOURCE.read_text()) if source is None else source
    if (
        source["rules"]["SHI-SERVICE-MARKET"]["state"] != "CA"
        or source["rules"]["SHI-CRADLE-DESTINATION"]["state"] != "WV"
    ):
        raise ValueError("Receipt territory changed; renew source reconciliation")
    output, selected = [], []
    identities = set()
    august = defaultdict(D)
    for row in journal_rows:
        if row["entity"] != "SHI" or int(row["month"]) == 0 or row["account_type"] != "revenue":
            continue
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
