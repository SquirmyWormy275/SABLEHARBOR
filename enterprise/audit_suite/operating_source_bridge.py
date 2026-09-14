"""Import selected existing synthetic operating-model records, independently of audits.

Month-close availability is a bridge disclosure rule, not an inferred business
occurrence. Source forecasts, synthetic identities and original rows remain intact.
This trusted local operator interface grants no access and creates no engagement.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .company_store import CompanyStore, CompanyStoreError

TABLE_KEYS = {
    "commercial_changes": "change_id",
    "service_incidents": "incident_id",
    "workforce_changes": "change_id",
    "contract_versions": "contract_id",
}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def source_pins(repository: Path):
    """Retain input/code identities; do not read secrets or private scenario banks."""
    roots = [repository / "enterprise" / family for family in ("business", "operations")]
    inputs = [p for root in roots for p in sorted((root / "source").glob("*.json"))]
    code = [p for root in roots for p in sorted(root.glob("*.py"))]
    code.append(Path(__file__).resolve())
    pins = {
        kind: [
            {"path": str(p.relative_to(repository)), "sha256": sha(p.read_bytes())} for p in files
        ]
        for kind, files in [("inputs", inputs), ("build_code", code)]
    }
    pins["git_revision"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()
    return pins


def month_bounds(row):
    month = row.get("month_index")
    if type(month) is not int or not 1 <= month <= 60:
        raise CompanyStoreError("Selected operating rows require a source month_index1–60")
    year, number = 2027 + (month - 1) // 12, (month - 1) % 12 + 1
    start = date(year, number, 1)
    end = date(year, number, calendar.monthrange(year, number)[1])
    if row.get("period") != end.isoformat():
        raise CompanyStoreError("Source period must equal the declared model month close")
    for name in ("applied_month", "requested_month"):
        value = row.get(name)
        if (
            name == "applied_month"
            and type(value) is int
            and value == 0
            and row.get("status") in {"HELD_PENDING_ACTIVATION", "NOT_APPLICABLE_CLOSED"}
        ):
            continue  # Explicit source sentinel: not applied, not a calendar month.
        if value is not None and (type(value) is not int or value > month or value < 1):
            raise CompanyStoreError(
                "Source row contains unresolved future/invalid month provenance"
            )
    available = datetime.combine(end + timedelta(days=1), datetime.min.time(), UTC)
    return start.isoformat(), end.isoformat(), available.isoformat()


def plan_operating_import(model, *, owner_ids, branch_ids, tables, repository: Path):
    """Validate the entire selected plan before any company-store writes."""
    if not getattr(model, "_built", False):
        raise CompanyStoreError("Build the existing operating model independently first")
    if not tables or len(tables) != len(set(tables)) or set(tables) - TABLE_KEYS.keys():
        raise CompanyStoreError("Select a distinct nonempty subset of approved operating tables")
    if set(owner_ids) != set(tables) or any(
        not isinstance(v, str) or not v for v in owner_ids.values()
    ):
        raise CompanyStoreError(
            "Explicit existing-person or role custody IDs required for each table"
        )
    if not branch_ids or set(branch_ids) - {"base", "downside", "expansion"}:
        raise CompanyStoreError("Explicit existing source scenarios required")
    if any(
        not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", v)
        for v in [*branch_ids.values(), *owner_ids.values()]
    ):
        raise CompanyStoreError("Valid existing owner and explicit branch identities required")
    if len(set(branch_ids.values())) != len(branch_ids):
        raise CompanyStoreError("Each source scenario requires an isolated distinct branch")
    input_hash = sha(encoded({"business": model.inputs, "operations": model.operations_inputs}))
    if input_hash != model.input_hash:
        raise CompanyStoreError("Operating model input hash mismatch")
    pins = source_pins(repository)
    entries, natural_groups, selected_scenarios = [], defaultdict(list), set()
    for table in tables:
        rows = model.tables[table]
        for ordinal, row in enumerate(rows):
            scenario = row.get("scenario")
            if scenario not in branch_ids:
                continue
            selected_scenarios.add(scenario)
            source_id, unit = row.get(TABLE_KEYS[table]), row.get("unit")
            if (
                not isinstance(source_id, str)
                or not source_id
                or not isinstance(unit, str)
                or not unit
            ):
                raise CompanyStoreError("Actual source identity and unit required")
            start, end, available = month_bounds(row)
            row_bytes = encoded(row)
            key = (scenario, table, unit, source_id)
            natural_groups[key].append(
                {
                    "source_row": row,
                    "source_row_sha256": sha(row_bytes),
                    "source_row_ordinal": ordinal,
                    "period_start": start,
                    "period_end": end,
                    "available_at": available,
                }
            )
    if selected_scenarios != set(branch_ids):
        raise CompanyStoreError("A requested scenario has no selected operating records")
    for key, rows in sorted(natural_groups.items()):
        scenario, table, unit, source_id = key
        # Contract versions give explicit order; other records require distinct source months.
        order_field = "version" if table == "contract_versions" else "month_index"
        orders = [r["source_row"].get(order_field) for r in rows]
        if any(type(x) is not int or x < 1 for x in orders) or len(orders) != len(set(orders)):
            raise CompanyStoreError("Ambiguous or repeated source-record chronology")
        ordered = sorted(rows, key=lambda r: r["source_row"][order_field])
        if any(
            a["available_at"] > b["available_at"]
            for a, b in zip(ordered, ordered[1:], strict=False)
        ):
            raise CompanyStoreError("Source versions have inverted availability")
        record_id = "OP-" + sha(encoded([table, unit, source_id]))[:40]
        for index, entry in enumerate(ordered):
            content = encoded(
                {
                    "schema_version": "1.0",
                    "record_origin": "MODEL_DERIVED_SYNTHETIC_HISTORY",
                    "source_table": table,
                    "source_scenario": scenario,
                    "source_row": entry["source_row"],
                    "qualification": (
                        "Existing conditional forecast/planning record; not "
                        "an actual production or bank capture"
                    ),
                }
            )
            provenance = {
                "source_reference": f"enterprise.operations.OperatingModel.tables/{table}",
                "input_hash": input_hash,
                "source_pins": pins,
                "source_row_sha256": entry["source_row_sha256"],
                "source_row_ordinal": entry["source_row_ordinal"],
                "source_identity": {"table": table, "unit": unit, TABLE_KEYS[table]: source_id},
                "source_scenario": scenario,
                "source_period_start": entry["period_start"],
                "source_period_end": entry["period_end"],
                "event_time_state": "UNKNOWN_MONTHLY_MODEL_SNAPSHOT_NOT_AN_EVENT_TIMESTAMP",
                "availability_basis": (
                    "Conservative UTC release after source month closes; "
                    "bridge disclosure rule, not actual event/retrieval time"
                ),
                "custody_basis": (
                    " PROVISIONAL_LOCAL_SOURCE_CUSTODY_USING_EXISTING_SCOPED_ID_NO_NEW_APPOINTMENT"
                ),
                "scope_mapping": (
                    "Company-source candidate only; no "
                    "automatic corporate SOC2/HIPAA control applicability"
                ),
            }
            command_id = (
                "OPIMPORT-" + sha(encoded([key, input_hash, entry["source_row_sha256"]]))[:48]
            )
            entries.append(
                {
                    "branch_id": branch_ids[scenario],
                    "system_id": table,
                    "record_id": record_id,
                    "owner_id": owner_ids[table],
                    "expected_version": index,
                    "command_id": command_id,
                    "event_at": None,
                    "available_at": entry["available_at"],
                    "content": content,
                    "provenance": provenance,
                }
            )
    return entries


def import_operating_tables(
    store: CompanyStore,
    model,
    *,
    company_id,
    owner_ids,
    branch_ids,
    tables=tuple(TABLE_KEYS),
    repository: Path,
):
    plan = plan_operating_import(
        model, owner_ids=owner_ids, branch_ids=branch_ids, tables=tables, repository=repository
    )
    for branch in branch_ids.values():
        for table in tables:
            CompanyStore._key(company_id, branch, table)
    receipts = []
    for row in plan:
        store.register_system(company_id, row["branch_id"], row["system_id"], row["owner_id"])
        receipts.append(
            store.append_version(
                company_id,
                row["branch_id"],
                row["system_id"],
                row["record_id"],
                expected_version=row["expected_version"],
                command_id=row["command_id"],
                event_at=None,
                available_at=row["available_at"],
                content=row["content"],
                provenance=row["provenance"],
                origin="MIGRATED_SYNTHETIC_HISTORY",
            )
        )
    return {
        "status": "IMPORTED_EXISTING_MODEL_QUALIFIED_COMPANY_RECORDS",
        "company_id": company_id,
        "branch_ids": branch_ids,
        "tables": list(tables),
        "source_input_hash": model.input_hash,
        "record_versions": len(receipts),
        "grants_created": 0,
        "engagements_created": 0,
        "receipts": receipts,
        "limitations": [
            "No actual event timestamps inferred from monthly model snapshots.",
            (
                "Existing synthetic/forecast identity and facts "
                "preserved; canon acceptance not promoted."
            ),
            (
                "Natural-key/source-version ambiguity fails closed; changed "
                "inputs require an explicit correction migration."
            ),
            (
                "Company-source existence is not professional "
                "applicability, population completeness or control effectiveness."
            ),
        ],
    }
