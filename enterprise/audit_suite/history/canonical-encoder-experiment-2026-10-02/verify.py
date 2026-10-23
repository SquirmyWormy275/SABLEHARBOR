"""Check a historical encoder experiment's exact bytes without importing it."""

import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    manifest = json.loads((HERE / "SOURCE_MANIFEST.json").read_text())
    source = HERE / manifest["original_file"]
    data = source.read_bytes()
    if len(data) != manifest["bytes"] or hashlib.sha256(data).hexdigest() != manifest["sha256"]:
        raise ValueError("Historical encoder source differs")
    ast.parse(data.decode("utf-8"))
    print(json.dumps({"result": "PASS", "bytes": len(data), "syntax": "parsed"}))


if __name__ == "__main__":
    main()
