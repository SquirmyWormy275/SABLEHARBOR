"""Export holder funding and reconcile historical capital without posting cash."""

import json
from collections import defaultdict
from decimal import Decimal as D

from industrial.planning.enterprise import write_csv

from .capital_register import build as register_build
from .historical_tax import build as history_build


def opening_bridge(journal, register):
    historical = history_build()
    subscriptions = D(register["verified_subscription_receipts_usd"])
    operating_result = sum(D(r["book_pretax_usd"]) for r in historical["annual"])
    expected_core = subscriptions + operating_result
    grouped = defaultdict(list)
    identities = set()
    for row in journal:
        if row["entity"] != "SHI" or int(row["year"]) != 2026 or int(row["month"]) != 0:
            continue
        identity = row["scenario"], row["journal_id"], row["line_no"]
        if identity in identities:
            raise ValueError("Duplicate parent opening journal leg")
        identities.add(identity)
        if row["account_type"] == "equity":
            grouped[row["scenario"]].append(row)
    if set(grouped) != {"base", "downside", "expansion"}:
        raise ValueError("Incomplete parent opening equity population")
    summary, details = [], []
    for scenario, rows in sorted(grouped.items()):
        legacy = [r for r in rows if r["account"] == "LEG_3000"]
        if {r["source_id"] for r in legacy} != {"LEGACY-OPEN-2026", "SH-VOICE-GW-01"} or len(legacy) != 2:
            raise ValueError("Core initialization/goodwill equity bridge changed")
        corrected_core = -sum(D(r["signed_usd"]) for r in legacy)
        if corrected_core != expected_core:
            raise ValueError("Historical subscriptions and operating results do not explain corrected Core opening")
        components = defaultdict(D)
        for row in rows:
            source = row["source_id"]
            category = (
                "CORE_INITIALIZATION" if row["account"] == "LEG_3000"
                else "INDUSTRIAL_NONCASH_RECONSTRUCTION" if source == "OPEN-MEMBER-BASIS"
                else "LEGACY_SUBSEQUENT_RETAINED_RESULT" if source == "LEGACY-OPEN-2026"
                else "DATED_OPENING_CORRECTION"
            )
            equity = -D(row["signed_usd"])
            components[category] += equity
            details.append(dict(
                scenario=scenario, legal_entity="SHI", year=2026, month=0,
                source_id=source, journal_id=row["journal_id"], line_no=row["line_no"],
                account=row["account"], category=category, equity_effect_usd=str(equity),
                description=row.get("description", ""), additional_cash_posted_usd="0",
            ))
        industrial = [r for r in rows if r["source_id"] == "OPEN-MEMBER-BASIS"]
        subsidiary = [r for r in journal if r["scenario"] == scenario and r["entity"] == "PS"
                      and int(r["year"]) == 2026 and int(r["month"]) == 0 and r["account"] == "3000"]
        if (len(industrial) != 1 or len(subsidiary) != 1
                or D(industrial[0]["signed_usd"]) != D(subsidiary[0]["signed_usd"])):
            raise ValueError("Industrial noncash reconstruction differs from subsidiary opening capital")
        if components["INDUSTRIAL_NONCASH_RECONSTRUCTION"] != D(register["historical_contribution_receipts_usd"]):
            raise ValueError("Authored historical contribution differs from opening reconstruction")
        total = sum(components.values(), D(0))
        summary.append(dict(
            scenario=scenario, legal_entity="SHI", historical_subscription_paid_in_usd=str(subscriptions),
            historical_industrial_contribution_paid_in_usd=register["historical_contribution_receipts_usd"],
            total_historical_paid_in_usd=register["total_historical_paid_in_usd"],
            historical_2016_2022_pretax_result_usd=str(operating_result),
            corrected_core_initialization_equity_usd=str(corrected_core),
            industrial_noncash_reconstruction_usd=str(components["INDUSTRIAL_NONCASH_RECONSTRUCTION"]),
            legacy_subsequent_retained_result_usd=str(components["LEGACY_SUBSEQUENT_RETAINED_RESULT"]),
            dated_opening_corrections_usd=str(components["DATED_OPENING_CORRECTION"]),
            total_parent_opening_equity_usd=str(total), additional_ledger_cash_or_equity_posted_usd="0",
            classification="Source bridge; 2026 noncash reconstruction represents the separately authored 2025 holder contribution, counted once; no additional current receipt",
        ))
    return summary, details


def export(output, successor):
    """Write existing-schema flat schedules alongside the complete source-bound register."""
    journal = successor["journal_rows"]
    result = register_build(journal)
    opening, details = opening_bridge(journal, result["register"])
    result["opening_equity_bridge"] = opening
    result["opening_equity_components"] = details
    events, allocations = [], []
    for item in result["events"]:
        row = dict(item["event"])
        row.update({key: value for key, value in item.items() if key not in {"event", "rows"}})
        events.append(row)
        for allocation in item["rows"]:
            allocations.append({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
                                for key, value in allocation.items()})
    populations = {
        "capital_unit_history": result["register"]["unit_history"],
        "capital_historical_contribution_holders": result["register"]["historical_industrial_contribution"]["holder_rows"],
        "capital_historical_downstream_funding": result["register"]["historical_industrial_contribution"]["downstream"],
        "capital_funding_events": events,
        "capital_holder_allocations": allocations,
        "capital_holder_rollforward": result["holder_rollforward"],
        "capital_opening_equity_bridge": opening,
        "capital_opening_equity_components": details,
    }
    for name, rows in populations.items():
        write_csv(output / f"{name}.csv", [
            {key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
             for key, value in row.items()} for row in rows
        ])
    (output / "capital_register.json").write_text(json.dumps(result, indent=2) + "\n")
    return {"population_counts": {name: len(rows) for name, rows in populations.items()},
            "historical_subscription_paid_in_usd": result["register"]["verified_subscription_receipts_usd"],
            "historical_industrial_contribution_paid_in_usd": result["register"]["historical_contribution_receipts_usd"],
            "total_historical_paid_in_usd": result["register"]["total_historical_paid_in_usd"],
            "total_units": result["register"]["total_units"], "additional_ledger_postings": 0}
