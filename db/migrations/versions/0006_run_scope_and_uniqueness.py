"""Add common-actual run scope and run-aware scenario-value uniqueness.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
LEGACY_COLUMNS = {"scenario_code", "metric_code", "entity_code", "period_code"}


def _legacy_constraint_name() -> str:
    constraints = sa.inspect(op.get_bind()).get_unique_constraints("scenario_value")
    for constraint in constraints:
        if set(constraint["column_names"]) == LEGACY_COLUMNS:
            return str(constraint["name"] or "uq_scenario_value_scenario_code")
    raise RuntimeError("Legacy scenario_value uniqueness constraint was not found")


def upgrade() -> None:
    legacy_constraint_name = _legacy_constraint_name()
    with op.batch_alter_table("generation_run") as batch:
        batch.add_column(
            sa.Column("actual_generation_run_id", sa.String(length=36), nullable=True)
        )
        batch.create_foreign_key(
            "fk_generation_run_actual_generation_run",
            "generation_run",
            ["actual_generation_run_id"],
            ["id"],
        )
        batch.create_index(
            "ix_generation_run_actual_generation_run_id", ["actual_generation_run_id"]
        )
    with op.batch_alter_table(
        "scenario_value", naming_convention=NAMING_CONVENTION
    ) as batch:
        batch.drop_constraint(legacy_constraint_name, type_="unique")
        batch.create_unique_constraint(
            "uq_scenario_value_run_metric_entity_period",
            [
                "generation_run_id",
                "scenario_code",
                "metric_code",
                "entity_code",
                "period_code",
            ],
        )


def downgrade() -> None:
    with op.batch_alter_table("scenario_value") as batch:
        batch.drop_constraint(
            "uq_scenario_value_run_metric_entity_period", type_="unique"
        )
        batch.create_unique_constraint(
            "uq_scenario_value_scenario_code",
            ["scenario_code", "metric_code", "entity_code", "period_code"],
        )
    with op.batch_alter_table("generation_run") as batch:
        batch.drop_index("ix_generation_run_actual_generation_run_id")
        batch.drop_constraint(
            "fk_generation_run_actual_generation_run", type_="foreignkey"
        )
        batch.drop_column("actual_generation_run_id")
