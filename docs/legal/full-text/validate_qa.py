"""Bind completed visual inspections to exact legal editions and saved review images."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REPORTS = [
    "qa/render/REVIEW.json",
    "qa/commercial-tax/PAGE_REVIEW.json",
    "qa/corporate-workforce/report.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_qa():
    manifest = json.loads((HERE / "render-manifest.json").read_text())
    artifacts = {r["id"]: r for r in manifest["artifacts"]}
    seen = set()
    records = []
    reports = []
    for relative in REPORTS:
        path = HERE / relative
        report = json.loads(path.read_text())
        assert not any(s in report["status"] for s in ("PENDING", "IN_PROGRESS")), relative
        reports.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path)})
        for record in report.get("records", report.get("documents", [])):
            identity = record["id"]
            assert identity in artifacts and identity not in seen, identity
            seen.add(identity)
            artifact = artifacts[identity]
            for kind in ("pdf", "html"):
                assert record[kind + "_sha256"] == artifact[kind + "_sha256"], identity
                assert sha(ROOT / artifact[kind]) == artifact[kind + "_sha256"], identity
            pages = record.get("pages", record.get("pdf_pages", []))
            views = record.get("views", record.get("html_views", record.get("html", [])))
            assert sorted(p["page"] for p in pages) == list(range(1, artifact["pages"] + 1)), (
                identity
            )
            assert sorted(p["width"] for p in views) == [390, 1280], identity
            checked = []
            for item in pages + views:
                result = item.get("result", item.get("manual_status", ""))
                assert result.startswith("PASS"), (identity, result)
                relative_image = item.get("image", item.get("render"))
                image = (ROOT / relative_image).resolve()
                assert image.is_relative_to(ROOT) and image.is_file(), relative_image
                image_hash = sha(image)
                expected_hash = item.get("sha256", item.get("render_sha256"))
                assert not expected_hash or expected_hash == image_hash, relative_image
                checked.append(
                    {
                        "image": relative_image,
                        "sha256": image_hash,
                        "page": item.get("page"),
                        "width": item.get("width"),
                    }
                )
            records.append(
                {
                    "id": identity,
                    "pdf_sha256": artifact["pdf_sha256"],
                    "html_sha256": artifact["html_sha256"],
                    "surfaces": checked,
                }
            )
    assert seen == artifacts.keys(), "Missing visual review records"
    return {
        "status": "IMPLEMENTATION_QA_PASS_OWNER_REVIEW_PENDING",
        "render_manifest_sha256": sha(HERE / "render-manifest.json"),
        "counts": {
            "documents": len(seen),
            "pdf_pages": sum(r["pages"] for r in artifacts.values()),
            "html_viewports": len(seen) * 2,
        },
        "reports": reports,
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="Bind completed reports; does not perform review"
    )
    args = parser.parse_args()
    expected = compile_qa()
    target = HERE / "QA_MANIFEST.json"
    if args.write:
        target.write_text(json.dumps(expected, indent=2) + "\n")
    else:
        assert json.loads(target.read_text()) == expected, "Visual inspection manifest is stale"
    print("PASS: " + json.dumps(expected["counts"]))


if __name__ == "__main__":
    main()
