"""Read-only GitHub PR review acquisition; source facts never imply control acceptance."""

import argparse
import base64
import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import connectors
from .collection import _private_write
from .testing import instant, nonempty


def normalize(pr, reviews, scope, owner, repo):
    """Preserve native Git object IDs, not invented SHA256 artifact identities."""
    if pr["base"]["repo"]["full_name"].lower() != f"{owner}/{repo}".lower():
        raise ValueError("Wrong source repository")
    if not pr.get("merged_at") or not pr.get("merged"):
        raise ValueError("Census includes an unmerged pull request")
    merged = instant(pr["merged_at"])
    if not instant(scope["period_start"]) <= merged <= instant(scope["period_end"]):
        raise ValueError("Pull request merge falls outside scope period")
    seen, latest = set(), {}
    for review in reviews:
        if review["id"] in seen:
            raise ValueError("Duplicate review ID")
        seen.add(review["id"])
        if review["state"] not in {
            "APPROVED",
            "CHANGES_REQUESTED",
            "DISMISSED",
            "COMMENTED",
            "PENDING",
        }:
            raise ValueError("Unknown GitHub review state")
        if review["state"] in {"COMMENTED", "PENDING"}:
            continue
        actor = str(review["user"]["id"])
        timestamp = instant(review["submitted_at"])
        rank = (timestamp, review["id"])
        if actor not in latest or rank > latest[actor][0]:
            latest[actor] = (rank, review)
    blocking = [r for _, r in latest.values() if r["state"] == "CHANGES_REQUESTED"]
    approvals = [
        r
        for _, r in latest.values()
        if r["state"] == "APPROVED"
        and r["commit_id"] == pr["head"]["sha"]
        and instant(r["submitted_at"]) <= merged
        and r["user"]["id"] != pr["user"]["id"]
    ]
    chosen = (
        max(approvals, key=lambda r: (instant(r["submitted_at"]), r["id"]))
        if approvals and not blocking
        else None
    )
    data = dict(
        author_id="github-user:" + str(pr["user"]["id"]),
        decision="APPROVE" if chosen else "NOT_ESTABLISHED",
        proposed_at=pr["created_at"],
        merged_at=pr["merged_at"],
        github_head_commit_id=pr["head"]["sha"],
        github_merge_commit_id=pr.get("merge_commit_sha"),
        github_review_commit_id=chosen["commit_id"] if chosen else None,
        github_latest_review_states=[
            dict(
                review_id=r["id"],
                user_id=r["user"]["id"],
                state=r["state"],
                commit_id=r["commit_id"],
                submitted_at=r["submitted_at"],
            )
            for _, r in sorted(latest.values(), key=lambda item: item[1]["id"])
        ],
    )
    if chosen:
        data.update(
            reviewer_id="github-user:" + str(chosen["user"]["id"]),
            reviewed_at=chosen["submitted_at"],
        )
    return dict(
        id=f"github:{owner}/{repo}:pull:{pr['number']}",
        origin=scope["origin"],
        boundary_id=scope["boundary_id"],
        occurred_at=pr["merged_at"],
        kind="revision_review",
        data=data,
        source_url=f"https://github.com/{owner}/{repo}/pull/{pr['number']}",
        source_limitations=[
            "Branch-protection enforcement and reviewer qualification not established",
            "Git commit IDs are not SHA256 artifact hashes; artifact identity fields remain absent",
            "Current REST review states do not reconstruct historical dismissal/branch policy at merge",
            "Operator-supplied PR selection is not an independently approved complete population",
        ],
    )


def acquire(config):
    owner, repo = config["owner"], config["repo"]
    if any(
        not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", v) or v in {".", ".."}
        for v in (owner, repo)
    ):
        raise ValueError("Invalid GitHub repository")
    numbers = config["pull_numbers"]
    if (
        not isinstance(numbers, list)
        or not 1 <= len(numbers) <= 100
        or any(type(n) is not int or n <= 0 for n in numbers)
        or len(set(numbers)) != len(numbers)
    ):
        raise ValueError("Supply 1-100 distinct positive PR numbers")
    scope = config["scope"]
    for k in ("boundary_id", "origin"):
        nonempty(scope[k])
    if scope["origin"] != "OPERATOR_SUPPLIED":
        raise ValueError("Live GitHub acquisition requires OPERATOR_SUPPLIED origin")
    if instant(scope["period_start"]) >= instant(scope["period_end"]):
        raise ValueError("Invalid scope period")
    maximum = config.get("max_bytes", 10_000_000)
    max_pages = config.get("max_pages_per_pr", 20)
    timeout = config.get("timeout_seconds", 15)
    if (
        type(maximum) is not int
        or not 1 <= maximum <= 20_000_000
        or type(max_pages) is not int
        or not 1 <= max_pages <= 100
        or type(timeout) not in (int, float)
        or not 0 < timeout <= 30
    ):
        raise ValueError("Invalid acquisition limits")
    secret = connectors._credential(config["credential"]) if config.get("credential") else None
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), connectors.NoRedirect(), connectors.PublicHTTPSHandler()
    )
    pages, consumed = [], 0

    def get(path):
        nonlocal consumed
        url = "https://api.github.com" + path
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "SABLEHARBOR-CCF-readonly",
        }
        if secret:
            headers["Authorization"] = "Bearer " + secret
        try:
            with opener.open(
                urllib.request.Request(url, headers=headers), timeout=timeout
            ) as response:
                raw = response.read(maximum - consumed + 1)
            consumed += len(raw)
            if consumed > maximum:
                raise ValueError("GitHub byte limit exceeded")
            value = json.loads(raw, object_pairs_hook=connectors._unique_object)
            if secret and (secret.encode() in raw or connectors._contains_secret(value, secret)):
                raise ValueError("GitHub response contains credential material")
        except (urllib.error.URLError, OSError):
            raise ValueError("GitHub request failed; check read access or rate limit") from None
        pages.append(
            dict(
                url=url,
                captured_at=datetime.now(timezone.utc).isoformat(),
                sha256=hashlib.sha256(raw).hexdigest(),
                raw_base64=base64.b64encode(raw).decode("ascii"),
            )
        )
        return value

    records = []
    for number in numbers:
        path = f"/repos/{owner}/{repo}/pulls/{number}"
        pr = get(path)
        if pr["number"] != number:
            raise ValueError("Wrong pull request returned")
        reviews = []
        for page in range(1, max_pages + 1):
            batch = get(path + f"/reviews?per_page=100&page={page}")
            if not isinstance(batch, list):
                raise ValueError("Expected GitHub review list")
            reviews.extend(batch)
            if len(batch) < 100:
                break
        else:
            raise ValueError("GitHub review pagination incomplete at configured limit")
        final = get(path)
        if any(
            final.get(k) != pr.get(k)
            for k in ("head", "merged_at", "merge_commit_sha", "updated_at")
        ):
            raise ValueError("Pull request changed during acquisition; retry")
        records.append(normalize(pr, reviews, scope, owner, repo))
    return dict(
        schema_version=1,
        records=records,
        provenance=dict(
            source_system=f"github:{owner}/{repo}",
            actual_source_acquisition=True,
            requested_pull_numbers=numbers,
            scope=scope,
            pages=pages,
            api_version="2026-03-10",
            population_status="OPERATOR_SELECTION_REQUIRES_INDEPENDENT_CENSUS_REVIEW",
        ),
        test_outcome="NOT_RUN",
    )


def export(config, output_dir):
    result = acquire(config)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    _private_write(output / "github-evidence.json", result["records"])
    _private_write(output / "github-source-receipt.json", result)
    evidence_config = dict(
        type="local_json",
        purpose="evidence",
        path=str((output / "github-evidence.json").resolve()),
        source_system=result["provenance"]["source_system"],
        query="GitHub operator-selected merged PRs: " + ",".join(map(str, config["pull_numbers"])),
        scope=config["scope"],
    )
    _private_write(output / "evidence-connector.json", evidence_config)
    return dict(
        output=str(output),
        record_count=len(result["records"]),
        test_outcome="NOT_RUN",
        evidence_config=evidence_config,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(json.loads(args.config.read_text()), args.output), indent=2))


if __name__ == "__main__":
    main()
