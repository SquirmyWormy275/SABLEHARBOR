"""Immutable native artifacts with safe rendering and bounded import inspection."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import os
import re
import stat
import zipfile
from pathlib import Path

from .store import DomainError, canonical, identifier

MAX_BYTES = 25 * 1024 * 1024
MAX_EXPANDED = 100 * 1024 * 1024
MIMES = {
    "csv": "text/csv",
    "json": "application/json",
    "html": "text/html",
    "log": "text/plain",
    "txt": "text/plain",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "png": "image/png",
}


def safe_name(name: str) -> str:
    if (
        not isinstance(name, str)
        or not name
        or len(name) > 180
        or name in {".", ".."}
        or any(ord(c) < 32 for c in name)
        or re.search(r"[/\\:]", name)
    ):
        raise DomainError("Invalid artifact filename")
    return name


def text_cell(value: object) -> str:
    text = str(value if value is not None else "")
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text):
        return text
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text


def render(recipe: dict) -> tuple[bytes, str]:
    """Render only the supplied audience projection, never an entire private fact graph.

    Redaction removes cells from the projection before a serializer sees them. PDF
    blackout overlays are deliberately not used. XLSX arithmetic is generated from
    fixed numeric-column totals, never from supplied formula expressions.
    """
    format_name = recipe.get("format")
    if format_name not in MIMES:
        raise DomainError("Unsupported renderer")
    title = str(recipe.get("title", "Company record"))
    columns = recipe.get("columns", [])
    rows = recipe.get("rows", [])
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        raise DomainError("Columns must be named strings")
    if len(set(columns)) != len(columns) or not isinstance(rows, list) or len(rows) > 100000:
        raise DomainError("Duplicate columns or excessive record count")
    redacted = set(recipe.get("redact_columns", []))
    if not redacted <= set(columns):
        raise DomainError("Unknown redaction column")
    projected = []
    for row in rows:
        if not isinstance(row, dict):
            raise DomainError("Records must be objects")
        projected.append({c: "[REDACTED]" if c in redacted else row.get(c, "") for c in columns})
    paragraphs = [str(p) for p in recipe.get("paragraphs", [])]
    if format_name == "json":
        if "document" in recipe:
            if not isinstance(recipe["document"], (dict, list)) or redacted:
                raise DomainError(
                    "Native JSON requires an explicitly projected object/array; "
                    "redact before supplying it"
                )
            data = (canonical(recipe["document"]) + "\n").encode()
        else:
            data = (
                canonical({"title": title, "records": projected, "paragraphs": paragraphs}) + "\n"
            ).encode()
    elif format_name == "csv":
        buf = io.StringIO(newline="")
        writer = csv.writer(buf)
        writer.writerow([text_cell(c) for c in columns])
        writer.writerows([[text_cell(r[c]) for c in columns] for r in projected])
        data = buf.getvalue().encode("utf-8-sig")
    elif format_name in {"txt", "log"}:
        data = (
            title
            + "\n"
            + "\n".join(paragraphs)
            + "\n"
            + "\n".join(" | ".join(str(r[c]) for c in columns) for r in projected)
        ).encode()
    elif format_name == "html":
        heads = "".join(f"<th scope='col'>{html.escape(c)}</th>" for c in columns)
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(r[c]))}</td>" for c in columns) + "</tr>"
            for r in projected
        )
        data = (
            "<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta http-equiv='Content-Security-Policy' "
            "content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            f"<title>{html.escape(title)}</title><style>"
            "body{font:16px Georgia;margin:3rem;max-width:80rem}"
            "table{border-collapse:collapse}"
            "td,th{padding:.6rem;border:1px solid #777;text-align:left}</style>"
            f"<h1>{html.escape(title)}</h1>"
            + "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
            + f"<table><thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></html>"
        ).encode()
    elif format_name == "xlsx":
        import xlsxwriter

        buf = io.BytesIO()
        workbook = xlsxwriter.Workbook(
            buf, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False}
        )
        sheet = workbook.add_worksheet("Records")
        heading = workbook.add_format(
            {"bold": True, "bg_color": "#101214", "font_color": "#FFFFFF"}
        )
        sheet.write_row(0, 0, columns, heading)
        for i, row in enumerate(projected, 1):
            sheet.write_row(
                i,
                0,
                [
                    row[c] if isinstance(row[c], (str, int, float, bool)) else canonical(row[c])
                    for c in columns
                ],
            )
        totals = recipe.get("total_columns", [])
        for column in totals:
            if column not in columns or column in redacted:
                raise DomainError("Cannot total absent or redacted column")
            values = [r[column] for r in projected]
            if any(type(v) not in {int, float} for v in values):
                raise DomainError("Totals require numerical cells")
            index = columns.index(column)
            from xlsxwriter.utility import xl_col_to_name

            letter = xl_col_to_name(index)
            if values:
                sheet.write_formula(
                    len(projected) + 1,
                    index,
                    f"=SUM({letter}2:{letter}{len(projected) + 1})",
                    None,
                    sum(values),
                )
        if columns:
            sheet.set_column(0, len(columns) - 1, 24)
            sheet.freeze_panes(1, 0)
            sheet.autofilter(0, 0, len(projected), len(columns) - 1)
        workbook.close()
        data = buf.getvalue()
    else:
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        y = 50
        # A native paginated PDF; literal text rather than HTML/JS interpretation.
        import textwrap

        for line in [
            title,
            *paragraphs,
            " | ".join(columns),
            *(" | ".join(str(r[c]) for c in columns) for r in projected),
        ]:
            for part in textwrap.wrap(line, width=90) or [""]:
                if y > 790:
                    page, y = doc.new_page(), 50
                page.insert_text((40, y), part, fontsize=10)
                y += 15
        data = (
            doc.tobytes(garbage=4, deflate=True)
            if format_name == "pdf"
            else doc[0].get_pixmap().tobytes("png")
        )
        doc.close()
    if len(data) > MAX_BYTES:
        raise DomainError("Rendered artifact exceeds size limit")
    damage = recipe.get("damage")
    if damage == "TRUNCATE":
        data = data[: min(24, max(1, len(data) // 10))]
    elif damage == "INVALID_CONTAINER":
        data = b"Incomplete file transfer\n"
    elif damage is not None:
        raise DomainError("Unsupported inert artifact damage")
    return data, MIMES[format_name]


def inspect_upload(name: str, data: bytes) -> dict:
    """Untrusted document parsing occurs only in an isolated worker."""
    from .parser_sandbox import parse

    safe_name(name)
    if not data or len(data) > MAX_BYTES:
        raise DomainError("Empty or oversized upload")
    return parse(
        "inspect", {"name": name, "id": "upload", "sha256": hashlib.sha256(data).hexdigest()}, data
    )


class Artifacts:
    def __init__(self, private_root: Path):
        self.root = private_root.resolve() / "artifacts"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)

    def retain(
        self,
        engagement_id: str,
        name: str,
        data: bytes,
        *,
        source: dict,
        coverage: dict,
        lineage: list[str] | None = None,
        generated: bool = False,
    ) -> dict:
        return self._retain(
            engagement_id,
            name,
            data,
            source=source,
            coverage=coverage,
            lineage=lineage,
            generated=generated,
            inspection=inspect_upload(name, data),
        )

    def retain_company(
        self,
        engagement_id: str,
        name: str,
        data: bytes,
        *,
        source: dict,
        coverage: dict,
    ) -> dict:
        """Trusted company adapters only; intake classification is not source assurance.

        Generic uploads must use retain(), regardless of their supplied metadata.
        The adapter validates source access, exact versions and hashes before this call.
        """
        kinds = {
            "COLLECTED_COMPANY_SOURCE": "COLLECTED_COMPANY_SOURCE",
            "COMPANY_CENSUS_QUERY": "COMPANY_SOURCE_DERIVED",
            "COMPANY_CENSUS_DERIVATION": "COMPANY_SOURCE_DERIVED",
            "COMPANY_POPULATION_QUERY": "COMPANY_SOURCE_DERIVED",
            "COMPANY_POPULATION_DERIVATION": "COMPANY_SOURCE_DERIVED",
        }
        if source.get("kind") not in kinds:
            raise DomainError("Unsupported trusted company intake kind")
        return self._retain(
            engagement_id,
            name,
            data,
            source=source,
            coverage=coverage,
            lineage=None,
            generated=False,
            inspection=inspect_upload(name, data),
            intake_origin=kinds[source["kind"]],
        )

    def retain_export(
        self, engagement_id: str, name: str, data: bytes, *, source: dict, coverage: dict
    ) -> dict:
        """Retain a bounded app-built review ZIP; never used by upload routes."""
        safe_name(name)
        if not name.lower().endswith(".zip") or not data or len(data) > MAX_EXPANDED:
            raise DomainError("Generated review archive exceeds the 100 MiB limit")
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > 10000 or sum(entry.file_size for entry in entries) > MAX_EXPANDED:
                    raise ValueError(
                        "Generated review archive exceeds expanded size or entry limit"
                    )
                names = set()
                for entry in entries:
                    parts = entry.filename.split("/")
                    if (
                        entry.filename in names
                        or entry.filename.startswith("/")
                        or "\\" in entry.filename
                        or ".." in parts
                        or "\x00" in entry.filename
                        or entry.flag_bits & 1
                    ):
                        raise ValueError("Unsafe generated review archive member")
                    names.add(entry.filename)
                if archive.testzip() is not None:
                    raise ValueError("Generated review archive member integrity failure")
        except (ValueError, zipfile.BadZipFile, RuntimeError) as exc:
            raise DomainError(str(exc)) from None
        return self._retain(
            engagement_id,
            name,
            data,
            source=source,
            coverage=coverage,
            lineage=None,
            generated=True,
            inspection={"mime": "application/zip", "status": "AVAILABLE", "reason": None},
        )

    def _retain(
        self,
        engagement_id: str,
        name: str,
        data: bytes,
        *,
        source: dict,
        coverage: dict,
        lineage: list[str] | None,
        generated: bool,
        inspection: dict,
        intake_origin: str | None = None,
    ) -> dict:
        content_hash = hashlib.sha256(data).hexdigest()
        path = self.root / content_hash
        try:
            with path.open("xb") as handle:
                os.chmod(path, 0o600)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != content_hash:
                raise DomainError("Artifact storage integrity failure") from None
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
        directory_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return {
            "id": identifier("ART"),
            "engagement_id": engagement_id,
            "name": name,
            "sha256": content_hash,
            "bytes": len(data),
            "mime": inspection["mime"],
            "status": inspection["status"],
            "quarantine_reason": inspection["reason"],
            "origin": intake_origin or ("SYNTHETIC" if generated else "LEARNER_SUBMITTED"),
            "source": source,
            "coverage": coverage,
            "lineage": lineage or [],
        }

    def read(self, manifest: dict) -> bytes:
        content_hash = manifest.get("sha256", "")
        if not re.fullmatch("[0-9a-f]{64}", content_hash):
            raise DomainError("Invalid artifact identity")
        path = self.root / content_hash
        if path.is_symlink():
            raise DomainError("Artifact symlink rejected")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != content_hash or len(data) != manifest["bytes"]:
            raise DomainError("Artifact integrity failure")
        return data

    def read_bounded(self, manifest: dict, *, max_bytes: int) -> bytes:
        """Read a pinned original through a physical byte limit for diagnostic paths."""
        content_hash = manifest.get("sha256", "")
        if not re.fullmatch("[0-9a-f]{64}", content_hash):
            raise DomainError("Invalid artifact identity")
        if type(max_bytes) is not int or not 0 <= max_bytes <= MAX_BYTES:
            raise DomainError("Invalid bounded artifact read limit")
        directory_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fd = os.open(content_hash, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size > max_bytes
            ):
                raise DomainError("Artifact exceeds bounded read or is not a regular original")
            data = stream.read(max_bytes + 1)
            after = os.fstat(stream.fileno())
            if (
                len(data) > max_bytes
                or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or len(data) != manifest.get("bytes")
                or hashlib.sha256(data).hexdigest() != content_hash
            ):
                raise DomainError("Artifact bounded read integrity failure")
        return data

    def bundle(self, manifests: list[dict], *, index: dict | None = None) -> bytes:
        if len(manifests) > 5000 or sum(m["bytes"] for m in manifests) > MAX_EXPANDED:
            raise DomainError("Export exceeds bounded archive limit")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            for manifest in manifests:
                # IDs avoid duplicate filenames without altering retained bytes.
                archive.writestr(
                    f"files/{safe_name(manifest['id'])}/{safe_name(manifest['name'])}",
                    self.read(manifest),
                )
            archive.writestr(
                "manifest.json", canonical({"artifacts": manifests, "index": index or {}})
            )
        return buf.getvalue()
