"""Selected fictional shipment qualification, not authorization for a real shipment."""

import json
from datetime import datetime
from decimal import ROUND_CEILING
from decimal import Decimal as D
from pathlib import Path

SOURCE = Path(__file__).with_name("september_shipment_qualification.json")


def validate(data):
    at = datetime.fromisoformat
    if data["available_on"] < data["authored_on"] or data["available_on"] != "2026-09-15":
        raise ValueError("Future qualification promoted into earlier evidence")
    if (
        data["shipper_entity"] != "RWH"
        or data["carrier_id"] != "SYN-RW-CARRIER-001"
        or data["receiver_id"] != "SYN-RW-CONVERTER-001"
    ):
        raise ValueError("Wrong legal party or unauthorized uranium carrier")
    if data["carrier"]["id"] != data["carrier_id"] or data["receiver"]["id"] != data["receiver_id"]:
        raise ValueError("Party identity mismatch")
    if data["available_at"][:10] < data["authored_on"]:
        raise ValueError("Imported availability precedes authorship")
    events = data["events"]
    ready = at(data["ready_at"])
    survey = at(data["survey"]["event_at"])
    if (
        not at(events[0]["event_at"])
        <= survey
        <= ready
        <= at(events[1]["event_at"])
        < at(events[2]["event_at"])
        <= at(data["available_at"])
    ):
        raise ValueError("Qualification survey release receipt chronology")
    if events[1]["event_at"][:10] <= "2026-09-06":
        raise ValueError("Historical OPEN state overwritten")
    if (
        len(data["checks"]) != 8
        or {c["check_id"] for c in data["checks"]} != {f"RW-SHIP-CHECK-{i:02}" for i in range(1, 9)}
        or any(c["outcome"] != "PASS" or not c["evidence_id"] for c in data["checks"])
    ):
        raise ValueError("Qualification check population failed or missing")
    release_day = events[1]["event_at"][:10]
    for period in [data["carrier"]["registration_period"], data["receiver"]["license_period"]]:
        if not period[0] <= release_day <= period[1]:
            raise ValueError("Carrier or receiver authority expired")
    if data["survey"]["calibration_expires"] < release_day:
        raise ValueError("Survey calibration expired")
    m = data["material"]
    s = data["survey"]
    if m["classification"] != "LSA-I" or D(m["u235_percent_of_uranium_mass"]) > D(".72"):
        raise ValueError("Classification facts changed; new review required")
    if (
        sum(
            D(m[k])
            for k in [
                "u235_percent_of_uranium_mass",
                "u234_percent_of_uranium_mass",
                "u238_percent_of_uranium_mass",
            ]
        )
        != 100
    ):
        raise ValueError("Isotope assay reconciliation")
    if (
        D(m["contained_u3o8_lb"]) != 200
        or D(m["contained_u3o8_lb"]) * D(".45359237") != D(m["contained_u3o8_kg"])
        or not D(m["contained_u3o8_kg"]) <= D(m["dry_concentrate_kg"]) < D(m["gross_package_kg"])
    ):
        raise ValueError("Lot or mass population mismatch")
    if D(m["specific_activity_bq_per_g_concentrate"]) * D(m["dry_concentrate_kg"]) * 1000 != D(
        m["total_activity_bq"]
    ):
        raise ValueError("Activity mass reconciliation")
    ti = (D(s["one_metre_max_msv_h"]) * 100).quantize(D(".1"), rounding=ROUND_CEILING)
    if ti != D(s["transport_index"]) or ti > 10:
        raise ValueError("Transport index wrong or above selected limit")
    wipe = D(s["max_wipe_activity_bq"]) / D(s["wipe_area_cm2"]) / D(s["wipe_efficiency"])
    if wipe != D(s["nonfixed_low_toxicity_alpha_bq_cm2"]) or wipe > 4:
        raise ValueError("Contamination result exceeds limit or arithmetic wrong")
    for key, limit in [
        ("surface_max_msv_h", "2"),
        ("unshielded_three_metre_msv_h", "10"),
        ("vehicle_surface_msv_h", "2"),
        ("vehicle_two_metre_msv_h", ".1"),
        ("occupied_space_msv_h", ".02"),
    ]:
        if not 0 <= D(s[key]) <= D(limit):
            raise ValueError("Dose rate exceeds scoped release limit")
    if (
        data["package"]["type"] != "IP-1"
        or data["package"]["design_review_date"] > events[1]["event_at"][:10]
    ):
        raise ValueError("Package review missing before release")
    people = {"RW-0112", "SYN-CBST-DRIVER-001", "SYN-MCS-RECEIVER-001"}
    if len(data["training"]) != 3 or {t["person_id"] for t in data["training"]} != people:
        raise ValueError("Training population missing or duplicate")
    for t in data["training"]:
        if (
            not t["completed_on"] <= events[1]["event_at"][:10] < t["internal_recheck_due"]
            or not t["certification"]
        ):
            raise ValueError("Training expired or after release")
    return {
        "qualification_id": data["qualification_id"],
        "shipment_id": data["shipment_id"],
        "checks": 8,
        "trained_individuals": 3,
        "contained_u3o8_lb": "200",
        "receipt_state": events[2]["state"],
        "title_owner": "RWH",
        "known_on": data["available_on"],
    }


if __name__ == "__main__":
    print(json.dumps(validate(json.loads(SOURCE.read_text())), indent=2))
