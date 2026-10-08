"""Explicit local build of the separately code-pinned canonical byte splitter."""

import os
import sys

if __package__ in (None, ""):
    sys.path[0] = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

import hashlib  # noqa: E402
import json  # noqa: E402
import shlex
import subprocess
import sysconfig
import tempfile
from pathlib import Path


def main():
    package = Path(__file__).resolve().parents[2] / "enterprise/audit_suite"
    source = package / "_canonical_fragmenter_native.c"
    target = package / ("_canonical_fragmenter_native" + sysconfig.get_config_var("EXT_SUFFIX"))
    command = shlex.split(os.environ.get("CC", sysconfig.get_config_var("CC")))
    with tempfile.TemporaryDirectory(
        prefix="canonical-fragmenter-build-", dir=package
    ) as temporary:
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
                "boundary": (
                    "Explicit local build only; expand and review complete executable origin pins"
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
