#!/usr/bin/env python3
"""Inventory every file in a pinned Git tree; preserve exact, located source occurrences.

This is a discovery index, not a canon adjudicator. Binary extraction and OCR are
explicitly distinguished from manual image review. Original bytes stay in Git.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import pathlib
import re
import sqlite3
import subprocess
import tarfile
import tempfile
import zipfile
from collections import Counter
from xml.etree import ElementTree as ET

BASE = pathlib.Path(__file__).resolve().parents[1]
ROOT = BASE.parent
CANON = "8d20e51a7cf0068729e3296840ccb5ba1ac1d7bd"
TERMS = re.compile(r"\b(location|site|facility|office|headquarters|HQ|mine|plant|yard|terminal|rail|railroad|warehouse|campus|lab|field|district|region|state|county|city|route|corridor|port|interchange|branch|project|acquisition|lease|property|parcel|Sacramento|Pittsburgh|Charleston|Belle|Kanawha|Hazelwood|Wamsutter|Bloodstone|Nevada|Wyoming|Deloraine|Tasmania|Australia|Afghanistan|Badakhshan|Reno|Elko|Tucson|California|Pennsylvania|Arizona|Sar.e.Sang|Carbon|Sweetwater|Red.Wash|Blackridge|West.Highwall)\b", re.I)
TEXT_EXT = {".md", ".txt", ".csv", ".json", ".geojson", ".yaml", ".yml", ".sql", ".py", ".html", ".svg", ".xml", ".toml", ".ini", ".mako", ".example", ".js", ".lock", ".sha256", ""}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def strings(value, pointer=""):
    if isinstance(value, str):
        yield pointer or "/", value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings(item, pointer + "/" + str(key).replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, pointer + "/" + str(index))


def extract(data, name, temp, ocr):
    suffix = pathlib.PurePosixPath(name).suffix.lower()
    if suffix in {".json", ".geojson"}:
        return list(strings(json.loads(data))), "JSON_STRINGS_EXTRACTED"
    if suffix in TEXT_EXT:
        return [(f"line:{i}", line) for i, line in enumerate(data.decode("utf-8").splitlines(), 1)], "TEXT_SCANNED"
    if suffix == ".pdf":
        from pypdf import PdfReader
        rows = []
        for p, page in enumerate(PdfReader(io.BytesIO(data)).pages, 1):
            rows.extend((f"page:{p}:line:{i}", line) for i, line in enumerate((page.extract_text() or "").splitlines(), 1))
        return rows, "PDF_TEXT_EXTRACTED_VISUAL_REVIEW_SEPARATE"
    if suffix in {".docx", ".pptx", ".xlsx"}:
        rows = []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for member in sorted(z.namelist()):
                if member.endswith(".xml") and member.startswith(("word/", "ppt/slides/", "ppt/notesSlides/", "xl/")):
                    root = ET.fromstring(z.read(member))
                    for i, element in enumerate(root.iter()):
                        if element.tag.rsplit("}", 1)[-1] in {"t", "v"} and element.text:
                            rows.append((f"{member}:element:{i}", element.text))
        return rows, "OFFICE_XML_EXTRACTED"
    if suffix in {".sqlite", ".sqlite3", ".db"}:
        file = temp / (sha(data) + suffix)
        file.write_bytes(data)
        rows = []
        with sqlite3.connect(f"file:{file}?mode=ro", uri=True) as db:
            for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
                quoted = '"' + table.replace('"', '""') + '"'
                cur = db.execute("SELECT * FROM " + quoted)
                columns = [d[0] for d in cur.description]
                for i, row in enumerate(cur, 1):
                    for col, val in zip(columns, row):
                        if isinstance(val, str):
                            rows.append((f"table:{table}:row:{i}:column:{col}", val))
        return rows, "SQLITE_TEXT_EXTRACTED"
    if suffix == ".zip":
        rows, statuses = [], []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for member in sorted(z.namelist()):
                if not member.endswith("/"):
                    part, status = extract(z.read(member), member, temp, ocr)
                    rows.extend((f"archive:{member}:{loc}", line) for loc, line in part)
                    statuses.append(status)
        return rows, "ARCHIVE_EXTRACTED:" + ";".join(sorted(set(statuses)))
    if suffix in {".png", ".jpg", ".jpeg"}:
        if not ocr:
            return [], "IMAGE_REGISTERED_OCR_DEFERRED"
        file = temp / (sha(data) + suffix)
        file.write_bytes(data)
        proc = subprocess.run(["tesseract", str(file), "stdout", "--psm", "11"], capture_output=True, text=True, check=True)
        return [(f"ocr-line:{i}", line) for i, line in enumerate(proc.stdout.splitlines(), 1)], "IMAGE_OCR_NOT_VISUAL_VERIFICATION"
    return [], "UNSUPPORTED_BINARY_REGISTERED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=CANON)
    ap.add_argument("--no-ocr", action="store_true")
    args = ap.parse_args()
    commit = subprocess.check_output(["git", "rev-parse", args.ref], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(["git", "archive", "--format=tar", commit], cwd=ROOT)
    coverage, hits, cache, errors = [], [], {}, []
    with tempfile.TemporaryDirectory(prefix="sh-geo-census-") as tmp:
        temp = pathlib.Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            members = sorted((m for m in tar if m.isfile()), key=lambda m: m.name)
            for count, member in enumerate(members, 1):
                data = tar.extractfile(member).read()
                digest = sha(data)
                try:
                    if digest not in cache:
                        cache[digest] = extract(data, member.name, temp, not args.no_ocr)
                    rows, method = cache[digest]
                except Exception as exc:
                    rows, method = [], "EXTRACTION_FAILED"
                    errors.append({"source_path": member.name, "error": str(exc)})
                coverage.append({"source_path": member.name, "source_commit": commit, "bytes": len(data), "file_sha256": digest, "extraction_method": method, "extracted_text_units": len(rows)})
                for locator, line in rows:
                    matches = sorted(set(m.group().lower() for m in TERMS.finditer(line)))
                    if matches:
                        key = member.name + "\0" + locator + "\0" + line
                        hits.append({"occurrence_id": "OCC-" + sha(key.encode())[:16], "source_path": member.name, "source_locator": locator, "source_commit": commit, "exact_source_wording": line, "matched_terms": ";".join(matches), "extraction_method": method, "review_status": "DISCOVERY_OCCURRENCE_NOT_CANON"})
                if count % 100 == 0:
                    print(f"Indexed {count}/{len(members)} source files", flush=True)
    out = BASE / "registers"
    write_csv(out / "SOURCE_COVERAGE.csv", coverage, list(coverage[0]))
    write_csv(out / "GEOGRAPHIC_CANDIDATE_OCCURRENCES.csv", hits, list(hits[0]))
    raw = (out / "GEOGRAPHIC_CANDIDATE_OCCURRENCES.csv").read_bytes()
    (out / "GEOGRAPHIC_CANDIDATE_OCCURRENCES.csv.gz").write_bytes(gzip.compress(raw, mtime=0))
    (out / "GEOGRAPHIC_CANDIDATE_OCCURRENCES.csv").unlink()
    unique = {}
    for hit in hits:
        wording = hit["exact_source_wording"]
        if wording not in unique:
            unique[wording] = {"statement_id": "STMT-" + sha(wording.encode())[:16], "exact_source_wording": wording, "occurrence_count": 0, "example_source": hit["source_path"], "example_locator": hit["source_locator"], "review_status": "DISCOVERY_ONLY_SEE_CURATED_OBJECT_REGISTER"}
        unique[wording]["occurrence_count"] += 1
    statements = sorted(unique.values(), key=lambda r: r["statement_id"])
    write_csv(out / "DISCOVERY_STATEMENTS.csv", statements, list(statements[0]))
    manifest = {"source_commit": commit, "tracked_files": len(coverage), "candidate_occurrences": len(hits), "extraction_methods": dict(Counter(r["extraction_method"] for r in coverage)), "errors": errors, "semantic_census_complete": False, "scope": "Entire pinned main tree, including Office XML, PDF text, SQLite text, ZIP contents, raster OCR. OCR is an extraction aid; named map originals receive separate visual review.", "canon_promotion": "None. Adjudicated objects live in GEOGRAPHIC_CENSUS_v0.1.csv."}
    (out / "CENSUS_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
