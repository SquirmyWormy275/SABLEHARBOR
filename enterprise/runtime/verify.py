"""Compare actual consumed runtime output to the reviewed deterministic output hash."""

import argparse
import hashlib
import json
from .model import ROOT, export, load


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runtime-output")
    p.add_argument("--record", action="store_true")
    a = p.parse_args()
    path = ROOT / "enterprise/runtime/acceptance_output.json"
    actual = export(load())
    if a.record:
        path.write_text(
            json.dumps(
                {
                    "runtime_sha256": digest(actual),
                    "scope": "Deterministic runtime output only; not full release acceptance",
                },
                indent=2,
            )
            + "\n"
        )
    else:
        supplied = (
            json.loads(__import__("pathlib").Path(a.runtime_output).read_text())
            if a.runtime_output
            else actual
        )
        expected = json.loads(path.read_text())
        if (
            digest(supplied) != digest(actual)
            or digest(actual) != expected["runtime_sha256"]
        ):
            raise ValueError("Runtime output/source drift; review and regenerate")
        print("PASS runtime output reproduces reviewed source-derived hash")


if __name__ == "__main__":
    main()
