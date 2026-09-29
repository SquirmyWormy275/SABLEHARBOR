"""Explicitly authorized, engagement-only offline reviewer archive."""

from __future__ import annotations

import hashlib
import html
import io
import json
import zipfile

from .artifacts import MAX_EXPANDED
from .generation import epoch_directory, read_plan, read_world, run_directory
from .store import DomainError, canonical


def build(engine, state: dict, actor: str) -> dict:
    """Retain a private review ZIP; the caller appends its manifest transactionally."""
    if engine.store.membership(actor, state["id"]) not in {"review", "instruct"}:
        raise DomainError("Reviewer membership required", status=403)
    included, withheld = [], []
    for manifest in state["artifacts"]:
        if manifest.get("engagement_id") != state["id"]:
            raise DomainError("Cross-engagement artifact rejected")
        reason = None
        if manifest.get("status") != "AVAILABLE":
            reason = "Quarantined or unavailable; original remains in protected storage"
        elif manifest.get("source", {}).get("kind") in {
            "HUMAN_REVIEW_EXPORT",
            "PRIVATE_REVIEW_EXPORT",
        }:
            reason = "Prior export indexed without recursively embedding its archive"
        if reason:
            withheld.append({"manifest": manifest, "reason": reason})
        else:
            included.append(manifest)

    root = run_directory(engine, state["id"])
    private_files = {}
    # Explicit allowlist excludes custom drafting history, credentials and other runs.
    paths = []
    world_pins = {}
    for epoch in range(state.get("generation_epoch", 0) + 1):
        directory = epoch_directory(engine, state["id"], epoch)
        paths.extend([directory / "world.json", *sorted(directory.glob("unit-*.json"))])
        prior = next(
            (item for item in state.get("scope_history", []) if item["generation_epoch"] == epoch),
            {},
        )
        world_pins[directory / "world.json"] = (
            state.get("generation", {}).get("world_digest")
            if epoch == state.get("generation_epoch", 0)
            else prior.get("world_digest")
        )
    source_index = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise DomainError("Private review source path rejected")
        data = path.read_bytes()
        json.loads(data)  # Fail closed on an incomplete private checkpoint.
        if path.name.startswith("unit-"):
            read_plan(path)
        elif path.name == "world.json":
            read_world(path, world_pins.get(path))
        name = "private/" + path.relative_to(root).as_posix()
        private_files[name] = data
        source_index.append(
            {
                "path": name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    # Only committed review references may select private appendices; never glob
    # arbitrary drafting/runtime files into an instructor export.
    review_pins = set()
    for review in state.get("reviews", []):
        pin = review.get("private_review_appendix")
        if isinstance(pin, dict) and pin.get("digest"):
            review_pins.add(pin["digest"])
        metadata = review.get("five_layer_review") or review.get("input_layers", {}).get(
            "five_layer_review", {}
        )
        pin = metadata.get("input_appendix", {})
        if pin.get("digest"):
            review_pins.add(pin["digest"])
    import re

    from .store import digest

    for key in sorted(review_pins):
        if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{64}", key):
            raise DomainError("Invalid private review appendix identity")
        path = root / "review-inputs" / (key + ".json")
        if path.resolve() != path.absolute() or not path.is_file() or path.stat().st_mode & 0o077:
            raise DomainError("Private review appendix path rejected")
        data = path.read_bytes()
        if digest(json.loads(data)) != key:
            raise DomainError("Private review appendix digest differs")
        name = "private/review-inputs/" + path.name
        private_files[name] = data
        source_index.append(
            {
                "path": name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "purpose": (
                    "Actual five-layer model review and exact scoped inputs; instructor "
                    "channel only"
                ),
            }
        )
    limits = {
        "audience": "REVIEWER",
        "engagement_id": state["id"],
        "revision": state["revision"],
        "cutoff": "Snapshot precedes this export command's committed event",
        "professional_status": "UNVALIDATED_TRAINING_MATERIAL",
        "overall_grade": "NOT_PROVIDED",
        "interpretation": (
            "Private case definitions describe intended synthetic conditions, not an "
            "objective grade. Compare delivered native files and retained learner work. "
            "Experimental AI observations require independent human review."
        ),
        "private_sources": source_index,
        "omitted_artifacts": withheld,
        "licensed_originals": "Not copied; source hashes and provenance only",
    }
    additions = {
        **private_files,
        "engagement.json": canonical(state).encode(),
        "reviewer-appendix.json": canonical(limits).encode(),
    }
    from .history_export import history_json

    # Reserve index/manifest framing before reading any history. The original
    # archive contract stays complete-or-rejected, with no omitted old states.
    budget = (
        MAX_EXPANDED
        - sum(m["bytes"] for m in included)
        - sum(map(len, additions.values()))
        - 1024 * 1024
    )
    additions["history.json"] = history_json(
        engine.store, actor, state["id"], revision=state["revision"], max_bytes=budget
    )
    links = "".join(
        f"<li><a href='{html.escape(name, quote=True)}'>{html.escape(name)}</a></li>"
        for name in additions
    )
    additions["index.html"] = (
        "<!doctype html><meta charset='utf-8'>"
        "<meta http-equiv='Content-Security-Policy' "
        "content=\"default-src 'none'; base-uri 'none'; form-action 'none'\">"
        "<title>Private training review</title>"
        f"<h1>{html.escape(state['title'])}</h1>"
        "<p><strong>Snapshot:</strong> engagement "
        f"{html.escape(str(state['id']))}, revision "
        f"{html.escape(str(state['revision']))}. "
        f"{html.escape(limits['cutoff'])}. Later changes are not included.</p>"
        "<p>Private reviewer edition. Contains scenario answers; do not distribute "
        "to learners. Training material has not received professional acceptance. "
        "No overall audit grade or issued opinion.</p>"
        "<p>engagement.json contains findings, workpapers and current records; "
        "history.json preserves earlier decisions. private/world.json records the "
        "selected cases and allocation; private/unit files retain intended records "
        "and delivery definitions. These are distinct from delivered evidence. "
        "private/review-inputs contains the actual five-layer instructor model results, "
        "source pins and explicit context omissions where review was requested.</p>"
        "<p><a href='manifest.json'>Exact native-file manifest</a></p><ul>" + links + "</ul>"
    ).encode()
    if sum(m["bytes"] for m in included) + sum(map(len, additions.values())) > MAX_EXPANDED:
        raise DomainError("Private review exceeds bounded archive limit")
    buf = io.BytesIO(engine.artifacts.bundle(included, index=limits))
    with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as archive:
        for name, data in additions.items():
            archive.writestr(name, data)
    result = engine.artifacts.retain_export(
        state["id"],
        f"{state['id']}-private-review-r{state['revision']}.zip",
        buf.getvalue(),
        source={"kind": "PRIVATE_REVIEW_EXPORT", "revision": state["revision"]},
        coverage=state["scope"],
    )
    result.update(
        status="AVAILABLE", quarantine_reason=None, mime="application/zip", audience="REVIEWER"
    )
    return result
