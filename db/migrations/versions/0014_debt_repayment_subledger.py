"""Add explicit run-owned debt repayments.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "debt_repayment",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("debt_draw_id", sa.String(length=36), nullable=False),
        sa.Column("repayment_date", sa.Date(), nullable=False),
        sa.Column("principal", sa.Numeric(20, 4), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.Column("generation_run_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["debt_draw_id"], ["debt_draw.id"]),
        sa.ForeignKeyConstraint(
            ["debt_draw_id", "generation_run_id"],
            ["debt_draw.id", "debt_draw.generation_run_id"],
            name="fk_debt_repayment_debt_draw_id_same_run",
        ),
        sa.ForeignKeyConstraint(["generation_run_id"], ["generation_run.id"]),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entry.id"]),
        sa.ForeignKeyConstraint(
            ["journal_entry_id", "generation_run_id"],
            ["journal_entry.id", "journal_entry.generation_run_id"],
            name="fk_debt_repayment_journal_entry_id_same_run",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "generation_run_id",
            name="uq_debt_repayment_id_generation_run_id",
        ),
    )
    op.create_index(
        "ix_debt_repayment_generation_run_id",
        "debt_repayment",
        ["generation_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_debt_repayment_generation_run_id", table_name="debt_repayment")
    op.drop_table("debt_repayment")
