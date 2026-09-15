"""Re-extract the residual census against its immutable original source bytes."""

from collections import defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from geospatial.scripts.census import extract

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "d91a22c35c91b213204411421de88815f27d8e16"


def build(output):
    hits = list(
        csv.DictReader(gzip.open(ROOT / "geospatial/completion/REMAINING_OCCURRENCES.csv.gz", "rt"))
    )
    sources = defaultdict(list)
    for hit in hits:
        sources[hit["source_path"]].append(hit)
    coverage = {
        r["source_path"]: r
        for r in csv.DictReader((ROOT / "geospatial/registers/SOURCE_COVERAGE.csv").open())
    }
    output.mkdir(parents=True, exist_ok=True)
    records = []
    source_units = {}
    with tempfile.TemporaryDirectory() as tmp:
        for path, rows in sorted(sources.items()):
            raw = subprocess.check_output(["git", "show", BASELINE + ":" + path], cwd=ROOT)
            digest = hashlib.sha256(raw).hexdigest()
            if digest != coverage[path]["file_sha256"]:
                raise ValueError("Source mismatch: " + path)
            units, method = extract(raw, path, Path(tmp), False)
            indexed = {loc: (i, text) for i, (loc, text) in enumerate(units)}
            source_units[path] = dict(sha256=digest, method=method, units=units)
            for hit in rows:
                index, text = indexed[hit["source_locator"]]
                if text != hit["exact_source_wording"]:
                    raise ValueError("Locator/text mismatch: " + hit["occurrence_id"])
                headings = [(loc, t) for loc, t in units[: index + 1] if t.startswith("#")]
                records.append(
                    dict(
                        **hit,
                        source_sha256=digest,
                        section=headings[-1] if headings else None,
                        context=units[max(0, index - 3) : index + 4],
                    )
                )
    (output / "EXTRACTED_RESIDUAL.json.gz").write_bytes(
        gzip.compress(json.dumps(records, ensure_ascii=False).encode(), mtime=0)
    )
    (output / "SOURCE_UNITS.json.gz").write_bytes(
        gzip.compress(json.dumps(source_units, ensure_ascii=False).encode(), mtime=0)
    )
    summary = dict(
        baseline=BASELINE,
        source_files=len(sources),
        exact_carriers=len(records),
        extracted_units=sum(len(s["units"]) for s in source_units.values()),
        scope="Verified extraction and context for semantic adjudication; extraction alone is not a disposition.",
    )
    (output / "EXTRACTION.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    build(ROOT / "var/final-review/extraction")
