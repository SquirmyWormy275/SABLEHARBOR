"""Enforce generation ownership, lifecycle, and same-run relationships.

Revision ID: 0011
Revises: 0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNED_TABLES = (
    "artifact", "atlas_evaluation", "business_party", "cash_receipt", "contract",
    "customer_contract", "debt_draw", "debt_facility", "depreciation_record", "engagement",
    "engagement_invoice_link", "environmental_obligation", "fixed_asset", "freight_movement",
    "goods_receipt", "interest_accrual", "inventory_lot", "invoice", "invoice_line",
    "journal_entry", "lineage_edge", "mine_production_batch", "payroll_line", "payroll_run",
    "performance_obligation", "production_record", "project_cost", "project_task",
    "purchase_order", "recovery_run", "revenue_recognition", "scenario_value", "time_entry",
    "uranium_shipment", "validation_result", "vendor_bill", "vendor_payment", "waybill",
    "willow_experiment", "worker",
)

# (child table, child foreign-key column, generated parent table)
SAME_RUN_LINKS = (
    ("journal_entry", "reversal_of_id", "journal_entry"),
    ("contract", "party_id", "business_party"),
    ("freight_movement", "customer_party_id", "business_party"),
    ("performance_obligation", "contract_id", "customer_contract"),
    ("invoice", "contract_id", "customer_contract"),
    ("invoice", "journal_entry_id", "journal_entry"),
    ("invoice_line", "invoice_id", "invoice"),
    ("invoice_line", "performance_obligation_id", "performance_obligation"),
    ("revenue_recognition", "performance_obligation_id", "performance_obligation"),
    ("revenue_recognition", "journal_entry_id", "journal_entry"),
    ("cash_receipt", "invoice_id", "invoice"),
    ("cash_receipt", "journal_entry_id", "journal_entry"),
    ("engagement", "contract_id", "customer_contract"),
    ("project_task", "engagement_id", "engagement"),
    ("time_entry", "task_id", "project_task"),
    ("time_entry", "worker_id", "worker"),
    ("project_cost", "engagement_id", "engagement"),
    ("project_cost", "time_entry_id", "time_entry"),
    ("project_cost", "journal_entry_id", "journal_entry"),
    ("engagement_invoice_link", "engagement_id", "engagement"),
    ("engagement_invoice_link", "invoice_id", "invoice"),
    ("waybill", "revenue_journal_entry_id", "journal_entry"),
    ("waybill", "cost_journal_entry_id", "journal_entry"),
    ("waybill", "receipt_journal_entry_id", "journal_entry"),
    ("mine_production_batch", "inventory_lot_id", "inventory_lot"),
    ("mine_production_batch", "journal_entry_id", "journal_entry"),
    ("uranium_shipment", "production_batch_id", "mine_production_batch"),
    ("uranium_shipment", "sale_journal_entry_id", "journal_entry"),
    ("uranium_shipment", "receipt_journal_entry_id", "journal_entry"),
    ("payroll_run", "journal_entry_id", "journal_entry"),
    ("payroll_line", "payroll_run_id", "payroll_run"),
    ("payroll_line", "worker_id", "worker"),
    ("goods_receipt", "purchase_order_id", "purchase_order"),
    ("vendor_bill", "purchase_order_id", "purchase_order"),
    ("vendor_bill", "receipt_id", "goods_receipt"),
    ("vendor_bill", "journal_entry_id", "journal_entry"),
    ("vendor_payment", "vendor_bill_id", "vendor_bill"),
    ("vendor_payment", "journal_entry_id", "journal_entry"),
    ("depreciation_record", "asset_id", "fixed_asset"),
    ("depreciation_record", "journal_entry_id", "journal_entry"),
    ("debt_draw", "facility_id", "debt_facility"),
    ("debt_draw", "journal_entry_id", "journal_entry"),
    ("interest_accrual", "debt_draw_id", "debt_draw"),
    ("interest_accrual", "journal_entry_id", "journal_entry"),
    ("recovery_run", "production_journal_entry_id", "journal_entry"),
    ("recovery_run", "sale_journal_entry_id", "journal_entry"),
    ("willow_experiment", "journal_entry_id", "journal_entry"),
    ("atlas_evaluation", "cost_journal_entry_id", "journal_entry"),
    ("atlas_evaluation", "revenue_journal_entry_id", "journal_entry"),
)


def _assert_no_null_ownership() -> None:
    connection = op.get_bind()
    preparer = connection.dialect.identifier_preparer
    offenders = [
        table for table in OWNED_TABLES
        if connection.execute(
            sa.text(
                f"SELECT 1 FROM {preparer.quote(table)} "
                "WHERE generation_run_id IS NULL LIMIT 1"
            )
        ).first()
        is not None
    ]
    if offenders:
        raise RuntimeError(
            "Cannot require generation ownership; null rows exist in: "
            + ", ".join(offenders)
        )


def _create_lifecycle_guard() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        op.execute("""
        CREATE TRIGGER trg_generation_run_completed_immutable
        BEFORE UPDATE ON generation_run
        FOR EACH ROW WHEN OLD.status = 'COMPLETED' AND (
          NEW.status IS NOT OLD.status OR NEW.completed_at IS NOT OLD.completed_at OR
          NEW.profile IS NOT OLD.profile OR NEW.scenario_id IS NOT OLD.scenario_id OR
          NEW.seed IS NOT OLD.seed OR NEW.generator_version IS NOT OLD.generator_version OR
          NEW.git_commit IS NOT OLD.git_commit OR
          NEW.generator_source_digest IS NOT OLD.generator_source_digest OR
          NEW.assumptions_digest IS NOT OLD.assumptions_digest OR
          NEW.canon_source_lock_digest IS NOT OLD.canon_source_lock_digest OR
          NEW.started_at IS NOT OLD.started_at OR
          NEW.actual_dataset_id IS NOT OLD.actual_dataset_id OR
          NEW.build_id IS NOT OLD.build_id OR
          NEW.input_manifest_digest IS NOT OLD.input_manifest_digest OR
          NEW.actual_generation_run_id IS NOT OLD.actual_generation_run_id OR
          NEW.actual_through IS NOT OLD.actual_through OR
          NEW.forecast_from IS NOT OLD.forecast_from OR
          NEW.schema_head IS NOT OLD.schema_head)
        BEGIN SELECT RAISE(ABORT, 'completed generation runs are immutable'); END
        """)
    else:
        op.execute("""
        CREATE FUNCTION guard_completed_generation_run() RETURNS trigger AS $$
        BEGIN
          IF OLD.status = 'COMPLETED' AND
             (NEW.status, NEW.completed_at, NEW.profile, NEW.scenario_id, NEW.seed,
              NEW.generator_version, NEW.git_commit, NEW.generator_source_digest,
              NEW.assumptions_digest, NEW.canon_source_lock_digest, NEW.started_at,
              NEW.actual_dataset_id, NEW.build_id,
              NEW.input_manifest_digest, NEW.actual_generation_run_id, NEW.actual_through,
              NEW.forecast_from, NEW.schema_head)
             IS DISTINCT FROM
             (OLD.status, OLD.completed_at, OLD.profile, OLD.scenario_id, OLD.seed,
              OLD.generator_version, OLD.git_commit, OLD.generator_source_digest,
              OLD.assumptions_digest, OLD.canon_source_lock_digest, OLD.started_at,
              OLD.actual_dataset_id, OLD.build_id,
              OLD.input_manifest_digest, OLD.actual_generation_run_id, OLD.actual_through,
              OLD.forecast_from, OLD.schema_head)
          THEN RAISE EXCEPTION 'completed generation runs are immutable'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
        """)
        op.execute(
            "CREATE TRIGGER trg_generation_run_completed_immutable "
            "BEFORE UPDATE ON generation_run FOR EACH ROW "
            "EXECUTE FUNCTION guard_completed_generation_run()"
        )


def upgrade() -> None:
    _assert_no_null_ownership()
    for table in OWNED_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.alter_column("generation_run_id", existing_type=sa.String(36), nullable=False)
            batch.create_unique_constraint(
                f"uq_{table}_id_generation_run_id", ["id", "generation_run_id"]
            )
    for child, column, parent in SAME_RUN_LINKS:
        with op.batch_alter_table(child) as batch:
            batch.create_foreign_key(
                f"fk_{child}_{column}_same_run", parent,
                [column, "generation_run_id"], ["id", "generation_run_id"],
            )

    with op.batch_alter_table("generation_run") as batch:
        batch.alter_column("actual_dataset_id", existing_type=sa.String(36), nullable=False)
        batch.create_unique_constraint(
            "uq_generation_run_id_actual_dataset_id", ["id", "actual_dataset_id"]
        )
        batch.create_foreign_key(
            "fk_generation_run_actual_dataset_compatible", "generation_run",
            ["actual_generation_run_id", "actual_dataset_id"], ["id", "actual_dataset_id"],
        )
        batch.create_check_constraint(
            "ck_generation_run_lifecycle",
            "(status = 'RUNNING' AND completed_at IS NULL) OR "
            "(status = 'COMPLETED' AND completed_at IS NOT NULL)",
        )
    _create_lifecycle_guard()


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER trg_generation_run_completed_immutable ON generation_run")
        op.execute("DROP FUNCTION guard_completed_generation_run()")
    else:
        op.execute("DROP TRIGGER trg_generation_run_completed_immutable")
    with op.batch_alter_table("generation_run") as batch:
        batch.drop_constraint("ck_generation_run_lifecycle", type_="check")
        batch.drop_constraint("fk_generation_run_actual_dataset_compatible", type_="foreignkey")
        batch.drop_constraint("uq_generation_run_id_actual_dataset_id", type_="unique")
        batch.alter_column("actual_dataset_id", existing_type=sa.String(36), nullable=True)
    for child, column, _parent in reversed(SAME_RUN_LINKS):
        with op.batch_alter_table(child) as batch:
            batch.drop_constraint(f"fk_{child}_{column}_same_run", type_="foreignkey")
    for table in reversed(OWNED_TABLES):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f"uq_{table}_id_generation_run_id", type_="unique")
            batch.alter_column("generation_run_id", existing_type=sa.String(36), nullable=True)
