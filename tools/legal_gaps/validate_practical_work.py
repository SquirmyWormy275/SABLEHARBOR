"""Validate exact reviewed practical-work inputs and retained visual evidence."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/legal/gap-instruments"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate():
    receipt = json.loads((BASE / "review-support/qa/v3/REVIEW.json").read_text())
    assert receipt["status"] == "MANUAL_REVIEW_COMPLETE_DRAFT_DESIGNS"
    assert receipt["owner_acceptance"] == "PENDING"
    successor_path = BASE / "review-support/qa/v3/NAVIGATION_SUCCESSOR_2026-09-15.json"
    successor = json.loads(successor_path.read_text())
    assert sha(BASE / "review-support/qa/v3/REVIEW.json") == successor["historical_receipt_sha256"]
    updates = {r["path"]: r for r in successor["records"]}
    assert set(updates) == {"docs/reader/transactions/README.md", "docs/reader/transactions/build.py",
                            "tools/legal_gaps/validate_practical_work.py"}
    for group in ("input_hashes", "evidence_hashes"):
        assert receipt[group], "Empty review coverage"
        for relative, digest in receipt[group].items():
            path = (ROOT / relative).resolve()
            assert path.is_relative_to(ROOT)
            if relative in updates:
                update = updates[relative]
                original = subprocess.check_output(
                    ["git", "show", f"{update['historical_revision']}:{relative}"], cwd=ROOT
                )
                assert hashlib.sha256(original).hexdigest() == digest == update["historical_sha256"]
                assert sha(path) == update["current_sha256"], ("Stale navigation successor", relative)
            else:
                assert sha(path) == digest, ("Stale review", relative)
    walk = json.loads((BASE / "walkthroughs/qa/REVIEW.json").read_text())
    assert walk["status"] == "MANUAL_REVIEW_PASS_DRAFT_DESIGN"
    assert sha(BASE / "walkthroughs/walkthroughs.xlsx") == walk["workbook_sha256"]
    for item in walk["evidence"]:
        assert sha(BASE / "walkthroughs" / item["path"]) == item["sha256"]
    recon = json.loads((BASE / "reconciliations/qa/REVIEW.json").read_text())
    assert recon["status"] == "MANUAL_REVIEW_PASS_DRAFT_DESIGN"
    for item in recon["records"]:
        assert sha(BASE / "reconciliations" / (item["mode"] + ".xlsx")) == item["workbook_sha256"]
        for page in item["pages"]:
            assert sha(ROOT / page["path"]) == page["sha256"]
    assert receipt["new_workbooks"] == 3 and receipt["new_worksheets"] == 23
    print(
        f"PASS: {len(receipt['input_hashes'])} practical-work inputs; "
        "all 23 new worksheets and retained visual evidence"
    )


if __name__ == "__main__":
    validate()
