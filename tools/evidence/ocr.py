"""Extract candidate text from hash-verified archived PNGs; never adjudicate it."""

import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def collect(root, output, source_inventory):
    executable = shutil.which("tesseract")
    if not executable:
        raise ValueError("OCR requires Tesseract and its English language data")
    version = subprocess.check_output([executable, "--version"], text=True)
    languages = subprocess.check_output([executable, "--list-langs"], text=True)
    match = re.search(r'"([^\"]+)"', languages)
    if not match or "eng" not in languages.splitlines():
        raise ValueError("Cannot identify the English OCR model")
    model = Path(match.group(1)) / "eng.traineddata"
    configuration = {
        "version": version,
        "language": "eng",
        "page_segmentation_mode": 11,
        "executable_sha256": hashlib.sha256(Path(executable).read_bytes()).hexdigest(),
        "language_model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
        "classification": "UNREVIEWED_OCR_CANDIDATES",
        "limitations": "Sparse-text OCR of the 97 individually registered baseline PNGs only. PDFs, embedded archive images and new images are not covered. Text and confidence are machine estimates; no geographic claim or visual review is implied.",
    }
    rows = [
        r
        for r in source_inventory["baseline_sources"]
        if r["extraction_method"] == "IMAGE_REGISTERED_OCR_DEFERRED"
    ]
    records = []
    logdir = output / "ocr"
    logdir.mkdir()
    with tempfile.TemporaryDirectory(prefix="sable-ocr-") as temp:
        for index, row in enumerate(rows):
            path = Path(temp) / "source.png"
            content = subprocess.check_output(
                ["git", "show", row["source_commit"] + ":" + row["source_path"]],
                cwd=root,
            )
            if hashlib.sha256(content).hexdigest() != row["file_sha256"]:
                raise ValueError("OCR source differs from the verified archive")
            path.write_bytes(content)
            started = datetime.now(timezone.utc).isoformat()
            clock = time.monotonic()
            result = subprocess.run(
                [executable, str(path), "stdout", "-l", "eng", "--psm", "11", "tsv"],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "OMP_THREAD_LIMIT": "1"},
            )
            stem = f"image-{index + 1:03d}"
            (logdir / (stem + ".tsv")).write_text(result.stdout)
            (logdir / (stem + ".log")).write_text(
                result.stderr.replace(str(path), "[archived source PNG]")
            )
            words = [
                r
                for r in csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
                if r.get("text", "").strip()
            ]
            records.append(
                {
                    "source_path": row["source_path"],
                    "source_commit": row["source_commit"],
                    "source_sha256": row["file_sha256"],
                    "classification": "UNREVIEWED_OCR_CANDIDATES",
                    "started_at_utc": started,
                    "elapsed_seconds": round(time.monotonic() - clock, 3),
                    "exit_code": result.returncode,
                    "word_count": len(words),
                    "text": " ".join(w["text"] for w in words),
                    "tsv": "ocr/" + stem + ".tsv",
                    "log": "ocr/" + stem + ".log",
                }
            )
    report = {
        "configuration": configuration,
        "images": records,
        "successful_images": sum(r["exit_code"] == 0 for r in records),
        "total_images": len(records),
        "reviewed_geographic_claims": 0,
    }
    (output / "ocr-results.json").write_text(json.dumps(report, indent=2) + "\n")
    if not all(r["exit_code"] == 0 for r in records):
        raise ValueError("OCR execution failed; inspect retained outputs")
    return report
