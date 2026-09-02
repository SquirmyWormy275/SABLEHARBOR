"""Blackridge schema-version baseline marker."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schema_migration_marker",
        sa.Column("schema_version", sa.String(32), primary_key=True),
        sa.Column("applied_at", sa.String(64), nullable=False),
    )
    op.execute(
        "INSERT INTO schema_migration_marker(schema_version,applied_at) "
        "VALUES ('0.1.0','2015-01-01T00:00:00+00:00')"
    )


def downgrade() -> None:
    op.drop_table("schema_migration_marker")
