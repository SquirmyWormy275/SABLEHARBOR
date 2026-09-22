"""Reuse accepted operations exports with the full composed cash-request population."""

import shutil

from enterprise.operations import controls, credit, exports, management, research
from enterprise.operations.model import OperatingModel
from industrial.planning import transactions


def build(output, operating, successor, op, fin, bridge, identity):
    industrial = transactions.build(
        output / "industrial/transactions", operating_rows=op["operating_rows"], forecast=fin
    )
    credit.allocate_treasury(
        operating,
        successor,
        additional_deferrable_source_types=("RUNTIME_CONDITIONAL_FORECAST_REQUEST",),
    )
    research.build_industrial_detail(
        operating, op["operating_rows"], industrial["tables"], fin["journal_rows"]
    )
    management.build(operating, successor, model_factory=OperatingModel)
    controls.build_controls(
        operating,
        successor,
        extras={"industrial_operations": op["operating_rows"], "replacement_bridge": bridge},
    )
    tables = exports.collect_tables(operating, successor)
    from enterprise.closeout import successor_records

    additions = successor_records.collect()
    if set(tables) & set(additions):
        raise ValueError("Successor export population collides with existing tables")
    successor_records.validate_tables(additions)
    tables.update(additions)
    schema, scope = successor_records.contracts()
    target = output / "exports"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()
    counts = exports.write_packages(target, tables, identity, schema=schema, scope=scope)
    exports.write_json(
        target / "coverage.json",
        {
            "table_counts": {k: len(v) for k, v in tables.items()},
            "unit_counts": counts,
            "corporate_scope": "Corporate, legal books, eliminations and consolidated populations remain in enterprise.sqlite3; seven unit extracts do not define company completeness",
            "treasury_request_scope": "Operating plus accepted runtime conditional investing requests; allocations do not create receipts or independent bank confirmation",
            "limitations": [
                "Source operating populations retain their own effective/available periods and are not all current headcount.",
                "No new schema or scope permissions are learned from output.",
            ],
        },
    )
    exports.inventory(target, identity)
    return counts
