"""Build internal CCF workbenches, verify their provenance, or export approved statements."""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from enterprise.ccf.__main__ import inputs, write_json
from enterprise.ccf.registry import ROOT, compile_registry, digest

from .catalog import starter
from .engine import data, plan, reviewed
from .examples import blank_assessment, example
from .models import Assessment, Catalog
from .reporting import csv_report, explorer, markdown, workbook


def read_json(path):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"Non-finite JSON value: {value}")

    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=constant)


def files(path):
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.iterdir())
        if p.name != "MANIFEST.json" and p.is_file()
    }


def verify_sources(catalog, source_root=None):
    """Keep licensed bytes outside exports; require content-addressed originals for real sources."""
    for source in catalog.sources:
        if source.access != "AVAILABLE":
            continue
        if source_root is None:
            raise ValueError("Available source requires --source-root with the original document")
        path = Path(source_root) / source.content_sha256
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing original source document: {source.id}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != source.content_sha256:
            raise ValueError(f"Original source hash mismatch: {source.id}")


def build(output, catalog, assessment, native, repository=ROOT, source_root=None):
    verify_sources(catalog, source_root)
    result = plan(catalog, assessment, native)
    output = Path(output)
    if output.exists():
        raise ValueError("Output must be a new directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-assurance-", dir=output.parent) as temp:
        staged = Path(temp) / "package"
        staged.mkdir(mode=0o700)
        write_json(staged / "catalog.json", data(catalog))
        write_json(staged / "assessment.json", data(assessment))
        write_json(staged / "delta.json", result)
        write_json(staged / "catalog.schema.json", Catalog.model_json_schema())
        write_json(staged / "assessment.schema.json", Assessment.model_json_schema())
        (staged / "DELTA.md").write_text(markdown(result))
        (staged / "delta.csv").write_text(csv_report(result), newline="")
        (staged / "explorer.html").write_text(explorer(result))
        workbook(staged / "workbench.xlsx", result, catalog, assessment, native)
        write_json(
            staged / "MANIFEST.json",
            dict(
                schema_version="0.2.0",
                audience="INTERNAL",
                origin=assessment.scope.origin,
                native_snapshot_id=digest(native),
                catalog_digest=digest(data(catalog)),
                assessment_digest=digest(data(assessment)),
                implementation_manifest=inputs(Path(repository)),
                files=files(staged),
            ),
        )
        for path in staged.iterdir():
            path.chmod(0o600)
        staged.rename(output)
    return result["summary"]


def verify(output, repository=ROOT, source_root=None):
    output = Path(output)
    manifest = read_json(output / "MANIFEST.json")
    expected_members = {
        "catalog.json",
        "assessment.json",
        "delta.json",
        "catalog.schema.json",
        "assessment.schema.json",
        "DELTA.md",
        "delta.csv",
        "explorer.html",
        "workbench.xlsx",
        "MANIFEST.json",
    }
    if {p.name for p in output.iterdir()} != expected_members or any(
        p.is_symlink() or not p.is_file() for p in output.iterdir()
    ):
        raise ValueError("Unknown, missing or indirect package member")
    if files(output) != manifest["files"]:
        raise ValueError("Package hash inventory differs")
    native = compile_registry(repository)
    catalog = Catalog.model_validate(read_json(output / "catalog.json"))
    assessment = Assessment.model_validate(read_json(output / "assessment.json"))
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "reperformed"
        build(expected, catalog, assessment, native, repository, source_root)
        for name in expected_members:
            if (output / name).read_bytes() != (expected / name).read_bytes():
                raise ValueError(f"Package differs from source re-performance: {name}")
    return {"verified": True, "native_snapshot_id": digest(native)}


def customer_statements(catalog, assessment, native, source_root=None):
    verify_sources(catalog, source_root)
    result = plan(catalog, assessment, native)
    if assessment.scope.origin != "OPERATING_RECORDS" or not reviewed(
        assessment.scope.review, assessment.scope.known_on
    ):
        raise ValueError("Customer export requires reviewed operating scope")
    if not assessment.disclosures:
        raise ValueError("No approved customer statements supplied")
    for disclosure in assessment.disclosures:
        if not reviewed(disclosure.review, assessment.scope.known_on):
            raise ValueError("Disclosure review is not available")
        rows = [r for r in result["rows"] if r["requirement_id"] in disclosure.requirement_ids]
        if {r["requirement_id"] for r in rows} != set(disclosure.requirement_ids) or any(
            r["status"] != "SUPPORTED" for r in rows
        ):
            raise ValueError(
                "Customer statement references unselected, excluded or unsupported requirements"
            )
    # Only the explicitly supplied, reviewed statement is exported. No private evidence, counts,
    # source locators, test findings or other internal fields are interpolated into customer prose.
    return dict(
        kind="APPROVED_CUSTOMER_STATEMENTS",
        scope_id=assessment.scope.id,
        period_start=str(assessment.scope.period_start),
        period_end=str(assessment.scope.period_end),
        statements=[
            dict(audience=d.audience, statement=d.statement) for d in assessment.disclosures
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["starter", "demo", "build", "verify", "customer"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--assessment", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument(
        "--target",
        action="append",
        help="Replace extension selection with this framework (repeatable); clears scope review",
    )
    args = parser.parse_args()
    if args.target and args.command not in {"starter", "demo", "build"}:
        parser.error("--target is only valid for starter/demo/build")
    try:
        if args.command == "verify":
            result = verify(args.output, source_root=args.source_root)
        else:
            native = compile_registry()
            if args.command == "starter":
                catalog = starter(native)
                assessment = blank_assessment(catalog)
            elif args.command == "demo":
                catalog, assessment = example(native)
            else:
                if not args.catalog or not args.assessment:
                    parser.error("build/customer require --catalog and --assessment")
                catalog = Catalog.model_validate(read_json(args.catalog))
                assessment = Assessment.model_validate(read_json(args.assessment))
            if args.target:
                framework_map = {f.id: f for f in catalog.frameworks}
                if (
                    len(args.target) != len(set(args.target))
                    or not set(args.target) <= framework_map.keys()
                ):
                    raise ValueError("Unknown or duplicate target framework")
                changed = data(assessment)
                changed["scope"]["targets"] = [
                    dict(framework_id=fid, categories=framework_map[fid].categories)
                    for fid in args.target
                ]
                changed["scope"]["review"] = None
                assessment = Assessment.model_validate(changed)
            if args.command == "customer":
                result = customer_statements(catalog, assessment, native, args.source_root)
                # Exclusive create keeps earlier customer statements immutable at this path.
                descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w") as file:
                    json.dump(result, file, indent=2, allow_nan=False)
                    file.write("\n")
            else:
                result = build(
                    args.output, catalog, assessment, native, source_root=args.source_root
                )
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"CCF assurance error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
