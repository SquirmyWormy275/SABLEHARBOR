"""Build a separate runtime enterprise successor and exact predecessor statement bridge."""

import argparse
import hashlib
import json
import subprocess
from decimal import Decimal as D
from enterprise.operations.model import OperatingModel
from enterprise.operations.build import enterprise_policy
from collections import defaultdict
from industrial.planning import enterprise, forecast, operating_model
from industrial.planning.legacy_adapter import legacy_snapshot
from industrial.tools.build_package import run_builders
from . import model
from .finance import RuntimeAdjustment, verify_land_adjustment

ROOT = model.ROOT
OUT = ROOT / "enterprise/generated/runtime-v1"


def replacement_bridge(before, after):
    keys = ("scenario", "entity", "year", "month", "account", "unit")
    bridge = []
    combined = defaultdict(D)
    expected = defaultdict(D)
    for row in before["journal_rows"]:
        key = tuple(row[k] for k in keys)
        combined[key] += D(row["signed_usd"])
        if int(row["year"]) > 2026:
            combined[key] -= D(row["signed_usd"])
            bridge.append(
                {k: row[k] for k in keys}
                | {
                    "action": "REMOVE_PRIOR_FORECAST",
                    "signed_usd": str(-D(row["signed_usd"])),
                    "source_id": row["source_id"],
                }
            )
    for row in after["journal_rows"]:
        key = tuple(row[k] for k in keys)
        expected[key] += D(row["signed_usd"])
        if int(row["year"]) > 2026 or row["source_id"] == "RT-LAND-20260904":
            combined[key] += D(row["signed_usd"])
            bridge.append(
                {k: row[k] for k in keys}
                | {
                    "action": "ADD_RUNTIME_LAND_OVERLAY"
                    if int(row["year"]) == 2026
                    else "ADD_SUCCESSOR_FORECAST",
                    "signed_usd": row["signed_usd"],
                    "source_id": row["source_id"],
                }
            )
    if {k: v for k, v in combined.items() if v} != {
        k: v for k, v in expected.items() if v
    }:
        raise ValueError("Runtime bridge does not reconstruct enterprise successor")
    return bridge


def build(allow_working_tree=False):
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ).strip()
    )
    if dirty and not allow_working_tree:
        raise ValueError(
            "Runtime release requires clean source; development needs --allow-working-tree"
        )
    source = model.load()
    model.validate(source, ROOT)
    from enterprise.operations.build import sources as operating_sources

    def snapshot():
        result = operating_sources(OperatingModel())
        for p in sorted((ROOT / "enterprise/runtime").rglob("*")):
            if (
                "tests" not in p.parts
                and p.suffix in {".py", ".json"}
                and "publications" not in p.parts
                and "visuals" not in p.parts
            ):
                result[str(p.relative_to(ROOT))] = hashlib.sha256(
                    p.read_bytes()
                ).hexdigest()
        for relative in model.FILES.values():
            result[relative] = hashlib.sha256(
                (ROOT / relative).read_bytes()
            ).hexdigest()
        return result

    source_snapshot = snapshot()
    initial = model.export(source)["source_sha256"]
    OUT.mkdir(parents=True, exist_ok=True)
    print(
        "Building runtime successor from retained operations and industrial sources",
        flush=True,
    )
    run_builders(ROOT)
    op = operating_model.build(OUT / "industrial/operations")
    fin = forecast.build(
        OUT / "industrial/forecast", operating_rows=op["operating_rows"]
    )
    legacy = legacy_snapshot()
    operating = OperatingModel().build()
    predecessor = enterprise.build(
        OUT / "predecessor",
        forecast_result=fin,
        legacy_result=legacy,
        source=enterprise_policy(operating, 4),
        core_provider=operating,
    )
    policy = enterprise_policy(operating, 5)
    policy.update(
        model_id="SH-ENTERPRISE-RUNTIME-V1",
        schema_version="5.0.0",
        knowledge_cutoff="2026-09-11",
        created_on="2026-09-11",
    )
    policy["canonical_sources"] += list(model.FILES.values())
    policy["core"]["additional_deferrable_source_types"] = [
        "RUNTIME_CONDITIONAL_FORECAST_REQUEST"
    ]
    successor = enterprise.build(
        OUT / "enterprise",
        forecast_result=fin,
        legacy_result=legacy,
        source=policy,
        core_provider=operating,
        adjustment_provider=RuntimeAdjustment(source),
    )
    rows = enterprise.read_csv(OUT / "enterprise/enterprise_journal.csv")
    check = verify_land_adjustment(rows)
    bridge = replacement_bridge(predecessor, successor)
    enterprise.write_csv(OUT / "runtime_statement_bridge.csv", bridge)
    # The accepted historical journals must survive byte-for-field outside adjustment identity dates.
    before = enterprise.read_csv(OUT / "predecessor/enterprise_journal.csv")
    fields = (
        "scenario",
        "entity",
        "year",
        "month",
        "account",
        "signed_usd",
        "source_id",
        "source_type",
        "description",
        "cash_flow",
        "segment",
    )

    def history(records):
        return sorted(
            tuple(r[k] for k in fields)
            for r in records
            if int(r["year"]) == 2026 and not r["source_id"].startswith("RT-")
        )

    if history(before) != history(rows):
        raise ValueError(
            "Runtime changed preserved 2026 journals outside explicit land overlay"
        )
    if (
        model.export(model.load())["source_sha256"] != initial
        or snapshot() != source_snapshot
        or revision
        != subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    ):
        raise ValueError("Runtime sources changed during build")
    identity = {
        "source_revision": revision,
        "runtime_source_sha256": initial,
        "dirty_development_build": dirty,
        "source_files": source_snapshot,
        "classification": "SYNTHETIC_SUCCESSOR_NOT_REAL_PAYMENTS",
        "land": check,
        "limitations": [
            "Settlement clearing is unresolved, not vendor financing.",
            "Future expenses and IT acceptance are conditional scenarios, not actual occupied employees or operations.",
            "Construction remains CIP; no building/plant in-service event is fabricated.",
            "Runtime delayed-build sensitivity is separate from the three consolidated enterprise scenarios.",
        ],
    }
    (OUT / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    (OUT / "runtime.json").write_text(json.dumps(model.export(source), indent=2) + "\n")
    inventory = {
        str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(OUT.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    }
    (OUT / "manifest.json").write_text(json.dumps(inventory, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in identity.items() if k != "source_files"}, indent=2
        ),
        flush=True,
    )
    return identity


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-working-tree", action="store_true")
    build(parser.parse_args().allow_working_tree)
