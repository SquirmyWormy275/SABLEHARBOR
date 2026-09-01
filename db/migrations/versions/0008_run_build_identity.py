"""Persist reproducible generation build and actual-dataset identity.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("generation_run") as batch:
        batch.add_column(sa.Column("actual_dataset_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("generator_source_digest", sa.String(64), nullable=True))
        batch.add_column(sa.Column("assumptions_digest", sa.String(64), nullable=True))
        batch.add_column(sa.Column("canon_source_lock_digest", sa.String(64), nullable=True))
        batch.add_column(sa.Column("actual_through", sa.Date(), nullable=True))
        batch.add_column(sa.Column("forecast_from", sa.Date(), nullable=True))
        batch.add_column(sa.Column("schema_head", sa.String(32), nullable=True))
        batch.create_index("ix_generation_run_actual_dataset_id", ["actual_dataset_id"])


def downgrade() -> None:
    with op.batch_alter_table("generation_run") as batch:
        batch.drop_index("ix_generation_run_actual_dataset_id")
        batch.drop_column("schema_head")
        batch.drop_column("forecast_from")
        batch.drop_column("actual_through")
        batch.drop_column("canon_source_lock_digest")
        batch.drop_column("assumptions_digest")
        batch.drop_column("generator_source_digest")
        batch.drop_column("actual_dataset_id")
