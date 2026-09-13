"""Inventory every baseline PDF page and archive image, with bounded OCR execution."""

import csv
import io
import json
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
import fitz
from geospatial.chronology.build import ROOT, archived, sha


def build(output, execute_ocr=True):
    output.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((ROOT / "geospatial/registers/SOURCE_COVERAGE.csv").open()))
    known = {
        r["file_sha256"]: r["source_path"]
        for r in rows
        if r["extraction_method"] == "IMAGE_REGISTERED_OCR_DEFERRED"
    }
    records = []
    pdf_seen = {}
    image_seen = {}
    source_count = 0

    def image_record(raw, path, locator):
        digest = sha(raw)
        records.append(
            dict(
                record_id=sha((path + "::" + locator).encode())[:24],
                source_path=path,
                locator=locator,
                kind="EMBEDDED_IMAGE",
                sha256=digest,
                bytes=len(raw),
                known_visual_source=known.get(digest),
                duplicate_of=image_seen.get(digest),
                disposition="EXACT_BYTES_OF_REVIEWED_BASELINE_PNG"
                if digest in known
                else "IMAGE_CONTENT_REVIEW_OPEN",
            )
        )
        image_seen.setdefault(digest, path + "::" + locator)

    def pdf(raw, path, locator):
        digest = sha(raw)
        if digest in pdf_seen:
            records.append(
                dict(
                    record_id=sha((path + "::" + locator).encode())[:24],
                    source_path=path,
                    locator=locator,
                    kind="PDF_DUPLICATE",
                    sha256=digest,
                    duplicate_of=pdf_seen[digest],
                    disposition="EXACT_BYTES_OF_INVENTORIED_PDF",
                )
            )
            return
        pdf_seen[digest] = path + "::" + locator
        doc = fitz.open(stream=raw, filetype="pdf")
        for index, page in enumerate(doc):
            loc = locator + f":page:{index + 1}"
            text = page.get_text()
            images = page.get_images(full=True)
            candidate = len(text.split()) < 40 and bool(images)
            ident = sha((path + "::" + loc).encode())[:24]
            record = dict(
                record_id=ident,
                source_path=path,
                locator=loc,
                kind="PDF_PAGE",
                source_sha256=digest,
                text_sha256=sha(text.encode()),
                text_words=len(text.split()),
                embedded_images=len(images),
                ocr_candidate=candidate,
                disposition="OCR_CANDIDATE"
                if candidate
                else "TEXT_LAYER_AVAILABLE_VISUAL_REVIEW_SEPARATE",
                ocr_status="NOT_REQUIRED_BY_SPARSE_IMAGE_RULE" if not candidate else "NOT_EXECUTED",
            )
            if candidate and execute_ocr:
                pixels = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image_path = output / (ident + ".png")
                pixels.save(image_path)
                result = subprocess.run(
                    ["tesseract", str(image_path), "stdout", "-l", "eng", "--psm", "11", "tsv"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env={**os.environ, "OMP_THREAD_LIMIT": "1"},
                )
                (output / (ident + ".tsv")).write_text(result.stdout)
                (output / (ident + ".log")).write_text(
                    result.stderr.replace(str(image_path), "[source page]")
                )
                record.update(
                    ocr_status="EXECUTED_MACHINE_CANDIDATES"
                    if result.returncode == 0
                    else "FAILED",
                    ocr_exit_code=result.returncode,
                    render_sha256=sha(image_path.read_bytes()),
                    tsv=ident + ".tsv",
                    tsv_sha256=sha(result.stdout.encode()),
                )
                image_path.unlink()
                if result.returncode:
                    raise ValueError("OCR failed: " + loc)
            records.append(record)
        for xref in sorted({img[0] for page in doc for img in page.get_images(full=True)}):
            image_record(doc.extract_image(xref)["image"], path, locator + f":image-xref:{xref}")
        doc.close()

    def container(raw, path, locator, depth=0):
        if depth > 3:
            raise ValueError("Nested archive exceeds supported depth")
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if (
                len(z.infolist()) > 10000
                or sum(r.file_size for r in z.infolist()) > 256 * 1024 * 1024
            ):
                raise ValueError("Archive exceeds inspection bound")
            for member in z.infolist():
                suffix = Path(member.filename).suffix.lower()
                if suffix not in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".pdf",
                    ".zip",
                    ".docx",
                    ".pptx",
                    ".xlsx",
                }:
                    continue
                content = z.read(member)
                loc = locator + "!" + member.filename
                if suffix == ".pdf":
                    pdf(content, path, loc)
                elif suffix in {".zip", ".docx", ".pptx", ".xlsx"}:
                    container(content, path, loc, depth + 1)
                else:
                    image_record(content, path, loc)

    for row in rows:
        path = row["source_path"]
        suffix = Path(path).suffix.lower()
        if suffix not in {".pdf", ".zip", ".docx", ".pptx", ".xlsx"}:
            continue
        raw = archived(path, row["source_commit"])
        if sha(raw) != row["file_sha256"]:
            raise ValueError("Raster inventory source hash mismatch")
        source_count += 1
        if suffix == ".pdf":
            pdf(raw, path, "document")
        else:
            container(raw, path, "archive")
    for row in rows:
        if not row["source_path"].endswith(".tif"):
            continue
        from rasterio.io import MemoryFile

        raw = archived(row["source_path"], row["source_commit"])
        if sha(raw) != row["file_sha256"]:
            raise ValueError("Numeric raster source hash mismatch")
        with MemoryFile(raw) as memory, memory.open() as dataset:
            records.append(
                dict(
                    record_id=sha(row["source_path"].encode())[:24],
                    source_path=row["source_path"],
                    locator="dataset",
                    kind="NUMERIC_GEOTIFF",
                    source_sha256=sha(raw),
                    crs=str(dataset.crs),
                    width=dataset.width,
                    height=dataset.height,
                    bands=dataset.count,
                    dtypes=list(dataset.dtypes),
                    transform=list(dataset.transform),
                    disposition="GEOGRAPHIC_NUMERIC_RASTER_NOT_TEXT_OCR",
                    limit="Elevation/reference cells remain source data; metadata read does not certify accuracy, tenure or site suitability.",
                )
            )
    version = (
        subprocess.check_output(["tesseract", "--version"], text=True).splitlines()[0]
        if execute_ocr
        else None
    )
    provenance = {}
    if execute_ocr:
        languages = subprocess.check_output(["tesseract", "--list-langs"], text=True)
        match = re.search(r'"([^"]+)"', languages)
        if not match:
            raise ValueError("Cannot identify OCR language model")
        model = Path(match[1]) / "eng.traineddata"
        provenance = dict(
            executable_sha256=sha(Path(shutil.which("tesseract")).read_bytes()),
            language_model_sha256=sha(model.read_bytes()),
            language="eng",
            page_segmentation_mode=11,
            dpi=144,
        )
    report = dict(
        ocr_provenance=provenance,
        baseline_revision=rows[0]["source_commit"],
        container_sources=source_count,
        unique_pdfs=len(pdf_seen),
        numeric_geotiffs=sum(r["kind"] == "NUMERIC_GEOTIFF" for r in records),
        pdf_pages=sum(r["kind"] == "PDF_PAGE" for r in records),
        embedded_image_occurrences=sum(r["kind"] == "EMBEDDED_IMAGE" for r in records),
        unique_image_bytes=len(image_seen),
        images_matching_reviewed_baseline_bytes=sum(
            r.get("known_visual_source") is not None for r in records
        ),
        ocr_candidates=sum(r.get("ocr_candidate", False) for r in records),
        ocr_executed=sum(r.get("ocr_status") == "EXECUTED_MACHINE_CANDIDATES" for r in records),
        ocr_engine=version,
        scope="All baseline PDF/ZIP/DOCX/PPTX/XLSX containers are inspected. OCR covers unique low-text PDF pages with raster images (<40 extracted words, 144 dpi, English psm 11). Image-role review, tiny vector labels and later source versions are separate; machine text is never promoted to canon.",
        records=records,
    )
    (output / "RASTER_INVENTORY.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--inventory-only", action="store_true")
    a = p.parse_args()
    r = build(a.output, not a.inventory_only)
    print(json.dumps({k: v for k, v in r.items() if k != "records"}, indent=2))
