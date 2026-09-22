"""Verify the successor close-review package and exact retained visual review."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/legal/gap-instruments"


def validate():
    receipt = json.loads((BASE / "review-support/qa/v4.3/REVIEW.json").read_text())
    assert receipt["status"] == "MANUAL_REVIEW_COMPLETE_DRAFT_DESIGNS"
    assert receipt["owner_acceptance"] == "APPROVED_IMPLEMENTATION_AND_V4_DESIGNS"
    for group in ("input_hashes", "evidence_hashes"):
        assert receipt[group], "Empty review coverage"
        for relative, digest in receipt[group].items():
            path = (ROOT / relative).resolve()
            assert path.is_relative_to(ROOT)
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (
                "Stale v4.3 review",
                relative,
            )
    for folder in ("period-close", "evidence-tracking"):
        reviewed = json.loads((BASE / folder / "qa/REVIEW.json").read_text())
        assert "PASS" in reviewed["status"], (folder, reviewed["status"])
    acceptance = json.loads((BASE / "case-briefs/ACCEPTANCE.json").read_text())
    assert acceptance["owner_statement"] == "I approve the changes"
    assert acceptance["status"] == "OWNER_APPROVED_IMPLEMENTATION_AND_V4_DESIGNS"
    assert len(acceptance["artifacts"]) == 13
    for relative, digest in acceptance["artifacts"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
    for proposal in (BASE / "case-briefs/qa/cold-start").rglob("PROPOSAL.md"):
        links = re.findall(r"\]\(<([^>]+)>\)", proposal.read_text())
        assert len(links) == 5, proposal
        for link in links:
            assert not Path(link).is_absolute(), ("Nonportable QA link", link)
            assert (proposal.parent / link).resolve().is_file(), link
    cold = (BASE / "case-briefs/qa/COLD_START.md").read_text()
    assert "FINAL RESULT: PASS" in cold, "Cold-start issues must be resolved and retested"
    print(f"PASS: {len(receipt['input_hashes'])} inputs; visual and cold-start evidence")


if __name__ == "__main__":
    validate()
