"""Add period-close and evidence follow-through to the immutable review editions."""

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.legal_gaps import package_v3 as previous

VERSION = "0.4.0-review.1"
ADDITIONS = ("period-close", "evidence-tracking", "source-impact", "case-briefs")


def build(output, allow_dirty=False):
    output = output.resolve()
    archive = Path(str(output) + ".zip")
    if output.exists() or archive.exists():
        raise ValueError("Use a new output path; never replace a delivered edition")
    version, additions = previous.VERSION, previous.ADDITIONS
    with tempfile.TemporaryDirectory() as scratch:
        intermediate = Path(scratch) / "review"
        try:
            previous.VERSION = VERSION
            previous.ADDITIONS = additions + ADDITIONS
            previous.build(intermediate, allow_dirty)
        finally:
            previous.VERSION, previous.ADDITIONS = version, additions
        start = intermediate / "START_HERE.html"
        links = "".join(
            f'<li><a href="{previous.PREFIX}/{folder}/README.md.html">{label}</a></li>'
            for folder, label in (
                ("case-briefs", "Start here: five one-page case briefs"),
                ("period-close", "Complete one ARU reporting-period close"),
                ("evidence-tracking", "Track evidence requests and responses"),
                ("source-impact", "Check which work a source change affects"),
            )
        )
        content = start.read_text().replace("<ul>", "<ul>" + links, 1)
        content = content.replace(
            "New designs and proposed terms remain unaccepted.",
            "The owner approved this implementation and the v0.4 designs on 13 September 2026. "
            "Proposed legal and billing terms retain their recorded draft status.",
        )
        content = content.replace(
            "</ul>",
            '<li><a href="'
            + previous.PREFIX
            + '/case-briefs/ACCEPTANCE.md.html">Scope of owner approval'
            + " and exact-file hashes</a></li></ul>",
            1,
        )
        start.write_text(content)
        # Long commands remain fully readable in new companions on narrow screens.
        for folder in ADDITIONS:
            for companion in (intermediate / previous.PREFIX / folder).rglob("*.md.html"):
                companion.write_text(
                    companion.read_text().replace(
                        "</style>", "pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>"
                    )
                )
        manifest = json.loads((intermediate / "MANIFEST.json").read_text())
        for name in ("MANIFEST.json", "SHA256SUMS.txt"):
            (intermediate / name).unlink()
        rows = [
            {
                "path": str(p.relative_to(intermediate)),
                "sha256": previous.previous.digest(p.read_bytes()),
                "bytes": p.stat().st_size,
            }
            for p in sorted(intermediate.rglob("*"))
            if p.is_file()
        ]
        manifest["files"] = rows
        manifest["predecessor"] = "0.3.0-review.1; original release bytes retained"
        (intermediate / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (intermediate / "SHA256SUMS.txt").write_text(
            "".join(r["sha256"] + "  " + r["path"] + "\n" for r in rows)
            + previous.previous.digest((intermediate / "MANIFEST.json").read_bytes())
            + "  MANIFEST.json\n"
        )
        previous.previous.verify(intermediate)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(intermediate, output)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for p in sorted(output.rglob("*")):
            if p.is_file():
                info = zipfile.ZipInfo(str(p.relative_to(output)), date_time=(2026, 9, 13, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                zipped.writestr(info, p.read_bytes())
    print(f"{archive}: {previous.previous.digest(archive.read_bytes())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    build(args.output, args.allow_dirty)
