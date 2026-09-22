"""Private opt-in administrative guidance from authorized recorded work only."""

import copy
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .audit_readiness import REFERENCE_COLLECTIONS, summarize
from .inference import _json
from .personal_views import PersonalViews, _reference
from .store import DomainError, canonical, digest
from .workspace_context import _basis, _resolve

FORMAT = "PRIVATE_WORK_GUIDANCE_ARCHIVE_V1"
MAX_EVENTS = 512
MAX_BYTES = 64 * 1024 * 1024
MAX_EVENT_BYTES = 1024 * 1024
MAX_RECORDS = 20000
MAX_CANDIDATES = 64
RULES = {
    "NO_ISSUED_REQUEST": (
        "Inspect the recorded request route",
        "No issued request is recorded for this control. This does not establish "
        "missing company evidence.",
    ),
    "OUTSTANDING_RESPONSE": (
        "Inspect the outstanding request",
        "The request has a recorded open response status. Inspect its history "
        "before deciding whether to follow up.",
    ),
    "RETAINED_ARTIFACT_WITHOUT_WORKPAPER_LINK": (
        "Inspect the retained original",
        "This original has no recorded workpaper link for the control. Relevance "
        "and testing support still require your judgment.",
    ),
    "PROVISIONAL_POPULATION": (
        "Inspect population review status",
        "The population is recorded as provisional. Its status does not establish "
        "completeness or an adverse conclusion.",
    ),
    "NO_CURRENT_DISTINCT_CONTRIBUTOR_REVIEW_RECORD": (
        "Inspect the review record",
        "No current review by a distinct recorded contributor is linked. Identity "
        "difference alone does not establish professional independence.",
    ),
    "RECORDED_SOURCE_OR_ARTIFACT_WARNING": (
        "Inspect the recorded source warning",
        "A source or artifact warning is recorded. Inspect its exact context; no "
        "new source discovery was performed.",
    ),
    "WORKPAPER_REFERENCES_MISSING_ARTIFACT": (
        "Inspect the unsupported artifact link",
        "A workpaper refers to an artifact absent from this authorized projection. "
        "This is not proof that the company record does not exist.",
    ),
}
EVENT_FIELDS = {
    "actor",
    "engagement",
    "version",
    "action",
    "recorded_at",
    "engagement_revision",
    "basis_sha256",
    "previous_sha256",
    "command_id",
    "request",
    "request_sha256",
    "data",
}


def require(value, message, *, code="INVALID_WORK_GUIDANCE", status=400):
    if not value:
        raise DomainError(message, code=code, status=status)


def text(value, maximum=2000):
    require(
        isinstance(value, str) and 0 < len(value.strip()) <= maximum,
        "Explicit bounded text required",
    )
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise DomainError("Valid Unicode required") from exc
    return value


def integer(value):
    require(type(value) is int and value >= 0, "Exact nonnegative integer required")


def sha(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def freeze(value):
    try:
        return _json(canonical(value))
    except (ValueError, TypeError, RecursionError) as exc:
        raise DomainError("Strict finite guidance data required") from exc


def reference_pin(value):
    require(
        isinstance(value, dict) and set(value) == {"kind", "id", "version", "sha256"},
        "Exact guidance reference required",
    )
    require(
        value["kind"] in REFERENCE_COLLECTIONS and sha(value["sha256"]),
        "Typed guidance reference required",
    )
    text(value["id"], 256)
    require(
        value["version"] is None or (type(value["version"]) is int and value["version"] > 0),
        "Exact reference version required",
    )


def current_reference(state, kind, row, version):
    if kind in ("request", "review"):
        control = row.get("control_id")
        if kind == "review" and row.get("workpaper_id"):
            workpapers = [w for w in state.get("workpapers", []) if w["id"] == row["workpaper_id"]]
            require(len(workpapers) == 1, "Reviewed workpaper unavailable")
            require(
                not control or control == workpapers[0].get("control_id"),
                "Review and workpaper controls differ",
            )
            control = workpapers[0].get("control_id")
        require(
            not control or control in {c["id"] for c in state["controls"]},
            "Reference control outside current scope",
        )
        boundary = row.get("boundary_id")
        require(
            not boundary or boundary in state["scope"].get("boundaries", []),
            "Reference boundary outside current scope",
        )
        reference = {
            "kind": kind,
            "id": row["id"],
            "version": row.get("version"),
            "sha256": digest(row),
        }
        reference_pin(reference)
        return reference
    resolved = _resolve(state, kind, row["id"], version)[0]
    _reference(state, resolved)
    return resolved


def annotate_decisions(result, events, basis, revision):
    decisions = {
        event["data"]["candidate_sha256"]: event["data"]
        for event in events
        if event["action"] == "DECIDE"
        and event["basis_sha256"] == basis
        and event["engagement_revision"] == revision
    }
    for candidate in result.get("candidates", []):
        if candidate["sha256"] in decisions:
            candidate["decision"] = copy.deepcopy(decisions[candidate["sha256"]])
    if "decision" in result:
        result["decision"] = copy.deepcopy(
            decisions.get(result["decision"]["candidate_sha256"], result["decision"])
        )


def _candidate_body(value):
    return {k: v for k, v in value.items() if k not in ("id", "sha256", "decision")}


def validate_archive(value):
    """Validate an inert history archive. No active-store import API exists."""
    value = freeze(value)
    require(
        isinstance(value, dict) and set(value) == {"schema", "captured_at", "restoration", "rows"},
        "Exact guidance archive required",
    )
    require(
        value["schema"] == FORMAT and value["restoration"] == "INERT_ONLY_NO_ACTIVE_REHYDRATION",
        "Inert guidance archive required",
    )
    text(value["captured_at"], 100)
    rows = value["rows"]
    require(isinstance(rows, list) and len(rows) <= 10000, "Guidance archive row bound exceeded")
    require(len(canonical(value).encode()) <= MAX_BYTES, "Guidance archive byte bound exceeded")
    chains = {}
    commands = set()
    for row in rows:
        require(
            isinstance(row, dict)
            and set(row) == {"actor", "engagement", "version", "command_id", "body", "sha256"},
            "Exact guidance row required",
        )
        text(row["actor"], 256)
        text(row["engagement"], 256)
        text(row["command_id"], 128)
        integer(row["version"])
        require(row["version"] > 0, "Positive history version required")
        require(
            isinstance(row["body"], str)
            and len(row["body"].encode()) <= MAX_EVENT_BYTES
            and sha(row["sha256"])
            and digest(_json(row["body"])) == row["sha256"],
            "Guidance history digest differs",
        )
        body = _json(row["body"])
        require(
            isinstance(body, dict) and set(body) == EVENT_FIELDS,
            "Exact guidance history fields required",
        )
        require(
            all(body[k] == row[k] for k in ("actor", "engagement", "command_id"))
            and type(body["version"]) is int
            and body["version"] == row["version"],
            "Guidance row owner or version differs",
        )
        identity = (row["actor"], row["engagement"])
        prior = chains.get(identity, [])
        require(
            row["version"] == len(prior) + 1
            and row["version"] <= MAX_EVENTS + 1
            and body["previous_sha256"] == (prior[-1]["sha256"] if prior else ""),
            "Guidance history chain differs",
        )
        require((identity, row["command_id"]) not in commands, "Duplicate guidance command")
        commands.add((identity, row["command_id"]))
        integer(body["engagement_revision"])
        require(sha(body["basis_sha256"]), "Guidance basis pin required")
        text(body["recorded_at"], 100)
        request = body["request"]
        require(
            isinstance(request, dict) and digest(request) == body["request_sha256"],
            "Guidance command digest differs",
        )
        action = body["action"]
        data = body["data"]
        require(
            action in ("OPT_IN", "REVEAL", "DECIDE") and request.get("action") == action,
            "Guidance action differs",
        )
        require(isinstance(data, dict), "Typed guidance data required")
        if action != "OPT_IN":
            preference = next(
                (event["body"] for event in reversed(prior) if event["body"]["action"] == "OPT_IN"),
                None,
            )
            require(
                preference is not None
                and preference["data"]["enabled"] is True
                and preference["basis_sha256"] == body["basis_sha256"],
                "Guidance history lacks current explicit opt-in",
            )
        if action == "OPT_IN":
            require(
                set(request)
                == {
                    "action",
                    "enabled",
                    "rationale",
                    "expected_version",
                    "expected_engagement_revision",
                },
                "Exact opt-in request required",
            )
            integer(request["expected_version"])
            require(request["expected_version"] == row["version"] - 1, "Opt-in version differs")
            require(
                type(request["enabled"]) is bool
                and canonical(data)
                == canonical({"enabled": request["enabled"], "rationale": request["rationale"]}),
                "Opt-in declaration differs",
            )
            text(request["rationale"])
        elif action == "REVEAL":
            require(
                set(request) == {"action", "context_ref", "expected_engagement_revision"}
                and set(data) == {"reveal_id", "candidates"},
                "Exact reveal required",
            )
            require(
                isinstance(data["candidates"], list) and len(data["candidates"]) <= MAX_CANDIDATES,
                "Candidate bound exceeded",
            )
            reference_pin(request["context_ref"])
            require(
                request["context_ref"]["kind"] == "control", "Control guidance context required"
            )
            text(data["reveal_id"], 128)
            require(
                len({c.get("id") for c in data["candidates"]}) == len(data["candidates"]),
                "Duplicate guidance candidate",
            )
            for candidate in data["candidates"]:
                require(
                    isinstance(candidate, dict)
                    and set(candidate)
                    == {
                        "id",
                        "sha256",
                        "code",
                        "title",
                        "reason",
                        "classification",
                        "context_ref",
                        "references",
                        "navigation",
                        "engagement_revision",
                        "basis_sha256",
                    },
                    "Exact candidate required",
                )
                integer(candidate["engagement_revision"])
                reference_pin(candidate["context_ref"])
                require(
                    isinstance(candidate["references"], list)
                    and len(candidate["references"]) <= 64,
                    "Bounded candidate references required",
                )
                for ref in candidate["references"]:
                    require(
                        isinstance(ref, dict) and set(ref) == {"kind", "id", "status", "reference"},
                        "Exact candidate reference wrapper required",
                    )
                    require(
                        ref["kind"] in REFERENCE_COLLECTIONS,
                        "Supported candidate reference required",
                    )
                    text(ref["id"], 256)
                    if ref["status"] == "CURRENT":
                        reference_pin(ref["reference"])
                        require(
                            ref["reference"]["kind"] == ref["kind"]
                            and ref["reference"]["id"] == ref["id"],
                            "Candidate reference identity differs",
                        )
                    else:
                        require(
                            ref["status"] == "UNAVAILABLE" and ref["reference"] is None,
                            "Unavailable reference must not navigate",
                        )
                require(
                    isinstance(candidate["navigation"], dict)
                    and set(candidate["navigation"]) == {"workspace"}
                    and candidate["navigation"]["workspace"]
                    in ("requests", "workpapers", "populations", "reviews", "artifacts"),
                    "Existing guidance workspace navigation required",
                )
                pin = digest(_candidate_body(candidate))
                require(
                    candidate["sha256"] == pin
                    and candidate["id"] == "GUIDE-" + pin[:32]
                    and candidate["code"] in RULES,
                    "Candidate integrity differs",
                )
                require(
                    candidate["context_ref"] == request["context_ref"]
                    and candidate["engagement_revision"] == body["engagement_revision"]
                    and candidate["basis_sha256"] == body["basis_sha256"],
                    "Candidate context differs",
                )
                require(
                    (candidate["title"], candidate["reason"]) == RULES[candidate["code"]]
                    and candidate["classification"] == "ADMINISTRATIVE_OBSERVATION",
                    "Candidate rule differs",
                )
        else:
            require(
                set(request)
                == {
                    "action",
                    "candidate_id",
                    "candidate_sha256",
                    "decision",
                    "rationale",
                    "expected_engagement_revision",
                },
                "Exact decision request required",
            )
            require(
                request["decision"] in ("REVIEW", "DISMISS") and sha(request["candidate_sha256"]),
                "Typed decision required",
            )
            text(request["rationale"])
            require(
                data
                == {
                    "candidate_id": request["candidate_id"],
                    "candidate_sha256": request["candidate_sha256"],
                    "action": request["decision"],
                    "rationale": request["rationale"],
                },
                "Decision content differs",
            )
            candidates = [
                c
                for event in prior
                if event["body"]["action"] == "REVEAL"
                and event["body"]["basis_sha256"] == body["basis_sha256"]
                and event["body"]["engagement_revision"] == body["engagement_revision"]
                for c in event["body"]["data"]["candidates"]
            ]
            require(
                any(
                    c["id"] == request["candidate_id"]
                    and c["sha256"] == request["candidate_sha256"]
                    for c in candidates
                ),
                "Decision has no exact prior disclosed candidate",
            )
        integer(request["expected_engagement_revision"])
        require(
            request["expected_engagement_revision"] == body["engagement_revision"],
            "Recorded engagement revision differs",
        )
        if row["version"] == MAX_EVENTS + 1:
            require(action == "OPT_IN" and data["enabled"] is False, "Reserved final opt-out only")
        chains[identity] = [*prior, {"body": body, "sha256": row["sha256"]}]
    return value


class WorkGuidance:
    def __init__(self, private_root, engine):
        self.root = Path(private_root).absolute()
        self.engine = engine
        PersonalViews._private(self.root, True)
        self.path = self.root / "work-guidance.sqlite3"
        if self.path.exists():
            PersonalViews._private(self.path)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self._db() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS events(
                actor TEXT,engagement TEXT,version INTEGER,command_id TEXT,body TEXT,sha256 TEXT,
                PRIMARY KEY(actor,engagement,version),UNIQUE(actor,engagement,command_id));
                CREATE TRIGGER IF NOT EXISTS guidance_no_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT,'Immutable guidance history'); END;
                CREATE TRIGGER IF NOT EXISTS guidance_no_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT,'Immutable guidance history'); END;""")

    @contextmanager
    def _db(self):
        root_before = PersonalViews._private(self.root, True)
        before = PersonalViews._private(self.path)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
                require(
                    PersonalViews._private(self.root, True) == root_before, "Guidance root changed"
                )
                require(
                    PersonalViews._private(self.path) == before, "Guidance storage identity changed"
                )
        finally:
            db.close()

    def _state(self, actor, eid):
        membership = self.engine.store.membership(actor, eid)
        require(
            membership in ("learn", "review", "instruct"),
            "Current engagement access required",
            status=403,
        )
        raw = self.engine.store.get(actor, eid)
        config = raw.get("configuration", {})
        allowed = config.get("work_guidance_allowed") is True
        policy_version = config.get("work_guidance_policy_revision", 0)
        integer(policy_version)
        state = self.engine.get(actor, eid)
        require(
            state["id"] == eid and state["revision"] == raw["revision"],
            "Engagement changed during guidance read",
            status=409,
        )
        basis = digest(
            {
                **_basis(state),
                "membership": membership,
                "policy_allowed": allowed,
                "policy_version": policy_version,
                "simulated_at": state.get("simulated_at"),
                "controls": state.get("controls", []),
                "retained_sources": state.get("artifacts", []),
            }
        )
        return state, basis, allowed, policy_version

    def _recheck(self, actor, eid, state, basis):
        current, pin, _, _ = self._state(actor, eid)
        require(
            current["revision"] == state["revision"] and pin == basis,
            "Guidance context changed; reload and opt in when required",
            status=409,
            code="GUIDANCE_CONTEXT_CHANGED",
        )

    def _history(self, db, actor, eid):
        count, size = db.execute(
            "SELECT COUNT(*),COALESCE(SUM(length(CAST(body AS BLOB))),0) FROM "
            "events WHERE actor=? AND engagement=?",
            (actor, eid),
        ).fetchone()
        require(count <= MAX_EVENTS + 1 and size <= MAX_BYTES, "Guidance history bound exceeded")
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM events WHERE actor=? AND engagement=? ORDER BY version", (actor, eid)
            )
        ]
        validate_archive(
            {
                "schema": FORMAT,
                "captured_at": "local-read",
                "restoration": "INERT_ONLY_NO_ACTIVE_REHYDRATION",
                "rows": rows,
            }
        )
        return [_json(r["body"]) for r in rows]

    def _view(self, state, basis, allowed, policy_version, events):
        pref = next((e for e in reversed(events) if e["action"] == "OPT_IN"), None)
        current = pref is not None and pref["basis_sha256"] == basis
        enabled = bool(allowed and current and pref["data"]["enabled"])
        value = {
            "engagement_id": state["id"],
            "current_engagement_revision": state["revision"],
            "version": len(events),
            "policy_allowed": allowed,
            "policy_version": policy_version,
            "opted_in": enabled,
            "personal_content_visible": bool(allowed and current),
            "contexts": [],
            "status": "POLICY_DISABLED"
            if not allowed
            else "CONTEXT_CHANGED"
            if pref and not current
            else "AVAILABLE"
            if enabled
            else "OPT_IN_REQUIRED",
            "backup_status": "INERT_ARCHIVE_ONLY",
        }
        if allowed and current:
            value["preference"] = copy.deepcopy(pref["data"])
        if enabled:
            controls = state.get("controls", [])
            if not isinstance(controls, list) or len(controls) > 256:
                value["status"] = "INPUT_LIMIT_EXCEEDED"
                return value
            require(
                len({c["id"] for c in controls}) == len(controls),
                "Ambiguous guidance control identity",
            )
            value["contexts"] = [
                {
                    "reference": _resolve(state, "control", c["id"], c.get("version"))[0],
                    "title": c.get("title", c["id"]),
                }
                for c in controls
            ]
        return value

    def status(self, actor, eid):
        state, basis, allowed, policy_version = self._state(actor, eid)
        with self._db() as db:
            db.execute("BEGIN")
            events = self._history(db, actor, eid)
            value = self._view(state, basis, allowed, policy_version, events)
            self._recheck(actor, eid, state, basis)
            return value

    def _candidates(self, state, basis, context_ref):
        require(
            isinstance(context_ref, dict) and context_ref.get("kind") == "control",
            "Exact control context required",
        )
        _reference(state, context_ref)
        require(
            all(isinstance(state.get(name, []), list) for name in REFERENCE_COLLECTIONS.values()),
            "Typed guidance input collections required",
        )
        total = sum(len(state.get(name, [])) for name in REFERENCE_COLLECTIONS.values())
        require(
            total <= MAX_RECORDS,
            "Guidance input collection bound exceeded",
            code="GUIDANCE_INPUT_LIMIT",
        )
        report = summarize(state)
        controls = [r for r in report["controls"] if r["control"]["id"] == context_ref["id"]]
        require(len(controls) == 1, "Guidance control context unavailable", status=409)
        reasons = controls[0]["reasons"]
        require(
            len(reasons) <= MAX_CANDIDATES, "Candidate bound exceeded", code="GUIDANCE_INPUT_LIMIT"
        )
        candidates = []
        for reason in reasons:
            require(
                reason["code"] in RULES and len(reason["references"]) <= 64,
                "Guidance reason or reference bound exceeded",
                code="GUIDANCE_INPUT_LIMIT",
            )
            refs = []
            for ref in reason["references"]:
                kind, row_id = ref["kind"], ref["id"]
                resolved = None
                rows = [r for r in state.get(REFERENCE_COLLECTIONS[kind], []) if r["id"] == row_id]
                if len(rows) == 1:
                    row = rows[0]
                    version = ref.get("version")
                    if kind == "workpaper":
                        versions = row.get("versions", [])
                        require(
                            all(
                                type(v.get("version")) is int and v["version"] > 0 for v in versions
                            ),
                            "Typed workpaper versions required",
                        )
                        if versions:
                            version = max(v["version"] for v in versions)
                    try:
                        resolved = current_reference(state, kind, row, version)
                    except DomainError:
                        resolved = None
                refs.append(
                    {
                        "kind": kind,
                        "id": row_id,
                        "status": "CURRENT" if resolved else "UNAVAILABLE",
                        "reference": resolved,
                    }
                )
            title, explanation = RULES[reason["code"]]
            candidate = {
                "code": reason["code"],
                "title": title,
                "reason": explanation,
                "classification": "ADMINISTRATIVE_OBSERVATION",
                "context_ref": copy.deepcopy(context_ref),
                "references": refs,
                "navigation": reason["navigation"],
                "engagement_revision": state["revision"],
                "basis_sha256": basis,
            }
            pin = digest(candidate)
            candidates.append({"id": "GUIDE-" + pin[:32], "sha256": pin, **candidate})
        return candidates

    def _write(self, actor, eid, request, command_id):
        request = freeze(request)
        text(command_id, 128)
        integer(request["expected_engagement_revision"])
        state, basis, allowed, policy_version = self._state(actor, eid)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            events = self._history(db, actor, eid)
            prior = next((e for e in events if e["command_id"] == command_id), None)
            if prior:
                require(
                    prior["request_sha256"] == digest(request),
                    "Guidance command ID already used",
                    status=409,
                )
                result = self._view(state, basis, allowed, policy_version, events)
                if (
                    result["opted_in"]
                    and prior["basis_sha256"] == basis
                    and prior["engagement_revision"] == state["revision"]
                ):
                    result.update(
                        copy.deepcopy(prior["data"])
                        if prior["action"] == "REVEAL"
                        else {"decision": copy.deepcopy(prior["data"])}
                        if prior["action"] == "DECIDE"
                        else {}
                    )
                annotate_decisions(result, events, basis, state["revision"])
                self._recheck(actor, eid, state, basis)
                return result
            require(
                state["revision"] == request["expected_engagement_revision"],
                "Engagement changed; reload guidance",
                status=409,
            )
            view = self._view(state, basis, allowed, policy_version, events)
            action = request["action"]
            if action == "OPT_IN":
                integer(request["expected_version"])
                require(
                    request["expected_version"] == len(events),
                    "Guidance preference version changed",
                    status=409,
                )
                require(type(request["enabled"]) is bool, "Explicit boolean opt-in required")
                text(request["rationale"])
                require(
                    not request["enabled"] or allowed,
                    "Instructor policy does not permit guidance",
                    status=403,
                )
                data = {"enabled": request["enabled"], "rationale": request["rationale"]}
            else:
                require(
                    view["status"] == "AVAILABLE",
                    "Guidance requires current policy and explicit personal opt-in",
                    status=403,
                )
                if action == "REVEAL":
                    data = {
                        "reveal_id": "REVEAL-" + digest([actor, eid, command_id])[:32],
                        "candidates": self._candidates(state, basis, request["context_ref"]),
                    }
                else:
                    require(
                        action == "DECIDE" and request["decision"] in ("REVIEW", "DISMISS"),
                        "Supported guidance decision required",
                    )
                    text(request["rationale"])
                    matching = [
                        c
                        for e in events
                        if e["action"] == "REVEAL"
                        and e["basis_sha256"] == basis
                        and e["engagement_revision"] == state["revision"]
                        for c in e["data"]["candidates"]
                        if c["id"] == request["candidate_id"]
                        and c["sha256"] == request["candidate_sha256"]
                    ]
                    require(matching, "Exact previously revealed candidate required", status=409)
                    current = self._candidates(state, basis, matching[-1]["context_ref"])
                    require(
                        any(
                            c["sha256"] == request["candidate_sha256"]
                            and c["id"] == request["candidate_id"]
                            for c in current
                        ),
                        "Guidance candidate changed",
                        status=409,
                    )
                    data = {
                        "candidate_id": request["candidate_id"],
                        "candidate_sha256": request["candidate_sha256"],
                        "action": request["decision"],
                        "rationale": request["rationale"],
                    }
            allow_last = action == "OPT_IN" and request["enabled"] is False
            require(
                len(events) < MAX_EVENTS + (1 if allow_last else 0),
                "Guidance history limit reached",
                status=409,
            )
            event = {
                "actor": actor,
                "engagement": eid,
                "version": len(events) + 1,
                "action": action,
                "recorded_at": datetime.now(UTC).isoformat(),
                "engagement_revision": state["revision"],
                "basis_sha256": basis,
                "previous_sha256": digest(events[-1]) if events else "",
                "command_id": command_id,
                "request": request,
                "request_sha256": digest(request),
                "data": data,
            }
            encoded = canonical(event)
            require(len(encoded.encode()) <= MAX_EVENT_BYTES, "Guidance event byte bound exceeded")
            total = db.execute(
                "SELECT COALESCE(SUM(length(CAST(body AS BLOB))),0) FROM events"
            ).fetchone()[0]
            require(
                total + len(encoded.encode()) <= MAX_BYTES, "Guidance database byte bound exceeded"
            )
            self._recheck(actor, eid, state, basis)
            db.execute(
                "INSERT INTO events VALUES (?,?,?,?,?,?)",
                (actor, eid, event["version"], command_id, encoded, digest(event)),
            )
            self._recheck(actor, eid, state, basis)
            result = self._view(state, basis, allowed, policy_version, [*events, event])
            if action == "REVEAL":
                result.update(copy.deepcopy(data))
                decisions = {
                    e["data"]["candidate_sha256"]: e["data"]
                    for e in events
                    if e["action"] == "DECIDE"
                    and e["basis_sha256"] == basis
                    and e["engagement_revision"] == state["revision"]
                }
                for candidate in result["candidates"]:
                    if candidate["sha256"] in decisions:
                        candidate["decision"] = copy.deepcopy(decisions[candidate["sha256"]])
            elif action == "DECIDE":
                result["decision"] = copy.deepcopy(data)
            annotate_decisions(result, [*events, event], basis, state["revision"])
            return result

    def opt_in(
        self,
        actor,
        eid,
        enabled,
        rationale,
        *,
        expected_version,
        expected_engagement_revision,
        command_id,
    ):
        return self._write(
            actor,
            eid,
            {
                "action": "OPT_IN",
                "enabled": enabled,
                "rationale": rationale,
                "expected_version": expected_version,
                "expected_engagement_revision": expected_engagement_revision,
            },
            command_id,
        )

    def reveal(self, actor, eid, context_ref, *, expected_engagement_revision, command_id):
        return self._write(
            actor,
            eid,
            {
                "action": "REVEAL",
                "context_ref": context_ref,
                "expected_engagement_revision": expected_engagement_revision,
            },
            command_id,
        )

    def decide(
        self,
        actor,
        eid,
        candidate_id,
        candidate_sha256,
        action,
        rationale,
        *,
        expected_engagement_revision,
        command_id,
    ):
        return self._write(
            actor,
            eid,
            {
                "action": "DECIDE",
                "candidate_id": candidate_id,
                "candidate_sha256": candidate_sha256,
                "decision": action,
                "rationale": rationale,
                "expected_engagement_revision": expected_engagement_revision,
            },
            command_id,
        )

    def snapshot(self):
        with self._db() as db:
            db.execute("BEGIN")
            size, count = db.execute(
                "SELECT COALESCE(SUM(length(CAST(body AS BLOB))),0),COUNT(*) FROM events"
            ).fetchone()
            require(size <= MAX_BYTES and count <= 10000, "Guidance archive bound exceeded")
            result = {
                "schema": FORMAT,
                "captured_at": datetime.now(UTC).isoformat(),
                "restoration": "INERT_ONLY_NO_ACTIVE_REHYDRATION",
                "rows": [
                    dict(r)
                    for r in db.execute("SELECT * FROM events ORDER BY actor,engagement,version")
                ],
            }
            return validate_archive(result)
