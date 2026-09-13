"""Check the reader priority overlay against current legal gap sources; never rewrite it."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTER = "docs/reader/transactions/gaps.json"
OVERLAY = "docs/reader/transactions/gap-priorities.json"


def validate(root: Path) -> list[str]:
    """Return current integrity failures without updating sources or hashes."""
    root = root.resolve()
    errors: list[str] = []
    try:
        gaps = json.loads((root / REGISTER).read_text())
        overlay = json.loads((root / OVERLAY).read_text())
    except (OSError, ValueError) as exc:
        return [f"Cannot read gap inputs: {exc}"]
    if not isinstance(gaps, list) or not isinstance(overlay, dict):
        return ["Expected a gap-register list and an overlay object"]
    if any(not isinstance(gap, dict) for gap in gaps):
        return ["Every controlling gap must be an object"]
    ids = [gap.get("id") for gap in gaps]
    if any(not isinstance(gap_id, str) for gap_id in ids):
        return ["Every controlling gap must have a string ID"]
    if len(ids) != 17 or len(set(ids)) != 17:
        errors.append(
            "Controlling register must contain 17 distinct gaps; re-audit a changed scope"
        )
    registered = {gap["id"]: gap for gap in gaps}
    if overlay.get("controlling_gap_register") != REGISTER:
        errors.append("Overlay references a different controlling register")
    if overlay.get("status") != "READER_IMPLEMENTATION_RECOMMENDATIONS_NO_CANON_CHANGE":
        errors.append("Overlay must retain its non-canon implementation status")
    rows = overlay.get("priorities")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return errors + ["priorities must be a list of objects"]
    row_ids = [row.get("gap_id") for row in rows]
    if any(not isinstance(gap_id, str) for gap_id in row_ids):
        return errors + ["Every priority must have a string gap_id"]
    if len(row_ids) != 17 or len(set(row_ids)) != len(row_ids):
        errors.append("Overlay must contain 17 unique gap IDs")
    missing, extra = set(ids) - set(row_ids), set(row_ids) - set(ids)
    if missing or extra:
        errors.append(f"Gap coverage differs: missing={sorted(missing)}, extra={sorted(extra)}")
    ranks = [row.get("rank") for row in rows]
    if any(type(rank) is not int for rank in ranks) or sorted(ranks) != list(range(1, 18)):
        errors.append("Priority ranks must be unique integers 1 through 17")
    hashes = overlay.get("source_hashes")
    if not isinstance(hashes, dict):
        return errors + ["source_hashes must be an object"]
    required_sources = {REGISTER, "docs/reader/transactions/RECONCILIATION.md"}
    allowed_priorities = {
        "USE_EXISTING_FIRST",
        "OWNER_REVIEW_IF_EXPANDING",
        "DEFER_NOT_REQUIRED",
    }
    for row in rows:
        gap_id = row["gap_id"]
        current = registered.get(gap_id)
        if row.get("priority") not in allowed_priorities:
            errors.append(f"{gap_id}: unknown priority classification")
        for field in ("current_disposition", "disposition", "status"):
            if field in row and current and row[field] != current.get("status"):
                errors.append(f"{gap_id}: {field} disagrees with the controlling disposition")
        sources = row.get("sources")
        if not isinstance(sources, list) or any(not isinstance(p, str) for p in sources):
            errors.append(f"{gap_id}: sources must be a list of repository paths")
            continue
        if not sources or len(sources) != len(set(sources)):
            errors.append(f"{gap_id}: source paths must be nonempty and distinct")
        required_sources.update(sources)
        if current:
            absent = set(current.get("sources", [])) - set(sources)
            if absent:
                errors.append(f"{gap_id}: missing controlling source references {sorted(absent)}")
    absent_hashes = required_sources - set(hashes)
    if absent_hashes:
        errors.append(f"Missing source hashes: {sorted(absent_hashes)}")
    for source, expected in hashes.items():
        path = root / source
        if Path(source).is_absolute() or not path.resolve().is_relative_to(root):
            errors.append(f"Source is outside the repository: {source}")
            continue
        if not path.is_file():
            errors.append(f"Missing source file: {source}")
            continue
        if not isinstance(expected, str) or len(expected) != 64:
            errors.append(f"Invalid SHA-256 value: {source}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"Source changed; re-audit rather than reseal automatically: {source}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository checkout to inspect")
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: all 17 legal gaps, ranks, controlling references and current source hashes agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
