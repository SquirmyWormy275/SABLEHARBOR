"""Publish a clean accepted-main checkout using existing local Git authentication."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from tools.wiki.audit import audit_export
from tools.wiki.export import MANIFEST, REPOSITORY, Exporter, sync

ROOT = Path(__file__).resolve().parents[2]


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def check_source(head, accepted, status):
    if status or head != accepted:
        raise ValueError(
            "Publish requires a clean checkout of the current accepted main commit"
        )


def publish():
    repository = f"https://github.com/{REPOSITORY}.git"
    git("fetch", repository, "main")
    revision = git("rev-parse", "HEAD")
    check_source(revision, git("rev-parse", "FETCH_HEAD"), git("status", "--porcelain"))
    with tempfile.TemporaryDirectory(prefix="sable-wiki-") as temp:
        directory = Path(temp)
        exported, wiki, verified = (
            directory / name for name in ("export", "wiki", "verified")
        )
        expected = Exporter(ROOT, revision).build(exported)
        report = audit_export(exported)
        if report["errors"]:
            raise ValueError(f"Wiki export failed navigation audit: {report}")
        url = f"https://github.com/{REPOSITORY}.wiki.git"
        git("clone", url, str(wiki))
        sync(exported, wiki)
        git("add", "--all", cwd=wiki)
        changed = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=wiki
        ).returncode
        if changed not in (0, 1):
            raise RuntimeError("Cannot inspect staged Wiki update")
        if changed:
            git(
                "commit",
                "-m",
                f"Publish accepted Sable Harbor snapshot {revision}",
                cwd=wiki,
            )
            git("push", "origin", "HEAD", cwd=wiki)
        git("clone", url, str(verified))
        actual = json.loads((verified / MANIFEST).read_text())
        if actual != expected:
            raise ValueError("Remote Wiki manifest differs")
        for name, digest in expected["files"].items():
            if hashlib.sha256((verified / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Remote Wiki page differs: {name}")
        report = {
            "source_revision": revision,
            "wiki_commit": git("rev-parse", "HEAD", cwd=verified),
            "verified_pages": len(expected["files"]),
            "canonical_pages": len(expected["files"]) - len(expected.get("aliases", {})),
            "historical_addresses": len(expected.get("aliases", {})),
            "url": f"https://github.com/{REPOSITORY}/wiki",
        }
        output = ROOT / "var/wiki-publication.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    publish()
