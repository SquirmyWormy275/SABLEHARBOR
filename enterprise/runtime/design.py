"""Versioned deployment requirements and component-rated engineering arithmetic."""

from datetime import date, timedelta
import copy
import math


def validate(design):
    if (
        design["image_admission"]["deployed"] is not False
        or design["image_admission"]["signed_digest"] is not None
    ):
        raise ValueError("Configuration choices are not a qualified deployment")
    mix = design["ai_job_mix"]
    if abs(sum(p["task_share"] for p in mix["profiles"]) - 1) > 1e-9 or any(
        p["relative_tokens"] <= 0
        or not 0 <= p["input_fraction"] <= 1
        or not 0 < p["context_fraction"] <= 1
        for p in mix["profiles"]
    ):
        raise ValueError("Invalid AI workload mixture")
    if mix["shared_private_training_authorized"] or mix["frontier_training_authorized"]:
        raise ValueError(
            "Runtime inference does not authorize private common-model or frontier training"
        )
    recovery = design["recovery_services"]
    known = {r["service_id"] for r in recovery}
    if len(known) != len(recovery):
        raise ValueError("Duplicate recovery service")
    resolved = set()
    for row in recovery:
        if (
            not set(row["dependencies"]) <= resolved
            or row["performance_verified"] is not False
        ):
            raise ValueError(
                "Recovery dependencies must precede a service; performance is unverified"
            )
        if row["tier"] not in {"BOOTSTRAP", "PRODUCTION", "ALEXANDRIA", "DEVELOPMENT"}:
            raise ValueError("Unknown recovery tier")
        resolved.add(row["service_id"])
    direction = design["enterprise_vendor_direction"]
    bindings = {row["domain"]: row for row in direction["bindings"]}
    approved = {
        "IAM": "Okta",
        "IGA": "IBM Security Verify",
        "HR": "SAP SuccessFactors",
        "UEM": "IBM MaaS360",
        "EDR_EPP": "Palo Alto Networks Cortex XDR",
        "NGFW": "Palo Alto Networks",
        "ZTNA_SASE": "Palo Alto Networks Prisma Access",
        "SIEM": "Palo Alto Networks Cortex",
        "DLP": "Palo Alto Networks Enterprise DLP",
        "CNAPP": "Palo Alto Networks Prisma Cloud",
    }
    if (
        len(bindings) != len(direction["bindings"])
        or set(bindings) != set(approved)
        or any(not bindings[k]["product"].startswith(v) for k, v in approved.items())
    ):
        raise ValueError(
            "Runtime vendor selection conflicts with accepted enterprise direction"
        )
    if direction["contracts_executed"] or direction["deployed"]:
        raise ValueError("Vendor direction is not contract or deployment evidence")
    platform = design["platform"]
    if next(p for p in platform if p["id"] == "IDENTITY")["product"] != "Okta":
        raise ValueError("Enterprise identity must follow the accepted Okta decision")
    ids = {p["id"] for p in platform}
    if len(ids) != len(platform):
        raise ValueError("Duplicate platform component")
    for row in platform:
        if not set(row["dependencies"]) <= ids or row["id"] in row["dependencies"]:
            raise ValueError("Unknown/self platform dependency")
        if row["support_until"] and date.fromisoformat(row["support_until"]) <= date(
            2026, 9, 11
        ):
            raise ValueError("Unsupported baseline product")
    a = design["asset_policy"]
    if (
        a["land_life_years"] is not None
        or a["incentive_credit"]
        or a["tax_shield_credit"]
    ):
        raise ValueError("Land depreciation or unsupported credits")
    if (
        not 0 <= a["refundable_deposit_fraction"] < 1
        or not 0 <= a["invoice_retention_fraction"] < 1
    ):
        raise ValueError("Invalid financial schedule fraction")
    e = design["electrical"]
    for key in (
        "voltage_ll",
        "power_factor",
        "generator_power_factor",
        "cooling_design_cop",
        "rack_voltage_ll",
    ):
        if e[key] <= 0:
            raise ValueError("Invalid engineering divisor")
    if not 0 < e["continuous_loading_fraction"] <= 1 or e["rack_feed_count"] != 2:
        raise ValueError("Invalid A/B feed configuration")
    for stage in ("initial", "expanded"):
        for key in (
            "ups_modules_per_path",
            "ups_paths",
            "generator_count",
            "cooling_modules",
        ):
            if type(e[stage][key]) is not int or e[stage][key] < 1:
                raise ValueError("Component count must be a positive integer")
        if e[stage]["ups_paths"] != 2:
            raise ValueError("Two UPS paths are required")
        result = engineering(design, stage)
        if not result["design_arithmetic_sufficient"]:
            raise ValueError("Insufficient component-rated plant design")
    return True


def engineering(design, stage="initial"):
    e = design["electrical"]
    s = e[stage]
    it = s["usable_it_kw"]
    heat = it * (1 + e["ups_loss_fraction"])
    cooling_input = heat / e["cooling_design_cop"]
    peak_input = heat + cooling_input + s["recharge_kw"] + s["other_peak_kw"]
    n1_generation = (s["generator_count"] - 1) * e["generator_unit_kw"]
    n1_cooling = (s["cooling_modules"] - 1) * e["cooling_module_thermal_kw"]
    one_path = s["ups_modules_per_path"] * e["ups_module_kw"]
    service_a = (
        e["service_kw"] * 1000 / (math.sqrt(3) * e["voltage_ll"] * e["power_factor"])
    )
    path_a = one_path * 1000 / (math.sqrt(3) * e["voltage_ll"] * e["power_factor"])
    generator_a = (
        e["generator_unit_kw"]
        * 1000
        / (math.sqrt(3) * e["voltage_ll"] * e["generator_power_factor"])
    )
    rack_delivery_kw = (
        e["rack_voltage_ll"]
        * e["rack_feed_a"]
        * math.sqrt(3)
        * e["power_factor"]
        * e["continuous_loading_fraction"]
        / 1000
    )
    sufficient = (
        one_path >= it
        and n1_generation >= peak_input
        and n1_cooling >= heat
        and peak_input <= e["service_kw"]
        and service_a <= e["service_breaker_a"] * e["continuous_loading_fraction"]
        and path_a <= s["ups_feeder_a"] * e["continuous_loading_fraction"]
        and generator_a <= e["generator_breaker_a"] * e["continuous_loading_fraction"]
    )
    return dict(
        stage=stage,
        usable_it_kw=it,
        heat_rejection_kw=round(heat, 2),
        cooling_input_kw=round(cooling_input, 2),
        peak_facility_input_kw=round(peak_input, 2),
        ups_surviving_path_kw=one_path,
        generation_n1_kw=n1_generation,
        cooling_n1_thermal_kw=n1_cooling,
        service_current_a=round(service_a, 2),
        ups_path_current_a=round(path_a, 2),
        generator_current_a=round(generator_a, 2),
        rack_single_feed_kw=round(rack_delivery_kw, 2),
        design_arithmetic_sufficient=sufficient,
        commissioned_kw=0,
        status="CONCEPT_COMPONENT_RATINGS_NOT_LICENSED_ENGINEERING",
        upstream_dependency="One utility/service switchgear boundary; A/B feeds do not prove two independent utilities",
    )


def export(a):
    from .planning import capacity

    d = a["technical_design"]
    if (
        d["ai_job_mix"]["background_preemptible_share"]
        > 1 - a["hardware"]["utilization_ceiling"]
    ):
        raise ValueError(
            "Preemptible background tasks exceed available operating headroom"
        )
    validate(d)
    if engineering(d)["rack_single_feed_kw"] < a["hardware"]["rack_max_kw"]:
        raise ValueError("Rack single-feed capacity is below the rack design limit")
    calibrated = copy.deepcopy(a)
    calibrated["hardware"]["gpu_system_peak_kw"] = d["hardware_reference"][
        "maximum_system_kw"
    ]
    cases = []
    for recovery in (False, True):
        size = capacity(calibrated, 2027, "base", recovery)
        cases.append(
            {
                "site": size["site"],
                "reference_maximum_peak_kw": size["peak_kw"],
                "racks": size["racks"],
                "initial_envelope_kw": 25 if recovery else 100,
                "envelope_sufficient": size["peak_kw"] <= (25 if recovery else 100),
                "state": "REFERENCE_MAXIMUM_SENSITIVITY_NOT_ACCEPTED_BOM",
            }
        )
    throughput_cases = []
    for name in ("low", "high"):
        alternative = copy.deepcopy(a)
        alternative["hardware"]["assumed_tokens_per_second"] = a["hardware"][
            "assumed_tokens_per_second_" + name
        ]
        for recovery in (False, True):
            size = capacity(alternative, 2027, "base", recovery)
            throughput_cases.append(
                dict(
                    bound=name,
                    site=size["site"],
                    assumed_tokens_per_second=alternative["hardware"][
                        "assumed_tokens_per_second"
                    ],
                    gpu_systems=size["gpu_systems"],
                    peak_kw=size["peak_kw"],
                    state="UNMEASURED_SENSITIVITY_NOT_PROBABILITY",
                )
            )
    lifecycle = []
    for row in d["platform"]:
        lifecycle.append(
            dict(
                id=row["id"],
                version=row["version"],
                upgrade_planning_by=str(
                    date.fromisoformat(row["support_until"])
                    - timedelta(days=d["image_admission"]["upgrade_lead_days"])
                )
                if row["support_until"]
                else "ROLLING_MONTHLY_REVIEW",
                deployment_qualified=False,
            )
        )
    return {
        "engineering": [engineering(d, s) for s in ("initial", "expanded")],
        "hardware_reference_sensitivity": cases,
        "throughput_sensitivity": throughput_cases,
        "platform_lifecycle": lifecycle,
        "workforce_phases": workforce_phases(a),
        "floor_rooms": floor_rooms(a),
        "configuration": copy.deepcopy(d),
        "configuration_state": "SELECTED_DESIGN_PENDING_QUALIFICATION",
    }


def workforce_phases(a):
    from .planning import workforce

    d = a["technical_design"]["workforce_phases"]
    rows = []
    for phase, start, end, owned in [
        (
            "COLO",
            d["colo_start"],
            str(date.fromisoformat(d["owned_start_assumption"]) - timedelta(days=1)),
            False,
        ),
        ("OWNED_CONDITIONAL", d["owned_start_assumption"], "2036-12-31", True),
    ]:
        w = workforce(a, owned)
        rows.append(
            dict(
                phase=phase,
                start=start,
                end=end,
                required_technical_fte=w["required_technical_fte"],
                additional_facilities_fte=w["proposed_facilities_positions"],
                additional_guard_fte=w["proposed_guard_positions"],
                annual_gross_payroll=w["annual_gross_payroll"],
                authorized_new_fte=0,
                occupied_new_fte=0,
                contractor_equivalent_fte=d["construction_specialist_fte"]
                if not owned
                else 0,
                contractor_cost_included_in="EXISTING_DESIGN_AND_COMMISSION_PHASES"
                if not owned
                else "NOT_APPLICABLE",
                internal_project_lead_allocation=d["construction_project_lead_fte"]
                if not owned
                else 0,
                lead_counting="WITHIN_RT_ROLE_VENDOR_COORDINATION_NOT_ADDITIONAL_PAY",
                headquarters_workstations=d["sacramento_workstations_required"],
                roving_site_allocations=d["site_roving_positions"],
                status="REQUIREMENTS_NOT_OCCUPANCY_OR_AUTHORIZATION",
            )
        )
    if (
        d["sacramento_workstations_required"] + d["site_roving_positions"]
        != rows[0]["required_technical_fte"]
    ):
        raise ValueError(
            "Workstation and roving workforce requirements do not reconcile"
        )
    if d["construction_project_lead_fte"] > next(
        r["required_fte"]
        for r in a["workforce"]["roles"]
        if r["id"] == "RT-ROLE-VENDOR_COORDINATION"
    ):
        raise ValueError("Project leadership exceeds its existing modeled pool")
    return rows


def floor_rooms(a):
    """Area-preserving 120 x 100 ft concept; 1,650 sf remains circulation."""
    areas = {r["name"]: r["area_sf"] for r in a["rooms"]}
    result = []
    banks = [
        (
            5,
            52,
            [
                ["Conventional hall"],
                ["Electrical / UPS"],
                ["Network A", "Receiving / quarantine"],
            ],
        ),
        (
            63.5,
            51.5,
            [
                ["AI hall"],
                ["Mechanical / CDU"],
                ["NOC / incident", "Spares / media"],
                ["Lobby / mantrap", "Key room", "Network B"],
            ],
        ),
    ]
    for x, width, bands in banks:
        top = 100
        for names in bands:
            height = sum(areas[n] for n in names) / width
            top -= height
            left = x
            for name in names:
                room_width = areas[name] / height
                result.append(
                    dict(
                        name=name,
                        x=left,
                        y=top,
                        width=room_width,
                        height=height,
                        area_sf=areas[name],
                    )
                )
                left += room_width
        if abs(top) > 1e-8:
            raise ValueError("Floor bank does not fill its envelope")
    if sum(r["area_sf"] for r in result) + areas["Support / circulation"] != 12000:
        raise ValueError("Floor areas do not reconcile")
    return result
