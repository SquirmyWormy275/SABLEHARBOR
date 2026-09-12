"""Fail closed when owner-selected V08 artifact bytes change."""

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
record = json.loads((BASE / "ACCEPTANCE.json").read_text())
assert record["selected_revision"] == "V08"
assert set(record["artifacts"]) == {"png", "pdf"}
for artifact in record["artifacts"].values():
    path = ROOT / artifact["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"], (
        f"Locked artwork changed: {path}"
    )
assert (ROOT / record["controlling_record"]).is_file()
print("PASS: owner-selected V08 PNG/PDF exactly match the locked hashes")
