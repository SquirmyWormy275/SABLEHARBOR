"""Add professional-services engagement subledger.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

from sable_harbor.commercial.models import (
    Engagement,
    EngagementInvoiceLink,
    ProjectCost,
    ProjectTask,
    TimeEntry,
)

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TABLES = [
    Engagement.__table__,
    ProjectTask.__table__,
    TimeEntry.__table__,
    ProjectCost.__table__,
    EngagementInvoiceLink.__table__,
]


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        table.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(TABLES):
        table.drop(bind, checkfirst=True)
