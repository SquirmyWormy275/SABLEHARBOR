"""Bind inspected embedded-image roles to a fresh baseline container inventory."""

import hashlib
import json

from geospatial.finalization.screen import BASE


def verify(inventory):
    reviewed = json.loads((BASE / "VISUAL_REVIEW.json").read_text())
    expected = {r["record_id"]: r for r in inventory["records"] if r["kind"] == "EMBEDDED_IMAGE"}
    seen = {}
    for image in reviewed["records"]:
        for occurrence in image["appearances"]:
            key = occurrence["record_id"]
            if key in seen or occurrence["sha256"] != image["sha256"]:
                raise ValueError("Duplicate or mismatched image appearance")
            if key not in expected or any(
                occurrence[k] != expected[key][k]
                for k in ("source_path", "locator", "sha256", "bytes")
            ):
                raise ValueError("Reviewed image differs from extracted source")
            seen[key] = dict(
                **occurrence,
                review_disposition=image["disposition"],
                meaning=image["meaning"],
                object_ids=image["object_ids"],
            )
    if set(seen) != set(expected):
        raise ValueError("Embedded image has no visual disposition")
    if len({r["sha256"] for r in reviewed["records"]}) != reviewed["unique_images"]:
        raise ValueError("Duplicate unique-image record")
    if len(seen) != reviewed["appearances"]:
        raise ValueError("Visual appearance count differs")
    return (
        dict(
            unique_images=len(reviewed["records"]),
            appearances=len(seen),
            all_embedded_appearances_reviewed=True,
            review_sha256=hashlib.sha256((BASE / "VISUAL_REVIEW.json").read_bytes()).hexdigest(),
            scope=reviewed["scope"],
        ),
        reviewed["records"],
        list(seen.values()),
    )
