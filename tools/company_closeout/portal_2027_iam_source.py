"""Bounded company-source candidates for the portal's 2027 Q1 access review.

The accepted August person/principal pairs are an opening *candidate* set.  This
module deliberately cannot turn an absent Sep-Dec bridge, service inventory or
2027 JML ledger into a complete 2027 population or review result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE = Path("enterprise/operations/source/portal_2027_iam_opening_2026_09_29.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique(rows: list[dict], key: str) -> dict[str, dict]:
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return result


def derive(records: dict, config: dict, policy: list[dict]) -> dict:
    release = config["accepted_august_release"]
    if records["repository_source_commit"] != release["source_commit"]:
        raise ValueError("Wrong accepted August source commit")
    if records["repository_source_available_at"] != release["source_available_at"]:
        raise ValueError("Changed August source availability")
    if records["effective_through"] != "2026-08-31":
        raise ValueError("Changed August period")
    if (
        config["scenario"] != "FICTIONAL_2027_ENGAGEMENT_CANDIDATE"
        or config["fact_status"] != "UNVERIFIED_2027_OPENING_NOT_COMPLETED_ACTUAL"
    ):
        raise ValueError("2027 candidate presented as completed history")

    people = unique(records["tables"]["people"], "person_id")
    principals = unique(records["tables"]["access"], "person_id")
    if len(people) != 702 or set(people) != set(principals):
        raise ValueError("August person-principal population differs")
    principal_ids = unique(records["tables"]["access"], "principal_id")
    if len(principal_ids) != 702:
        raise ValueError("August principal population differs")
    for person_id, account in principals.items():
        person = people[person_id]
        if (
            account["principal_id"] != f"SH-IAM-{person_id}"
            or account["legal_entity"] != person["legal_employer"]
            or account["unit"] != person["unit"]
            or account["tenant_id"] != "sable-harbor"
            or account["entitlement"] != "RESOLVE_USING_ACCEPTED_INFORMATION_NATURE_POLICY"
            or account["runtime_state"] != "COMPANY_INPUT_NOT_DEPLOYMENT_EVIDENCE"
        ):
            raise ValueError("August person-principal join or policy boundary differs")

    events = unique(records["tables"]["change_events"], "event_id")
    if set(events) != set(config["bridge"]["known_september_event_ids"]):
        raise ValueError("September JML event population differs")
    exit_event = events["SH-HR-2026-09-01"]
    if (
        exit_event["action"] != "EXIT"
        or exit_event["person_id"] not in people
        or exit_event["effective_at"][:10] != "2026-09-04"
        or exit_event["revoked_at"][:10] != "2026-09-07"
        or exit_event["effective_at"] >= exit_event["revoked_at"]
    ):
        raise ValueError("Known September exit/revocation differs")
    if not (
        config["bridge"]["unreconciled_start"] > exit_event["revoked_at"][:10]
        and config["bridge"]["unreconciled_end_exclusive"] == "2027-01-01"
        and config["bridge"]["september_december_jml_population_complete"] is False
        and config["bridge"]["unrepresented_jml_count"] is None
    ):
        raise ValueError("Unreconciled Sep-Dec bridge hidden")

    procedure = [row for row in policy if row["control_id"] == "SH-IAM-007"]
    if len(procedure) != 1 or not procedure[0]["procedure"].startswith(
        "Quarterly for privileged access"
    ):
        raise ValueError("IAM-007 draft procedure differs")
    q1 = config["q1_iam_007"]
    if (
        q1["start"] != "2027-01-01T00:00:00Z"
        or q1["end_exclusive"] != "2027-04-01T00:00:00Z"
        or q1["procedure_state"] != "DRAFT_CCF_PROCEDURE_NOT_ACCEPTED_COMPANY_CALENDAR"
        or q1["company_due_at"] is not None
        or q1["privileged_review_due_count"] is not None
        or q1["nonprivileged_review_due_count"] is not None
        or q1["complete_2027_jml_population"] is not False
        or q1["known_2027_jml_event_ids"] != []
        or q1["unrepresented_2027_jml_count"] is not None
        or q1["performance_source_ids"] != []
        or q1["missing_performance_count"] is not None
    ):
        raise ValueError("Q1 due/performance state promoted without source")
    opening = config["opening"]
    if any(
        opening[field] is not False
        for field in (
            "candidate_is_confirmed_active",
            "complete_service_inventory",
            "complete_entitlement_inventory",
        )
    ) or any(
        opening[field] is not None
        for field in (
            "confirmed_active_person_count",
            "confirmed_active_account_count",
            "privileged_account_population",
        )
    ):
        raise ValueError("Unverified 2027 opening promoted to complete census")
    if any(
        branch["baseline"] != "COMMON_CANDIDATE_ONLY"
        or branch["company_delta_state"] != "NOT_AUTHORED"
        for branch in config["case_branches"].values()
    ) or set(config["case_branches"]) != {"A", "B"}:
        raise ValueError("Unaccepted A/B company delta")

    candidates = [
        {
            "candidate_id": f"SH-IAM-Q1-2027-{person_id}",
            "person_id": person_id,
            "declared_company_principal_id": principals[person_id]["principal_id"],
            "legal_entity_at_august": people[person_id]["legal_employer"],
            "unit_at_august": people[person_id]["unit"],
            "service_id_at_2027_opening": None,
            "system_account_id_at_2027_opening": None,
            "entitlements_at_2027_opening": None,
            "privileged_at_2027_opening": None,
            "presence_at_2027_opening": "UNKNOWN_PENDING_SEP_DEC_BRIDGE_AND_2027_CENSUS",
            "candidate_basis": "ACCEPTED_AUGUST_PERSON_PRINCIPAL_LESS_KNOWN_SEPTEMBER_EXIT",
            "case_branch": "COMMON_A_B_CANDIDATE",
        }
        for person_id in sorted(set(people) - {exit_event["person_id"]})
    ]
    directors = unique(records["tables"]["nonemployees"], "person_id")
    if set(directors) & set(people) or len(directors) != 7:
        raise ValueError("Director exclusion population differs")
    return {
        "record_id": "SH-PORTAL-IAM-Q1-2027-OPENING-CANDIDATES-v0.1",
        "state": config["state"],
        "authored_day": config["authored_day"],
        "scenario": config["scenario"],
        "fact_status": config["fact_status"],
        "access_scope": config["access_scope"],
        "source_edition": release["tag"],
        "source_commit": release["source_commit"],
        "source_available_at": release["source_available_at"],
        "source_release_published_at": release["release_published_at"],
        "2027_case_source_available_at": None,
        "august_employee_principal_pairs": len(people),
        "supported_september_exit_count": 1,
        "last_supported_september_person_principal_pairs": len(candidates),
        "excluded_nonemployee_directors": len(directors),
        "confirmed_2027_opening_person_principal_pairs": None,
        "opening_candidates": candidates,
        "september_december_bridge": config["bridge"],
        "opening_census_state": opening,
        "q1_due_event_schedule": [
            {
                "event_id": "SH-IAM-007-2027-Q1-PROVISIONAL-WINDOW",
                **q1,
                "candidate_person_principal_pairs": len(candidates),
                "confirmed_account_review_population": None,
                "observed_performance_source_count": 0,
                "observed_performance_source_count_basis": (
                    "No accepted 2027 performance source; this does not prove no performance"
                ),
            }
        ],
        "case_branches": config["case_branches"],
        "excluded": config["excluded"],
    }


def load(records_path: Path, receipt_path: Path, source_root: Path) -> dict:
    config = json.loads((source_root / SOURCE).read_text())
    release = config["accepted_august_release"]
    if sha256(records_path) != release["records_sha256"]:
        raise ValueError("Accepted records byte pin mismatch")
    if sha256(receipt_path) != release["receipt_sha256"]:
        raise ValueError("Accepted release receipt byte pin mismatch")
    for path_key, hash_key in (
        ("august_roster_and_event", "august_roster_and_event_sha256"),
        ("iam_procedure", "iam_procedure_sha256"),
    ):
        if (
            sha256(source_root / config["source_paths"][path_key])
            != config["source_paths"][hash_key]
        ):
            raise ValueError(f"Changed source: {path_key}")
    receipt = json.loads(receipt_path.read_text())
    if (
        receipt["source_commit"] != release["source_commit"]
        or receipt["status"] != "ACCEPTED_SCOPED_EDITION"
    ):
        raise ValueError("Accepted release state differs")
    records = json.loads(records_path.read_text())
    policy = json.loads((source_root / config["source_paths"]["iam_procedure"]).read_text())
    return derive(records, config, policy)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = (
        json.dumps(load(args.records, args.receipt, args.source_root), indent=2, sort_keys=True)
        + "\n"
    ).encode()
    if args.check:
        if args.output.read_bytes() != rendered:
            raise ValueError("Stale Q1 IAM opening candidate export")
    else:
        if args.output.exists():
            raise ValueError("Output already exists; use --check or a new version")
        args.output.write_bytes(rendered)
    print("PASS bounded 2027 Q1 IAM candidate source input")


if __name__ == "__main__":
    main()
