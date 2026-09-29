"""Finite explicitly selected debriefs and portable exports; no grading or model calls."""

import hashlib
import html
import io
import json
import re
import zipfile
from copy import deepcopy
from datetime import UTC, datetime, timedelta

from .explanation_binding import verify_snapshot
from .history_inspection import inspect_history
from .store import DomainError, canonical, digest, identifier

SCHEMA = "SELECTED_INSTRUCTOR_DEBRIEF_V1"
MAX_TOTAL = 16 * 1024 * 1024


def require(ok, message, status=400):
    if not ok:
        raise DomainError(message, status=status)


def fields(value, names):
    require(isinstance(value, dict) and set(value) == set(names), "Exact debrief fields required")


def text(value, limit=4000):
    require(
        isinstance(value, str) and 0 < len(value.strip()) <= limit, "Bounded debrief text required"
    )
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise DomainError("Valid Unicode required") from error
    return value


def ids(value, limit=10):
    require(isinstance(value, list) and len(value) <= limit, "Bounded selected IDs required")
    for item in value:
        text(item, 128)
    require(len(set(value)) == len(value), "Duplicate selection")
    return value


def pin(value):
    require(
        isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value), "Exact SHA256 required"
    )
    return value


def annotation(value):
    fields(value, ("artifact_id", "sha256", "note", "locator", "attach"))
    text(value["artifact_id"], 128)
    pin(value["sha256"])
    text(value["note"], 1000)
    require(type(value["attach"]) is bool, "Explicit attachment selection required")
    if value["locator"] is not None:
        fields(value["locator"], ("kind", "value"))
        require(
            isinstance(value["locator"]["kind"], str)
            and value["locator"]["kind"] in {"PAGE", "LINE", "CELL", "TIME", "OTHER"},
            "Typed locator required",
        )
        text(value["locator"]["value"], 200)


def validate_document(document):
    fields(
        document,
        (
            "schema",
            "title",
            "version",
            "predecessor",
            "key_manifest_sha256",
            "learner",
            "source_references",
            "sections",
            "qualification",
        ),
    )
    require(
        document["schema"] == SCHEMA
        and type(document["version"]) is int
        and document["version"] > 0,
        "Invalid debrief schema/version",
    )
    text(document["title"], 200)
    pin(document["key_manifest_sha256"])
    require(
        document["qualification"]
        == "INSTRUCTOR_AUTHORED_UNVALIDATED_LOCATORS_NOT_VERIFIED_NO_GRADING",
        "Debrief qualification differs",
    )
    learner = document["learner"]
    fields(
        learner,
        (
            "actor_id",
            "revision",
            "state_sha256",
            "event_sha256",
            "history_sha256",
            "simulated_at",
            "qualification",
        ),
    )
    text(learner["actor_id"], 128)
    require(
        type(learner["revision"]) is int and learner["revision"] >= 0,
        "Historical revision required",
    )
    require(
        learner["simulated_at"] is None or isinstance(learner["simulated_at"], str),
        "Historical clock differs",
    )
    for name in ("state_sha256", "event_sha256", "history_sha256"):
        pin(learner[name])
    require(
        learner["qualification"]
        == "SHARED_STATE_NOT_SUBMISSION_KEY_SUPPORT_MAY_POSTDATE_LEARNER_REVISION",
        "Learner qualification differs",
    )
    if document["predecessor"] is None:
        require(document["version"] == 1, "Initial debrief version differs")
    else:
        fields(document["predecessor"], ("release_id", "release_sha256"))
        text(document["predecessor"]["release_id"], 128)
        pin(document["predecessor"]["release_sha256"])
        require(document["version"] > 1, "Correction version differs")
    require(
        isinstance(document["sections"], list) and 1 <= len(document["sections"]) <= 10,
        "One to ten sections required",
    )
    require(len(canonical(document).encode()) <= 256 * 1024, "Debrief document limit")
    for section in document["sections"]:
        fields(
            section,
            ("issues", "expectations", "explanation", "limitations", "prompts", "annotations"),
        )
        require(
            isinstance(section["issues"], list) and 1 <= len(section["issues"]) <= 10,
            "Selected issues required",
        )
        issue_ids = []
        for issue in section["issues"]:
            require(
                isinstance(issue, dict)
                and set(issue)
                in ({"id", "control_ids", "claim"}, {"id", "control_ids", "claim", "uncertainty"}),
                "Selected issue fields differ",
            )
            text(issue["id"], 128)
            ids(issue["control_ids"], 100)
            text(issue["claim"], 16000)
            if "uncertainty" in issue:
                text(issue["uncertainty"], 16000)
            issue_ids.append(issue["id"])
        ids(issue_ids)
        require(
            isinstance(section["expectations"], list) and len(section["expectations"]) <= 10,
            "Expectation limit",
        )
        expectation_ids = []
        for expected in section["expectations"]:
            fields(expected, ("id", "issue_ids", "procedure", "acceptable_alternatives"))
            text(expected["id"], 128)
            expectation_ids.append(expected["id"])
            ids(expected["issue_ids"])
            require(set(expected["issue_ids"]) <= set(issue_ids), "Expectation selection differs")
            text(expected["procedure"], 16000)
            require(
                isinstance(expected["acceptable_alternatives"], list)
                and len(expected["acceptable_alternatives"]) <= 100,
                "Alternative limit",
            )
            for alternative in expected["acceptable_alternatives"]:
                text(alternative, 16000)
        ids(expectation_ids)
        require(
            isinstance(section["annotations"], list) and len(section["annotations"]) <= 8,
            "Annotation limit",
        )
        for item in section["annotations"]:
            annotation(item)
        require(
            len({a["artifact_id"] for a in section["annotations"]}) == len(section["annotations"]),
            "Duplicate annotation",
        )
        text(section["explanation"])
        text(section["limitations"])
        require(
            isinstance(section["prompts"], list) and 1 <= len(section["prompts"]) <= 8,
            "One to eight prompts required",
        )
        for prompt in section["prompts"]:
            text(prompt, 1000)
    originals = {}
    for section in document["sections"]:
        for item in section["annotations"]:
            require(
                item["artifact_id"] not in originals
                or originals[item["artifact_id"]] == (item["sha256"], item["attach"]),
                "Inconsistent original selection",
            )
            originals[item["artifact_id"]] = (item["sha256"], item["attach"])
    require(len(originals) <= 8, "Original selection limit")
    require(
        isinstance(document["source_references"], list)
        and len(document["source_references"]) == len(originals),
        "Selected source references differ",
    )  # noqa: E501
    seen_sources = set()
    for reference in document["source_references"]:
        fields(reference, ("artifact_id", "artifact_sha256", "status", "native"))
        require(
            reference["artifact_id"] in originals
            and reference["artifact_id"] not in seen_sources
            and reference["artifact_sha256"] == originals[reference["artifact_id"]][0],
            "Source reference artifact differs",
        )  # noqa: E501
        seen_sources.add(reference["artifact_id"])
        require(
            reference["status"] in {"RECORDED_EXACT_NATIVE_IDENTITY", "UNRECORDED"},
            "Source identity status differs",
        )  # noqa: E501
        if reference["status"] == "UNRECORDED":
            require(reference["native"] is None, "Unrecorded source must remain null")
        else:
            native = reference["native"]
            require(
                isinstance(native, dict)
                and set(native)
                <= {
                    "company",
                    "branch",
                    "system",
                    "record",
                    "version",
                    "sha256",
                    "source_store_id",
                    "source_system_alias",
                    "registry_sha256",
                    "portfolio_qualification",
                }
                and {"company", "branch", "system", "record", "version", "sha256"} <= set(native),
                "Native identity fields differ",
            )  # noqa: E501
            require(
                type(native["version"]) is int
                and native["version"] > 0
                and native["sha256"] == reference["artifact_sha256"],
                "Native identity pin differs",
            )  # noqa: E501
            for key, value in native.items():
                if key != "version":
                    text(value, 300)
            pin(native["sha256"])
            if "registry_sha256" in native:
                pin(native["registry_sha256"])
    return document


def validate_export_preview(value):
    fields(
        value,
        (
            "id",
            "actor_id",
            "engagement_id",
            "current_state_sha256",
            "release_id",
            "release_sha256",
            "filename",
            "sha256",
            "bytes",
            "members",
            "expires_at",
        ),
    )
    for key in ("id", "actor_id", "engagement_id", "release_id"):
        text(value[key], 128)
    for key in ("current_state_sha256", "release_sha256", "sha256"):
        pin(value[key])
    require(
        value["filename"] == "selected-debrief.zip"
        and type(value["bytes"]) is int
        and 0 < value["bytes"] <= 20 * 1024 * 1024,
        "Export size/name differs",
    )
    require(
        datetime.fromisoformat(value["expires_at"]).tzinfo is not None,
        "Export expiry timezone required",
    )
    require(
        isinstance(value["members"], list) and 2 <= len(value["members"]) <= 10,
        "Export member limit",
    )
    names = []
    for member in value["members"]:
        fields(member, ("name", "bytes", "sha256"))
        name = member["name"]
        require(
            isinstance(name, str)
            and (
                name in {"debrief.html", "manifest.json"}
                or re.fullmatch(r"originals/[0-9]{2}-[a-f0-9]{64}\.bin", name)
            ),
            "Unsafe export member",
        )
        require(
            type(member["bytes"]) is int and 0 <= member["bytes"] <= MAX_TOTAL,
            "Invalid member bytes",
        )
        pin(member["sha256"])
        names.append(name)
    require(
        len(names) == len(set(names))
        and names == sorted(names)
        and {"debrief.html", "manifest.json"} <= set(names),
        "Export members differ",
    )
    return value


def package(value, attachments):
    """ZIP_STORED fixed metadata avoids compressor/version nondeterminism."""
    document = validate_document(value["content"]["document"])
    manifest = {
        "schema": "PORTABLE_SELECTED_DEBRIEF_V1",
        "release_id": value["id"],
        "release_sha256": digest(value),
        "document": document,
        "attachments": [],
    }
    files = {}
    for index, (annotation, data) in enumerate(attachments, 1):
        name = f"originals/{index:02d}-{annotation['sha256']}.bin"
        require(
            hashlib.sha256(data).hexdigest() == annotation["sha256"],
            "Attachment bytes changed",
            409,
        )
        files[name] = data
        manifest["attachments"].append(
            {
                "name": name,
                "artifact_id": annotation["artifact_id"],
                "sha256": annotation["sha256"],
                "bytes": len(data),
            }
        )
    require(sum(map(len, files.values())) <= MAX_TOTAL, "Attachment total limit")

    def escape(value):
        return html.escape(str(value), quote=True)

    body = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">",  # noqa: E501
        "<title>Selected debrief</title><style>body{font:16px/1.6 sans-serif;max-width:70ch;margin:2rem auto;padding:0 1rem;overflow-wrap:anywhere}section{border-top:1px solid #aaa;margin-top:2rem}pre{white-space:pre-wrap}small{color:#444}</style></head><body>",  # noqa: E501
        f"<h1>{escape(document['title'])}</h1>",
        "<p>Instructor-authored interpretation. Professional acceptance and grading are not asserted.</p>",  # noqa: E501
        f"<p>Selected learner revision {document['learner']['revision']}; recorded clock: {escape(document['learner']['simulated_at'] or 'Unavailable')}. This is shared engagement history, not a submission or individual performance record. Selected Key support may postdate this learner revision.</p>",  # noqa: E501
        f"<p>Document version {document['version']}. Only the selected sections and expressly included originals are provided.</p>",  # noqa: E501
    ]
    attached = {a["artifact_id"]: a["name"] for a in manifest["attachments"]}
    for n, section in enumerate(document["sections"], 1):
        body.append(f"<section><h2>Section {n}</h2><h3>Authored issues</h3>")
        for issue in section["issues"]:
            body.append(
                f"<h4>{escape(issue['id'])}</h4><p>{escape(issue['claim'])}</p><p><strong>Authored uncertainty:</strong> {escape(issue.get('uncertainty', 'Not supplied'))}</p>"  # noqa: E501
            )
        body.append(
            f"<h3>Explanation</h3><p>{escape(section['explanation'])}</p><h3>Limitations</h3><p>{escape(section['limitations'])}</p>"  # noqa: E501
        )
        for expected in section["expectations"]:
            body.append(
                f"<h3>Authored procedure {escape(expected['id'])}</h3><p>{escape(expected['procedure'])}</p><h4>Acceptable alternatives (authored)</h4><ul>"  # noqa: E501
            )
            body.extend(f"<li>{escape(item)}</li>" for item in expected["acceptable_alternatives"])
            body.append("</ul>")
        body.append("<h3>Discussion prompts</h3><ol>")
        body.extend(f"<li>{escape(item)}</li>" for item in section["prompts"])
        body.append("</ol>")
        if section["annotations"]:
            body.append(
                "<h3>Annotated originals</h3><p>Locators are instructor-supplied and not independently verified.</p><ul>"  # noqa: E501
            )
            for a in section["annotations"]:
                body.append(
                    f"<li><strong>{escape(a['artifact_id'])}</strong><p>{escape(a['note'])}</p>"
                )
                if a["locator"]:
                    body.append(
                        f"<p>Locator: {escape(a['locator']['kind'])} {escape(a['locator']['value'])}</p>"  # noqa: E501
                    )
                body.append(f"<small>SHA256 {escape(a['sha256'])}</small>")
                if a["artifact_id"] in attached:
                    body.append(
                        f"<p><a href='{escape(attached[a['artifact_id']])}'>Open explicitly included original bytes</a></p>"  # noqa: E501
                    )
                else:
                    body.append("<p>Original bytes were not selected for this package.</p>")
                body.append("</li>")
            body.append("</ul>")
        body.append("</section>")
    body.append("<details><summary>Source and version pins</summary>")
    for label, value in (
        ("Release", manifest["release_id"]),
        ("Release SHA256", manifest["release_sha256"]),
        ("Key manifest SHA256", document["key_manifest_sha256"]),
        ("Historical state SHA256", document["learner"]["state_sha256"]),
        ("Historical event SHA256", document["learner"]["event_sha256"]),
        ("Historical history SHA256", document["learner"]["history_sha256"]),
    ):
        body.append(f"<p>{escape(label)}: <code>{escape(value)}</code></p>")
    if document["predecessor"]:
        body.append(
            f"<p>Predecessor: {escape(document['predecessor']['release_id'])}, SHA256 {escape(document['predecessor']['release_sha256'])}</p>"  # noqa: E501
        )
    for source in document["source_references"]:
        body.append(
            f"<h3>Original {escape(source['artifact_id'])}</h3><p>{escape(source['status'])}</p>"
        )  # noqa: E501
        if source["native"]:
            body.append("<dl>")
            for key, value in source["native"].items():
                body.append(f"<dt>{escape(key)}</dt><dd>{escape(value)}</dd>")
            body.append("</dl>")
    body.append("</details></body></html>")
    files["debrief.html"] = "".join(body).encode()
    files["manifest.json"] = canonical(manifest).encode()
    members = [
        {"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted(files.items())
    ]
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            archive.writestr(info, data)
    result = stream.getvalue()
    require(len(result) <= 20 * 1024 * 1024, "Portable package limit")
    return result, members


class DebriefMixin:
    def _debrief_snapshot(self, instructor, eid):
        key = self._key(instructor, eid)
        selected = deepcopy(self.bindings[eid])
        snapshot = verify_snapshot(selected["path"], expected_manifest_sha256=key)
        require(self._key(instructor, eid) == key, "Key changed", 409)
        return key, snapshot

    def debrief_options(self, instructor, eid):
        options = self.options(instructor, eid)
        key, snapshot = self._debrief_snapshot(instructor, eid)
        state = self.engine.store.get(instructor, eid)
        rows = {r["id"]: r for r in state.get("artifacts", [])}
        options["artifacts"] = [
            {
                "id": r["id"],
                "title": r["name"],
                "sha256": r["sha256"],
                "bytes": rows[r["id"]]["bytes"],
            }
            for r in options["artifacts"]
        ]
        authored = snapshot["authored"]
        require(
            len(authored["issues"]) <= 2000 and len(authored["expectations"]) <= 2000,
            "Debrief options limit",
        )
        options.update(
            key_manifest_sha256=key,
            learner_revision_range={"minimum": 0, "maximum": options["revision"]},
            issues=[
                {"id": i["id"], "title": i.get("title", i["id"]), "control_ids": i["control_ids"]}
                for i in authored["issues"]
            ],
            expectations=[
                {"id": i["id"], "title": i.get("title", i["id"]), "issue_ids": i["issue_ids"]}
                for i in authored["expectations"]
            ],
        )
        require(
            self.engine.store.get(instructor, eid)["revision"] == options["revision"],
            "Options changed",
            409,
        )
        return options

    def _debrief_check(self, state, content, verify_bytes=True, row_index=None):
        document = validate_document(content["document"])
        require(
            self._source_references(state, document["sections"]) == document["source_references"],
            "Recorded source identity changed",
            409,
        )
        seen = set()
        total = 0
        for section in document["sections"]:
            for a in section["annotations"]:
                pointer = {"kind": "artifact", "id": a["artifact_id"], "sha256": a["sha256"]}
                self._pointers(state, [pointer], verify_bytes=verify_bytes, row_index=row_index)
                if a["artifact_id"] not in seen:
                    seen.add(a["artifact_id"])
                    row = next(r for r in state["artifacts"] if r["id"] == a["artifact_id"])
                    total += row["bytes"] if a["attach"] else 0
        require(len(seen) <= 8 and total <= MAX_TOTAL, "Selected original quota")

    @staticmethod
    def _source_references(state, sections):
        rows = {r["id"]: r for r in state.get("artifacts", [])}
        result, seen = [], set()
        for section in sections:
            for a in section["annotations"]:
                if a["artifact_id"] in seen:
                    continue
                seen.add(a["artifact_id"])
                row = rows.get(a["artifact_id"], {})
                source = row.get("source", {})
                receipt = source.get("receipt", {})
                native = receipt.get("source", {})
                selected = {
                    k: deepcopy(native[k])
                    for k in (
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "sha256",
                        "source_store_id",
                        "source_system_alias",
                        "registry_sha256",
                        "portfolio_qualification",
                    )
                    if k in native
                }  # noqa: E501
                valid = (
                    all(
                        isinstance(selected.get(k), str) and selected[k]
                        for k in ("company", "branch", "system", "record", "sha256")
                    )
                    and type(selected.get("version")) is int
                    and selected["version"] > 0
                    and selected["sha256"] == a["sha256"]
                )  # noqa: E501
                result.append(
                    {
                        "artifact_id": a["artifact_id"],
                        "artifact_sha256": a["sha256"],
                        "status": "RECORDED_EXACT_NATIVE_IDENTITY" if valid else "UNRECORDED",
                        "native": selected if valid else None,
                    }
                )  # noqa: E501
        return result

    def debrief_preview(self, instructor, eid, payload):
        from .instructor_releases import basis

        fields(
            payload,
            (
                "recipient_id",
                "expected_revision",
                "learner_revision",
                "title",
                "sections",
                "predecessor_release_id",
            ),
        )
        p = json.loads(canonical(payload))
        state = self._state(instructor, p["recipient_id"], eid)
        require(
            type(p["expected_revision"]) is int and state["revision"] == p["expected_revision"],
            "Preview revision changed",
            409,
        )
        require(
            type(p["learner_revision"]) is int and 0 <= p["learner_revision"] <= state["revision"],
            "Explicit historical revision required",
        )
        text(p["title"], 200)
        key, snapshot = self._debrief_snapshot(instructor, eid)
        bound = snapshot["engagement"]
        history = inspect_history(
            self.engine.store, instructor, eid, revisions=[bound["revision"], p["learner_revision"]]
        )
        require(
            history["prefix_sha256"].get(bound["revision"]) == bound["history_sha256"]
            and digest(history["selected"][bound["revision"]]["state"]) == bound["state_sha256"],
            "Bound history differs",
            409,
        )
        selected = history["selected"][p["learner_revision"]]
        require(
            selected["state"].get("scope") == state.get("scope"),
            "Historical learner scope differs",
            409,
        )
        require(
            isinstance(p["sections"], list) and 1 <= len(p["sections"]) <= 10,
            "One to ten sections required",
        )
        issues = {r["id"]: r for r in snapshot["authored"]["issues"]}
        expectations = {r["id"]: r for r in snapshot["authored"]["expectations"]}
        sections = []
        for s in p["sections"]:
            fields(
                s,
                (
                    "issue_ids",
                    "expectation_ids",
                    "explanation",
                    "limitations",
                    "prompts",
                    "annotations",
                ),
            )
            chosen = ids(s["issue_ids"])
            expect = ids(s["expectation_ids"])
            require(
                chosen
                and all(i in issues for i in chosen)
                and all(i in expectations for i in expect),
                "Selected Key item unavailable",
            )
            require(
                all(set(expectations[i]["issue_ids"]) <= set(chosen) for i in expect),
                "Expectation requires explicitly selected issues",
            )
            require(
                isinstance(s["annotations"], list) and len(s["annotations"]) <= 8,
                "Annotation limit",
            )
            for a in s["annotations"]:
                annotation(a)
                fields(a, ("artifact_id", "sha256", "note", "locator", "attach"))
                text(a["note"], 1000)
                require(type(a["attach"]) is bool, "Explicit attachment selection required")
                if a["locator"] is not None:
                    fields(a["locator"], ("kind", "value"))
                    require(
                        a["locator"]["kind"] in {"PAGE", "LINE", "CELL", "TIME", "OTHER"},
                        "Typed locator required",
                    )
                    text(a["locator"]["value"], 200)
            sections.append(
                {
                    "issues": [
                        {
                            k: deepcopy(issues[i][k])
                            for k in ("id", "control_ids", "claim", "uncertainty")
                            if k in issues[i]
                        }
                        for i in chosen
                    ],
                    "expectations": [
                        {
                            k: deepcopy(expectations[i][k])
                            for k in ("id", "issue_ids", "procedure", "acceptable_alternatives")
                            if k in expectations[i]
                        }
                        for i in expect
                    ],
                    **{k: s[k] for k in ("explanation", "limitations", "prompts", "annotations")},
                }
            )
        document = {
            "schema": SCHEMA,
            "title": p["title"],
            "version": 1,
            "predecessor": None,
            "key_manifest_sha256": key,
            "learner": {
                "actor_id": p["recipient_id"],
                "simulated_at": selected["state"].get("simulated_at"),
                "revision": selected["revision"],
                "state_sha256": digest(selected["state"]),
                "event_sha256": selected["hash"],
                "history_sha256": history["prefix_sha256"][selected["revision"]],
                "qualification": "SHARED_STATE_NOT_SUBMISSION_KEY_SUPPORT_MAY_POSTDATE_LEARNER_REVISION",  # noqa: E501
            },
            "source_references": self._source_references(state, sections),
            "sections": sections,
            "qualification": "INSTRUCTOR_AUTHORED_UNVALIDATED_LOCATORS_NOT_VERIFIED_NO_GRADING",
        }
        with self._db() as db:
            if p["predecessor_release_id"] is not None:
                prior = self._get(db, p["predecessor_release_id"], "RELEASE")
                require(
                    (
                        prior["engagement_id"],
                        prior["instructor_id"],
                        prior["recipient_id"],
                        prior["content"]["stage"],
                    )
                    == (eid, instructor, p["recipient_id"], "EXPLANATION"),
                    "Correction predecessor differs",
                    403,
                )
                document["version"] = prior["content"]["document"]["version"] + 1
                document["predecessor"] = {
                    "release_id": prior["id"],
                    "release_sha256": digest(prior),
                }
            validate_document(document)
            value = {
                "id": identifier("PREVIEW"),
                "engagement_id": eid,
                "instructor_id": instructor,
                "recipient_id": p["recipient_id"],
                "revision": state["revision"],
                "state_sha256": digest(state),
                "context_sha256": digest(basis(state)),
                "key_manifest_sha256": key,
                "expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
                "content": {
                    "stage": "EXPLANATION",
                    "text": p["title"],
                    "pointers": [],
                    "document": document,
                    "authorship": "INSTRUCTOR_AUTHORED_ASSISTANCE_NOT_VERIFIED_FINDING",
                    "professional_acceptance": "NOT_ASSERTED",
                },
            }
            self._check(value, exact=True)
            self._put(db, "PREVIEW", value)
        return {"preview": value, "preview_sha256": digest(value), "delivered": False}

    def _export_value(self, db, actor, eid, rid):
        value = self._get(db, rid, "RELEASE")
        require(
            value["engagement_id"] == eid
            and actor in {value["instructor_id"], value["recipient_id"]},
            "Export unavailable",
            403,
        )
        require(
            value["content"]["stage"] == "EXPLANATION", "Only selected debrief exports supported"
        )
        self._check(value)
        require("REVOKED" not in self._actions(db, rid), "Release revoked", 403)
        return value

    def _package(self, value):
        state = self._state(value["instructor_id"], value["recipient_id"], value["engagement_id"])
        attachments, seen = [], set()
        for s in value["content"]["document"]["sections"]:
            for a in s["annotations"]:
                if a["attach"] and a["artifact_id"] not in seen:
                    seen.add(a["artifact_id"])
                    row = next(r for r in state["artifacts"] if r["id"] == a["artifact_id"])
                    attachments.append((a, self.engine.artifacts.read(row)))
        return package(value, attachments)

    def export_preview(self, actor, eid, release_id, payload):
        fields(payload, ("release_sha256",))
        with self._db() as db:
            value = self._export_value(db, actor, eid, release_id)
            require(digest(value) == payload["release_sha256"], "Release pin differs", 409)
            data, members = self._package(value)
            preview = {
                "id": identifier("EXPORTPREVIEW"),
                "actor_id": actor,
                "engagement_id": eid,
                "current_state_sha256": digest(
                    self._state(value["instructor_id"], value["recipient_id"], eid)
                ),
                "release_id": release_id,
                "release_sha256": digest(value),
                "filename": "selected-debrief.zip",
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "members": members,
                "expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
            }
            self._export_value(db, actor, eid, release_id)
            validate_export_preview(preview)
            self._put(db, "EXPORT_PREVIEW", preview)
        return {"preview": preview, "preview_sha256": digest(preview), "exported": False}

    def export_confirm(self, actor, eid, release_id, payload):
        fields(payload, ("preview_id", "preview_sha256", "command_id"))
        with self._db() as db:
            preview = self._get(db, payload["preview_id"], "EXPORT_PREVIEW")
            require(
                (preview["actor_id"], preview["engagement_id"], preview["release_id"])
                == (actor, eid, release_id)
                and digest(preview) == payload["preview_sha256"],
                "Export preview unavailable",
                403,
            )
            value = self._export_value(db, actor, eid, release_id)
            require(
                digest(self._state(value["instructor_id"], value["recipient_id"], eid))
                == preview["current_state_sha256"],
                "Export context changed",
                409,
            )
            replay = self._replay(db, actor, eid, payload)
            if not replay:
                require(
                    datetime.now(UTC) < datetime.fromisoformat(preview["expires_at"]),
                    "Export preview expired",
                    409,
                )
            data, members = self._package(value)
            require(
                digest(value) == preview["release_sha256"]
                and hashlib.sha256(data).hexdigest() == preview["sha256"]
                and len(data) == preview["bytes"]
                and members == preview["members"],
                "Export bytes changed",
                409,
            )
            self._export_value(db, actor, eid, release_id)
            result = {
                "release_id": release_id,
                "filename": preview["filename"],
                "sha256": preview["sha256"],
                "byte_count": len(data),
                "exported": True,
            }
            if not replay:
                self._event(
                    db,
                    "EXPORTED",
                    release_id,
                    actor,
                    {"preview_id": preview["id"], "sha256": preview["sha256"], "bytes": len(data)},
                )
                self._receipt(db, actor, eid, payload, result)
            else:
                require(replay == result, "Export replay differs", 409)
            self._export_value(db, actor, eid, release_id)
            require(
                digest(self._state(value["instructor_id"], value["recipient_id"], eid))
                == preview["current_state_sha256"],
                "Export context changed",
                409,
            )
            return {**result, "bytes": data}
