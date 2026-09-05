"""Scope generated natural keys to their owning generation run.

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}

RUN_SCOPED_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("worker", ("worker_number",)),
    ("business_party", ("code",)),
    ("contract", ("code",)),
    ("fixed_asset", ("asset_number",)),
    ("inventory_lot", ("lot_number",)),
    ("production_record", ("site_id", "period_code")),
    ("freight_movement", ("movement_number",)),
    ("customer_contract", ("contract_number",)),
    ("invoice", ("invoice_number",)),
    ("engagement", ("engagement_code",)),
    ("purchase_order", ("po_number",)),
    ("vendor_bill", ("bill_number",)),
    ("debt_facility", ("facility_number",)),
    ("mine_production_batch", ("batch_number",)),
    ("uranium_shipment", ("shipment_number",)),
    ("waybill", ("waybill_number",)),
    ("recovery_run", ("run_number",)),
    ("willow_experiment", ("experiment_number",)),
    ("atlas_evaluation", ("evaluation_number",)),
)


def _constraint_name(table: str, first_column: str) -> str:
    return f"uq_{table}_{first_column}"


def _existing_unique_name(table: str, columns: tuple[str, ...]) -> str:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        # Batch mode applies the declared convention to legacy unnamed constraints.
        return _constraint_name(table, columns[0])
    for constraint in sa.inspect(connection).get_unique_constraints(table):
        if tuple(constraint["column_names"]) == columns and constraint["name"]:
            return str(constraint["name"])
    raise RuntimeError(f"Missing expected unique constraint {table}{columns}")


def upgrade() -> None:
    for table, natural_key in RUN_SCOPED_KEYS:
        existing_name = _existing_unique_name(table, natural_key)
        with op.batch_alter_table(table, naming_convention=NAMING_CONVENTION) as batch:
            batch.drop_constraint(existing_name, type_="unique")
            batch.create_unique_constraint(
                _constraint_name(table, "generation_run_id"),
                ("generation_run_id", *natural_key),
            )


def downgrade() -> None:
    connection = op.get_bind()
    preparer = connection.dialect.identifier_preparer
    conflicts: list[str] = []
    for table, natural_key in RUN_SCOPED_KEYS:
        quoted_table = preparer.quote(table)
        quoted_columns = [preparer.quote(column) for column in natural_key]
        non_null = " AND ".join(f"{column} IS NOT NULL" for column in quoted_columns)
        grouped = ", ".join(quoted_columns)
        duplicate = connection.execute(
            sa.text(
                f"SELECT 1 FROM {quoted_table} WHERE {non_null} "
                f"GROUP BY {grouped} HAVING COUNT(*) > 1 LIMIT 1"
            )
        ).first()
        if duplicate is not None:
            conflicts.append(f"{table}({', '.join(natural_key)})")
    if conflicts:
        raise RuntimeError(
            "Cannot downgrade revision 0010 without losing populated multi-run "
            "natural-key data; conflicting global keys exist in: " + ", ".join(conflicts)
        )

    for table, natural_key in reversed(RUN_SCOPED_KEYS):
        with op.batch_alter_table(table, naming_convention=NAMING_CONVENTION) as batch:
            batch.drop_constraint(
                _constraint_name(table, "generation_run_id"), type_="unique"
            )
            batch.create_unique_constraint(
                _constraint_name(table, natural_key[0]), natural_key
            )
