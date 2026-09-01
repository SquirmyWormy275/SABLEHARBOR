"""Widen scenario period codes for annual and range markers.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("scenario_value") as batch:
        batch.alter_column(
            "period_code", existing_type=sa.String(length=7), type_=sa.String(length=16)
        )


def downgrade() -> None:
    with op.batch_alter_table("scenario_value") as batch:
        batch.alter_column(
            "period_code", existing_type=sa.String(length=16), type_=sa.String(length=7)
        )
