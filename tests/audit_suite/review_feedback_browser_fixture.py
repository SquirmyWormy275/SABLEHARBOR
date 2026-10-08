"""Persist ordinary neutral review histories for the real modal browser check."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from enterprise.audit_suite.engine import COLLECTIONS, Engine
from enterprise.audit_suite.store import DomainError, digest


def main(output: Path) -> None:
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    engine = Engine(output / "audit-state")
    preparer = engine.store.provision("Neutral preparer", ["instructor"])["id"]
    reviewer = engine.store.provision("Neutral independent reviewer", ["reviewer"])["id"]
    records = []
    for kind in ("SCRIPTED_ENGINEERING", "SYNTHETIC_TECHNICAL"):
        data = {key: [] for key in COLLECTIONS}
        data.update(scope={}, phase="ACTIVE", simulated_at="2028-01-02T09:00:00+00:00")
        initial = engine.store.create(preparer, data, f"neutral-create-{kind}")
        eid = initial["id"]
        engine.store.grant(eid, reviewer, "review")
        sequence = 0

        def command(actor: str, command_kind: str, payload: dict, *, eid=eid, kind=kind) -> dict:
            nonlocal sequence
            sequence += 1
            current = engine.store.get(actor, eid)
            engine.command(
                actor,
                eid,
                {
                    "command_id": f"mobile-review-{kind}-{sequence}",
                    "expected_revision": current["revision"],
                    "kind": command_kind,
                    "payload": payload,
                },
            )
            return engine.store.get(actor, eid)

        state = command(
            preparer,
            "workpaper.add",
            {"title": "Neutral saved paper", "text": "Original selected documentary examination."},
        )
        paper = state["workpapers"][0]
        state = command(
            reviewer,
            "review.comment",
            {
                "workpaper_id": paper["id"],
                "review_kind": kind,
                "comment": "Explain the limited selected source basis; no professional acceptance.",
            },
        )
        original = state["reviews"][0]
        assert original["professional_acceptance"] == "NOT_ASSERTED"
        assert original["workpaper_version_digest"] == digest(paper["versions"][0])
        stages = []

        def save_stage(*, stages=stages, eid=eid) -> None:
            stages.append(
                {
                    "preparer": engine.get(preparer, eid),
                    "reviewer": engine.get(reviewer, eid),
                }
            )

        save_stage()
        command(
            preparer,
            "workpaper.update",
            {
                "workpaper_id": paper["id"],
                "text": "Current version adds context; selected examination remains limited.",
            },
        )
        state = command(
            preparer,
            "review.resolve",
            {
                "review_id": original["id"],
                "disposition": "agree",
                "response": "Added limited documentary context; the review remains open.",
            },
        )
        assert state["reviews"][0]["status"] == "OPEN"
        response = state["reviews"][0]["history"][0]
        assert response["response_workpaper_version"] == 2
        assert response["response_workpaper_version_digest"] == digest(
            state["workpapers"][0]["versions"][-1]
        )
        save_stage()
        before = digest(engine.store.get(preparer, eid))
        try:
            command(
                preparer,
                "review.resolve",
                {
                    "review_id": original["id"],
                    "response": "Own contributor cannot independently resolve.",
                },
            )
        except DomainError as exc:
            assert "contributor" in str(exc)
        else:
            raise AssertionError("Contributor resolution must refuse")
        assert digest(engine.store.get(preparer, eid)) == before
        state = command(
            reviewer,
            "review.resolve",
            {
                "review_id": original["id"],
                "response": "Recorded independent technical resolution of this limited paper.",
            },
        )
        assert state["reviews"][0]["status"] == "RESOLVED"
        assert state["reviews"][0]["kind"] == kind
        save_stage()
        records.append(
            {"kind": kind, "preparer_id": preparer, "reviewer_id": reviewer, "stages": stages}
        )
    path = output / "PERSISTED_INPUT.json"
    path.write_text(json.dumps(records, ensure_ascii=False) + "\n")
    path.chmod(0o600)
    db = output / "audit-state" / "engagements.sqlite3"
    proof = {
        "schema": "SH_NEUTRAL_PERSISTED_REVIEW_BROWSER_INPUT_V1",
        "source": (
            "Fresh ordinary commands, saved rows and actual Engine permission projection; "
            "no actual company, audit or Key inputs"
        ),
        "origins": [r["kind"] for r in records],
        "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "journal_sha256": hashlib.sha256(db.read_bytes()).hexdigest(),
        "contributor_resolution_refused": True,
        "credentials_exported": False,
    }
    (output / "INPUT_PROOF.json").write_text(json.dumps(proof, indent=2) + "\n")
    (output / "INPUT_PROOF.json").chmod(0o600)
    for parent, dirs, files in os.walk(output):
        Path(parent).chmod(0o700)
        for name in dirs:
            (Path(parent) / name).chmod(0o700)
        for name in files:
            (Path(parent) / name).chmod(0o600)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
