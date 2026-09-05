"""Widen scenario-value period codes for explicit cutoff markers.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scenario_value") as batch:
        batch.alter_column(
            "period_code",
            existing_type=sa.String(length=16),
            type_=sa.String(length=64),
            existing_nullable=False,
        )


def downgrade() -> None:
    connection = op.get_bind()
    too_long = connection.execute(
        sa.text("SELECT 1 FROM scenario_value WHERE length(period_code) > 16 LIMIT 1")
    ).first()
    if too_long is not None:
        raise RuntimeError(
            "Cannot downgrade revision 0013 while scenario period codes exceed 16 characters"
        )
    with op.batch_alter_table("scenario_value") as batch:
        batch.alter_column(
            "period_code",
            existing_type=sa.String(length=64),
            type_=sa.String(length=16),
            existing_nullable=False,
        )
