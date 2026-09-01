"""Add queryable provenance and lineage records.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

from sable_harbor.provenance.models import (
    Artifact,
    GenerationRun,
    LineageEdge,
    ModelAssumption,
    Scenario,
    SourceDocument,
    ValidationResult,
)

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLES = [
    SourceDocument.__table__,
    ModelAssumption.__table__,
    Scenario.__table__,
    GenerationRun.__table__,
    Artifact.__table__,
    LineageEdge.__table__,
    ValidationResult.__table__,
]


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        table.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(TABLES):
        table.drop(bind, checkfirst=True)
