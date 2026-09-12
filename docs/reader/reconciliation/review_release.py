"""Record a bounded manifest search of the independently pinned operating release."""

import hashlib
import json
import sys
import zipfile
from pathlib import Path

OUT = Path(__file__).resolve().parent
EXPECTED = "b8e81572d829fec7209d1d18eb15bac21e52b37714211aee005b5f1a68ab5817"


def main(archive, check=False):
    archive = Path(archive)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == EXPECTED
    baseline = json.loads((OUT / "records.json").read_text())
    with zipfile.ZipFile(archive) as release:
        manifests = {
            name: release.read(name)
            for name in sorted(release.namelist())
            if name.endswith(".json") and "manifest" in name.lower()
        }
        root = json.loads(manifests["manifest.json"])
        inputs = root["identity"]["source_files"]
        matches = []
        for row in baseline["records"]:
            refs = [
                name for name, content in manifests.items()
                if row["source"].encode() in content
                or row["source_sha256"].encode() in content
            ]
            if refs:
                matches.append({
                    "source": row["source"],
                    "source_sha256": row["source_sha256"],
                    "candidate_manifest_members": refs,
                    "release_input_sha256": inputs.get(row["source"]),
                    "disposition": "CANDIDATE_REFERENCE_ONLY_NO_DOCUMENT_PAIRING",
                })
        data = {
            "record_id": "SH-READER-RELEASE-FOLLOW-UP-2026-09-12",
            "baseline_revision": baseline["base_revision"],
            "archive": "sable-harbor-business-operations-v1.0.0.zip",
            "archive_sha256": EXPECTED,
            "archive_member_count": len(release.namelist()),
            "release_source_revision": root["identity"]["source_revision"],
            "manifest_search_inventory": [
                {"member": name, "sha256": hashlib.sha256(content).hexdigest()}
                for name, content in manifests.items()
            ],
            "candidate_records": matches,
            "review_result": "Source-input and artifact inventories do not explicitly map these Markdown records to equivalent PDF/XLSX publications. No baseline disposition changed.",
        }
    target = OUT / "release-member-review.json"
    content = json.dumps(data, indent=2) + "\n"
    if check:
        assert target.read_text() == content
    else:
        target.write_text(content)
    print(f"PASS: archive hash; {len(manifests)} manifests; {len(matches)} candidate records; no asserted counterpart.")


if __name__ == "__main__":
    main(sys.argv[1], "--check" in sys.argv[2:])
