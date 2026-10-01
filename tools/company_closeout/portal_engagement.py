"""Closeout-owned worker using pinned portal APIs in an isolated subprocess."""

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path


def run(plan):
    from enterprise.audit_suite.engine import COLLECTIONS, Engine
    from enterprise.audit_suite.store import DomainError, digest

    destination = Path(plan["destination"])
    engine = Engine(destination / "engagement", company_root=destination / "company")
    preparer = engine.store.provision("Closeout synthetic preparer", ["learner"])["id"]
    reviewer = engine.store.provision("Closeout synthetic independent reviewer", ["reviewer"])["id"]
    state = {key: [] for key in COLLECTIONS}
    state.update(
        title="Selected company edition evidence rehearsal",
        phase="ACTIVE",
        discipline="IT",
        mode="CLEAN",
        simulated_at=plan["available_at"],
        scope=dict(
            boundaries=plan["components"],
            period_start="2026-08-01",
            period_end="2026-09-15",
            timezone="UTC",
        ),
        configuration={"selections": []},
    )
    state["requests"] = [dict(id="CLOSEOUT-SOURCE-REQUEST", status="ISSUED", artifact_ids=[])]
    state = engine.store.create(preparer, state, "closeout-create")
    engine.store.grant(state["id"], reviewer, "review")
    engine.company_bindings[state["id"]] = dict(company="SH", branch=plan["edition_id"])

    def command(actor, kind, payload, command_id):
        return engine.command(
            actor,
            state["id"],
            dict(
                command_id=command_id,
                expected_revision=state["revision"],
                kind=kind,
                payload=payload,
            ),
        )

    retained = []
    for index, selected in enumerate(plan["selected"]):
        system = selected["system"]
        engine.company_store.grant(preparer, state["id"], "SH", plan["edition_id"], system)
        for part_index, part in enumerate(selected["parts"]):
            state = command(
                preparer,
                "company.collect",
                dict(
                    system_id=system,
                    record_id=part["record"],
                    version=1,
                    request_id="CLOSEOUT-SOURCE-REQUEST",
                ),
                f"collect-{index}-{part_index}",
            )
            artifact = state["artifacts"][-1]
            raw = engine.artifacts.read(artifact)
            if hashlib.sha256(raw).hexdigest() != part["sha256"]:
                raise ValueError("Retained source bytes differ from edition transport")
            retained.append(
                dict(
                    artifact_id=artifact["id"],
                    artifact_name=artifact["name"],
                    sha256=artifact["sha256"],
                    source_path=selected["path"],
                    source_sha256=selected["sha256"],
                    source_record=part["record"],
                    system=system,
                )
            )
    evidence_ids = [r["artifact_id"] for r in retained]
    state = command(
        preparer,
        "workpaper.add",
        dict(
            title="Selected edition byte custody",
            text=json.dumps(
                dict(selection=plan["selected"], status="SOFTWARE_EXERCISE_NOT_AUDIT_OPINION")
            ),
            evidence_ids=evidence_ids,
            conclusion="LIMITATION",
        ),
        "prepare",
    )
    workpaper_id = state["workpapers"][0]["id"]
    state = command(
        preparer,
        "workpaper.update",
        dict(
            workpaper_id=workpaper_id,
            text=(
                "Retained selected originals match pinned edition hashes. "
                "Selection is not a complete control population. Hold/disposal and "
                "remaining indirect disclosures are not tested."
            ),
            evidence_ids=evidence_ids,
            conclusion="LIMITATION",
        ),
        "prepare-followup",
    )
    before = state["revision"]
    try:
        command(
            preparer,
            "review.comment",
            dict(workpaper_id=workpaper_id, comment="Self review"),
            "denied-self-review",
        )
    except DomainError:
        if engine.store.get(preparer, state["id"])["revision"] != before:
            raise ValueError("Rejected self review changed engagement") from None
    else:
        raise ValueError("Self review unexpectedly permitted")
    state = command(
        reviewer,
        "review.comment",
        dict(
            workpaper_id=workpaper_id,
            comment=(
                "Independent software-role review: selected retained byte hashes and "
                "source identities reconcile. Company-wide completeness, hold/disposal "
                "and professional assurance remain unassessed."
            ),
        ),
        "independent-review",
    )
    state = command(preparer, "review.export", dict(edition="EVIDENCE"), "retained-export")
    export = state["artifacts"][-1]
    raw = engine.artifacts.read(export)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        exported = json.loads(archive.read("engagement.json"))
        wp = exported["workpapers"][0]
        review = exported["reviews"][0]
        if wp["prepared_by"] != preparer or review["actor"] != reviewer or preparer == reviewer:
            raise ValueError("Preparer/reviewer identity mismatch")
        if len(wp["versions"]) != 2 or review["workpaper_version_digest"] != digest(
            wp["versions"][-1]
        ):
            raise ValueError("Independent review does not bind current workpaper version")
        if wp["versions"][-1]["evidence_ids"] != evidence_ids:
            raise ValueError("Workpaper lost retained evidence links")
        for row in retained:
            member = f"files/{row['artifact_id']}/{row['artifact_name']}"
            if hashlib.sha256(archive.read(member)).hexdigest() != row["sha256"]:
                raise ValueError("Export changed retained original")
    (destination / "SELECTED_REVIEW_EXPORT.zip").write_bytes(raw)
    return dict(
        result="PASS",
        edition_id=plan["edition_id"],
        selected=plan["selected"],
        surrounding_population=plan["surrounding_population"],
        selection_rule=plan["selection_rule"],
        source_available_at=plan["available_at"],
        retained=retained,
        workpaper_versions=2,
        self_review_denied=True,
        rejected_self_review_atomic=True,
        preparer_id=preparer,
        reviewer_id=reviewer,
        independent_review_version_bound=True,
        export_sha256=hashlib.sha256(raw).hexdigest(),
        export_artifact_id=export["id"],
        engagement_id=state["id"],
        review_status="SOFTWARE_ROLE_EXERCISE;LIMITATION;NOT_AUDIT_OPINION",
        hold_disposal_status="NOT_EXERCISED;EXISTING_STORE_LACKS_CLASS_BASED_HOLD_DISPOSAL",
    )


if __name__ == "__main__":
    plan = json.loads(Path(sys.argv[1]).read_text())
    result = run(plan)
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
