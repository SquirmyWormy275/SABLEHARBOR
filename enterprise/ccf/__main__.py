"""Build and verify a reproducible, scoped CCF preparation package."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from enterprise.ccf import database, examples
from enterprise.ccf.registry import ROOT, compile_registry, coverage, digest, validate


def inputs(repository):
    paths = sorted(
        p
        for p in (Path(repository) / "enterprise/ccf").rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix in {".py", ".json", ".sql", ".md"}
    )
    # The finance assertion adapter and runtime recovery function are executable dependencies.
    paths += [
        Path(repository) / "enterprise/operations/controls.py",
        Path(repository) / "enterprise/runtime/security.py",
        Path(repository) / "enterprise/runtime/model.py",
        Path(repository) / "enterprise/runtime/source_schema.json",
    ]
    return {
        str(p.relative_to(repository)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
    }


def write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    )


def build(output, repository=ROOT):
    output, repository = Path(output), Path(repository)
    if output.exists():
        raise ValueError("Build output must be new; existing evidence is never overwritten")
    registry = compile_registry(repository)
    exercises = examples.run(registry, repository)
    # Build to private staging; expose a complete package only after validation.
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ccf-", dir=output.parent) as temp:
        staged = Path(temp) / "package"
        staged.mkdir()
        write_json(staged / "registry.json", registry)
        write_json(staged / "exercises.json", exercises)
        (staged / "COVERAGE.md").write_text(coverage(registry))
        with database.connect(staged / "registry.sqlite3") as connection:
            identity = database.append(connection, registry)
        files = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(staged.iterdir())
        }
        manifest = dict(
            schema_version="0.1.0",
            classification="PUBLIC_SYNTHETIC_PREPARATION",
            snapshot_id=identity,
            source_manifest=registry["source_manifest"],
            implementation_manifest=inputs(repository),
            files=files,
        )
        write_json(staged / "MANIFEST.json", manifest)
        (staged / "SHA256SUMS.txt").write_text(
            "".join(
                f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
                for p in sorted(staged.iterdir())
            )
        )
        staged.rename(output)
    return manifest


def verify(output, repository=ROOT):
    output = Path(output)
    manifest = json.loads((output / "MANIFEST.json").read_text())
    required = {"registry.json", "exercises.json", "COVERAGE.md", "registry.sqlite3"}
    if set(manifest["files"]) != required or {p.name for p in output.iterdir()} != required | {
        "MANIFEST.json",
        "SHA256SUMS.txt",
    }:
        raise ValueError("Unknown or missing package member")
    for name, sha in manifest["files"].items():
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != sha:
            raise ValueError(f"Package content changed: {name}")
    sums = "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
        for p in sorted(output.iterdir())
        if p.name != "SHA256SUMS.txt"
    )
    if sums != (output / "SHA256SUMS.txt").read_text():
        raise ValueError("Checksum inventory differs")
    if inputs(Path(repository)) != manifest["implementation_manifest"]:
        raise ValueError("Implementation source drift")
    actual = json.loads((output / "registry.json").read_text())
    expected = compile_registry(repository)
    if (
        actual != expected
        or digest(actual) != manifest["snapshot_id"]
        or actual["source_manifest"] != manifest["source_manifest"]
    ):
        raise ValueError("Registry differs from native sources")
    if json.loads((output / "exercises.json").read_text()) != examples.run(expected, repository):
        raise ValueError("Exercise output differs from source re-performance")
    if (output / "COVERAGE.md").read_text() != coverage(expected):
        raise ValueError("Coverage differs from registry")
    # Compare full database logical content with a fresh migration/import, not just row counts.
    with tempfile.TemporaryDirectory() as temp:
        with (
            database.connect(Path(temp) / "expected.sqlite3") as check,
            database.connect(output / "registry.sqlite3") as actual_db,
        ):
            database.append(check, expected)
            if list(check.iterdump()) != list(actual_db.iterdump()):
                raise ValueError("Database differs from normalized registry")
    return validate(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify", "validate", "query"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--as-of")
    parser.add_argument("--known-on")
    args = parser.parse_args()
    if args.command == "validate":
        result = validate(compile_registry(), ROOT)
    elif args.command == "query":
        if not args.database or not args.database.is_file() or not args.as_of or not args.known_on:
            parser.error("query requires existing --database, --as-of and --known-on")
        with database.connect(args.database) as connection:
            result = database.historical(connection, args.as_of, args.known_on)
    else:
        if args.output is None:
            parser.error("--output is required")
        result = build(args.output) if args.command == "build" else verify(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
