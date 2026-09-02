"""Add run-scoped accounting period close state.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_period_close",
        sa.Column("generation_run_id", sa.String(36), nullable=False),
        sa.Column("period_id", sa.String(36), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["generation_run_id"], ["generation_run.id"]),
        sa.ForeignKeyConstraint(["period_id"], ["fiscal_period.id"]),
        sa.PrimaryKeyConstraint("generation_run_id", "period_id"),
    )
    # A CLOSED fiscal_period was a global posting lock before this revision.
    # Preserve that lock for every run that existed at upgrade time.  The
    # legacy state is deliberately retained as a compatibility guard for runs
    # created after the upgrade.
    op.execute(
        sa.text(
            """
            INSERT INTO generation_period_close
                (generation_run_id, period_id, closed_at)
            SELECT generation_run.id, fiscal_period.id, CURRENT_TIMESTAMP
            FROM generation_run CROSS JOIN fiscal_period
            WHERE fiscal_period.state = 'CLOSED'
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    incompatible_period = connection.execute(
        sa.text(
            """
            SELECT generation_period_close.period_id
            FROM generation_period_close
            GROUP BY generation_period_close.period_id
            HAVING COUNT(*) <> (SELECT COUNT(*) FROM generation_run)
            """
        )
    ).first()
    if incompatible_period is not None:
        raise RuntimeError(
            "Cannot downgrade revision 0012: run-scoped period close state "
            "cannot be represented by the legacy global fiscal-period state"
        )
    op.execute(
        sa.text(
            """
            UPDATE fiscal_period
            SET state = 'CLOSED'
            WHERE id IN (SELECT DISTINCT period_id FROM generation_period_close)
            """
        )
    )
    op.drop_table("generation_period_close")
