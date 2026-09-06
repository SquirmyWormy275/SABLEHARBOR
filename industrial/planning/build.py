"""Build the preserved industrial case and its versioned planning successor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from industrial.planning import (
    capital,
    enterprise,
    forecast,
    integrity,
    operating_model,
    transactions,
)
from industrial.tools.build_package import run_builders

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "industrial/generated/planning"


def build(output=OUT, *, allow_working_tree=False, package=True):
    """Rebuild all dependencies before accepting or distributing their outputs."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    print("Rebuilding preserved v1 industrial and mine anchors", flush=True)
    run_builders()
    integrity.preservation()
    print("Building physical operating scenarios", flush=True)
    operations = operating_model.build(output / "operations")
    print("Building 2027–2031 monthly financial statements", flush=True)
    finances = forecast.build(output / "forecast", operating_rows=operations["operating_rows"])
    print("Comparing current, outside and owned capital options", flush=True)
    capital.build(output / "capital")
    print("Building linked procurement, service, payroll and cash evidence", flush=True)
    transactions.build(
        output / "transactions", operating_rows=operations["operating_rows"], forecast=finances
    )
    print("Building legal, enterprise and unit consolidation", flush=True)
    enterprise.build(output / "enterprise", forecast_result=finances)
    print("Independently recomputing exported accounts and temporal controls", flush=True)
    report = integrity.validate(output)
    if package:
        if output.resolve() != OUT.resolve():
            raise ValueError(
                "Participant catalog selects canonical outputs; custom output cannot be packaged"
            )
        from industrial.planning.package import build as package_build

        report["package"] = package_build(allow_working_tree=allow_working_tree)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-working-tree", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            build(allow_working_tree=args.allow_working_tree, package=not args.skip_package),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
