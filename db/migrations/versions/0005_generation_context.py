"""Tie generated journals and scenario values to an explicit generation run.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("journal_entry") as batch:
        batch.add_column(sa.Column("generation_run_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            "fk_journal_entry_generation_run",
            "generation_run",
            ["generation_run_id"],
            ["id"],
        )
        batch.create_index("ix_journal_entry_generation_run_id", ["generation_run_id"])
    with op.batch_alter_table("scenario_value") as batch:
        batch.add_column(sa.Column("generation_run_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            "fk_scenario_value_generation_run",
            "generation_run",
            ["generation_run_id"],
            ["id"],
        )
        batch.create_index("ix_scenario_value_generation_run_id", ["generation_run_id"])


def downgrade() -> None:
    with op.batch_alter_table("scenario_value") as batch:
        batch.drop_index("ix_scenario_value_generation_run_id")
        batch.drop_constraint("fk_scenario_value_generation_run", type_="foreignkey")
        batch.drop_column("generation_run_id")
    with op.batch_alter_table("journal_entry") as batch:
        batch.drop_index("ix_journal_entry_generation_run_id")
        batch.drop_constraint("fk_journal_entry_generation_run", type_="foreignkey")
        batch.drop_column("generation_run_id")
