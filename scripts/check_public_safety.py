#!/usr/bin/env python3
import subprocess
from pathlib import Path

FORBIDDEN = ("ghp_", "github_pat_", "sk-proj-", "BEGIN PRIVATE KEY")
MAX_BYTES = 10 * 1024 * 1024


def tracked_files() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z"], check=True, capture_output=True
    ).stdout.decode()
    return [Path(name) for name in output.split("\0") if name]


def main() -> None:
    failures: list[str] = []
    for path in tracked_files():
        if "var/private" in path.as_posix():
            failures.append(f"private benchmark path tracked: {path}")
        if path.stat().st_size > MAX_BYTES:
            failures.append(f"large file exceeds 10 MiB: {path}")
        if path.suffix.lower() in {".png", ".pdf", ".pptx", ".zip", ".xlsx"}:
            continue
        text = path.read_text(errors="ignore")
        for marker in FORBIDDEN:
            if marker in text:
                failures.append(f"possible credential marker {marker!r}: {path}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("PASS: no tracked private benchmark paths, credential markers, or >10 MiB files")


if __name__ == "__main__":
    main()
