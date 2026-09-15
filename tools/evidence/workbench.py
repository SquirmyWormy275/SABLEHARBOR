"""Create a self-contained, offline evidence review interface."""

import hashlib
import json
from pathlib import Path


def render(
    output, revision, dirty, cases, residual, issues, inventory, version, ocr=None
):
    data = {
        "version": version,
        "revision": revision,
        "dirty": dirty,
        "cases": cases,
        "backlog": residual,
        "issues": issues,
        "inventory": inventory,
        "ocr": ocr,
    }
    # Drafts are bound to this exact source and occurrence population.
    data["identity"] = hashlib.sha256(
        json.dumps({"revision": revision, "rows": residual}, sort_keys=True).encode()
    ).hexdigest()
    encoded = (
        json.dumps(data, ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    template = Path(__file__).with_suffix(".html").read_text()
    (output / "review.html").write_text(template.replace("__PAYLOAD__", encoded))
