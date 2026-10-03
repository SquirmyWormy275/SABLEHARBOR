"""Explicit local build of the optional, code-pinned CPython JSON validator."""

import hashlib
import json
import os
import shlex
import subprocess
import sysconfig
import tempfile
from pathlib import Path


def main():
    package = Path(__file__).resolve().parents[2] / "enterprise/audit_suite"
    source = package / "_serialized_json_native.c"
    target = package / ("_serialized_json_native" + sysconfig.get_config_var("EXT_SUFFIX"))
    command = shlex.split(os.environ.get("CC", sysconfig.get_config_var("CC")))
    with tempfile.TemporaryDirectory(prefix="serialized-json-build-", dir=package) as temporary:
        output = Path(temporary) / target.name
        subprocess.run(
            [
                *command,
                "-shared",
                "-fPIC",
                "-O3",
                "-std=c99",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-I" + sysconfig.get_path("include"),
                str(source),
                "-o",
                str(output),
            ],
            check=True,
        )
        os.chmod(output, 0o600)
        os.replace(output, target)
    print(
        json.dumps(
            {
                "source": str(source),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "binary": str(target),
                "binary_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "abi": sysconfig.get_config_var("SOABI"),
                "boundary": "Explicit local build only; regenerate pinned configuration before use",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
