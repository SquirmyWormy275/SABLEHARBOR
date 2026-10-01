"""Reconcile exact discovery carriers without treating implementation copies as canon."""

import ast
from collections import Counter
import csv
import gzip
import io
import json
from pathlib import Path

from geospatial.chronology.build import ROOT, archived, pointer, sha
from geospatial.chronology.operations_review import DISCOVERY
from tools.evidence.closeout import residual_geography

# This scope was inspected as an implementation/representation population. Narrative,
# spreadsheet and publication claims are deliberately not rejected by file extension.
IMPLEMENTATION = {".py", ".js", ".sql", ".yml", ".toml", ".sha256", ".svg", ".html"}
FINANCE = "industrial/source/finance.json"
FINANCE_SCOPES = {
    "acquisition_tax_allocation": "ACQUISITION_ACCOUNTING_ALLOCATION",
    "aro_successor": "MODELLED_RECLAMATION_LIABILITY",
    "assumption_ledger": "EXPLICIT_FINANCIAL_ASSUMPTION",
    "contracts": "SYNTHETIC_CONTRACT_RECORD",
    "customers": "CUSTOMER_IDENTITY_RECORD",
    "employees": "WORKFORCE_ALLOCATION_RECORD",
    "forecast_2026": "FINANCIAL_FORECAST_REFERENCE",
    "legal_book_policy": "ACCOUNTING_POLICY_REFERENCE",
    "transaction": "SYNTHETIC_TRANSACTION_RECORD",
    "working_capital_support": "WORKING_CAPITAL_REFERENCE",
}


def category(path):
    ext = Path(path).suffix
    if ext in IMPLEMENTATION:
        return "IMPLEMENTATION_REFERENCE"
    if ext == ".geojson" and path.startswith("industrial/source/geography/"):
        return "FEATURE_PROPERTY"
    if path == FINANCE:
        return "FINANCIAL_RECORD"
    return None


def context(raw, hit):
    text = raw.decode()
    locator = hit["source_locator"]
    if locator.startswith("line:"):
        number = int(locator.split(":")[1])
        lines = text.splitlines()
        if lines[number - 1] != hit["exact_source_wording"]:
            raise ValueError("Source line mismatch: " + hit["occurrence_id"])
        first, last = max(1, number - 4), min(len(lines), number + 4)
        owner = "module"
        if hit["source_path"].endswith(".py"):
            tree = ast.parse(text)
            nodes = [
                n
                for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and n.lineno <= number <= n.end_lineno
            ]
            if nodes:
                node = min(nodes, key=lambda n: n.end_lineno - n.lineno)
                owner = type(node).__name__ + ":" + node.name
        return f"lines:{first}-{last}", "\n".join(lines[first - 1 : last]), owner
    if locator.startswith("/"):
        doc = json.loads(text)
        value = pointer(doc, locator)
        if value != hit["exact_source_wording"]:
            raise ValueError("Source value mismatch: " + hit["occurrence_id"])
        parts = locator.split("/")[1:]
        record_path = "/" + parts[0]
        if len(parts) > 1 and parts[1].isdigit():
            record_path += "/" + parts[1]
        return record_path, pointer(doc, record_path), parts[0]
    raise ValueError("Unsupported source locator: " + locator)


def review():
    residual, earlier = residual_geography()
    operations = json.loads((ROOT / "geospatial/chronology/OPERATIONS_REVIEW.json").read_text())
    after_operations = [
        r for r in residual if r["source_path"] != "industrial/source/operations.json"
    ]
    coverage = {
        r["source_path"]: r
        for r in csv.DictReader((ROOT / "geospatial/registers/SOURCE_COVERAGE.csv").open())
    }
    raw_sources = {}
    output = []
    for hit in after_operations:
        path = hit["source_path"]
        kind = category(path)
        if not kind:
            continue
        if path not in raw_sources:
            raw_sources[path] = archived(path, DISCOVERY)
            if sha(raw_sources[path]) != coverage[path]["file_sha256"]:
                raise ValueError("Source hash mismatch: " + path)
        locator, record, owner = context(raw_sources[path], hit)
        geometry_hash = None
        if kind == "FINANCIAL_RECORD":
            disposition = FINANCE_SCOPES[owner]
            limit = "Keep the full dated financial/contract record. This carrier is not independent parcel, access, historical alignment or occupancy evidence. Financial semantics remain in the source; no tax/legal execution is asserted."
        elif kind == "FEATURE_PROPERTY":
            geometry_hash = sha(
                json.dumps(record["geometry"], sort_keys=True, separators=(",", ":")).encode()
            )
            disposition = (
                "SYNTHETIC_NETWORK_PROPERTY"
                if Path(path).name in ("network.geojson", "selected_mainline.geojson")
                else "EXTERNAL_REFERENCE_FEATURE_PROPERTY"
            )
            limit = "Retain the entire feature, all properties and its geometry hash. Historical source geometry is not promoted into current canon, title or historic occupancy."
        else:
            ext = Path(path).suffix
            disposition = {
                ".svg": "RENDERED_DIAGRAM_OR_IDENTITY_REFERENCE",
                ".sha256": "ARTIFACT_CHECKSUM_REFERENCE",
                ".sql": "DATABASE_SCHEMA_OR_QUERY_REFERENCE",
                ".yml": "CONFIGURATION_OR_WORKFLOW_REFERENCE",
                ".toml": "PROJECT_CONFIGURATION_REFERENCE",
                ".html": "RENDERED_INTERFACE_REFERENCE",
            }.get(ext, "EXECUTABLE_OR_TEST_REFERENCE")
            limit = "The exact carrier occurs in implementation or a rendered representation. Keep identifiers, literal values and nearby source context; do not use this copy as independent geographic corroboration. Embedded fixture/geometry content is not erased or declared false."
        output.append(
            dict(
                **hit,
                source_sha256=coverage[path]["file_sha256"],
                disposition=disposition,
                containing_locator=locator,
                containing_record=record,
                implementation_owner=owner,
                geometry_sha256=geometry_hash,
                limit=limit,
            )
        )
    selected = {r["occurrence_id"] for r in output}
    remaining = [r for r in after_operations if r["occurrence_id"] not in selected]
    summary = dict(
        baseline_revision=DISCOVERY,
        reviewed_carriers=len(output),
        source_files=len(raw_sources),
        prior_reviewed_carriers=operations["cumulative_reviewed_occurrences"],
        cumulative_reviewed_carriers=operations["cumulative_reviewed_occurrences"] + len(output),
        remaining_carriers=len(remaining),
        by_disposition=dict(sorted(Counter(r["disposition"] for r in output).items())),
        scope="Carrier-level semantic distinction for implementation, financial records and geographic feature properties; narrative and later-source claim adjudication remains separate.",
        semantic_census_complete=False,
        issue_108_complete=False,
        new_geometry_or_occupancy=False,
    )
    if summary["cumulative_reviewed_carriers"] + len(remaining) != earlier["baseline"]:
        raise ValueError("Discovery population does not reconcile")
    return output, remaining, summary


def write(output):
    rows, remaining, summary = review()
    output.mkdir(parents=True, exist_ok=True)
    for name, values in [("SOURCE_REVIEW", rows), ("REMAINING_OCCURRENCES", remaining)]:
        stream = io.StringIO()
        writer = csv.DictWriter(stream, list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            {
                k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                for k, v in r.items()
            }
            for r in values
        )
        raw = gzip.compress(stream.getvalue().encode(), mtime=0)
        (output / (name + ".csv.gz")).write_bytes(raw)
        summary[name.lower() + "_sha256"] = sha(raw)
    (output / "SOURCE_REVIEW.json").write_text(json.dumps(summary, indent=2) + "\n")
    return rows, summary


if __name__ == "__main__":
    write(ROOT / "geospatial/completion")
