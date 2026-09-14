"""Linux bubblewrap parser boundary: no private filesystem or network access."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_INPUT = 25 * 1024 * 1024


def parse(mode, manifest, data):
    fallback = (
        {
            "status": "QUARANTINED",
            "reason": "Isolated parser unavailable or failed; human review required",
            "mime": "application/octet-stream",
        }
        if mode == "inspect"
        else {
            "artifact_id": manifest["id"],
            "status": "HUMAN_REVIEW_REQUIRED",
            "sources": [],
            "limitation": "Isolated parser unavailable or failed; no in-process fallback",
        }
    )
    if mode not in {"extract", "inspect"} or len(data) > MAX_INPUT or sys.platform != "linux":
        return fallback
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return fallback
    python = Path(sys.executable).resolve()
    python_root = python.parent.parent
    packages = (
        Path(sys.prefix)
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    worker = Path(__file__).with_name("parser_worker.py").resolve()
    # The temporary host folder is never mounted; only the single input file is.
    scratch = Path(os.environ.get("TMPDIR", Path.home() / ".cache"))
    try:
        with tempfile.TemporaryDirectory(prefix="audit-parser-", dir=scratch) as temporary:
            source = Path(temporary) / "input"
            source.write_bytes(data)
            source.chmod(0o600)
            command = [
                bwrap,
                "--unshare-all",
                "--die-with-parent",
                "--new-session",
                "--clearenv",
                "--ro-bind",
                "/usr",
                "/usr",
                "--symlink",
                "usr/lib",
                "/lib",
                "--symlink",
                "usr/lib",
                "/lib64",
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--size",
                str(64 * 1024 * 1024),
                "--tmpfs",
                "/tmp",
                "--ro-bind",
                str(python_root),
                "/python",
                "--ro-bind",
                str(packages),
                "/packages",
                "--ro-bind",
                str(worker),
                "/worker.py",
                "--ro-bind",
                str(source),
                "/input",
                "--chdir",
                "/tmp",
                "--setenv",
                "LANG",
                "C.UTF-8",
                "/python/bin/" + python.name,
                "-I",
                "-S",
                "/worker.py",
                mode,
                manifest["name"],
                manifest.get("id", "upload"),
                manifest.get("sha256", ""),
            ]
            output_path = Path(temporary) / "output"
            with output_path.open("w+b") as output:
                output_path.chmod(0o600)
                completed = subprocess.run(
                    command,
                    stdout=output,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                    check=False,
                    env={},
                )
                if completed.returncode or os.fstat(output.fileno()).st_size > 8 * 1024 * 1024:
                    return fallback
                output.seek(0)
                result = json.loads(output.read(8 * 1024 * 1024 + 1))
            if not isinstance(result, dict) or "sandbox_error" in result:
                return fallback
            result["parser_isolation"] = {
                "mechanism": "BUBBLEWRAP_USER_MOUNT_PID_NETWORK_NAMESPACE",
                "network": "ISOLATED",
                "private_filesystem": "NOT_MOUNTED",
                "cpu_seconds": 10,
                "wall_seconds": 15,
                "address_space_mib": 768,
            }
            return result
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return fallback
