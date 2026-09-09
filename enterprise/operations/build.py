"""Build and reconcile the complete operating-depth successor."""

import argparse
import json
import shutil
import zipfile
from pathlib import Path

from enterprise.business import validation as old_validation
from enterprise.business.build import git, replacement_bridge
from enterprise.business.build import sources as base_sources
from enterprise.business.model import BusinessModel
from industrial.planning import enterprise, forecast, operating_model, transactions
from industrial.planning.legacy_adapter import legacy_snapshot
from industrial.tools.build_package import run_builders
from sable_harbor.exports.safety import scan_generated_artifacts
from sable_harbor.provenance.identity import generation_input_paths

from . import (
    commercial,
    controls,
    credit,
    exports,
    management,
    matters,
    research,
    workforce,
)
from .model import OperatingModel

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "enterprise/generated/operations-v1"
DIST = ROOT / "enterprise/dist/operations-v1.0.0"
VERSION = "1.0.0"


def sources(model):
    result = base_sources(model)
    for relative in generation_input_paths():
        path = ROOT / relative
        result[str(path.relative_to(ROOT))] = exports.file_hash(path)
    for relative in ("alembic.ini", "db/migrations/env.py", "pyproject.toml"):
        if (ROOT / relative).is_file():
            result[relative] = exports.file_hash(ROOT / relative)
    for path in sorted((ROOT / "enterprise/operations").rglob("*")):
        if path.is_file() and path.suffix in {".py", ".json", ".md", ".mjs", ".xlsx"}:
            if "__pycache__" not in path.parts and "tests" not in path.parts:
                result[str(path.relative_to(ROOT))] = exports.file_hash(path)
    return result


def enterprise_policy(model, version):
    policy = json.loads(enterprise.SOURCE.read_text())
    policy["model_id"] = f"SH-ENTERPRISE-OPERATING-V{version}"
    policy["schema_version"] = f"{version}.0.0"
    policy["knowledge_cutoff"] = model.policy["available_at"]
    policy["created_on"] = model.policy["as_of"]
    policy["core"]["payment_deferral_accounts"] = {
        "OPERATING": "CORE_UNPAID",
        "INVESTING": "BIZ_CAPITAL_UNPAID",
        "FINANCING": "BIZ_DEBT_UNPAID",
    }
    policy["canonical_sources"] = list(
        dict.fromkeys(policy["canonical_sources"] + model.policy["canonical_sources"])
    )
    return policy


def prepare_output(output):
    if output.resolve() != OUT.resolve():
        raise ValueError("Only the explicit operations output directory is allowed")
    marker = output / "generator.json"
    if output.exists():
        if (
            not marker.is_file()
            or json.loads(marker.read_text()).get("generator") != "operations-v1"
        ):
            raise ValueError("Refusing to replace an unowned output directory")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    exports.write_json(marker, {"generator": "operations-v1"})


def build(*, allow_working_tree=False, schema_draft=False, prepare_review=False, package=True):
    revision = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    if (dirty or schema_draft or prepare_review) and not allow_working_tree:
        raise ValueError("Development options/dirty source require --allow-working-tree")
    model = OperatingModel()
    initial = sources(model)
    prepare_output(OUT)
    print("Building operating histories and financial journals", flush=True)
    model.build()
    business_checks = old_validation.business(model)
    domains = {
        m.__name__.split(".")[-1]: m.validate(model)
        for m in (credit, commercial, matters, research, workforce)
    }
    print("Preserving industrial and 2026 reconstruction boundaries", flush=True)
    run_builders(ROOT)
    ops = operating_model.build(OUT / "industrial/operations")
    fin = forecast.build(OUT / "industrial/forecast", operating_rows=ops["operating_rows"])
    industrial = transactions.build(
        OUT / "industrial/transactions", operating_rows=ops["operating_rows"], forecast=fin
    )
    legacy = legacy_snapshot()
    previous = BusinessModel().build()
    baseline = enterprise.build(
        OUT / "comparison/business-v1",
        forecast_result=fin,
        legacy_result=legacy,
        source=enterprise_policy(previous, 3),
        core_provider=previous,
    )
    result = enterprise.build(
        OUT / "enterprise",
        forecast_result=fin,
        legacy_result=legacy,
        source=enterprise_policy(model, 4),
        core_provider=model,
    )
    integrated = old_validation.enterprise(result, baseline, model)
    bridge = replacement_bridge(baseline, result)
    exports.csv_table(OUT / "replacement_bridge.csv", bridge)
    print("Allocating cash requests, revising forecasts and testing controls", flush=True)
    credit.allocate_treasury(model, result)
    research.build_industrial_detail(
        model, ops["operating_rows"], industrial["tables"], fin["journal_rows"]
    )
    management.build(model, result, model_factory=OperatingModel)
    matters.build_matter_packages(model, OUT / "client_packages")
    controls.build_controls(
        model,
        result,
        extras={"industrial_operations": ops["operating_rows"], "replacement_bridge": bridge},
    )
    for module in (credit, commercial, matters, research, workforce, management, controls):
        domains[module.__name__.split(".")[-1]] = module.validate(model)
    identity = {
        "version": VERSION,
        "run_id": result["summary"]["run_id"],
        "source_revision": revision,
        "business_input_sha256": model.input_hash,
        "source_snapshot_sha256": exports.content_hash(initial),
        "source_files": initial,
        "legacy_generation_identity": legacy["metadata"],
        "classification": "PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST",
        "periods": "2026 preserved calibration; 2027–2031 conditional operating scenarios",
        "dirty_development_build": dirty,
        "schema_draft": schema_draft,
        "review_preparation_only": prepare_review,
    }
    exports.write_json(OUT / "identity.json", identity)
    tables = exports.collect_tables(model, result)
    from .review import review_inputs, verify_review

    review = review_inputs(model, result)
    exports.write_json(OUT / "review_inputs.json", review)
    if not prepare_review:
        verify_review(review, OUT)
    if schema_draft:
        # Review proposals are not released exports and cannot produce a ZIP.
        exports.write_json(
            OUT / "proposed_export_schema.json",
            {n: exports.columns(r) for n, r in sorted(tables.items())},
        )
        exports.write_json(OUT / "proposed_export_scope.json", exports.proposed_scope(tables))
        counts = {n: len(r) for n, r in tables.items()}
    else:
        print("Writing and checking scoped CSV/SQLite packages", flush=True)
        counts = exports.write_packages(OUT, tables, identity)
    report = {
        "status": "DEVELOPMENT" if schema_draft or prepare_review else "PASS",
        "business": business_checks,
        "enterprise": integrated,
        "domains": domains,
        "table_counts": {n: len(r) for n, r in tables.items()},
        "unit_table_counts": counts,
        "source_revision": revision,
        "limitations": [
            "Synthetic scenarios, not observed company records or operational approvals.",
            "Industrial dated allocations may expose infeasible dispatch capacity.",
            "Control FAIL and NOT_RUN outcomes are distinct from software acceptance.",
            "Treasury attributes modeled requests; unit cash does not establish bank balances.",
            "Legal elections, appointments, production access/retention and geography remain gated.",
        ],
    }
    exports.write_json(OUT / "validation.json", report)
    if not (schema_draft or prepare_review):
        print("Scanning every final artifact before release acceptance", flush=True)
        failures = scan_generated_artifacts(OUT)
        if failures:
            raise ValueError(f"Complete release artifact safety failed: {failures[:5]}")
        exports.write_json(
            OUT / "public_safety.json",
            {"status": "PASS", "scope": "Complete final output", "findings": []},
        )
    if initial != sources(model) or revision != git("rev-parse", "HEAD"):
        raise ValueError("Source changed during build; repeat from stable checkout")
    exports.inventory(OUT, identity)
    old_validation.verify_files(OUT)
    if package and not (schema_draft or prepare_review):
        DIST.mkdir(parents=True, exist_ok=True)
        archive = DIST / f"sable-harbor-business-operations-v{VERSION}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for path in sorted(OUT.rglob("*")):
                if path.is_file():
                    info = zipfile.ZipInfo(str(path.relative_to(OUT)), (2026, 9, 9, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    bundle.writestr(info, path.read_bytes())
        (DIST / "SHA256SUMS.txt").write_text(
            exports.file_hash(archive) + "  " + archive.name + "\n"
        )
        report["archive"] = str(archive.relative_to(ROOT))
    print(
        json.dumps(
            {
                "status": report["status"],
                "events": len(model.tables["events"]),
                "tables": len(tables),
                "archive": report.get("archive"),
            },
            indent=2,
        ),
        flush=True,
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-working-tree", action="store_true")
    parser.add_argument("--schema-draft", action="store_true")
    parser.add_argument("--prepare-review", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    args = parser.parse_args()
    build(
        allow_working_tree=args.allow_working_tree,
        schema_draft=args.schema_draft,
        prepare_review=args.prepare_review,
        package=not args.skip_package,
    )


if __name__ == "__main__":
    main()
