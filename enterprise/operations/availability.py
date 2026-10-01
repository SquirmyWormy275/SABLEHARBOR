"""Deterministic repository availability, separate from authored fictional dates."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = "DIRTY_WORKING_COPY_PREVIEW_NOT_PUBLISHABLE"


def repository_context(root=ROOT):
    commit, timestamp = (
        subprocess.check_output(
            ["git", "show", "-s", "--format=%H%n%cI", "HEAD"], cwd=root, text=True
        )
        .strip()
        .splitlines()
    )
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=root, text=True
        ).strip()
    )
    available = (
        datetime.fromisoformat(timestamp)
        .astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )
    return dict(
        repository_source_commit=commit,
        repository_source_available_at=available,
        publication_state=PREVIEW
        if dirty
        else "COMMITTED_SOURCE_REVIEWABLE_NOT_RELEASE_ACCEPTANCE",
        publishable_source_snapshot=not dirty,
    )


def apply(result, context=None):
    context = context or repository_context()
    floor = datetime.fromisoformat(context["repository_source_available_at"])

    def visit(value):
        if isinstance(value, list):
            for row in value:
                visit(row)
        elif isinstance(value, dict):
            for nested in list(value.values()):
                visit(nested)
            if "available_at" in value:
                declared = value.get("declared_available_at", value["available_at"])
                value["declared_available_at"] = declared
                value["declared_available_precision"] = (
                    "DAY" if declared[11:] in {"00:00:00Z", "00:00:00+00:00"} else "TIMESTAMP"
                )
                value["authored_day"] = declared[:10]
                value.update(context)
                value["available_at"] = (
                    max(datetime.fromisoformat(declared), floor)
                    .astimezone(UTC)
                    .isoformat()
                    .replace("+00:00", "Z")
                )
                if "recorded_at" in value:
                    value.setdefault("declared_recorded_at", value["recorded_at"])
                    value["recorded_at"] = value["available_at"]

    visit(result)
    result.update(context)
    return result


def queryable(row, allow_preview=False):
    return allow_preview or row.get("publication_state") != PREVIEW
