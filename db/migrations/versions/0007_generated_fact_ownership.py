"""Add generation-run ownership to scenario-dependent operational facts.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

FACT_TABLES = (
    "worker",
    "business_party",
    "contract",
    "fixed_asset",
    "inventory_lot",
    "production_record",
    "freight_movement",
    "environmental_obligation",
    "payroll_run",
    "payroll_line",
    "purchase_order",
    "goods_receipt",
    "vendor_bill",
    "vendor_payment",
    "depreciation_record",
    "debt_facility",
    "debt_draw",
    "interest_accrual",
    "mine_production_batch",
    "uranium_shipment",
    "waybill",
    "recovery_run",
    "willow_experiment",
    "atlas_evaluation",
    "customer_contract",
    "performance_obligation",
    "invoice",
    "invoice_line",
    "revenue_recognition",
    "cash_receipt",
    "engagement",
    "project_task",
    "time_entry",
    "project_cost",
    "engagement_invoice_link",
)


def upgrade() -> None:
    for table in FACT_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column("generation_run_id", sa.String(length=36), nullable=True)
            )
            batch.create_foreign_key(
                f"fk_{table}_generation_run",
                "generation_run",
                ["generation_run_id"],
                ["id"],
            )
            batch.create_index(f"ix_{table}_generation_run_id", ["generation_run_id"])


def downgrade() -> None:
    for table in reversed(FACT_TABLES):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_generation_run_id")
            batch.drop_constraint(f"fk_{table}_generation_run", type_="foreignkey")
            batch.drop_column("generation_run_id")
