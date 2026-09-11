"""Render source-derived runtime results for the controlled PDF and institutional catalog."""

import argparse
from pathlib import Path
from . import model


def render(data):
    result = model.export(data)
    a = data["capital"]["implementation_assumptions"]
    bridge = next(
        r for r in result["construction_finance_bridge"] if r["scenario"] == "base"
    )
    lines = [
        "# Runtime estate calculated design register",
        "",
        "**Document ID:** SH-RT-RESULTS-001",
        "**Version:** 1.0.0",
        "**State:** GENERATED SYNTHETIC DESIGN; no operating acceptance",
        "**Owner:** Enterprise Technology Services / Finance",
        "**Prepared:** 2026-09-11",
        "**Authority:** September 11 runtime decisions; generated output does not create canon",
        "**Structured companion:** enterprise/services/source/runtime_sites_2026-09-11.json; enterprise/services/source/runtime_capital_plan_2026-09-11.json",
        "",
        "Source content SHA-256: `"
        + result["source_sha256"]
        + "`. Regenerate with `python -m enterprise.runtime.report`. Do not edit calculated values in this derivative.",
        "",
        "## Current design boundary",
        "",
        "Selected providers remain uncontracted, unreserved and uninstalled. The synthetic owned parcel is acquired/preconstruction, with 0% vertical construction and 0 kW commissioned. September 2026 actual service-operation history is not established.",
        "",
        "| Site | Planned facility / geography | State |",
        "|---|---|---|",
    ]
    for site in result["sites"]:
        lines.append(f"| {site['name']} | {site['geography']} | {site['status']} |")
    lines += [
        "",
        "## Causal configuration classes",
        "",
        "All quantities are unmeasured planning assumptions. Accelerator throughput, power limits and thermal configuration need qualified acceptance. Each rack observes space, peak power, weight and separation constraints; A/B feeds are not additive load.",
        "",
        "| Case / year | Site | CPU / GPU systems | Shelves / racks | Peak / typical kW | Durable TiB |",
        "|---|---|---|---|---|---|",
    ]
    for r in result["capacity"]:
        lines.append(
            f"| {r['scenario']} / {r['year']} | {r['site']} | {r['cpu_hosts']} / {r['gpu_systems']} | {r['storage_shelves']} / {r['racks']} | {r['peak_kw']} / {r['typical_synthetic_kw']} | {r['durable_tib']} |"
        )
    lines += [
        "",
        "## Reference hardware and uncertainty",
        "",
        "The sourced DGX H100 10.2 kW maximum is a separate sensitivity from the unqualified 8 kW capped design class. It is not an adopted supplier BOM or proof that the proposed throughput is attainable at a cap.",
        "",
        "| Site | Reference maximum kW | Racks | Initial envelope sufficient |",
        "|---|---|---|---|",
    ]
    for r in result["technical_design"]["hardware_reference_sensitivity"]:
        lines.append(
            f"| {r['site']} | {r['reference_maximum_peak_kw']} | {r['racks']} | {r['envelope_sufficient']} |"
        )
    lines += [
        "",
        "| Throughput sensitivity | Site | GPU systems | Peak kW |",
        "|---|---|---|---|",
    ]
    for r in result["technical_design"]["throughput_sensitivity"]:
        lines.append(
            f"| {r['bound']} / {r['assumed_tokens_per_second']} tokens/sec | {r['site']} | {r['gpu_systems']} | {r['peak_kw']} |"
        )
    lines += [
        "",
        "## Owned engineering arithmetic",
        "",
        "These are component ratings for a concept, not a licensed protection, structural, fire or hydraulic design. Annual PUE does not replace coincident peak-load calculations.",
        "",
        "| Stage | Usable IT kW | Peak facility input kW | Surviving UPS path kW | N+1 generation / thermal cooling kW |",
        "|---|---|---|---|---|",
    ]
    for r in result["technical_design"]["engineering"]:
        lines.append(
            f"| {r['stage']} | {r['usable_it_kw']} | {r['peak_facility_input_kw']} | {r['ups_surviving_path_kw']} | {r['generation_n1_kw']} / {r['cooling_n1_thermal_kw']} |"
        )
    lines += [
        "",
        "## Finance and workforce reconciliation",
        "",
        f"Phase I includes the $3M land overlay. No land payment is evidenced. The ${float(bridge['phase_i_envelope']):,.0f} envelope reconciles to ${float(bridge['land_non_cash_overlay']):,.0f} land, ${float(bridge['pre_2027_unaccepted_unrecognized_requests']):,.0f} unaccepted/unrecognized 2026 requests, ${float(bridge['conditional_post_2026_cip_requests']):,.0f} conditional post-2026 CIP requests and ${float(bridge['unspent_reserve']):,.0f} unspent reserve. Earlier calibrated journals remain unchanged outside the separate land overlay. The enterprise successor applies existing finite Treasury limits to conditional requests.",
        "",
        "| Workforce phase | Technical FTE | Facilities / guards | Annual gross payroll | New authorized / occupied |",
        "|---|---|---|---|---|",
    ]
    for r in result["technical_design"]["workforce_phases"]:
        lines.append(
            f"| {r['phase']} | {r['required_technical_fte']} | {r['additional_facilities_fte']} / {r['additional_guard_fte']} | ${r['annual_gross_payroll']:,.0f} | {r['authorized_new_fte']} / {r['occupied_new_fte']} |"
        )
    lines += [
        "",
        "Construction lead allocation is within the vendor-coordination pool; purchased specialist capacity is within design/commissioning costs. Neither is added again as permanent payroll. Workstations and roving assignments remain requirements, not occupancy records.",
        "",
        "| Base case year | Facility request | IT request | Operating request | Gross requirement |",
        "|---|---|---|---|---|",
    ]
    for r in result["finance"]["annual"]:
        if r["scenario"] == "base":
            lines.append(
                f"| {r['year']} | {r['facility_cash_request']} | {r['hardware_cash_request']} | {r['operating_cash_request']} | {r['gross_cash_request']} |"
            )
    lines += [
        "",
        "Owned investment sensitivities separately include a demand-triggered second module, refurbishment, escalation, migration overlap and decommissioning. Cases above the 500 kW owned envelope remain infeasible; an attractive arithmetic NPV cannot approve an undersized facility. Terminal proceeds occur only in the terminal period. Tax benefits and verified displaced-cost credits are zero.",
        "",
        "## Recovery and execution gates",
        "",
        "| Native service | Tier | Minimum service |",
        "|---|---|---|",
    ]
    for r in a["technical_design"]["recovery_services"]:
        lines.append(f"| {r['service_id']} | {r['tier']} | {r['minimum_service']} |")
    lines += [
        "",
        "Recovery is unverified for every tier. Prepositioned copies, independent keys/identities/DNS, complete logs and restore tombstones are required; a full network seed is not the timed minimum-service restore. The source register and accountable external evidence gates are in `enterprise/runtime/readiness.json`. Management owns implementation; Internal Audit retains independent evaluation.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=model.ROOT / "enterprise/runtime/docs/MODEL_RESULTS.md",
    )
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    text = render(model.load())
    if args.verify:
        if args.output.read_text() != text:
            raise ValueError("Calculated controlled report drift")
    else:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
