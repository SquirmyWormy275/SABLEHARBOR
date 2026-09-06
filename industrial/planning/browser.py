"""Build an offline browser from explicitly selected planning exports."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(__file__).with_name("browser_template.html")


def dataset(path, relative):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        rows = []
        for source in reader:
            row = []
            for col in columns:
                value = source.get(col, "")
                if value is None:
                    raise ValueError(f"excess CSV fields: {relative}")
                if col in {"year", "month"} or col.endswith("_usd"):
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        pass
                row.append(value)
            rows.append(row)
    dictionaries = {}
    # Repeated metadata dominates the half-million-row case. Column dictionaries
    # reduce disk parsing and let the browser reuse the same immutable strings.
    for index in range(len(columns)):
        values = [row[index] for row in rows]
        if not values or not all(isinstance(value, str) for value in values):
            continue
        unique = list(dict.fromkeys(values))
        if len(unique) * 2 >= len(values):
            continue
        lookup = {value: number for number, value in enumerate(unique)}
        dictionaries[str(index)] = unique
        for row in rows:
            row[index] = lookup[row[index]]
    return {
        "path": relative,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "columns": columns,
        "rows": rows,
        "string_dictionaries": dictionaries,
    }


def build(stage, entries, source_revision, source_state):
    stage = Path(stage)
    tables = {}
    documents = []
    for item in entries:
        path = item["path"]
        file = stage / path
        if path.startswith("industrial/generated/planning/") and file.suffix == ".csv":
            short = path.removeprefix("industrial/generated/planning/")[:-4]
            # Enterprise baseline staging has execution provenance in its raw
            # database. Only allowlisted canonical CSV tables enter this browser.
            tables[short] = dataset(file, path)
        if file.suffix.lower() in {".md", ".pdf", ".svg", ".png"}:
            documents.append(
                {
                    key: item.get(key, "")
                    for key in ("path", "kind", "available_at", "fact_state", "sha256")
                }
            )
    if not tables:
        raise ValueError("No planning datasets selected for offline browser")
    names = set()
    for table in tables.values():
        if "scenario" in table["columns"]:
            idx = table["columns"].index("scenario")
            dictionary = table["string_dictionaries"].get(str(idx))
            names.update(
                value
                for row in table["rows"]
                if (value := dictionary[row[idx]] if dictionary is not None else row[idx])
            )
    payload = {
        "version": "2.0.0",
        "source_revision": source_revision,
        "source_state": source_state,
        "scenarios": sorted(names),
        "tables": tables,
        "documents": documents,
    }
    serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    # Prevent content in a synthetic source record from terminating a script tag
    # when the companion payload is inspected or embedded in a later renderer.
    serialized = serialized.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    (stage / "case_data.js").write_text("window.SABLE_CASE=" + serialized + ";\n")
    shutil.copyfile(TEMPLATE, stage / "case_browser.html")
    return {
        "table_count": len(tables),
        "document_count": len(documents),
        "record_count": sum(len(t["rows"]) for t in tables.values()),
        "browser_path": "case_browser.html",
        "data_path": "case_data.js",
    }
