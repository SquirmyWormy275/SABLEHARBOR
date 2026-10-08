"""Check the reviewed sources retained by the audit history admission contract."""

import hashlib
import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (root / "docs/audit-suite/REVIEWED_RUNTIME_SOURCE_PINS.json").read_bytes()
    )
    for name, expected in manifest["files"].items():
        path = root / name
        if not name.startswith("enterprise/audit_suite/") or not path.resolve().is_relative_to(
            root
        ):
            raise SystemExit(f"Invalid reviewed source path: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"Reviewed runtime source changed: {name}")
        compile(path.read_bytes(), str(path), "exec")
    print(f"PASS reviewed audit runtime sources: {len(manifest['files'])} exact SHA-256 pins")


if __name__ == "__main__":
    main()
