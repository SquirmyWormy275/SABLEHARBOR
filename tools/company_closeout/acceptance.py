"""Bind scoped edition acceptance to actual merged repository evidence."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .edition import EditionError, member_path, sha, timestamp

REPOSITORY = "SquirmyWormy275/SABLEHARBOR"


def read_merge(number):
    if type(number) is not int or number <= 0:
        raise EditionError("Positive acceptance PR number required")
    try:
        record = json.loads(
            subprocess.check_output(["gh", "api", f"repos/{REPOSITORY}/pulls/{number}"], text=True)
        )
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise EditionError("Cannot verify acceptance PR through repository API") from exc
    if (
        record.get("merged") is not True
        or record.get("state") != "closed"
        or record.get("base", {}).get("ref") != "main"
        or record.get("base", {}).get("repo", {}).get("full_name") != REPOSITORY
        or record.get("html_url") != f"https://github.com/{REPOSITORY}/pull/{number}"
    ):
        raise EditionError("Acceptance requires an actually merged PR to this repository main")
    return {
        "pr_number": number,
        "pr_url": record["html_url"],
        "merge_commit": record["merge_commit_sha"],
        "accepted_at": record["merged_at"],
    }


def collect(root: Path, revision: str, number: int, adoption_path: str):
    merge = read_merge(number)
    # Freeze at the exact reviewed merge. Later unrelated descendants require
    # their own accepted edition rather than inheriting this PR's authority.
    if merge["merge_commit"] != revision:
        raise EditionError("Accepted edition source must equal its actual merge commit")
    member_path(adoption_path)
    path = root / adoption_path
    if path.is_symlink() or not path.is_file():
        raise EditionError("Missing scoped adoption source")
    scope = json.loads(path.read_bytes())
    if (
        scope.get("status") != "LOCKED_ON_REPOSITORY_ACCEPTANCE"
        or not scope.get("adopted_sources")
        or not scope.get("preserved_states")
        or {p["id"] for p in scope.get("work_packages", [])}
        != {f"SH-C{i:02d}" for i in range(1, 11)}
    ):
        raise EditionError("Incomplete scoped adoption source")
    for source in scope["adopted_sources"]:
        member_path(source["path"])
        target = root / source["path"]
        if (
            not source.get("scope")
            or target.is_symlink()
            or sha(target.read_bytes()) != source["sha256"]
        ):
            raise EditionError("Changed or unscoped adopted source")
    return dict(
        merge,
        source_commit=revision,
        adoption_path=adoption_path,
        adoption_sha256=sha(path.read_bytes()),
        adopted_sources=scope["adopted_sources"],
        preserved_states=scope["preserved_states"],
        work_packages=scope["work_packages"],
        observed_at=datetime.now(timezone.utc).isoformat(),
    )


def validate(contract):
    receipt = contract.get("acceptance_receipt")
    if contract["status"] != "ACCEPTED_SCOPED_EDITION":
        if receipt is not None:
            raise EditionError("Review candidate cannot carry accepted receipt")
        return
    if not isinstance(receipt, dict):
        raise EditionError("Accepted edition requires merged acceptance receipt")
    revision = contract.get("source_commit_required")
    if (
        not revision
        or receipt.get("source_commit") != revision
        or receipt.get("merge_commit") != revision
    ):
        raise EditionError("Acceptance receipt source/merge differs from edition")
    number = receipt.get("pr_number")
    if (
        type(number) is not int
        or number <= 0
        or receipt.get("pr_url") != f"https://github.com/{REPOSITORY}/pull/{number}"
    ):
        raise EditionError("Invalid acceptance repository PR identity")
    accepted = timestamp(receipt["accepted_at"])
    if timestamp(receipt["observed_at"]) < accepted:
        raise EditionError("Acceptance observation precedes merge")
    members = {m["path"]: m["sha256"] for c in contract["components"] for m in c["members"]}
    if members.get(receipt.get("adoption_path")) != receipt.get(
        "adoption_sha256"
    ) or not receipt.get("adoption_sha256"):
        raise EditionError("Scoped adoption source is missing or changed")
    if not receipt.get("adopted_sources") or not receipt.get("preserved_states"):
        raise EditionError("Explicit adopted scope and preserved states required")
    seen = set()
    for source in receipt["adopted_sources"]:
        if (
            source["path"] in seen
            or not source.get("scope")
            or members.get(source["path"]) != source["sha256"]
        ):
            raise EditionError("Adopted source omitted, duplicated or changed")
        seen.add(source["path"])
    packages = receipt.get("work_packages", [])
    if len(packages) != 10 or {p["id"] for p in packages} != {f"SH-C{i:02d}" for i in range(1, 11)}:
        raise EditionError("Acceptance must disposition all ten work packages")
    if any(timestamp(c["available_at"]) < accepted for c in contract["components"]):
        raise EditionError("Accepted package availability precedes repository acceptance")


def verify_live(contract, root):
    receipt = contract["acceptance_receipt"]
    observed = collect(
        root, contract["source_commit_required"], receipt["pr_number"], receipt["adoption_path"]
    )
    if any(observed[key] != receipt[key] for key in observed if key != "observed_at"):
        raise EditionError("Acceptance receipt differs from merged repository/source evidence")


def verify_packaged_scope(contract, content):
    if contract["status"] != "ACCEPTED_SCOPED_EDITION":
        return
    receipt = contract["acceptance_receipt"]
    scope = json.loads((content / receipt["adoption_path"]).read_bytes())
    if scope.get("status") != "LOCKED_ON_REPOSITORY_ACCEPTANCE" or any(
        scope.get(key) != receipt[key]
        for key in ("adopted_sources", "preserved_states", "work_packages")
    ):
        raise EditionError("Packaged adoption scope contradicts acceptance receipt")
