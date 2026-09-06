"""Execute the governed v0.1 engine in isolation and select its explicit run context."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def legacy_snapshot(seed=20260831):
    """Return deterministic selected business rows, never an unfiltered database sum.

    Real execution timestamps remain in the temporary database and are intentionally
    absent from the semantic extract. The legacy immutable run/canon guards execute.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import select

    from sable_harbor import schema as schema  # noqa: F401
    from sable_harbor.accounting.models import (
        Account,
        AccountingBook,
        JournalEntry,
        JournalLine,
        LegalEntity,
    )
    from sable_harbor.accounting.validation import validate_financial_integrity
    from sable_harbor.core.database import build_engine, require_migrated_schema, session_for
    from sable_harbor.generation import generate_standard
    from sable_harbor.provenance.identity import repository_head
    from sable_harbor.provenance.service import (
        complete_generation_run,
        link_journals,
        record_generation_run,
        run_context,
        seed_provenance,
    )

    previous_url = os.environ.get("SHFIN_DATABASE_URL")
    previous_cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="sable-enterprise-legacy-") as temporary:
        url = "sqlite:///" + str(Path(temporary) / "isolated-legacy.sqlite3")
        os.environ["SHFIN_DATABASE_URL"] = url
        try:
            os.chdir(ROOT)
            configuration = Config(str(ROOT / "alembic.ini"))
            command.upgrade(configuration, "head")
            engine = build_engine(url)
            require_migrated_schema(engine)
            with session_for(engine) as session:
                run = record_generation_run(
                    session,
                    profile="standard",
                    scenario_code="base",
                    seed=seed,
                    git_commit=repository_head(),
                )
                generate_standard(session, seed=seed, scenario="base")
                seed_provenance(session)
                link_journals(session, run)
                complete_generation_run(session, run)
                session.commit()
                context = run_context(session, run.id)
                validation = validate_financial_integrity(session, run.id)
                if not validation.passed:
                    raise ValueError("Legacy engine financial validation failed")
                entities = {
                    entity.id: entity.code for entity in session.scalars(select(LegalEntity))
                }
                query = (
                    select(JournalEntry, JournalLine, AccountingBook, LegalEntity, Account)
                    .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
                    .join(AccountingBook, AccountingBook.id == JournalEntry.book_id)
                    .join(LegalEntity, LegalEntity.id == AccountingBook.entity_id)
                    .join(Account, Account.id == JournalLine.account_id)
                    .where(JournalEntry.generation_run_id.in_(context.included_run_ids))
                    .order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id)
                )
                rows = []
                for entry, line, book, entity, account in session.execute(query):
                    if str(entry.state.value) != "POSTED":
                        raise ValueError("Unposted legacy journal in selected context")
                    rows.append(
                        {
                            "legacy_run_id": entry.generation_run_id,
                            "journal_id": entry.id,
                            "line_id": line.id,
                            "entry_date": entry.entry_date.isoformat(),
                            "entity": entity.code,
                            "book": book.code,
                            "segment": line.segment_code or "CORPORATE",
                            "account": account.code,
                            "account_name": account.name,
                            "account_type": account.account_class.lower(),
                            "debit_usd": str(line.debit),
                            "credit_usd": str(line.credit),
                            "signed_usd": str(line.debit - line.credit),
                            "counterparty": entities.get(line.counterparty_entity_id, ""),
                            "description": entry.description,
                            "source_type": entry.source_type,
                            "source_id": entry.source_id,
                            "fact_state": "LEGACY_SYNTHETIC_CALIBRATION_OR_FORECAST",
                        }
                    )
                metadata = {
                    "profile": "standard",
                    "scenario": "base",
                    "seed": seed,
                    "run_id": context.generation_run_id,
                    "included_run_ids": list(context.included_run_ids),
                    "input_manifest_digest": run.input_manifest_digest,
                    "schema_head": run.schema_head,
                    "source_revision": repository_head(),
                    "validation_controls": len(validation.controls),
                    "selected_rows": len(rows),
                    "semantic_rows_sha256": hashlib.sha256(canonical_bytes(rows)).hexdigest(),
                    "database_execution": "Fresh isolated Alembic DB; no production/shared DB",
                    "determinism_boundary": "Canonical rows; excludes execution timestamps",
                    "evidence_boundary": "Synthetic calibration; no observed company accounts",
                }
            engine.dispose()
        finally:
            os.chdir(previous_cwd)
            if previous_url is None:
                os.environ.pop("SHFIN_DATABASE_URL", None)
            else:
                os.environ["SHFIN_DATABASE_URL"] = previous_url
    return {"metadata": metadata, "rows": rows}
