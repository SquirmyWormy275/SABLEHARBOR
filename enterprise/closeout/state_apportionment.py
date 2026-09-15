"""State receipt factors for the finite company edition; never posts tax journals."""

import hashlib
import json
from collections import defaultdict
from decimal import ROUND_HALF_UP
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name("source") / "state_apportionment.json"
MEMBERS = ("SHI", "SHIH", "PS", "ARU", "BST")
TRANSPORT = ("ARU", "BST")
IC_ACCOUNTS = {"4100", "4700", "SHARED_REV"}
SIX = D(".000001")
PRECISION = D(".000000000001")


def il_transport_conversion(everywhere, transport_numerators, transport_denominators):
    """Schedule SUB: N_i / sum(D_subgroup) times sum(E_subgroup)."""
    members = set(everywhere)
    if members != set(transport_numerators) or members != set(transport_denominators):
        raise ValueError("Transport subgroup population mismatch")
    e = {k: D(str(v)) for k, v in everywhere.items()}
    n = {k: D(str(v)) for k, v in transport_numerators.items()}
    d = {k: D(str(v)) for k, v in transport_denominators.items()}
    if any(v < 0 for values in [e, n, d] for v in values.values()):
        raise ValueError("Negative transport gross-receipt population")
    if any(n[k] > d[k] or d[k] > e[k] for k in members):
        raise ValueError("Transport numerator/denominator exceeds eligible receipts")
    denominator, total = sum(d.values()), sum(e.values())
    if denominator == 0:
        if total:
            raise ValueError("Transport subgroup has no transport denominator")
        return {k: D(0) for k in members}
    return {k: (n[k] / denominator).quantize(SIX, rounding=ROUND_HALF_UP) * total for k in members}


def factors(everywhere, state_sales, transport_receipts, qualified_receipts, taxable_members):
    """Compute one annual scenario from already reconciled member populations."""
    if set(everywhere) != set(MEMBERS):
        raise ValueError("State group member omitted or duplicated")
    e = {m: D(str(everywhere[m])) for m in MEMBERS}
    total = sum(e.values())
    if total <= 0 or any(v < 0 for v in e.values()):
        raise ValueError("Meaningless annual receipts denominator")
    qualified = D(str(qualified_receipts))
    if not 0 <= qualified <= total:
        raise ValueError("Qualified activity exceeds group receipts")
    if qualified / total > D(".5"):
        raise ValueError("CA qualified activity exceeds50%; property/payroll three-factor inputs required")
    output = []
    for state in ["CA", "IL", "WV"]:
        numerators = {m: D(str(state_sales[state].get(m, 0))) for m in MEMBERS}
        if any(not 0 <= numerators[m] <= e[m] for m in MEMBERS):
            raise ValueError("Market numerator outside member receipts")
        if state == "IL":
            converted = il_transport_conversion(
                {m: e[m] for m in TRANSPORT},
                {m: numerators[m] for m in TRANSPORT},
                {m: transport_receipts[m] for m in TRANSPORT},
            )
            numerators.update(converted)
            nontaxable = sum(v for m, v in numerators.items() if m not in taxable_members[state])
            taxable_sales = sum(v for m, v in numerators.items() if m in taxable_members[state])
            if nontaxable and taxable_sales == 0:
                raise ValueError("Finnigan allocation lacks supported taxable-member sales basis")
            original = dict(numerators)
            for member in MEMBERS:
                numerators[member] = (
                    original[member] + nontaxable * original[member] / taxable_sales
                    if member in taxable_members[state] and taxable_sales
                    else D(0)
                )
        group_factor = sum(numerators.values()) / total
        for member in MEMBERS:
            factor = numerators[member] / total
            output.append(dict(
                jurisdiction=state, member=member, external_receipts_usd=str(e[member]),
                market_numerator_usd=str(numerators[member]), group_denominator_usd=str(total),
                member_factor=str(factor.quantize(PRECISION)),
                group_factor=str(group_factor.quantize(PRECISION)),
                member_factor_return_6dp=str(factor.quantize(SIX, rounding=ROUND_HALF_UP)),
                ca_qualified_receipts_usd=str(qualified), ca_qualified_share=str((qualified / total).quantize(PRECISION)),
                ca_three_factor_required=False, taxable_member=member in taxable_members[state],
                method="IL_SUBGROUP_FINNIGAN" if state == "IL" else "COMBINED_SINGLE_SALES",
            ))
    return output


def _identity(row):
    return (row.get("scenario", "CURRENT"), row["entity"], int(row["year"]),
            row["journal_id"], str(row.get("line_no", row["account"])))


def _validate_source(source):
    for path, digest in source["source_hashes"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Changed factor source: {path}")
    unitary = json.loads((ROOT / source["unitary_source"]).read_text())
    if set(unitary["taxpayer_members"]) != set(MEMBERS):
        raise ValueError("Unitary source membership changed")
    if source["years"] != list(range(2026, 2032)) or set(source["scenarios"]) != {"base", "downside", "expansion"}:
        raise ValueError("Changed scenario/year factor contract")
    transition = source["jan2026_aru_bst"]
    if [transition[k] for k in ["book_owned_days", "new_target_tax_days", "old_target_days"]] != [25, 24, 1]:
        raise ValueError("Changed January ownership/tax period contract")
    contracts = source["industrial_contracts"]
    if len(contracts) != 29 or len({r["contract_id"] for r in contracts}) != 29:
        raise ValueError("Industrial contract population changed")
    native_contracts = json.loads((ROOT / "industrial/source/finance.json").read_text())["contracts"]
    expected_contracts = {r["contract_id"]: r["segment"] for r in native_contracts}
    if {r["contract_id"]: r["segment"] for r in contracts} != expected_contracts:
        raise ValueError("Industrial contract identities/segments differ from controlling source")
    if any(r["transport"] != (r["segment"] in {"BST", "TRUCKING"}) for r in contracts):
        raise ValueError("Industrial transport classification changed")
    if any(r["performance_state"] != "WY" for r in contracts):
        raise ValueError("New transport territory requires actual receipts/mileage allocation")
    return source


def build(result, forecast_result, anchor, *, market_rows=None, source=None):
    """Return annual factors plus source bridges; inputs retain their own immutable editions."""
    source = _validate_source(json.loads(SOURCE.read_text()) if source is None else source)
    if market_rows is None:
        from enterprise.closeout.receipt_markets import allocate
        market_rows = allocate(result["journal_rows"])
    expected = {(s, y) for s in source["scenarios"] for y in source["years"]}
    external, markets, ic, oldtarget, qualified, legal_shi = (defaultdict(D) for _ in range(6))
    seen, periods = set(), defaultdict(set)
    for row in result["journal_rows"]:
        if int(row["month"]) == 0 or row["account_type"] != "revenue":
            continue
        identity = _identity(row)
        if identity in seen:
            raise ValueError("Duplicate legal revenue journal identity")
        seen.add(identity)
        entity, account = row["entity"], row["account"]
        if entity == "ELIM":
            if account not in IC_ACCOUNTS:
                raise ValueError("Unclassified elimination revenue")
            continue
        if entity not in set(MEMBERS) | {"RWH"}:
            raise ValueError("Unclassified legal revenue entity")
        sy = (row["scenario"], int(row["year"]))
        month = int(row["month"])
        if sy not in expected or not 1 <= month <= 12:
            raise ValueError("State factor revenue outside declared scenario/period")
        if account in IC_ACCOUNTS:
            ic[sy, entity] += -D(row["signed_usd"])
            continue
        if entity == "SHI":
            legal_shi[sy] += -D(row["signed_usd"])
            periods[sy, entity].add(month)
            continue
        if account != "4000" or entity not in {"PS", "RWH", "ARU", "BST"}:
            raise ValueError("Unclassified industrial external receipt")
        member = "PS" if entity == "RWH" else entity
        amount = -D(row["signed_usd"])
        if entity in TRANSPORT and sy[1] == 2026 and month == 1:
            oldtarget[sy, member] += amount / 25
            amount *= D(24) / 25
        external[sy, member] += amount
        periods[sy, entity].add(month)
        if entity == "RWH":
            markets[sy, "IL", member] += amount
            qualified[sy] += amount
        elif entity == "PS" and amount:
            raise ValueError("New PS external services require customer market facts")
    market_seen = set()
    for row in market_rows:
        sy = (row["scenario"], int(row["year"]))
        if sy not in expected:
            raise ValueError("SHI market row outside factor period")
        if row["population"] == "INTERCOMPANY_ALLOCATION":
            continue
        ident = (row["scenario"], row["entity"], int(row["year"]), row["journal_id"], str(row["line_no"]))
        if ident not in seen or (ident, row["market_state"]) in market_seen:
            raise ValueError("Unmatched or duplicate SHI market source")
        market_seen.add((ident, row["market_state"]))
        amount = D(row["receipts_usd"])
        external[sy, "SHI"] += amount
        state = row["market_state"]
        if state not in {"CA", "WV"}:
            raise ValueError("SHI market outside authored source")
        markets[sy, state, "SHI"] += amount
        if state == "WV":
            qualified[sy] += amount
    for sy in expected:
        if legal_shi[sy] != external[sy, "SHI"]:
            raise ValueError("SHI source-to-market revenue differs")
        for entity in ["SHI", "RWH", "ARU", "BST"]:
            if periods[sy, entity] != set(range(1, 13)):
                raise ValueError("Missing annual external revenue month population")
    # Native industrial rows retain segment detail lost in the legal monthly aggregation.
    transport, industrial_total = defaultdict(D), defaultdict(D)
    inputs = [(r, s) for r in anchor for s in source["scenarios"]]
    inputs += [(r, r["scenario"]) for r in forecast_result["journal_rows"]]
    native_seen = set()
    for row, scenario in inputs:
        if row["entity"] not in {"ARU_GROUP", "RWH_PS"} or row["account"] != "4000" or int(row["month"]) == 0:
            continue
        ident = (scenario,) + _identity(row)[1:]
        if ident in native_seen:
            raise ValueError("Duplicate native industrial receipt leg")
        native_seen.add(ident)
        sy = (scenario, int(row["year"]))
        if sy not in expected:
            raise ValueError("Native industrial receipt outside factor period")
        segment = row["segment"]
        if row["entity"] == "RWH_PS":
            member = "PS"
        elif segment == "BST":
            member = "BST"
        elif segment in {"TRUCKING", "TERMINALS", "WAREHOUSE"}:
            member = "ARU"
        else:
            raise ValueError("Unclassified native industrial segment")
        amount = -D(row["signed_usd"])
        if member in TRANSPORT and sy[1] == 2026 and int(row["month"]) == 1:
            amount *= D(24) / 25
        industrial_total[sy, member] += amount
        if segment in {"BST", "TRUCKING"}:
            transport[sy, member] += amount
    output = []
    for scenario, year in sorted(expected):
        sy = (scenario, year)
        for member in ["PS", "ARU", "BST"]:
            if abs(industrial_total[sy, member] - external[sy, member]) > D(".01"):
                raise ValueError("Native receipts do not reconcile to legal member receipts")
        annual = factors(
            {m: external[sy, m] for m in MEMBERS},
            {state: {m: markets[sy, state, m] for m in MEMBERS} for state in ["CA", "IL", "WV"]},
            {m: transport[sy, m] for m in TRANSPORT}, qualified[sy], source["nexus_members"],
        )
        pa_denominator = external[sy, "SHI"] + ic[sy, "SHI"]
        annual.append(dict(jurisdiction="PA", member="SHI", external_receipts_usd=str(external[sy, "SHI"]),
                           market_numerator_usd="0", group_denominator_usd=str(pa_denominator),
                           member_factor="0", group_factor="0", member_factor_return_6dp="0.000000",
                           taxable_member=True, method="SEPARATE_SHI_MARKET_SALES_WITH_INTERCOMPANY"))
        for row in annual:
            row.update(scenario=scenario, year=year, period_role="ANNUAL_PROVISION_SCENARIO_NOT_COMPLETED_RETURN",
                       source_id=source["document_id"], oldtarget_january7_receipts_excluded_usd=str(oldtarget[sy, row["member"]]),
                       group_intercompany_receipts_eliminated_usd=str(sum(ic[sy, m] for m in set(MEMBERS) | {"RWH"})),
                       source_contract_count=29, source_version=source["version"],
                       authority_source="STATE_UNITARY_ANALYSIS.md;STATE_TAX_IMPLEMENTATION_ADDENDUM.md",
                       fact_state="AUTHORED_MARKET_FACTS_WITH_RECONCILED_SOURCE_RECEIPTS", monetary_journals_posted=0)
        output.extend(annual)
    return output
