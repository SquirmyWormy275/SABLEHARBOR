"""Persist content-addressed generation input and build identity.

Revision ID: 0009
Revises: 0008
"""

import hashlib
import json
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_IDENTITY_COLUMNS = ("profile", "scenario_id", "seed", "generator_version")
IDENTITY_NAMESPACE = uuid.UUID("89586ef5-49ff-49f6-a20f-ec42c411f5c1")


def _legacy_identity_constraint_name() -> str:
    constraints = sa.inspect(op.get_bind()).get_unique_constraints("generation_run")
    for constraint in constraints:
        if tuple(constraint["column_names"]) == LEGACY_IDENTITY_COLUMNS:
            return str(constraint["name"] or "uq_generation_run_profile")
    raise RuntimeError("Legacy generation-run identity constraint was not found")


def upgrade() -> None:
    constraint_name = _legacy_identity_constraint_name()
    with op.batch_alter_table(
        "generation_run", naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"}
    ) as batch:
        batch.drop_constraint(constraint_name, type_="unique")
        batch.add_column(sa.Column("build_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("input_manifest_digest", sa.String(64), nullable=True))
        batch.create_unique_constraint("uq_generation_run_build_id", ["build_id"])

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, profile, scenario_id, seed, generator_version, git_commit, "
            "generator_source_digest, assumptions_digest, canon_source_lock_digest, "
            "actual_through, forecast_from, schema_head FROM generation_run"
        )
    ).mappings()
    for row in rows:
        legacy_manifest = hashlib.sha256(
            json.dumps(dict(row), sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest()
        legacy_build_id = str(
            uuid.uuid5(IDENTITY_NAMESPACE, f"legacy-build:{row['id']}:{legacy_manifest}")
        )
        connection.execute(
            sa.text(
                "UPDATE generation_run SET build_id = :build_id, "
                "input_manifest_digest = :manifest WHERE id = :id"
            ),
            {"build_id": legacy_build_id, "manifest": legacy_manifest, "id": row["id"]},
        )

    with op.batch_alter_table("generation_run") as batch:
        batch.alter_column("build_id", existing_type=sa.String(36), nullable=False)
        batch.alter_column("input_manifest_digest", existing_type=sa.String(64), nullable=False)


def downgrade() -> None:
    connection = op.get_bind()
    duplicate = connection.execute(
        sa.text(
            "SELECT 1 FROM generation_run GROUP BY profile, scenario_id, seed, "
            "generator_version HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot downgrade revision 0009 without losing content-addressed generation "
            "runs; duplicate legacy profile/scenario/seed/version identities exist"
        )
    with op.batch_alter_table("generation_run") as batch:
        batch.drop_constraint("uq_generation_run_build_id", type_="unique")
        batch.drop_column("input_manifest_digest")
        batch.drop_column("build_id")
        batch.create_unique_constraint(
            "uq_generation_run_profile", LEGACY_IDENTITY_COLUMNS
        )
