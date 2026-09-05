"""Enforce ledger integrity and freeze completed-run evidence.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence
from datetime import date

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}

EPISTEMIC_STATES = (
    "LOCKED",
    "DERIVED",
    "SUPPORTED_ESTIMATE",
    "PROVISIONAL_ASSUMPTION",
    "SCENARIO",
    "OPEN",
    "CONFLICT",
    "SUPERSEDED",
)

FACT_STATES = (
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
)

RUN_OWNED_TABLES = (
    "artifact",
    "atlas_evaluation",
    "business_party",
    "cash_receipt",
    "contract",
    "customer",
    "customer_contract",
    "debt_draw",
    "debt_facility",
    "debt_repayment",
    "depreciation_record",
    "engagement",
    "engagement_invoice_link",
    "environmental_obligation",
    "fixed_asset",
    "freight_movement",
    "goods_receipt",
    "interest_accrual",
    "inventory_lot",
    "invoice",
    "invoice_line",
    "journal_entry",
    "lineage_edge",
    "mine_production_batch",
    "payroll_line",
    "payroll_run",
    "performance_obligation",
    "production_record",
    "project_cost",
    "project_task",
    "purchase_order",
    "recovery_run",
    "revenue_recognition",
    "scenario_value",
    "time_entry",
    "uranium_shipment",
    "validation_result",
    "vendor",
    "vendor_bill",
    "vendor_payment",
    "waybill",
    "willow_experiment",
    "worker",
)

SHI_ID = "71795c5a-bda9-55b8-80e8-b815cfec0dbd"
RWH_ID = "66321a51-e743-5644-be4f-85f2ae83f73a"
ARU_ID = "932eed72-0384-5a74-8869-90d57bb885bd"
BST_ID = "42d8f671-4283-5f68-88fa-0c404d29c6dc"
LEGACY_CONS_ID = "0dff78a9-a7de-59b4-b4b2-365d64db9448"
CONSOLIDATION_BOOK_ID = "45d09f45-a09f-5740-a69f-8523be1b4db7"

CANON_SOURCE = "docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md"
GOVERNANCE_SOURCE = "docs/governance/2026_ENTITY_AND_BOARD_GOVERNANCE_DECISIONS.md"
RECONCILIATION_SOURCE = "docs/finance/QUANTITATIVE_BASELINE_RECONCILIATION.md"


def _existing_unique_name(table: str, columns: tuple[str, ...]) -> str:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        return f"uq_{table}_{columns[0]}"
    for constraint in sa.inspect(connection).get_unique_constraints(table):
        if tuple(constraint["column_names"]) == columns and constraint["name"]:
            return str(constraint["name"])
    raise RuntimeError(f"Missing expected unique constraint {table}{columns}")


def _backfill_owned_master(table: str, child: str, foreign_key: str) -> None:
    connection = op.get_bind()
    preparer = connection.dialect.identifier_preparer
    q_table = preparer.quote(table)
    q_child = preparer.quote(child)
    q_fk = preparer.quote(foreign_key)
    ambiguous = connection.execute(
        sa.text(
            f"SELECT {q_fk} FROM {q_child} GROUP BY {q_fk} "
            "HAVING COUNT(DISTINCT generation_run_id) > 1 LIMIT 1"
        )
    ).first()
    if ambiguous is not None:
        raise RuntimeError(f"Cannot run-own {table}: a master is shared by multiple runs")
    connection.execute(
        sa.text(
            f"UPDATE {q_table} SET generation_run_id = "
            f"(SELECT MIN(generation_run_id) FROM {q_child} WHERE {q_fk} = {q_table}.id)"
        )
    )
    orphan = connection.execute(
        sa.text(f"SELECT id FROM {q_table} WHERE generation_run_id IS NULL LIMIT 1")
    ).first()
    if orphan is not None:
        raise RuntimeError(f"Cannot run-own {table}: an unreferenced generated master exists")


def _add_master_ownership() -> None:
    for table in ("customer", "vendor"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("generation_run_id", sa.String(36), nullable=True))
    _backfill_owned_master("customer", "customer_contract", "customer_id")
    _backfill_owned_master("vendor", "purchase_order", "vendor_id")

    vendor_code_unique = _existing_unique_name("vendor", ("code",))
    with op.batch_alter_table("customer") as batch:
        batch.alter_column("generation_run_id", existing_type=sa.String(36), nullable=False)
        batch.create_foreign_key(
            "fk_customer_generation_run_id", "generation_run", ["generation_run_id"], ["id"]
        )
        batch.create_unique_constraint(
            "uq_customer_id_generation_run_id", ["id", "generation_run_id"]
        )
    op.create_index("ix_customer_generation_run_id", "customer", ["generation_run_id"])
    with op.batch_alter_table("vendor", naming_convention=NAMING_CONVENTION) as batch:
        batch.alter_column("generation_run_id", existing_type=sa.String(36), nullable=False)
        batch.drop_constraint(vendor_code_unique, type_="unique")
        batch.create_foreign_key(
            "fk_vendor_generation_run_id", "generation_run", ["generation_run_id"], ["id"]
        )
        batch.create_unique_constraint("uq_vendor_generation_run_id", ["generation_run_id", "code"])
        batch.create_unique_constraint(
            "uq_vendor_id_generation_run_id", ["id", "generation_run_id"]
        )
    op.create_index("ix_vendor_generation_run_id", "vendor", ["generation_run_id"])
    with op.batch_alter_table("customer_contract") as batch:
        batch.create_foreign_key(
            "fk_customer_contract_customer_id_same_run",
            "customer",
            ["customer_id", "generation_run_id"],
            ["id", "generation_run_id"],
        )
    with op.batch_alter_table("purchase_order") as batch:
        batch.create_foreign_key(
            "fk_purchase_order_vendor_id_same_run",
            "vendor",
            ["vendor_id", "generation_run_id"],
            ["id", "generation_run_id"],
        )


def _epistemic_type() -> sa.types.TypeEngine:
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.ENUM(*EPISTEMIC_STATES, name="epistemicstate", create_type=False)
    return sa.Enum(*EPISTEMIC_STATES, name="epistemicstate")


def _fact_state_type() -> sa.types.TypeEngine:
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.ENUM(*FACT_STATES, name="factstate", create_type=False)
    return sa.Enum(*FACT_STATES, name="factstate")


def _upsert_code_master(
    connection: sa.engine.Connection, table: sa.TableClause, values: dict[str, object]
) -> None:
    expected_id = str(values["id"])
    expected_code = str(values["code"])
    code_owner = connection.scalar(sa.select(table.c.id).where(table.c.code == expected_code))
    if code_owner is not None and str(code_owner) != expected_id:
        raise RuntimeError(
            f"Cannot reconcile {table.name} {expected_code!r}: its code belongs to "
            "a noncanonical deterministic ID"
        )
    existing = connection.scalar(sa.select(table.c.id).where(table.c.id == expected_id))
    if existing is None:
        connection.execute(table.insert().values(**values))
    else:
        connection.execute(table.update().where(table.c.id == expected_id).values(**values))


def _reassign_legacy_consolidation_entity(connection: sa.engine.Connection) -> None:
    accounting_book = sa.table(
        "accounting_book",
        sa.column("id", sa.String()),
        sa.column("entity_id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("currency", sa.String()),
    )
    canonical_key_owner = connection.scalar(
        sa.select(accounting_book.c.id).where(
            accounting_book.c.entity_id == SHI_ID,
            accounting_book.c.code == "CONSOLIDATION_USD",
        )
    )
    if canonical_key_owner is not None and str(canonical_key_owner) != CONSOLIDATION_BOOK_ID:
        raise RuntimeError(
            "Cannot retire the legacy CONS entity: the canonical consolidation-book key "
            "belongs to a different ID"
        )
    consolidation_book = connection.scalar(
        sa.select(accounting_book.c.id).where(accounting_book.c.id == CONSOLIDATION_BOOK_ID)
    )
    if consolidation_book is not None:
        connection.execute(
            accounting_book.update()
            .where(accounting_book.c.id == CONSOLIDATION_BOOK_ID)
            .values(entity_id=SHI_ID, code="CONSOLIDATION_USD", currency="USD")
        )

    remaining_books = connection.execute(
        sa.select(accounting_book.c.id, accounting_book.c.code).where(
            accounting_book.c.entity_id == LEGACY_CONS_ID
        )
    ).all()
    for book_id, code in remaining_books:
        collision = connection.scalar(
            sa.select(accounting_book.c.id).where(
                accounting_book.c.entity_id == SHI_ID,
                accounting_book.c.code == code,
            )
        )
        if collision is not None and str(collision) != str(book_id):
            raise RuntimeError(
                f"Cannot retire the legacy CONS entity: accounting-book code {code!r} "
                "collides under SHI"
            )
        connection.execute(
            accounting_book.update().where(accounting_book.c.id == book_id).values(entity_id=SHI_ID)
        )

    inspector = sa.inspect(connection)
    for table_name in inspector.get_table_names():
        if table_name == "accounting_book":
            continue
        for foreign_key in inspector.get_foreign_keys(table_name):
            if foreign_key.get("referred_table") != "legal_entity":
                continue
            constrained = foreign_key.get("constrained_columns") or []
            referred = foreign_key.get("referred_columns") or []
            if len(constrained) != 1 or referred != ["id"]:
                raise RuntimeError(
                    f"Cannot retire CONS through unsupported foreign key on {table_name}"
                )
            column_name = str(constrained[0])
            referencing = sa.table(
                table_name,
                sa.column(column_name, sa.String()),
            )
            connection.execute(
                referencing.update()
                .where(referencing.c[column_name] == LEGACY_CONS_ID)
                .values({column_name: SHI_ID})
            )

    legal_entity = sa.table(
        "legal_entity",
        sa.column("id", sa.String()),
    )
    connection.execute(legal_entity.delete().where(legal_entity.c.id == LEGACY_CONS_ID))


def _reconcile_legacy_canon_masters() -> None:
    """Upgrade populated pre-0015 masters to the controlling entity/site ontology."""
    connection = op.get_bind()
    state_type = _epistemic_type()
    fact_state_type = _fact_state_type()
    legal_entity = sa.table(
        "legal_entity",
        sa.column("id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("fact_state", fact_state_type),
        sa.column("existence_state", state_type),
        sa.column("identity_state", state_type),
        sa.column("relationship_state", state_type),
        sa.column("effective_date_state", state_type),
        sa.column("effective_from", sa.Date()),
        sa.column("valid_to", sa.Date()),
        sa.column("recorded_on", sa.Date()),
        sa.column("known_on", sa.Date()),
        sa.column("superseded_on", sa.Date()),
        sa.column("source_reference", sa.String()),
        sa.column("parent_id", sa.String()),
        sa.column("jurisdiction", sa.String()),
    )
    legacy_model_present = connection.scalar(
        sa.select(legal_entity.c.id).where(legal_entity.c.code == "SHI")
    )
    if legacy_model_present is None:
        return
    if str(legacy_model_present) != SHI_ID:
        raise RuntimeError("Cannot reconcile SHI: its code uses a noncanonical deterministic ID")

    common_entity_values = {
        "fact_state": "MODEL_PROPOSED",
        "existence_state": "LOCKED",
        "identity_state": "OPEN",
        "relationship_state": "LOCKED",
        "effective_date_state": "PROVISIONAL_ASSUMPTION",
        "valid_to": None,
        "recorded_on": date(2026, 9, 5),
        "known_on": date(2026, 9, 3),
        "superseded_on": None,
        "jurisdiction": "OPEN",
    }
    for values in (
        {
            **common_entity_values,
            "id": SHI_ID,
            "code": "SHI",
            "name": "Sable Harbor (model parent; formal legal name open)",
            "effective_from": date(2016, 1, 1),
            "source_reference": CANON_SOURCE,
            "parent_id": None,
        },
        {
            **common_entity_values,
            "id": RWH_ID,
            "code": "RWH",
            "name": "Dedicated Red Wash operator (formal legal identity open)",
            "effective_from": date(2025, 7, 1),
            "source_reference": GOVERNANCE_SOURCE,
            "parent_id": SHI_ID,
        },
        {
            **common_entity_values,
            "id": ARU_ID,
            "code": "ARU",
            "name": "American Resource Utility (formal legal name open)",
            "effective_from": date(2026, 2, 1),
            "source_reference": GOVERNANCE_SOURCE,
            "parent_id": SHI_ID,
        },
        {
            **common_entity_values,
            "id": BST_ID,
            "code": "BST",
            "name": "Blood, Sweat & Tears Railway (formal legal name open)",
            "effective_from": date(2026, 2, 1),
            "source_reference": GOVERNANCE_SOURCE,
            "parent_id": ARU_ID,
        },
    ):
        _upsert_code_master(connection, legal_entity, values)

    site = sa.table(
        "site",
        sa.column("id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("site_type", sa.String()),
        sa.column("region", sa.String()),
        sa.column("owner_entity_id", sa.String()),
        sa.column("fact_state", fact_state_type),
        sa.column("effective_from", sa.Date()),
        sa.column("valid_to", sa.Date()),
        sa.column("recorded_on", sa.Date()),
        sa.column("known_on", sa.Date()),
        sa.column("superseded_on", sa.Date()),
        sa.column("source_reference", sa.String()),
    )
    for values in (
        {
            "id": "2d0018d5-a091-534a-82b5-618d9bb4b860",
            "code": "SAC",
            "name": "Sacramento headquarters",
            "site_type": "OFFICE",
            "region": "California",
            "owner_entity_id": SHI_ID,
            "fact_state": "MODEL_PROPOSED",
            "effective_from": date(2016, 1, 1),
            "valid_to": None,
            "recorded_on": date(2026, 9, 5),
            "known_on": date(2026, 9, 5),
            "superseded_on": None,
            "source_reference": RECONCILIATION_SOURCE,
        },
        {
            "id": "7637d233-b956-5de0-b9fe-eb6cb3c46e53",
            "code": "PIT",
            "name": "Willow laboratory — Pittsburgh area",
            "site_type": "LABORATORY",
            "region": "Pittsburgh area",
            "owner_entity_id": SHI_ID,
            "fact_state": "LOCKED_CANON",
            "effective_from": None,
            "valid_to": None,
            "recorded_on": date(2026, 9, 5),
            "known_on": date(2026, 9, 3),
            "superseded_on": None,
            "source_reference": CANON_SOURCE,
        },
        {
            "id": "2507aa14-4b4d-5684-894e-6198c4d88f80",
            "code": "RED_WASH",
            "name": "Red Wash Mine",
            "site_type": "UNDERGROUND_MINE_MILL",
            "region": "Wyoming",
            "owner_entity_id": RWH_ID,
            "fact_state": "LOCKED_CANON",
            "effective_from": None,
            "valid_to": None,
            "recorded_on": date(2026, 9, 5),
            "known_on": date(2026, 9, 3),
            "superseded_on": None,
            "source_reference": CANON_SOURCE,
        },
        {
            "id": "0d36f3af-d2af-5308-bd25-406682b195a8",
            "code": "ARU_HUB",
            "name": "BS&T railway operating estate (details open)",
            "site_type": "RAIL_TERMINAL_NETWORK",
            "region": "Mountain West",
            "owner_entity_id": BST_ID,
            "fact_state": "MODEL_PROPOSED",
            "effective_from": None,
            "valid_to": None,
            "recorded_on": date(2026, 9, 5),
            "known_on": date(2026, 9, 5),
            "superseded_on": None,
            "source_reference": RECONCILIATION_SOURCE,
        },
    ):
        _upsert_code_master(connection, site, values)

    _reassign_legacy_consolidation_entity(connection)


def _add_master_epistemic_fields() -> None:
    connection = op.get_bind()
    epistemic_cast = "::epistemicstate" if connection.dialect.name == "postgresql" else ""
    date_cast = "::date" if connection.dialect.name == "postgresql" else ""
    if connection.dialect.name == "postgresql":
        postgresql.ENUM(*EPISTEMIC_STATES, name="epistemicstate").create(
            connection, checkfirst=True
        )
    state_type = _epistemic_type()
    with op.batch_alter_table("legal_entity") as batch:
        for column in (
            "existence_state",
            "identity_state",
            "relationship_state",
            "effective_date_state",
        ):
            batch.add_column(sa.Column(column, state_type, nullable=True))
        batch.add_column(sa.Column("valid_to", sa.Date(), nullable=True))
        batch.add_column(sa.Column("recorded_on", sa.Date(), nullable=True))
        batch.add_column(sa.Column("known_on", sa.Date(), nullable=True))
        batch.add_column(sa.Column("superseded_on", sa.Date(), nullable=True))
        batch.add_column(sa.Column("source_reference", sa.String(500), nullable=True))
    connection.execute(
        sa.text(
            "UPDATE legal_entity SET "
            "existence_state = CASE WHEN code IN ('SHI','RWH','ARU','BST') "
            f"THEN 'LOCKED' ELSE 'PROVISIONAL_ASSUMPTION' END{epistemic_cast}, "
            "identity_state = CASE WHEN code IN ('SHI','RWH','ARU','BST') "
            f"THEN 'OPEN' ELSE 'PROVISIONAL_ASSUMPTION' END{epistemic_cast}, "
            "relationship_state = CASE WHEN code IN ('SHI','RWH','ARU','BST') "
            f"THEN 'LOCKED' ELSE 'PROVISIONAL_ASSUMPTION' END{epistemic_cast}, "
            "effective_date_state = 'PROVISIONAL_ASSUMPTION', "
            "recorded_on = '2026-09-05', known_on = '2026-09-03', "
            "source_reference = CASE WHEN code = 'SHI' "
            "THEN 'docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md' "
            "ELSE 'docs/governance/2026_ENTITY_AND_BOARD_GOVERNANCE_DECISIONS.md' END"
        )
    )
    with op.batch_alter_table("legal_entity") as batch:
        for column in (
            "existence_state",
            "identity_state",
            "relationship_state",
            "effective_date_state",
        ):
            batch.alter_column(column, existing_type=state_type, nullable=False)

    with op.batch_alter_table("site") as batch:
        batch.add_column(sa.Column("effective_from", sa.Date(), nullable=True))
        batch.add_column(sa.Column("valid_to", sa.Date(), nullable=True))
        batch.add_column(sa.Column("recorded_on", sa.Date(), nullable=True))
        batch.add_column(sa.Column("known_on", sa.Date(), nullable=True))
        batch.add_column(sa.Column("superseded_on", sa.Date(), nullable=True))
        batch.add_column(sa.Column("source_reference", sa.String(500), nullable=True))
    connection.execute(
        sa.text(
            "UPDATE site SET recorded_on = '2026-09-05', "
            "known_on = CASE WHEN code IN ('PIT','RED_WASH') "
            f"THEN '2026-09-03' ELSE '2026-09-05' END{date_cast}, "
            "source_reference = CASE WHEN code IN ('PIT','RED_WASH') "
            "THEN 'docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md' "
            "ELSE 'docs/finance/QUANTITATIVE_BASELINE_RECONCILIATION.md' END"
        )
    )
    _reconcile_legacy_canon_masters()


def _add_ledger_constraints() -> None:
    with op.batch_alter_table("fiscal_period") as batch:
        batch.create_unique_constraint("uq_fiscal_period_id_book_id", ["id", "book_id"])
        batch.create_check_constraint("ck_fiscal_period_date_order", "starts_on <= ends_on")
    with op.batch_alter_table("journal_entry") as batch:
        batch.create_unique_constraint(
            "uq_journal_entry_generation_run_id_reversal_of_id",
            ["generation_run_id", "reversal_of_id"],
        )
        batch.create_foreign_key(
            "fk_journal_entry_period_book",
            "fiscal_period",
            ["period_id", "book_id"],
            ["id", "book_id"],
        )
        batch.create_check_constraint(
            "ck_journal_entry_lifecycle",
            "(state = 'DRAFT' AND posted_at IS NULL) OR "
            "(state = 'POSTED' AND posted_at IS NOT NULL)",
        )
    with op.batch_alter_table("journal_line") as batch:
        batch.create_check_constraint("ck_journal_line_nonnegative", "debit >= 0 AND credit >= 0")
        batch.create_check_constraint(
            "ck_journal_line_one_side",
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
        )
        batch.create_check_constraint(
            "ck_journal_line_functional_equation", "functional_amount = debit - credit"
        )
        batch.create_check_constraint(
            "ck_journal_line_reporting_equation", "reporting_amount = functional_amount"
        )


def _sqlite_guards() -> None:
    for table in RUN_OWNED_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_running_insert
            BEFORE INSERT ON {table}
            FOR EACH ROW WHEN COALESCE(
              (SELECT status FROM generation_run WHERE id = NEW.generation_run_id), 'MISSING'
            ) <> 'RUNNING'
            BEGIN SELECT RAISE(ABORT, 'generation-owned content requires a running run'); END
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_running_update
            BEFORE UPDATE ON {table}
            FOR EACH ROW WHEN OLD.generation_run_id IS NOT NEW.generation_run_id OR
              COALESCE(
                (SELECT status FROM generation_run WHERE id = OLD.generation_run_id), 'MISSING'
              ) <> 'RUNNING'
            BEGIN SELECT RAISE(ABORT, 'completed generation content is immutable'); END
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_running_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW WHEN COALESCE(
              (SELECT status FROM generation_run WHERE id = OLD.generation_run_id), 'MISSING'
            ) <> 'RUNNING'
            BEGIN SELECT RAISE(ABORT, 'completed generation content is immutable'); END
            """
        )
    for operation in ("update", "delete"):
        op.execute(
            f"""
            CREATE TRIGGER trg_generation_period_close_immutable_{operation}
            BEFORE {operation.upper()} ON generation_period_close
            FOR EACH ROW
            BEGIN SELECT RAISE(ABORT, 'period-close evidence is immutable'); END
            """
        )
    for operation, reference in (("insert", "NEW"), ("update", "OLD"), ("delete", "OLD")):
        reassignment_guard = "NEW.entry_id IS NOT OLD.entry_id OR" if operation == "update" else ""
        op.execute(
            f"""
            CREATE TRIGGER trg_journal_line_running_{operation}
            BEFORE {operation.upper()} ON journal_line
            FOR EACH ROW WHEN {reassignment_guard} COALESCE((
              SELECT gr.status FROM generation_run gr
              JOIN journal_entry je ON je.generation_run_id = gr.id
              WHERE je.id = {reference}.entry_id
            ), 'MISSING') <> 'RUNNING' OR COALESCE((
              SELECT je.state FROM journal_entry je WHERE je.id = {reference}.entry_id
            ), 'MISSING') <> 'DRAFT'
            BEGIN SELECT RAISE(ABORT, 'completed or posted journal content is immutable'); END
            """
        )
    op.execute(
        """
        CREATE TRIGGER trg_journal_entry_draft_insert
        BEFORE INSERT ON journal_entry FOR EACH ROW WHEN
          NEW.state <> 'DRAFT' OR NEW.posted_at IS NOT NULL
        BEGIN SELECT RAISE(ABORT, 'journal entries must be inserted as drafts'); END
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_journal_entry_posted_update
        BEFORE UPDATE ON journal_entry FOR EACH ROW WHEN OLD.state = 'POSTED'
        BEGIN SELECT RAISE(ABORT, 'posted journal entries are immutable'); END
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_journal_entry_posted_delete
        BEFORE DELETE ON journal_entry FOR EACH ROW WHEN OLD.state = 'POSTED'
        BEGIN SELECT RAISE(ABORT, 'posted journal entries are immutable'); END
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_journal_entry_posting_balance
        BEFORE UPDATE OF state ON journal_entry FOR EACH ROW
        WHEN NEW.state = 'POSTED' AND (
          OLD.state <> 'DRAFT' OR NEW.posted_at IS NULL OR NOT EXISTS (
            SELECT 1 FROM journal_line jl WHERE jl.entry_id = OLD.id
            GROUP BY jl.entry_id
            HAVING COUNT(jl.id) > 0 AND SUM(jl.debit) > 0
              AND SUM(jl.debit) = SUM(jl.credit)
          )
        )
        BEGIN SELECT RAISE(ABORT, 'posted journal entries must be balanced and nonzero'); END
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_journal_entry_period_date_insert
        BEFORE INSERT ON journal_entry FOR EACH ROW WHEN NOT EXISTS (
          SELECT 1 FROM fiscal_period fp
          WHERE fp.id = NEW.period_id AND fp.book_id = NEW.book_id
            AND NEW.entry_date BETWEEN fp.starts_on AND fp.ends_on
            AND fp.state = 'OPEN'
            AND NOT EXISTS (
              SELECT 1 FROM generation_period_close gpc
              WHERE gpc.generation_run_id = NEW.generation_run_id
                AND gpc.period_id = NEW.period_id
            )
        )
        BEGIN SELECT RAISE(ABORT, 'journal period, book, and date are incompatible'); END
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_journal_entry_period_date_update
        BEFORE UPDATE OF period_id, book_id, entry_date, state ON journal_entry
        FOR EACH ROW WHEN NOT EXISTS (
          SELECT 1 FROM fiscal_period fp
          WHERE fp.id = NEW.period_id AND fp.book_id = NEW.book_id
            AND NEW.entry_date BETWEEN fp.starts_on AND fp.ends_on
            AND fp.state = 'OPEN'
            AND NOT EXISTS (
              SELECT 1 FROM generation_period_close gpc
              WHERE gpc.generation_run_id = NEW.generation_run_id
                AND gpc.period_id = NEW.period_id
            )
        )
        BEGIN SELECT RAISE(ABORT, 'journal period, book, and date are incompatible'); END
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_generation_run_completion_accounting
        BEFORE UPDATE OF status ON generation_run
        FOR EACH ROW WHEN OLD.status = 'RUNNING' AND NEW.status = 'COMPLETED'
        BEGIN
          SELECT CASE WHEN EXISTS (
            SELECT 1 FROM journal_entry je
            LEFT JOIN fiscal_period fp ON fp.id = je.period_id AND fp.book_id = je.book_id
            WHERE je.generation_run_id = OLD.id
              AND (je.state <> 'POSTED' OR fp.id IS NULL
                   OR je.entry_date < fp.starts_on OR je.entry_date > fp.ends_on)
          ) THEN RAISE(ABORT, 'generation run has invalid journals') END;
          SELECT CASE WHEN EXISTS (
            SELECT 1 FROM journal_entry je
            LEFT JOIN journal_line jl ON jl.entry_id = je.id
            WHERE je.generation_run_id = OLD.id
            GROUP BY je.id
            HAVING COUNT(jl.id) = 0 OR SUM(jl.debit) <= 0 OR SUM(jl.debit) <> SUM(jl.credit)
          ) THEN RAISE(ABORT, 'generation run has unbalanced journals') END;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_debt_repayment_principal_insert
        BEFORE INSERT ON debt_repayment FOR EACH ROW WHEN
          NEW.principal <= 0 OR NEW.principal + COALESCE((
            SELECT SUM(principal) FROM debt_repayment WHERE debt_draw_id = NEW.debt_draw_id
          ), 0) > (SELECT principal FROM debt_draw WHERE id = NEW.debt_draw_id)
        BEGIN SELECT RAISE(ABORT, 'debt repayments exceed draw principal'); END
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_debt_repayment_principal_update
        BEFORE UPDATE OF debt_draw_id, principal ON debt_repayment FOR EACH ROW WHEN
          NEW.principal <= 0 OR NEW.principal + COALESCE((
            SELECT SUM(principal) FROM debt_repayment
            WHERE debt_draw_id = NEW.debt_draw_id AND id <> OLD.id
          ), 0) > (SELECT principal FROM debt_draw WHERE id = NEW.debt_draw_id)
        BEGIN SELECT RAISE(ABORT, 'debt repayments exceed draw principal'); END
        """
    )


def _postgres_guards() -> None:
    op.execute(
        """
        CREATE FUNCTION guard_run_owned_content() RETURNS trigger AS $$
        DECLARE owner_id text; owner_status text;
        BEGIN
          owner_id := CASE WHEN TG_OP = 'INSERT'
            THEN NEW.generation_run_id ELSE OLD.generation_run_id END;
          IF TG_OP = 'UPDATE' AND NEW.generation_run_id IS DISTINCT FROM OLD.generation_run_id THEN
            RAISE EXCEPTION 'generation ownership is immutable';
          END IF;
          SELECT status INTO owner_status FROM generation_run WHERE id = owner_id;
          IF owner_status IS DISTINCT FROM 'RUNNING' THEN
            RAISE EXCEPTION 'completed generation content is immutable';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END; $$ LANGUAGE plpgsql
        """
    )
    for table in RUN_OWNED_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_running_write BEFORE INSERT OR UPDATE OR DELETE "
            f"ON {table} FOR EACH ROW EXECUTE FUNCTION guard_run_owned_content()"
        )
    op.execute(
        """
        CREATE FUNCTION guard_period_close_evidence() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'period-close evidence is immutable';
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_generation_period_close_immutable BEFORE UPDATE OR DELETE "
        "ON generation_period_close FOR EACH ROW EXECUTE FUNCTION guard_period_close_evidence()"
    )
    op.execute(
        """
        CREATE FUNCTION guard_journal_line_write() RETURNS trigger AS $$
        DECLARE target_entry text; owner_status text; entry_state text;
        BEGIN
          target_entry := CASE WHEN TG_OP = 'INSERT' THEN NEW.entry_id ELSE OLD.entry_id END;
          IF TG_OP = 'UPDATE' AND NEW.entry_id IS DISTINCT FROM OLD.entry_id THEN
            RAISE EXCEPTION 'journal-line ownership is immutable';
          END IF;
          SELECT gr.status INTO owner_status FROM generation_run gr
          JOIN journal_entry je ON je.generation_run_id = gr.id WHERE je.id = target_entry;
          SELECT state::text INTO entry_state FROM journal_entry WHERE id = target_entry;
          IF owner_status IS DISTINCT FROM 'RUNNING' OR entry_state IS DISTINCT FROM 'DRAFT' THEN
            RAISE EXCEPTION 'completed or posted journal content is immutable';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_journal_line_running_write BEFORE INSERT OR UPDATE OR DELETE "
        "ON journal_line FOR EACH ROW EXECUTE FUNCTION guard_journal_line_write()"
    )
    op.execute(
        """
        CREATE FUNCTION guard_journal_entry_state() RETURNS trigger AS $$
        DECLARE line_count bigint; total_debit numeric; total_credit numeric;
        BEGIN
          IF TG_OP = 'INSERT' THEN
            IF NEW.state::text <> 'DRAFT' OR NEW.posted_at IS NOT NULL THEN
              RAISE EXCEPTION 'journal entries must be inserted as drafts';
            END IF;
            RETURN NEW;
          END IF;
          IF TG_OP = 'DELETE' THEN
            IF OLD.state::text = 'POSTED' THEN
              RAISE EXCEPTION 'posted journal entries are immutable';
            END IF;
            RETURN OLD;
          END IF;
          IF OLD.state::text = 'POSTED' THEN
            RAISE EXCEPTION 'posted journal entries are immutable';
          END IF;
          IF NEW.state::text = 'POSTED' THEN
            SELECT COUNT(*), COALESCE(SUM(debit), 0), COALESCE(SUM(credit), 0)
              INTO line_count, total_debit, total_credit
              FROM journal_line WHERE entry_id = OLD.id;
            IF NEW.posted_at IS NULL OR line_count = 0 OR total_debit <= 0
              OR total_debit <> total_credit THEN
              RAISE EXCEPTION 'posted journal entries must be balanced and nonzero';
            END IF;
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_journal_entry_state BEFORE INSERT OR UPDATE OR DELETE "
        "ON journal_entry FOR EACH ROW EXECUTE FUNCTION guard_journal_entry_state()"
    )
    op.execute(
        """
        CREATE FUNCTION guard_journal_period_date() RETURNS trigger AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM fiscal_period fp WHERE fp.id = NEW.period_id
              AND fp.book_id = NEW.book_id
              AND NEW.entry_date BETWEEN fp.starts_on AND fp.ends_on
              AND fp.state = 'OPEN'
              AND NOT EXISTS (
                SELECT 1 FROM generation_period_close gpc
                WHERE gpc.generation_run_id = NEW.generation_run_id
                  AND gpc.period_id = NEW.period_id
              )
          ) THEN RAISE EXCEPTION 'journal period, book, and date are incompatible'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_journal_entry_period_date BEFORE INSERT OR UPDATE OF "
        "period_id, book_id, entry_date, state ON journal_entry FOR EACH ROW "
        "EXECUTE FUNCTION guard_journal_period_date()"
    )
    op.execute(
        """
        CREATE FUNCTION guard_generation_completion_accounting() RETURNS trigger AS $$
        BEGIN
          IF OLD.status = 'RUNNING' AND NEW.status = 'COMPLETED' THEN
            IF EXISTS (
              SELECT 1 FROM journal_entry je
              LEFT JOIN fiscal_period fp ON fp.id = je.period_id AND fp.book_id = je.book_id
              WHERE je.generation_run_id = OLD.id
                AND (je.state <> 'POSTED' OR fp.id IS NULL
                     OR je.entry_date < fp.starts_on OR je.entry_date > fp.ends_on)
            ) OR EXISTS (
              SELECT 1 FROM journal_entry je LEFT JOIN journal_line jl ON jl.entry_id = je.id
              WHERE je.generation_run_id = OLD.id GROUP BY je.id
              HAVING COUNT(jl.id) = 0 OR SUM(jl.debit) <= 0 OR SUM(jl.debit) <> SUM(jl.credit)
            ) THEN RAISE EXCEPTION 'generation run has invalid or unbalanced journals'; END IF;
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_generation_run_completion_accounting BEFORE UPDATE OF status "
        "ON generation_run FOR EACH ROW EXECUTE FUNCTION guard_generation_completion_accounting()"
    )
    op.execute(
        """
        CREATE FUNCTION guard_debt_repayment_principal() RETURNS trigger AS $$
        DECLARE already_repaid numeric; drawn numeric;
        BEGIN
          SELECT principal INTO drawn FROM debt_draw WHERE id = NEW.debt_draw_id FOR UPDATE;
          IF TG_OP = 'INSERT' THEN
            SELECT COALESCE(SUM(principal), 0) INTO already_repaid FROM debt_repayment
            WHERE debt_draw_id = NEW.debt_draw_id;
          ELSE
            SELECT COALESCE(SUM(principal), 0) INTO already_repaid FROM debt_repayment
            WHERE debt_draw_id = NEW.debt_draw_id AND id <> OLD.id;
          END IF;
          IF NEW.principal <= 0 OR NEW.principal + already_repaid > drawn THEN
            RAISE EXCEPTION 'debt repayments exceed draw principal';
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_debt_repayment_principal BEFORE INSERT OR UPDATE OF "
        "debt_draw_id, principal ON debt_repayment FOR EACH ROW "
        "EXECUTE FUNCTION guard_debt_repayment_principal()"
    )


def upgrade() -> None:
    _add_master_ownership()
    _add_master_epistemic_fields()
    _add_ledger_constraints()
    if op.get_bind().dialect.name == "sqlite":
        _sqlite_guards()
    else:
        _postgres_guards()


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        for name in (
            "trg_generation_period_close_immutable_delete",
            "trg_generation_period_close_immutable_update",
            "trg_debt_repayment_principal_update",
            "trg_debt_repayment_principal_insert",
            "trg_generation_run_completion_accounting",
            "trg_journal_entry_period_date_update",
            "trg_journal_entry_period_date_insert",
            "trg_journal_entry_posting_balance",
            "trg_journal_entry_posted_delete",
            "trg_journal_entry_posted_update",
            "trg_journal_entry_draft_insert",
        ):
            op.execute(f"DROP TRIGGER {name}")
        for operation in ("delete", "update", "insert"):
            op.execute(f"DROP TRIGGER trg_journal_line_running_{operation}")
        for table in reversed(RUN_OWNED_TABLES):
            for operation in ("delete", "update", "insert"):
                op.execute(f"DROP TRIGGER trg_{table}_running_{operation}")
    else:
        op.execute("DROP TRIGGER trg_generation_period_close_immutable ON generation_period_close")
        op.execute("DROP FUNCTION guard_period_close_evidence()")
        op.execute("DROP TRIGGER trg_debt_repayment_principal ON debt_repayment")
        op.execute("DROP FUNCTION guard_debt_repayment_principal()")
        op.execute("DROP TRIGGER trg_generation_run_completion_accounting ON generation_run")
        op.execute("DROP FUNCTION guard_generation_completion_accounting()")
        op.execute("DROP TRIGGER trg_journal_entry_period_date ON journal_entry")
        op.execute("DROP FUNCTION guard_journal_period_date()")
        op.execute("DROP TRIGGER trg_journal_entry_state ON journal_entry")
        op.execute("DROP FUNCTION guard_journal_entry_state()")
        op.execute("DROP TRIGGER trg_journal_line_running_write ON journal_line")
        op.execute("DROP FUNCTION guard_journal_line_write()")
        for table in reversed(RUN_OWNED_TABLES):
            op.execute(f"DROP TRIGGER trg_{table}_running_write ON {table}")
        op.execute("DROP FUNCTION guard_run_owned_content()")

    with op.batch_alter_table("journal_line") as batch:
        for name in (
            "ck_journal_line_reporting_equation",
            "ck_journal_line_functional_equation",
            "ck_journal_line_one_side",
            "ck_journal_line_nonnegative",
        ):
            batch.drop_constraint(name, type_="check")
    with op.batch_alter_table("journal_entry") as batch:
        batch.drop_constraint("ck_journal_entry_lifecycle", type_="check")
        batch.drop_constraint("fk_journal_entry_period_book", type_="foreignkey")
        batch.drop_constraint("uq_journal_entry_generation_run_id_reversal_of_id", type_="unique")
    with op.batch_alter_table("fiscal_period") as batch:
        batch.drop_constraint("ck_fiscal_period_date_order", type_="check")
        batch.drop_constraint("uq_fiscal_period_id_book_id", type_="unique")

    with op.batch_alter_table("site") as batch:
        for column in (
            "source_reference",
            "superseded_on",
            "known_on",
            "recorded_on",
            "valid_to",
            "effective_from",
        ):
            batch.drop_column(column)
    with op.batch_alter_table("legal_entity") as batch:
        for column in (
            "source_reference",
            "superseded_on",
            "known_on",
            "recorded_on",
            "valid_to",
            "effective_date_state",
            "relationship_state",
            "identity_state",
            "existence_state",
        ):
            batch.drop_column(column)
    if connection.dialect.name == "postgresql":
        postgresql.ENUM(*EPISTEMIC_STATES, name="epistemicstate").drop(connection, checkfirst=True)

    with op.batch_alter_table("purchase_order") as batch:
        batch.drop_constraint("fk_purchase_order_vendor_id_same_run", type_="foreignkey")
    with op.batch_alter_table("customer_contract") as batch:
        batch.drop_constraint("fk_customer_contract_customer_id_same_run", type_="foreignkey")
    duplicate_vendor = connection.execute(
        sa.text("SELECT code FROM vendor GROUP BY code HAVING COUNT(*) > 1 LIMIT 1")
    ).first()
    if duplicate_vendor is not None:
        raise RuntimeError("Cannot downgrade 0015: vendor codes collide across runs")
    op.drop_index("ix_vendor_generation_run_id", table_name="vendor")
    with op.batch_alter_table("vendor") as batch:
        batch.drop_constraint("uq_vendor_id_generation_run_id", type_="unique")
        batch.drop_constraint("uq_vendor_generation_run_id", type_="unique")
        batch.drop_constraint("fk_vendor_generation_run_id", type_="foreignkey")
        batch.drop_column("generation_run_id")
        batch.create_unique_constraint("uq_vendor_code", ["code"])
    op.drop_index("ix_customer_generation_run_id", table_name="customer")
    with op.batch_alter_table("customer") as batch:
        batch.drop_constraint("uq_customer_id_generation_run_id", type_="unique")
        batch.drop_constraint("fk_customer_generation_run_id", type_="foreignkey")
        batch.drop_column("generation_run_id")
