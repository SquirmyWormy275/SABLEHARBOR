"""Read-only, bounded dependency impact analysis; never regenerates publications."""

import argparse
import hashlib
import json
import posixpath
import sqlite3
import subprocess
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "docs/legal/gap-instruments"
DEST = ROOT / PREFIX / "source-impact"


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def read(root, path, revision=None):
    if path.startswith("/") or ".." in Path(path).parts:
        raise ValueError("Unsafe repository path: " + path)
    if revision:
        result = subprocess.run(
            ["git", "-C", str(root), "show", revision + ":" + path],
            capture_output=True,
            check=False,
        )
        return result.stdout if result.returncode == 0 else None
    target = root / path
    if target.is_symlink():
        raise ValueError("Symlink input rejected: " + path)
    return target.read_bytes() if target.is_file() else None


class Builder:
    def __init__(self, root, revision):
        self.root, self.revision = root, revision
        self.nodes, self.edges, self.problems = {}, [], []

    def file(self, path, role="source"):
        if path not in self.nodes:
            value = read(self.root, path, self.revision)
            self.nodes[path] = dict(
                id=path, path=path, kind="file", role=role, sha256=digest(value)
            )
            if value is None:
                self.problems.append("Missing graph file: " + path)
        return path

    def load(self, path):
        self.file(path, "register")
        value = read(self.root, path, self.revision)
        if value is None:
            raise ValueError("Missing required register: " + path)
        return json.loads(value)

    def edge(self, source, target, basis, **details):
        self.edges.append(dict(source=source, target=target, basis=basis, **details))

    def outputs(self, inputs, outputs, basis, **details):
        for output in outputs:
            self.file(output, "artifact")
            for source in inputs:
                self.edge(self.file(source), output, basis, **details)

    def pin(self, path, expected, basis):
        self.file(path)
        if self.nodes[path]["sha256"] != expected:
            self.problems.append("Register pin mismatch: " + path + " in " + basis)


def build_graph(root=ROOT, revision="HEAD"):
    revision = git(root, "rev-parse", revision).decode().strip()
    b = Builder(root, revision)
    manifest = PREFIX + "/manifest.json"
    m = b.load(manifest)
    common = [r["path"] for r in m["inputs"]]
    for r in m["inputs"]:
        b.pin(r["path"], r["sha256"], manifest)
    for p in m["packages"]:
        local = [p["source"], p["structured"]]
        for dep in p["dependencies"]:
            b.pin(dep["path"], dep["sha256"], manifest)
            b.outputs(
                [dep["path"]], local, manifest + "/packages/dependencies", case_id=p["gap_id"]
            )
        b.outputs(
            [*local, *common, manifest],
            [r["path"] for r in p["artifacts"]],
            manifest + "/packages/artifacts",
            case_id=p["gap_id"],
        )
    other = m["other_artifacts"]
    b.outputs(
        [*common, manifest, *[p["structured"] for p in m["packages"]]],
        [r["path"] for r in other],
        manifest + "/other_artifacts",
    )

    reg = PREFIX + "/accounting/links.json"
    a = b.load(reg)
    aout = [PREFIX + "/accounting/" + x for x in ["LINKS.md", "links.xlsx", "links.sqlite3"]]
    b.outputs(
        [PREFIX + "/accounting/source.json", "tools/legal_gaps/accounting.py"],
        [reg],
        "accounting.py build outputs",
    )
    for path, sha in a["sources"].items():
        b.pin(path, sha, reg)
        b.outputs([path], [reg], reg + "/sources")
    for row in a["links"]:
        ident = reg + "#" + row["id"]
        b.nodes[ident] = dict(
            id=ident,
            kind="selection",
            case_id=row["gap_id"],
            link_id=row["id"],
            selector=row["selector"],
            clause_heading=row["clause_heading"],
        )
        for source in [row["source_path"], row["clause_path"], reg]:
            b.edge(b.file(source), ident, reg + "/links", selector=row["selector"])
        for out in aout:
            b.edge(ident, b.file(out, "artifact"), reg + "/links", link_id=row["id"])

    pm = PREFIX + "/practice/manifest.json"
    practice = b.load(pm)
    b.pin("tools/legal_gaps/practice.py", practice["generator_sha256"], pm)
    for slug in ["acquisition", "debt", "revenue-dispute", "legal-due-diligence"]:
        packet = PREFIX + "/practice/" + slug + "/packet.json"
        p = b.load(packet)
        outputs = [
            r["path"]
            for r in practice["artifacts"]
            if "/" + slug + "/" in r["path"] and r["path"] != packet
        ]
        b.outputs(
            [packet, pm, "tools/legal_gaps/practice.py"],
            outputs,
            pm + "/artifacts",
            case_id=p["id"],
        )
        for e in p["evidence"]:
            b.pin(e["path"], e["sha256"], packet)
            b.outputs([e["path"]], [packet], packet + "/evidence", case_id=p["id"])
        for row in p["inputs"]:
            node = packet + "#input/" + row["id"]
            b.nodes[node] = dict(id=node, kind="input", case_id=p["id"], locator=row["locator"])
            b.edge(b.file(row["source_path"]), node, packet + "/inputs", locator=row["locator"])
        for c in p["calculations"]:
            node = packet + "#calculation/" + c["id"]
            b.nodes[node] = dict(
                id=node,
                kind="calculation",
                case_id=p["id"],
                calculation_id=c["id"],
                terms=c["terms"],
            )
            for _, inp in c["terms"]:
                b.edge(packet + "#input/" + inp, node, packet + "/calculations/terms")
            b.edge(packet, node, packet + "/calculations")
            for out in outputs:
                b.edge(node, b.file(out), packet + "/calculations", calculation_id=c["id"])
    shared = [
        r["path"]
        for r in practice["artifacts"]
        if "/practice/" in r["path"] and str(Path(r["path"]).parent) == PREFIX + "/practice"
    ]
    b.outputs(
        [r["path"] for r in practice["artifacts"] if r["path"].endswith("/packet.json")],
        shared,
        pm + "/artifacts",
    )

    recon = PREFIX + "/reconciliations/source.json"
    rm = PREFIX + "/reconciliations/manifest.json"
    r, rmanifest = b.load(recon), b.load(rm)
    outs = [PREFIX + "/reconciliations/" + x for x in rmanifest["files"] if x != "source.json"]
    b.outputs([recon, rm, "tools/legal_gaps/reconciliations.py"], outs, rm + "/files")
    evidence = {e["id"]: e for e in r["evidence"]}
    for e in evidence.values():
        b.pin(e["path"], e["sha256"], recon)
        b.outputs([e["path"]], [recon], recon + "/evidence", selector=e["selector"])
    for w in r["workpapers"]:
        for i, c in enumerate(w["checks"]):
            node = recon + "#" + w["id"] + "/check/" + str(i)
            b.nodes[node] = dict(
                id=node, kind="calculation", case_id=w["id"], label=c["label"], terms=c["terms"]
            )
            b.edge(recon, node, recon + "/workpapers/checks")
            for inp, _ in c["terms"]:
                item = w["inputs"][inp]
                e = evidence[item["evidence"]]
                b.edge(
                    b.file(e["path"]),
                    node,
                    recon + "/workpapers/inputs",
                    selector=e["selector"],
                    field=item["field"],
                    row_index=item["row_index"],
                )
            for out in outs:
                b.edge(node, b.file(out), recon + "/workpapers/checks", case_id=w["id"])

    wr = PREFIX + "/walkthroughs/source-register.json"
    walk = b.load(wr)
    woutputs = [
        PREFIX + "/walkthroughs/" + x
        for x in ["README.md", "walkthroughs.xlsx", "walkthroughs.sqlite3"]
    ]
    woutputs += [PREFIX + "/walkthroughs/source/" + x + ".csv" for x in walk["tables"]]
    for s in walk["sources"]:
        b.pin(s["path"], s["sha256"], wr)
        b.outputs(
            [s["path"]],
            [wr],
            wr + "/sources",
            precision="package-level; not a cell-level dependency",
        )
    b.outputs(
        [wr, "tools/legal_gaps/walkthroughs.py"],
        woutputs,
        wr + "/tables",
        case_ids=["ARU acquisition", "Foundry Field", "Red Wash"],
    )

    extend_current_cases(b)

    # Exact recorded original-file membership, not a guess based on directory names.
    for name in ["v0.2", "v0.3"]:
        path = PREFIX + "/source-impact/release-manifests/" + name + ".json"
        raw = read(root, path)
        release = json.loads(raw)
        node = "release:sable-harbor-legal-review-v" + release["version"]
        b.nodes[node] = dict(
            id=node,
            kind="retained_release",
            source_revision=release["source_revision"],
            membership_manifest=path,
            membership_sha256=digest(raw),
            action="REVIEW_SUCCESSOR; NEVER_OVERWRITE_RETAINED_RELEASE",
        )
        for member in release["original_files"]:
            if member in b.nodes:
                b.edge(member, node, path + "/original_files")

    graph = dict(
        schema_version=1,
        baseline_revision=revision,
        status="BOUNDED_REVIEW_TOOL_NOT_CANON",
        nodes=sorted(b.nodes.values(), key=lambda n: n["id"]),
        edges=sorted(b.edges, key=lambda e: json.dumps(e, sort_keys=True)),
        baseline_problems=sorted(set(b.problems)),
        uncovered_scope=[
            "Other enterprise generators and source chains are not mapped.",
            "Walkthrough dependencies are package-level, not individual worksheet cells.",
            "Release targets cover graph members only, not all files in each bundle.",
            "Changes outside these registers require classification; no universal clean claim.",
        ],
    )
    validate_graph(graph)
    return graph


def extend_current_cases(b):
    """Explicit adapters; absent packages at an older Git baseline stay out of scope."""
    inputs = PREFIX + "/period-close/inputs.json"
    if read(b.root, inputs, b.revision) is not None:
        native = b.load(inputs)
        manifest_path = PREFIX + "/period-close/manifest.json"
        manifest = b.load(manifest_path)
        case_path = PREFIX + "/period-close/case.json"
        case = b.load(case_path)
        outs = [PREFIX + "/period-close/" + x for x in manifest["files"] if x != "case.json"]
        b.pin(inputs, manifest["inputs_sha256"], manifest_path)
        b.outputs([inputs, "tools/legal_gaps/period_close.py"], [case_path], inputs + "/sources")
        for source in native["sources"]:
            b.pin(source["path"], source["sha256"], inputs)
            b.outputs(
                [source["path"]],
                [case_path],
                inputs + "/sources",
                selector=source.get("selector"),
                source_id=source["id"],
                release_member=source.get("release_member"),
                precision="case-level selection",
            )
            if source.get("upstream_path"):
                b.pin(source["upstream_path"], source["upstream_sha256"], inputs)
                b.outputs(
                    [source["upstream_path"]], [source["path"]], inputs + "/sources/upstream_path"
                )
        b.outputs(
            [case_path, manifest_path],
            outs,
            manifest_path + "/files",
            case_id="SH-PERIOD-CLOSE-ARU-2027-01",
        )
        for i, check in enumerate(case["checks"]):
            node = case_path + "#check/" + str(i)
            b.nodes[node] = dict(
                id=node,
                kind="calculation",
                case_id="SH-PERIOD-CLOSE-ARU-2027-01",
                name=check["name"],
                basis=check["basis"],
                precision="case-level dependency",
            )
            b.edge(case_path, node, case_path + "/checks")
            for out in outs:
                b.edge(node, b.file(out), case_path + "/checks")
    tracker_path = PREFIX + "/evidence-tracking/tracker.json"
    if read(b.root, tracker_path, b.revision) is not None:
        tracker = b.load(tracker_path)
        b.outputs(
            ["tools/legal_gaps/evidence_tracking.py"], [tracker_path], "evidence_tracking.py build"
        )
        for path, sha in tracker["source_pins"].items():
            b.pin(path, sha, tracker_path)
            b.outputs([path], [tracker_path], tracker_path + "/source_pins")
        outs = [PREFIX + "/evidence-tracking/" + x for x in ["tracker.xlsx", "tracker.sqlite3"]]
        for request in tracker["requests"]:
            node = tracker_path + "#" + request["id"]
            b.nodes[node] = dict(
                id=node,
                kind="evidence_request",
                request_id=request["id"],
                source_locator=request["source_locator"],
            )
            for source in [tracker_path, request["source_path"], request["context_path"]]:
                b.edge(
                    b.file(source),
                    node,
                    tracker_path + "/requests",
                    locator=request["source_locator"],
                )
            for out in outs:
                b.edge(node, b.file(out, "artifact"), tracker_path + "/requests")
    brief_path = PREFIX + "/case-briefs/source.json"
    if read(b.root, brief_path, b.revision) is not None:
        brief = b.load(brief_path)
        # Manifest membership is authoritative; source case IDs label the dependency details.
        bm = PREFIX + "/case-briefs/manifest.json"
        manifest = b.load(bm)
        for path, sha in manifest["inputs"].items():
            b.pin(path, sha, bm)
        outputs = manifest["files"]
        if isinstance(outputs, dict):
            outputs = list(outputs)
        else:
            outputs = [x["path"] for x in outputs]
        outputs = [
            x if x.startswith(PREFIX + "/") else PREFIX + "/case-briefs/" + x for x in outputs
        ]
        for case in brief["cases"]:
            for source in case["files"]:
                path = posixpath.normpath(PREFIX + "/case-briefs/" + source["path"])
                b.outputs(
                    [path],
                    [brief_path],
                    brief_path + "/cases/files",
                    case_id=case["id"],
                    precision="Reference dependency; recheck brief after source changes",
                )
        b.outputs([brief_path, bm, *manifest["inputs"]], outputs, bm + "/files")


def validate_graph(graph):
    nodes = {n["id"]: n for n in graph["nodes"]}
    if len(nodes) != len(graph["nodes"]):
        raise ValueError("Duplicate node IDs")
    degree = {n: 0 for n in nodes}
    adjacency = defaultdict(list)
    for e in graph["edges"]:
        if e["source"] not in nodes or e["target"] not in nodes:
            raise ValueError("Unknown edge endpoint: " + str(e))
        degree[e["target"]] += 1
        adjacency[e["source"]].append(e["target"])
    q = deque(n for n, d in degree.items() if d == 0)
    seen = 0
    while q:
        n = q.popleft()
        seen += 1
        for target in adjacency[n]:
            degree[target] -= 1
            if degree[target] == 0:
                q.append(target)
    if seen != len(nodes):
        raise ValueError("Dependency cycle; cannot certify graph")


def analyze(graph, current_hashes, changed_paths=()):
    validate_graph(graph)
    nodes = {n["id"]: n for n in graph["nodes"]}
    changes = []
    for node in graph["nodes"]:
        if node["kind"] != "file":
            continue
        old, new = node["sha256"], current_hashes.get(node["path"])
        if old is None or new != old:
            changes.append(
                dict(
                    path=node["path"],
                    before=old,
                    after=new,
                    change="ADDED"
                    if old is None and new
                    else "MISSING"
                    if new is None
                    else "MODIFIED",
                )
            )
    adjacency = defaultdict(list)
    for edge in graph["edges"]:
        adjacency[edge["source"]].append(edge)
    impacted = {}
    for change in changes:
        q = deque([change["path"]])
        seen = {change["path"]}
        while q:
            source = q.popleft()
            for edge in adjacency[source]:
                target = edge["target"]
                item = impacted.setdefault(
                    target, dict(node=nodes[target], changed_inputs=[], dependency_edges=[])
                )
                if change["path"] not in item["changed_inputs"]:
                    item["changed_inputs"].append(change["path"])
                if edge not in item["dependency_edges"]:
                    item["dependency_edges"].append(edge)
                if target not in seen:
                    seen.add(target)
                    q.append(target)
    outside = sorted(
        set(changed_paths) - {n["path"] for n in graph["nodes"] if n["kind"] == "file"}
    )
    problems = list(graph.get("baseline_problems", []))
    return dict(
        baseline_revision=graph["baseline_revision"],
        status="REVIEW_REQUIRED"
        if changes or outside or problems
        else "NO_CHANGE_IN_BOUNDED_GRAPH",
        changes=changes,
        impacted=[impacted[k] for k in sorted(impacted)],
        unclassified_changes=outside,
        baseline_problems=problems,
        uncovered_scope=graph["uncovered_scope"],
    )


def report(graph, root=ROOT, current=None):
    if current:
        current = git(root, "rev-parse", "--verify", current + "^{commit}").decode().strip()
    hashes = {
        n["path"]: digest(read(root, n["path"], current))
        for n in graph["nodes"]
        if n["kind"] == "file"
    }
    args = ["diff", "--name-only", "-z", graph["baseline_revision"]]
    if current:
        args.append(current)
    changed = git(root, *args).decode().split("\0")
    if not current:
        changed += (
            git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
        )
    result = analyze(graph, hashes, filter(None, changed))
    for node in graph["nodes"]:
        if node["kind"] == "retained_release":
            actual = digest(read(root, node["membership_manifest"]))
            if actual != node["membership_sha256"]:
                result["baseline_problems"].append(
                    "Release membership record changed: " + node["membership_manifest"]
                )
                result["status"] = "REVIEW_REQUIRED"
    result["current_revision"] = current or "WORKTREE"
    return result


def write_report(result, output):
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# Source-change impact report",
        "",
        "**" + result["status"] + "**",
        "",
        "Baseline: `"
        + result["baseline_revision"]
        + "`. Current: `"
        + result.get("current_revision", "TEST_OVERLAY")
        + "`.",
        "",
        "This report requests rechecking; it does not regenerate, approve or overwrite anything.",
        "",
        f"Changed/missing mapped files: {len(result['changes'])}. "
        f"Impacted nodes: {len(result['impacted'])}.",
        "",
        "## Changed inputs",
        "",
    ]
    lines += ["- `" + x["path"] + "` — " + x["change"] for x in result["changes"]] or [
        "None in the bounded graph."
    ]
    lines += ["", "## Recheck queue", ""]
    for x in result["impacted"]:
        node = x["node"]
        lines += [
            "- `"
            + node["id"]
            + "` — "
            + node.get("action", node["kind"])
            + "; caused by "
            + ", ".join("`" + p + "`" for p in x["changed_inputs"])
            + "."
        ]
    lines += [
        "",
        "Exact selectors, calculation IDs and traversed edges are in report.json "
        "and the SQLite impact table.",
        "",
        "## Unclassified changes",
        "",
    ]
    lines += ["- `" + x + "`" for x in result["unclassified_changes"]] or ["None."]
    lines += ["", "## Baseline problems", ""] + (
        ["- " + x for x in result["baseline_problems"]] or ["None."]
    )
    lines += ["", "## Coverage limits", ""] + ["- " + x for x in result["uncovered_scope"]]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")
    with sqlite3.connect(output / "report.sqlite3") as db:
        db.execute("CREATE TABLE report (json TEXT NOT NULL)")
        db.execute("INSERT INTO report VALUES (?)", (json.dumps(result, sort_keys=True),))
        db.execute("CREATE TABLE impact (node_id TEXT PRIMARY KEY, kind TEXT, detail_json TEXT)")
        db.executemany(
            "INSERT INTO impact VALUES (?, ?, ?)",
            [
                (x["node"]["id"], x["node"]["kind"], json.dumps(x, sort_keys=True))
                for x in result["impacted"]
            ],
        )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["baseline", "report", "audit"])
    p.add_argument("--graph", type=Path, default=DEST / "graph.json")
    p.add_argument("--baseline", default="HEAD")
    p.add_argument("--current")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.command == "baseline":
        if a.output.exists():
            raise ValueError("New baseline path required; preserve prior baseline")
        a.output.write_text(json.dumps(build_graph(revision=a.baseline), indent=2) + "\n")
    else:
        graph = json.loads(a.graph.read_text())
        if a.command == "report":
            result = report(graph, current=a.current)
        else:
            hashes = {n["path"]: n["sha256"] for n in graph["nodes"] if n["kind"] == "file"}
            target = "docs/finance/evidence/SH-FIN-HUMAN-001/source.json"
            hashes[target] = digest(b"TEST MUTATION; REAL SOURCE UNCHANGED")
            result = analyze(graph, hashes, [target])
            result["audit_method"] = "In-memory hash overlay; no source bytes written."
            result["current_revision"] = "SIMULATED_CHANGE_NOT_REAL_SOURCE"
        write_report(result, a.output)
        print(
            result["status"],
            len(result["changes"]),
            "changed;",
            len(result["impacted"]),
            "impacted",
        )


if __name__ == "__main__":
    main()
