"""Causal sizing, recovery and gross unfunded cash scenarios; never actual postings."""

from collections import defaultdict
from datetime import date
from decimal import Decimal as D
import math


def number(value):
    if type(value) not in (int, float, str):
        raise ValueError("Expected finite quantity, not boolean")
    result = D(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("Expected finite nonnegative quantity")
    return result


def validate(a, buckets):
    required = {
        "origin",
        "drivers",
        "hardware",
        "scenarios",
        "commercial",
        "recovery",
        "workforce",
        "phases",
        "control_implementations",
        "rooms",
    }
    if set(a) != required:
        raise ValueError("Unknown or missing runtime implementation section")
    for group in ("drivers", "hardware", "commercial"):
        for key, value in a[group].items():
            if key in {"throughput_state", "reno_billing", "boise_billing"}:
                if not isinstance(value, str) or not value:
                    raise ValueError("Missing assumption classification")
            elif key == "reno_power_included":
                if type(value) is not bool:
                    raise ValueError("Power inclusion requires boolean")
            else:
                number(value)
    for group in ("drivers", "hardware", "commercial", "recovery", "workforce"):
        for key, value in a[group].items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                number(value)
    for key in (
        "active_share",
        "atlas_hosted_share",
        "foundry_central_share",
        "concurrent_ai_share",
        "daily_change_fraction",
    ):
        if not 0 <= number(a["drivers"][key]) <= 1:
            raise ValueError(f"Invalid driver fraction: {key}")
    h = a["hardware"]
    for key in (
        "cpu_cores",
        "cpu_memory_gib",
        "gpu_count",
        "gpu_memory_gib",
        "accepted_tokens_per_second",
        "storage_usable_tib",
        "rack_usable_u",
        "rack_max_kw",
    ):
        if number(h[key]) <= 0:
            raise ValueError(f"Invalid hardware divisor: {key}")
    if not 0 < number(h["utilization_ceiling"]) < 1:
        raise ValueError("Invalid utilization ceiling")
    if a["recovery"]["performance_verified"] is not False:
        raise ValueError("Capacity calculation cannot verify recovery performance")
    wf = a["workforce"]
    if not 0 < number(wf["productive_fraction"]) <= 1:
        raise ValueError("Invalid productive availability")
    if any(
        wf[k] != 0
        for k in (
            "verified_reusable_fte",
            "authorized_new_positions",
            "occupied_new_positions",
        )
    ):
        raise ValueError("No new position authority or reusable capacity is evidenced")
    seen = set()
    for role in wf["roles"]:
        if role["id"] in seen or role["owner"] == "TEAM-audit":
            raise ValueError("Duplicate role or management assigned to audit")
        seen.add(role["id"])
        if not 0 < number(role["allocated_fraction"]) <= 1:
            raise ValueError("Role overallocation")
        number(role["required_fte"])
        number(role["annual_loaded_cost"])
    phases = {p["id"]: p for p in a["phases"]}
    if len(phases) != len(a["phases"]):
        raise ValueError("Duplicate phase")
    total = defaultdict(int)
    for p in phases.values():
        if date.fromisoformat(p["start"]) > date.fromisoformat(p["end"]):
            raise ValueError("Reversed schedule dates")
        total[p["bucket"]] += number(p["cost"])
        if p["bucket"] not in buckets:
            raise ValueError("Unknown capital cost object")
        if any(p[k] != 0 for k in ("committed", "invoiced", "paid")):
            raise ValueError(
                "Unapproved forecast cannot become an obligation or payment"
            )
        for dep in p["dependencies"]:
            if dep not in phases or dep == p["id"] or phases[dep]["end"] > p["start"]:
                raise ValueError(
                    "Invalid phase dependency or impossible predecessor date"
                )
        if p["id"] != "RT-LAND" and p["actual_completion"] is not None:
            raise ValueError("Forecast completion is not accepted history")
    for bucket, amount in total.items():
        if amount != buckets[bucket]:
            raise ValueError(f"Phase/budget mismatch: {bucket}")
    ids = set()
    for c in a["control_implementations"]:
        if c["implementation_id"] in ids:
            raise ValueError("Duplicate local control implementation")
        ids.add(c["implementation_id"])
        if (
            c["operating_assessment"] != "NOT_ASSERTED"
            or c["evidence_origin"] != "SYNTHETIC_REFERENCE"
        ):
            raise ValueError(
                "Synthetic controls cannot acquire operating effectiveness"
            )
        if (
            c["implementation_owner_role"] == "Internal Audit"
            or not c["evidence_sources"]
        ):
            raise ValueError("Invalid control ownership or evidence requirement")
    if sum(number(r["area_sf"]) for r in a["rooms"]) != 12000:
        raise ValueError("Room program does not reconcile to 12,000 sf")


def capacity(a, year, scenario, recovery=False):
    if type(year) is not int or not 2027 <= year <= 2036:
        raise ValueError("Capacity year must be an explicit 2027–2036 integer")
    d, h, r = a["drivers"], a["hardware"], a["recovery"]
    s = a["scenarios"][scenario]
    elapsed = year - 2027
    factor = s["demand_factor"] * (1 + s["annual_user_growth"]) ** elapsed
    users = (
        d["internal_users"]
        + d["atlas_clients"] * d["atlas_hosted_share"] * d["atlas_users_per_client"]
        + d["foundry_clients"]
        * d["foundry_central_share"]
        * d["foundry_users_per_client"]
    ) * factor
    active = users * d["active_share"]
    cores = (
        d["fixed_cpu_cores"]
        + active * d["requests_per_active_second"] * d["cpu_seconds_per_request"]
    )
    ram = d["fixed_memory_gib"] + active * d["memory_gib_per_active"]
    tokens_s = (
        users
        * d["tasks_per_user_day"]
        * d["tokens_per_task"]
        * d["peak_factor"]
        / (d["service_window_hours"] * 3600)
    )
    sessions = math.ceil(users * d["concurrent_ai_share"])
    storage = (
        d["durable_tib"]
        * d["retention_years"]
        / d["baseline_retention_years"]
        * (1 + d["annual_storage_growth"]) ** elapsed
        * s["demand_factor"]
    )
    if recovery:
        cores *= r["cpu_share"]
        ram *= r["cpu_share"]
        tokens_s *= r["ai_share"]
        sessions = math.ceil(sessions * r["ai_share"])
        storage *= r["storage_share"]
    throughput = h["accepted_tokens_per_second"] * (1 + s["efficiency_gain"]) ** elapsed
    model_gib = d["model_parameters_billion"] * 1e9 * d["weight_bits"] / 8 / 2**30
    memory_per_system = h["gpu_count"] * h["gpu_memory_gib"]
    if model_gib >= memory_per_system:
        raise ValueError("Model weights exceed accelerator-system memory")
    ceiling = h["utilization_ceiling"]
    cpu = (
        math.ceil(max(cores / h["cpu_cores"], ram / h["cpu_memory_gib"]) / ceiling) + 1
    )
    gpu = (
        max(
            math.ceil(tokens_s / throughput / ceiling),
            math.ceil(
                sessions
                * d["kv_gib_per_session"]
                * d["context_tokens"]
                / d["kv_reference_context_tokens"]
                / (memory_per_system - model_gib)
            ),
        )
        + 1
    )
    # Each shelf is an independently protected copy; two copies plus one failure spare.
    shelves = math.ceil(storage / h["storage_usable_tib"]) * 2 + 1
    peak = (
        cpu * h["cpu_peak_kw"]
        + gpu * h["gpu_system_peak_kw"]
        + shelves * h["storage_peak_kw"]
        + h["network_hsm_peak_kw"]
    )
    typical = (
        cpu * h["cpu_typical_kw"]
        + gpu * h["gpu_system_typical_kw"]
        + shelves * h["storage_typical_kw"]
        + h["network_hsm_typical_kw"]
    )
    units = (
        cpu * h["cpu_u"]
        + gpu * h["gpu_system_u"]
        + shelves * h["storage_u"]
        + h["network_hsm_u"]
    )
    items = []
    for kind, count, prefix in [
        ("CPU", cpu, "cpu"),
        ("GPU", gpu, "gpu_system"),
        ("STORAGE", shelves, "storage"),
        ("NETWORK_HSM", 1, "network_hsm"),
    ]:
        for n in range(count):
            weight_key = (
                "gpu_system_weight_kg"
                if prefix == "gpu_system"
                else prefix + "_weight_kg"
            )
            weight = h[weight_key]
            items.append(
                dict(
                    id=f"{kind}-{n + 1:03}",
                    kind=kind,
                    u=h[prefix + "_u"],
                    peak_kw=h[prefix + "_peak_kw"],
                    weight_kg=weight,
                )
            )
    placements = pack_racks(items, h)
    weight = sum(i["weight_kg"] for i in items)
    racks = len(placements)
    cost = (
        cpu * h["cpu_price"]
        + gpu * h["gpu_system_price"]
        + shelves * h["storage_price"]
        + h["network_hsm_price"]
    )
    replication = (
        storage
        * d["daily_change_fraction"]
        * 2**40
        * 8
        / (86400 * 1e9)
        * (1 + r["protocol_overhead_fraction"])
        / r["compression_ratio"]
    )
    full_restore_hours = (
        storage
        * 2**40
        * 8
        * (1 + r["protocol_overhead_fraction"])
        / (r["replication_gbps"] * 1e9 * 3600)
    )
    return dict(
        year=year,
        scenario=scenario,
        site="BOISE" if recovery else "RENO",
        users=round(users, 2),
        cores=round(cores, 2),
        memory_gib=round(ram, 2),
        tokens_per_second=round(tokens_s, 2),
        cpu_hosts=cpu,
        gpu_systems=gpu,
        storage_shelves=shelves,
        durable_tib=round(storage, 2),
        rack_u=units,
        racks=racks,
        rack_placements=placements,
        equipment_weight_kg=weight,
        peak_kw=round(peak, 3),
        typical_synthetic_kw=round(typical, 3),
        equipment_cost=cost,
        replication_required_gbps=round(replication, 4),
        full_network_restore_hours=round(full_restore_hours, 2),
        network_sufficient=replication <= r["replication_gbps"],
        performance_verified=False,
        sizing_state="SYNTHETIC_CONFIGURATION_CLASS_NOT_BENCHMARK",
        minimum_service_scope="Basic institutional records and prioritized transactions; accelerator throughput degraded"
        if recovery
        else "Full planning workload",
    )


def pack_racks(items, hardware):
    """First-fit decreasing physical placement; each A/B feed supports the full rack."""
    limits = {
        "u": hardware["rack_usable_u"],
        "peak_kw": hardware["rack_max_kw"],
        "weight_kg": hardware["rack_max_weight_kg"],
    }
    racks = []
    for item in sorted(items, key=lambda i: (-i["peak_kw"], -i["u"], i["id"])):
        if any(item[k] > limit for k, limit in limits.items()):
            raise ValueError("Single appliance exceeds rack configuration")
        target = next(
            (
                r
                for r in racks
                if all(r[k] + item[k] <= limit for k, limit in limits.items())
            ),
            None,
        )
        if target is None:
            target = dict(
                id=f"RACK-{len(racks) + 1:02}",
                u=0,
                peak_kw=0,
                weight_kg=0,
                equipment=[],
            )
            racks.append(target)
        target["equipment"].append(dict(item, first_u=target["u"] + 1))
        for key in limits:
            target[key] += item[key]
    return racks


def recovery_gate(
    size, available_kw, prepositioned, independent_bootstrap, accepted_test=False
):
    reasons = []
    if size["peak_kw"] > available_kw:
        reasons.append("INSUFFICIENT_POWER")
    if not size["network_sufficient"]:
        reasons.append("INSUFFICIENT_REPLICATION")
    if not prepositioned:
        reasons.append("PREPOSITIONED_COPY_MISSING")
    if not independent_bootstrap:
        reasons.append("BOOTSTRAP_NOT_VERIFIED")
    return {
        "design_gate": "FAIL" if reasons else "PASS",
        "reasons": reasons,
        "operating_recovery": "ELIGIBLE_FOR_EVIDENCE_REVIEW"
        if not reasons and accepted_test
        else "NOT_ASSERTED",
    }


def workforce(a, owned=False):
    w = a["workforce"]
    productive = w["hours_per_week"] * w["weeks_per_year"] * w["productive_fraction"]
    required = sum(r["required_fte"] * r["allocated_fraction"] for r in w["roles"])
    payroll = sum(r["required_fte"] * r["annual_loaded_cost"] for r in w["roles"])
    guard_fte = 8760 / productive if owned else 0
    # Budget discrete relief, not a fractional guard advertised as continuous coverage.
    guard_positions = math.ceil(guard_fte)
    facilities = 2 if owned else 0
    return dict(
        required_technical_fte=required,
        productive_hours_per_fte=productive,
        authorized_new_positions=w["authorized_new_positions"],
        occupied_new_positions=w["occupied_new_positions"],
        verified_reusable_fte=w["verified_reusable_fte"],
        proposed_new_technical_positions=math.ceil(required),
        continuous_security_fte=round(guard_fte, 4),
        proposed_guard_positions=guard_positions,
        proposed_facilities_positions=facilities,
        annual_gross_payroll=payroll + guard_positions * 105000 + facilities * 155000,
        coverage="Colo provider facility coverage plus internal on-call; owned scenario adds one continuous security seat",
        personnel_state="UNAUTHORIZED_REQUIREMENT_NOT_OCCUPIED_ROSTER",
    )


def colo_charge(draw, committed, rate, billing, power_included=True, energy_charge=0):
    if power_included and energy_charge:
        raise ValueError("Power-inclusive colocation cannot charge utility power again")
    if billing not in ("MEASURED", "COMMITTED"):
        raise ValueError("Unknown billing method")
    return number(draw if billing == "MEASURED" else committed) * number(rate) + number(
        energy_charge
    )


def phase_cash(a, scenario):
    result = defaultdict(lambda: D(0))
    delay = a["scenarios"][scenario]["construction_delay_months"]
    for p in a["phases"]:
        if p["id"] == "RT-CONTINGENCY":
            continue  # Unspent reserve is funding capacity, not cash expenditure.
        start, end = date.fromisoformat(p["start"]), date.fromisoformat(p["end"])
        first, last = start.year * 12 + start.month - 1, end.year * 12 + end.month - 1
        shift = delay if start.year >= 2027 else 0
        count = last - first + 1
        monthly = (number(p["cost"]) / count).quantize(D("0.01"))
        for n in range(count):
            y, m = divmod(first + n + shift, 12)
            amount = (
                monthly if n < count - 1 else number(p["cost"]) - monthly * (count - 1)
            )
            result[(y, m + 1)] += amount
    return result


def finance(data):
    a = data["capital"]["implementation_assumptions"]
    c = a["commercial"]
    annual, monthly = [], []
    for scenario in a["scenarios"]:
        phases = phase_cash(a, scenario)
        previous_hardware = 0
        for year in range(2026, 2037):
            size = capacity(a, max(year, 2027), scenario)
            dr = capacity(a, max(year, 2027), scenario, True)
            equipment = size["equipment_cost"] + dr["equipment_cost"]
            replacement = (
                year >= 2027 and (year - 2027) % c["hardware_refresh_years"] == 0
            )
            hardware = (
                equipment
                if replacement
                else max(0, equipment - previous_hardware)
                if year >= 2027
                else 0
            )
            previous_hardware = equipment if year >= 2027 else 0
            # Explicit design envelope expansion; commitment remains unexecuted.
            reno_commit = max(75, math.ceil(size["peak_kw"] / 25) * 25)
            reno = (
                colo_charge(
                    size["typical_synthetic_kw"],
                    reno_commit,
                    c["reno_rate_per_kw_month"],
                    "COMMITTED",
                )
                * 12
            )
            boise = (
                colo_charge(
                    dr["typical_synthetic_kw"],
                    dr["peak_kw"],
                    data["sites"]["sites"][1][
                        "published_planning_price_usd_per_kw_month"
                    ],
                    "MEASURED",
                )
                * 12
            )
            escalator = D(str((1 + c["annual_escalation"]) ** max(0, year - 2027)))
            payroll = workforce(a)["annual_gross_payroll"] if year >= 2027 else 0
            operating = (
                (
                    reno
                    + boise
                    + (
                        c["connectivity_per_site_month"]
                        + c["remote_hands_per_site_month"]
                    )
                    * 24
                    + c["software_support_year"]
                    + D(str(size["durable_tib"]))
                    * (c["backup_per_tib_month"] * 12 + c["offline_per_tib_year"])
                    + payroll
                )
                * escalator
                if year >= 2027
                else D(0)
            )
            phase_total = sum(v for (y, m), v in phases.items() if y == year)
            terminal = (
                number(c["terminal_sale_value"])
                if year == c["terminal_sale_year"]
                else D(0)
            )
            gross = phase_total + hardware + operating
            net = gross - terminal
            annual.append(
                dict(
                    scenario=scenario,
                    year=year,
                    facility_cash_request=str(phase_total),
                    hardware_cash_request=str(hardware),
                    operating_cash_request=str(operating.quantize(D(".01"))),
                    terminal_cash=str(terminal),
                    gross_cash_request=str(gross.quantize(D(".01"))),
                    net_cash_request=str(net.quantize(D(".01"))),
                    discounted_net_cash=str(
                        (
                            net / (1 + number(c["discount_rate"])) ** (year - 2026)
                        ).quantize(D(".01"))
                    ),
                    actual_paid_cash="0.00",
                    evidenced_funding="0.00",
                    funding_gap=str(gross.quantize(D(".01"))),
                    contingency_unspent="500000.00",
                    state="GROSS_UNFUNDED_PLANNING_REQUEST",
                    reno_commit_design_kw=reno_commit,
                    boise_peak_design_kw=dr["peak_kw"],
                    envelope_sufficient=size["peak_kw"] <= 100 and dr["peak_kw"] <= 25,
                )
            )
            if year <= 2031:
                for month in range(1, 13):
                    monthly.append(
                        dict(
                            scenario=scenario,
                            year=year,
                            month=month,
                            facility_cash_request=str(phases[(year, month)]),
                            hardware_cash_request=str(hardware if month == 1 else 0),
                            operating_cash_request=str(operating / 12),
                            actual_paid_cash="0.00",
                        )
                    )
    return {
        "annual": annual,
        "monthly": monthly,
        "land_adjustment": {
            "id": "RT-LAND-20260904",
            "entity": "SHI",
            "effective_on": "2026-09-04",
            "recorded_on": "2026-09-11",
            "debit_land": "3000000.00",
            "credit_unresolved_settlement_clearing": "3000000.00",
            "cash": "0.00",
            "posting_state": "RECONCILIATION_OVERLAY_NOT_RELEASED_LEDGER",
            "limitation": "Clearing is unresolved settlement, not evidence of vendor financing or a payable agreement.",
        },
        "legacy_state": "2026 calibration and business/operations predecessors preserved; gross runtime requests are not funded consolidated statements",
    }


def investment(data):
    """Common hardware/workload/Boise costs cancel only after being shown in both cases."""
    a = data["capital"]["implementation_assumptions"]
    c = a["commercial"]
    rows = []
    requirements = finance(data)["annual"]
    for scenario in a["scenarios"]:
        migration_year = (
            2029 + a["scenarios"][scenario]["construction_delay_months"] // 12
        )
        for req in (r for r in requirements if r["scenario"] == scenario):
            year = req["year"]
            size = capacity(a, max(2027, year), scenario)
            hardware = D(req["hardware_cash_request"])
            common = D(req["operating_cash_request"])
            phases = D(req["facility_cash_request"])
            reno = (
                colo_charge(
                    size["typical_synthetic_kw"],
                    req["reno_commit_design_kw"],
                    c["reno_rate_per_kw_month"],
                    "COMMITTED",
                )
                * 12
            )
            reno *= D(str((1 + c["annual_escalation"]) ** max(0, year - 2027)))
            owned_running = D(
                str(
                    size["typical_synthetic_kw"]
                    * 8760
                    * c["owned_pue"]
                    * c["owned_electricity_per_kwh"]
                    + c["owned_maintenance_year"]
                )
            )
            owned_running += (
                workforce(a, True)["annual_gross_payroll"]
                - workforce(a)["annual_gross_payroll"]
            )
            # Commissioning/migration is an explicit hypothetical acceptance, never world-state.
            owned_opex = (
                common - reno + owned_running if year >= migration_year else common
            )
            if year == migration_year:
                owned_opex += (
                    reno * D(c["migration_overlap_months"]) / 12 + c["migration_cost"]
                )
            colo_cash = hardware + common + (3000000 if year == 2026 else 0)
            owned_cash = hardware + owned_opex + phases
            terminal = D(req["terminal_cash"])
            if year == 2036:
                owned_cash += c["decommission_cost"]
            discount = (1 + number(c["discount_rate"])) ** (year - 2026)
            rows.append(
                dict(
                    scenario=scenario,
                    year=year,
                    colo_cash=str(colo_cash.quantize(D(".01"))),
                    owned_cash_before_sale=str(owned_cash.quantize(D(".01"))),
                    terminal_sale=str(terminal),
                    owned_cash_after_sale=str(
                        (owned_cash - terminal).quantize(D(".01"))
                    ),
                    incremental_discounted_cost=str(
                        ((owned_cash - terminal - colo_cash) / discount).quantize(
                            D(".01")
                        )
                    ),
                    migration_assumption=migration_year,
                    state="HYPOTHETICAL_ACCEPTANCE_NOT_CONSTRUCTION_HISTORY",
                    limitation="Tax benefits zero; no residual credit before terminal period; critical-plant replacement beyond horizon separately unpriced.",
                )
            )
    return rows
