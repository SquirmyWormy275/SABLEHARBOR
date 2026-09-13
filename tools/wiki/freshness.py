"""Compare the published Wiki with the reading inputs in the inspected checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from tools.wiki.export import Exporter, MANIFEST, REPOSITORY

ROOT = Path(__file__).resolve().parents[2]


def compare(expected, published, wiki):
    """Ignore unrelated commit movement while detecting input drift and live edits."""
    altered = [name for name, digest in published.get("files", {}).items()
               if Path(name).name != name or not (wiki / name).is_file()
               or (wiki / name).is_symlink()
               or hashlib.sha256((wiki / name).read_bytes()).hexdigest() != digest]
    changed = {}
    for field in ("inputs", "directory_trees", "files"):
        before, after = published.get(field, {}), expected.get(field, {})
        changed[field] = sorted(key for key in before.keys() | after.keys()
                                if before.get(key) != after.get(key))
    state = ("modified" if altered else "unverifiable" if not published.get("inputs")
             else "stale" if any(changed.values()) else "current")
    return {"state": state, "published_revision": published.get("source_revision"),
            "changed": changed, "altered_or_missing_pages": sorted(altered),
            "published_pages": len(published.get("files", {})),
            "action": "No publication needed." if state == "current" else
            "Review the differences, then publish a clean accepted-main checkout with make wiki-publish."}


def inspect(root, wiki):
    manifest_path = wiki / MANIFEST
    if manifest_path.is_symlink():
        raise ValueError("Refusing a publication-manifest symlink")
    published = json.loads(manifest_path.read_text())
    with tempfile.TemporaryDirectory(prefix="wiki-freshness-export-") as temp:
        # Reuse the publication revision in links: a code-only main commit does not
        # make an otherwise identical reading edition stale.
        expected = Exporter(root, published["source_revision"]).build(Path(temp))
        report = compare(expected, published, wiki)
    report["inspected_revision"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, help="Inspect an existing Wiki clone instead of cloning the remote")
    parser.add_argument("--output", type=Path, default=ROOT / "var/wiki-freshness.json")
    parser.add_argument("--report-only", action="store_true", help="Report drift without a failing exit status")
    args = parser.parse_args()
    try:
        if args.wiki:
            report = inspect(ROOT, args.wiki)
        else:
            with tempfile.TemporaryDirectory(prefix="wiki-freshness-") as temp:
                wiki = Path(temp) / "wiki"
                subprocess.run(["git", "clone", "--depth", "1",
                                f"https://github.com/{REPOSITORY}.wiki.git", str(wiki)], check=True)
                report = inspect(ROOT, wiki)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        report = {"state": "unavailable", "error": str(error),
                  "action": "Resolve the inspection error; publication freshness is not verified."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["state"] == "current" or args.report_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
