"""Frozen explicit enterprise schema baseline through revision 0004.

Revision ID: 0004
Revises: None
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("account_class", sa.String(length=32), nullable=False),
        sa.Column("normal_balance", sa.String(length=6), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "business_party",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("party_type", sa.String(length=20), nullable=False),
        sa.Column("segment_code", sa.String(length=32), nullable=False),
        sa.Column("risk_tier", sa.String(length=16), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "customer",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("segment", sa.String(length=80), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "legal_entity",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("parent_id", sa.String(length=36), nullable=True),
        sa.Column("jurisdiction", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["legal_entity.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "scenario",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "scenario_value",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scenario_code", sa.String(length=20), nullable=False),
        sa.Column("metric_code", sa.String(length=60), nullable=False),
        sa.Column("entity_code", sa.String(length=32), nullable=False),
        sa.Column("period_code", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.Column("provenance", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scenario_code", "metric_code", "entity_code", "period_code"),
    )
    op.create_table(
        "source_document",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("branch", sa.String(length=200), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("controlling", sa.Boolean(), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path", "commit_sha"),
    )
    op.create_table(
        "vendor",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "accounting_book",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_id", "code"),
    )
    op.create_table(
        "contract",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), nullable=False),
        sa.Column("contract_type", sa.String(length=32), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("committed_value", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["party_id"],
            ["business_party.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "customer_contract",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("contract_number", sa.String(length=80), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("transaction_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customer.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_number"),
    )
    op.create_table(
        "debt_facility",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("facility_number", sa.String(length=40), nullable=False),
        sa.Column("commitment", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("annual_rate", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("facility_number"),
    )
    op.create_table(
        "freight_movement",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("movement_number", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("customer_party_id", sa.String(length=36), nullable=True),
        sa.Column("movement_date", sa.Date(), nullable=False),
        sa.Column("commodity", sa.String(length=40), nullable=False),
        sa.Column("tonnes", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("intercompany", sa.Boolean(), nullable=False),
        sa.Column("custody_status", sa.String(length=24), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_party_id"],
            ["business_party.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("movement_number"),
    )
    op.create_table(
        "generation_run",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile", sa.String(length=32), nullable=False),
        sa.Column("scenario_id", sa.String(length=36), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("generator_version", sa.String(length=40), nullable=False),
        sa.Column("git_commit", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenario.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile", "scenario_id", "seed", "generator_version"),
    )
    op.create_table(
        "model_assumption",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("assumption_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("base_value", sa.String(length=100), nullable=False),
        sa.Column("low_value", sa.String(length=100), nullable=True),
        sa.Column("high_value", sa.String(length=100), nullable=True),
        sa.Column("units", sa.String(length=40), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("sensitivity", sa.String(length=40), nullable=False),
        sa.Column("reversible", sa.Boolean(), nullable=False),
        sa.Column("decision_owner", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("last_review_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["source_document.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assumption_code"),
    )
    op.create_table(
        "purchase_order",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("vendor_id", sa.String(length=36), nullable=False),
        sa.Column("po_number", sa.String(length=40), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"],
            ["vendor.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("po_number"),
    )
    op.create_table(
        "site",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("site_type", sa.String(length=40), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=False),
        sa.Column("owner_entity_id", sa.String(length=36), nullable=True),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_entity_id"],
            ["legal_entity.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "artifact",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("generation_run_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_type", sa.String(length=40), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("public_classification", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_run_id"],
            ["generation_run.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_run_id", "path"),
    )
    op.create_table(
        "engagement",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=False),
        sa.Column("engagement_code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("billing_method", sa.String(length=30), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["customer_contract.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("engagement_code"),
    )
    op.create_table(
        "environmental_obligation",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("obligation_type", sa.String(length=32), nullable=False),
        sa.Column("undiscounted_amount", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("discount_rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("recognized_liability", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("expected_settlement_year", sa.Integer(), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["site.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "fiscal_period",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("book_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=7), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("state", sa.Enum("OPEN", "CLOSED", name="periodstate"), nullable=False),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["accounting_book.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id", "code"),
    )
    op.create_table(
        "fixed_asset",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asset_number", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("site_id", sa.String(length=36), nullable=True),
        sa.Column("asset_class", sa.String(length=40), nullable=False),
        sa.Column("placed_in_service", sa.Date(), nullable=False),
        sa.Column("cost", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("useful_life_months", sa.Integer(), nullable=False),
        sa.Column("acquisition_layer", sa.Boolean(), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["site.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_number"),
    )
    op.create_table(
        "goods_receipt",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("purchase_order_id", sa.String(length=36), nullable=False),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.ForeignKeyConstraint(
            ["purchase_order_id"],
            ["purchase_order.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "inventory_lot",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lot_number", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("inventory_stage", sa.String(length=24), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("carrying_value", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["site.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lot_number"),
    )
    op.create_table(
        "lineage_edge",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("generation_run_id", sa.String(length=36), nullable=False),
        sa.Column("upstream_type", sa.String(length=80), nullable=False),
        sa.Column("upstream_id", sa.String(length=100), nullable=False),
        sa.Column("downstream_type", sa.String(length=80), nullable=False),
        sa.Column("downstream_id", sa.String(length=100), nullable=False),
        sa.Column("transformation", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_run_id"],
            ["generation_run.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "generation_run_id", "upstream_type", "upstream_id", "downstream_type", "downstream_id"
        ),
    )
    op.create_table(
        "performance_obligation",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("revenue_method", sa.String(length=40), nullable=False),
        sa.Column("allocated_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["customer_contract.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "production_record",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("period_code", sa.String(length=7), nullable=False),
        sa.Column("ore_tonnes", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("mill_feed_tonnes", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("concentrate_lbs", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("recovery_rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["site.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "period_code"),
    )
    op.create_table(
        "validation_result",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("generation_run_id", sa.String(length=36), nullable=False),
        sa.Column("check_code", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("observed_value", sa.String(length=200), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_run_id"],
            ["generation_run.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_run_id", "check_code"),
    )
    op.create_table(
        "worker",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("worker_number", sa.String(length=20), nullable=False),
        sa.Column("worker_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("site_id", sa.String(length=36), nullable=True),
        sa.Column("segment_code", sa.String(length=32), nullable=False),
        sa.Column("function_code", sa.String(length=40), nullable=False),
        sa.Column("annual_cost", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["site.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_number"),
    )
    op.create_table(
        "journal_entry",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("book_id", sa.String(length=36), nullable=False),
        sa.Column("period_id", sa.String(length=36), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("state", sa.Enum("DRAFT", "POSTED", name="entrystate"), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversal_of_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["accounting_book.id"],
        ),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["fiscal_period.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reversal_of_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "project_task",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("engagement_id", sa.String(length=36), nullable=False),
        sa.Column("task_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(
            ["engagement_id"],
            ["engagement.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("engagement_id", "task_code"),
    )
    op.create_table(
        "atlas_evaluation",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("evaluation_number", sa.String(length=40), nullable=False),
        sa.Column("evaluation_date", sa.Date(), nullable=False),
        sa.Column("model_version", sa.String(length=60), nullable=False),
        sa.Column("investigation_question", sa.Text(), nullable=False),
        sa.Column("compute_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("validation_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("customer_fee", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("owns_final_decision", sa.Boolean(), nullable=False),
        sa.Column("cost_journal_entry_id", sa.String(length=36), nullable=False),
        sa.Column("revenue_journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["cost_journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["revenue_journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_number"),
    )
    op.create_table(
        "debt_draw",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("facility_id", sa.String(length=36), nullable=False),
        sa.Column("draw_date", sa.Date(), nullable=False),
        sa.Column("principal", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["facility_id"],
            ["debt_facility.id"],
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "depreciation_record",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("period_code", sa.String(length=7), nullable=False),
        sa.Column("depreciation_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["fixed_asset.id"],
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "invoice",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_number", sa.String(length=80), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["customer_contract.id"],
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
    )
    op.create_table(
        "journal_line",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("debit", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("credit", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("transaction_currency", sa.String(length=3), nullable=False),
        sa.Column("functional_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("reporting_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column(
            "fact_state",
            sa.Enum(
                "LOCKED_CANON",
                "PROVISIONAL_CANON",
                "OPEN_CANON",
                "SUPERSEDED",
                "LEGACY_CALIBRATION",
                "MODEL_PROPOSED",
                "SCENARIO_INPUT",
                "SYNTHETIC_INSTANCE",
                "DERIVED",
                "EXTERNAL_RESEARCH",
                name="factstate",
            ),
            nullable=False,
        ),
        sa.Column("segment_code", sa.String(length=32), nullable=True),
        sa.Column("cost_center_code", sa.String(length=32), nullable=True),
        sa.Column("project_code", sa.String(length=32), nullable=True),
        sa.Column("counterparty_entity_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["account.id"],
        ),
        sa.ForeignKeyConstraint(
            ["counterparty_entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "mine_production_batch",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("batch_number", sa.String(length=40), nullable=False),
        sa.Column("production_date", sa.Date(), nullable=False),
        sa.Column("feed_tons", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("grade_fraction", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column("recovery_fraction", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column("pounds_u3o8", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("production_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("inventory_lot_id", sa.String(length=36), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["inventory_lot_id"],
            ["inventory_lot.id"],
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["site.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_number"),
    )
    op.create_table(
        "payroll_run",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("pay_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("gross_pay", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("employer_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "recovery_run",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("run_number", sa.String(length=40), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("host_operator_code", sa.String(length=40), nullable=False),
        sa.Column("host_asset_owned", sa.Boolean(), nullable=False),
        sa.Column("feed_tons", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("grade_fraction", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column("recovery_fraction", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column("recovered_units", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("operating_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("host_share", sa.Numeric(precision=12, scale=8), nullable=False),
        sa.Column("gross_sale", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("host_share_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("production_journal_entry_id", sa.String(length=36), nullable=False),
        sa.Column("sale_journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["production_journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sale_journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_number"),
    )
    op.create_table(
        "revenue_recognition",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("performance_obligation_id", sa.String(length=36), nullable=False),
        sa.Column("recognition_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["performance_obligation_id"],
            ["performance_obligation.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "time_entry",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("worker_id", sa.String(length=36), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("bill_rate", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("cost_rate", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["project_task.id"],
        ),
        sa.ForeignKeyConstraint(
            ["worker_id"],
            ["worker.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "vendor_bill",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("purchase_order_id", sa.String(length=36), nullable=False),
        sa.Column("receipt_id", sa.String(length=36), nullable=False),
        sa.Column("bill_number", sa.String(length=40), nullable=False),
        sa.Column("bill_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("match_status", sa.String(length=24), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["purchase_order_id"],
            ["purchase_order.id"],
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["goods_receipt.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bill_number"),
    )
    op.create_table(
        "waybill",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("waybill_number", sa.String(length=40), nullable=False),
        sa.Column("movement_date", sa.Date(), nullable=False),
        sa.Column("carloads", sa.Integer(), nullable=False),
        sa.Column("tons", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("route_miles", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("ton_miles", sa.Numeric(precision=24, scale=4), nullable=False),
        sa.Column("base_rate", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("fuel_surcharge", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("fuel_gallons", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("fuel_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("crew_hours", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("crew_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("intercompany", sa.Boolean(), nullable=False),
        sa.Column("custody_status", sa.String(length=24), nullable=False),
        sa.Column("revenue_journal_entry_id", sa.String(length=36), nullable=False),
        sa.Column("cost_journal_entry_id", sa.String(length=36), nullable=False),
        sa.Column("receipt_journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["cost_journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["receipt_journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["revenue_journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("waybill_number"),
    )
    op.create_table(
        "willow_experiment",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("experiment_number", sa.String(length=40), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("belief", sa.Text(), nullable=False),
        sa.Column("experiment_date", sa.Date(), nullable=False),
        sa.Column("budget", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("actual_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("gate_decision", sa.String(length=16), nullable=False),
        sa.Column("transfer_target", sa.String(length=40), nullable=True),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["legal_entity.id"],
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_number"),
    )
    op.create_table(
        "cash_receipt",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoice.id"],
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "engagement_invoice_link",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("engagement_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("billed_hours", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("billed_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.ForeignKeyConstraint(
            ["engagement_id"],
            ["engagement.id"],
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoice.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "interest_accrual",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("debt_draw_id", sa.String(length=36), nullable=False),
        sa.Column("accrual_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["debt_draw_id"],
            ["debt_draw.id"],
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "invoice_line",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("performance_obligation_id", sa.String(length=36), nullable=False),
        sa.Column("description", sa.String(length=250), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoice.id"],
        ),
        sa.ForeignKeyConstraint(
            ["performance_obligation_id"],
            ["performance_obligation.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "payroll_line",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("payroll_run_id", sa.String(length=36), nullable=False),
        sa.Column("worker_id", sa.String(length=36), nullable=False),
        sa.Column("gross_pay", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("employer_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.ForeignKeyConstraint(
            ["payroll_run_id"],
            ["payroll_run.id"],
        ),
        sa.ForeignKeyConstraint(
            ["worker_id"],
            ["worker.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "project_cost",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("engagement_id", sa.String(length=36), nullable=False),
        sa.Column("time_entry_id", sa.String(length=36), nullable=False),
        sa.Column("cost_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["engagement_id"],
            ["engagement.id"],
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["time_entry_id"],
            ["time_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "uranium_shipment",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("production_batch_id", sa.String(length=36), nullable=False),
        sa.Column("shipment_number", sa.String(length=40), nullable=False),
        sa.Column("shipment_date", sa.Date(), nullable=False),
        sa.Column("pounds_shipped", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("realized_price_per_lb", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("cost_of_sales", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("sale_journal_entry_id", sa.String(length=36), nullable=False),
        sa.Column("receipt_journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["production_batch_id"],
            ["mine_production_batch.id"],
        ),
        sa.ForeignKeyConstraint(
            ["receipt_journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sale_journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_number"),
    )
    op.create_table(
        "vendor_payment",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("vendor_bill_id", sa.String(length=36), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["vendor_bill_id"],
            ["vendor_bill.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("vendor_payment")
    op.drop_table("uranium_shipment")
    op.drop_table("project_cost")
    op.drop_table("payroll_line")
    op.drop_table("invoice_line")
    op.drop_table("interest_accrual")
    op.drop_table("engagement_invoice_link")
    op.drop_table("cash_receipt")
    op.drop_table("willow_experiment")
    op.drop_table("waybill")
    op.drop_table("vendor_bill")
    op.drop_table("time_entry")
    op.drop_table("revenue_recognition")
    op.drop_table("recovery_run")
    op.drop_table("payroll_run")
    op.drop_table("mine_production_batch")
    op.drop_table("journal_line")
    op.drop_table("invoice")
    op.drop_table("depreciation_record")
    op.drop_table("debt_draw")
    op.drop_table("atlas_evaluation")
    op.drop_table("project_task")
    op.drop_table("journal_entry")
    op.drop_table("worker")
    op.drop_table("validation_result")
    op.drop_table("production_record")
    op.drop_table("performance_obligation")
    op.drop_table("lineage_edge")
    op.drop_table("inventory_lot")
    op.drop_table("goods_receipt")
    op.drop_table("fixed_asset")
    op.drop_table("fiscal_period")
    op.drop_table("environmental_obligation")
    op.drop_table("engagement")
    op.drop_table("artifact")
    op.drop_table("site")
    op.drop_table("purchase_order")
    op.drop_table("model_assumption")
    op.drop_table("generation_run")
    op.drop_table("freight_movement")
    op.drop_table("debt_facility")
    op.drop_table("customer_contract")
    op.drop_table("contract")
    op.drop_table("accounting_book")
    op.drop_table("vendor")
    op.drop_table("source_document")
    op.drop_table("scenario_value")
    op.drop_table("scenario")
    op.drop_table("legal_entity")
    op.drop_table("customer")
    op.drop_table("business_party")
    op.drop_table("account")
