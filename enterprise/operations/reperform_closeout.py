"""Read-only independent joins over one materialized company source edition."""

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

from .completed_period import ROOT, SOURCE, read, validate
from .current_balances import verify_core_asset_balances, verify_legal_balances
from .current_records import validate_current, verify_current_finance
from .debt_host import validate as validate_debt_host
from .payroll_legal_bridge import verify as verify_payroll_legal
from .september_custody import build as build_custody
from .september_custody import verify_source_expense


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_hashes(base, expected):
    base = base.resolve()
    for relative, value in expected.items():
        path = (base / relative).resolve()
        if not path.is_relative_to(base) or not path.is_file() or digest(path) != value:
            raise ValueError(f"Missing, stale or unsafe materialized input: {relative}")


def verify_identity(completed_manifest, completed, finance_identity, september, revision):
    revisions = [
        completed_manifest["source_commit"],
        completed["repository_source_commit"],
        finance_identity["source_revision"],
        september["repository_source_commit"],
    ]
    if any(value != revision for value in revisions):
        raise ValueError(
            "Mixed source revisions: regenerate all components from selected source commit"
        )
    if (
        finance_identity.get("dirty_development_build")
        or not completed.get("publishable_source_snapshot")
        or not september.get("publishable_source_snapshot")
    ):
        raise ValueError("Dirty preview cannot support final composite reperformance")
    if completed.get("effective_through") != "2026-08-31":
        raise ValueError("Wrong completed-period edition")


def verify_csv_tables(completed_dir, tables):
    """Compare nested JSON by typed content and scalar CSV fields exactly."""
    for name, expected in tables.items():
        with (completed_dir / (name + ".csv")).open(newline="") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            fields = reader.fieldnames or []
        keys = {key for row in expected for key in row}
        if len(fields) != len(set(fields)) or set(fields) != keys or len(rows) != len(expected):
            raise ValueError(f"CSV/JSON population mismatch: {name}")
        for actual, source in zip(rows, expected, strict=True):
            for key in keys:
                value = source.get(key)
                cell = actual[key]
                if isinstance(value, (dict, list)):
                    try:
                        # Canonical JSON preserves number/bool type distinction too.
                        match = json.dumps(json.loads(cell), sort_keys=True) == json.dumps(
                            value, sort_keys=True
                        )
                    except (ValueError, TypeError):
                        match = False
                else:
                    match = cell == ("" if value is None else str(value))
                if not match:
                    raise ValueError(f"CSV/JSON population mismatch: {name}/{key}")


def reperform(completed_dir, finance_dir, september_dir, revision):
    paths = [
        completed_dir / "manifest.json",
        completed_dir / "records.json",
        finance_dir / "manifest.json",
        finance_dir / "identity.json",
        september_dir / "records.json",
    ]
    cm, edition, fm, identity, september = [json.loads(p.read_text()) for p in paths]
    verify_identity(cm, edition, identity, september, revision)
    subprocess.run(
        ["git", "cat-file", "-e", revision + "^{commit}"], cwd=ROOT, check=True, capture_output=True
    )
    verify_hashes(completed_dir, cm["artifacts"])
    verify_hashes(finance_dir, fm)
    verify_hashes(ROOT, edition["source_hashes"])
    verify_hashes(ROOT, identity["source_files"])
    verify_hashes(ROOT, september["source_hashes"])
    tables = edition["tables"]
    verify_csv_tables(completed_dir, tables)
    journal_path = finance_dir / "enterprise/enterprise_journal.csv"
    tb_path = finance_dir / "enterprise/legal_monthly_trial_balances.csv"
    journal = list(csv.DictReader(journal_path.open()))
    trial = list(csv.DictReader(tb_path.open()))
    from industrial.planning.enterprise import load_anchor
    from industrial.planning.legacy_adapter import legacy_snapshot

    anchor = load_anchor()
    checks = dict(
        completed_population=validate(read(SOURCE), tables),
        current_population=validate_current(read(SOURCE), tables),
        current_source_finance=verify_current_finance(edition, legacy_snapshot(), anchor),
        legal_balances=verify_legal_balances(tables, trial),
        core_assets=verify_core_asset_balances(tables, trial),
        payroll_legal=verify_payroll_legal(edition, journal, trial),
        september_freight=verify_source_expense(september, anchor),
        debt_host=validate_debt_host(edition["debt_host_evidence"], anchor),
    )
    custody = build_custody(august=edition)
    for key in ("record_id", "lot_rollforward", "expense_bridge"):
        if september[key] != custody[key]:
            raise ValueError("September custody derivative differs from controlling source")
    for actual, expected in zip(september["events"], custody["events"], strict=True):
        if any(
            actual[key] != expected[key]
            for key in (
                "event_id",
                "event",
                "effective_at",
                "qualification_id",
                "lot_id",
                "drum_id",
                "quantity_lb_u3o8",
                "legal_owner",
                "custodian_id",
            )
        ):
            raise ValueError("September event identity or custody differs from source")
    hashed = {str(p): digest(p) for p in paths + [journal_path, tb_path]}
    hashed.update({str(completed_dir / name): value for name, value in cm["artifacts"].items()})
    return dict(
        status="PASS_SELECTED_COMPOSITE_REPERFORMANCE",
        source_commit=revision,
        input_hashes=hashed,
        finance_manifest_sha256=digest(finance_dir / "manifest.json"),
        table_counts={name: len(rows) for name, rows in tables.items()},
        checks=checks,
        limitations=[
            "Synthetic internal evidence; no audit opinion or real bank/agency confirmation.",
            "Tests reperform declared populations; hashes alone do not prove completeness.",
            "Acceptance, deployment and unresolved rights retain separate edition dispositions.",
        ],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--completed-dir", type=Path, default=ROOT / "enterprise/generated/completed-period-2026-08"
    )
    parser.add_argument(
        "--finance-dir", type=Path, default=ROOT / "enterprise/generated/company-closeout-v1"
    )
    parser.add_argument(
        "--september-dir", type=Path, default=ROOT / "enterprise/generated/september-custody-2026"
    )
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    revision = (
        args.source_commit
        or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    )
    result = reperform(args.completed_dir, args.finance_dir, args.september_dir, revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {"status": result["status"], "source_commit": revision, "output": str(args.output)}
        )
    )


if __name__ == "__main__":
    main()
