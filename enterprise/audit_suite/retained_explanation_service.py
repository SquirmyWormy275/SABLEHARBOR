"""Protected explanations on the existing retained company workroom service.

This local operator configuration adds the existing instructor views only.
It never changes company sources, audit membership, evidence or task results.
Explanations are authored inferences; they remain separate from learner inputs.
"""

from __future__ import annotations

import hashlib
import importlib
import re
from pathlib import Path

from .bound_instructor import load_bindings
from .company_store import _time
from .explanation_binding import verify_snapshot
from .fresh_sec003_procedure import require
from .history_inspection import inspect_history
from .persistent_company_service import RetainedWorkroom, absolute_path, pinned_json
from .source_library_audit import file_sha, quiescent_read
from .store import DomainError, digest

SCHEMA = "SH_RETAINED_COMPANY_EXPLANATION_SERVICE_CONFIG_V1"
MODULES = (
    "retained_explanation_service.py",
    "bound_instructor.py",
    "explanation_binding.py",
    "history_inspection.py",
    "portfolio_explanation.py",
    "instructor_comparison.py",
    "instructor_access.py",
    "instructor_key_views.py",
)


def configuration(workroom_path, workroom_sha256, bindings_path, bindings_sha256, *, repository):
    """Serialize supplied operator pins; this supplies no independent acceptance."""
    pinned_json(Path(workroom_path), workroom_sha256)
    pinned_json(Path(bindings_path), bindings_sha256)
    return {
        "schema": SCHEMA,
        "retained_workroom": {
            "path": str(Path(workroom_path).absolute()),
            "sha256": workroom_sha256,
        },
        "explanation_bindings": {
            "path": str(Path(bindings_path).absolute()),
            "sha256": bindings_sha256,
        },
        "code_pins": {
            name: file_sha(Path(repository) / "enterprise/audit_suite" / name) for name in MODULES
        },
    }


class ExplainedWorkroom:
    def __init__(self, config_path, expected_sha256, *, private_root, repository, **settings):
        self.repository = Path(repository).absolute()
        self.path = absolute_path(str(config_path))
        self.pin = expected_sha256
        self.config = pinned_json(self.path, self.pin)
        require(
            set(self.config) == {"schema", "retained_workroom", "explanation_bindings", "code_pins"}
            and self.config["schema"] == SCHEMA,
            "Exact retained explanation configuration required",
        )
        self.check_code()
        for key in ("retained_workroom", "explanation_bindings"):
            item = self.config[key]
            require(
                isinstance(item, dict) and set(item) == {"path", "sha256"},
                "Exact operator pins required",
            )
            absolute_path(item["path"])
        item = self.config["retained_workroom"]
        self.retained = RetainedWorkroom(
            Path(item["path"]),
            item["sha256"],
            private_root=private_root,
            repository=repository,
            **settings,
        )
        self.validate_explanation()

    def check_code(self):
        pins = self.config["code_pins"]
        require(
            isinstance(pins, dict) and set(pins) == set(MODULES),
            "Exact explanation module pins required",
        )
        for name, pin in pins.items():
            path = self.repository / "enterprise/audit_suite" / name
            module = importlib.import_module("enterprise.audit_suite." + name.removesuffix(".py"))
            require(
                not any(p.is_symlink() for p in [path, *path.parents])
                and Path(module.__file__).resolve() == path.resolve()
                and Path(module.__spec__.origin).resolve() == path.resolve()
                and file_sha(path) == pin,
                "Explanation code pin or loaded origin differs",
            )

    def validate_explanation(self):
        """Fresh exact history/source verification, never answer or grading inference."""
        require(
            pinned_json(self.path, self.pin) == self.config, "Explanation configuration changed"
        )
        self.check_code()
        item = self.config["explanation_bindings"]
        path = Path(item["path"])
        index = pinned_json(path, item["sha256"])
        retained = self.retained
        require(set(index) == {retained.engagement}, "Only this retained engagement may have a Key")
        bindings = load_bindings(path)
        binding = bindings[retained.engagement]
        snapshot = verify_snapshot(
            binding["path"], expected_manifest_sha256=binding["manifest_sha256"]
        )
        identities = retained.binding["identities"]
        require(
            snapshot["company_binding"] == retained.selected
            and snapshot["engagement"]["id"] == retained.engagement
            and snapshot["instructor_id"] == identities["operator"]
            and snapshot["audited_actor_id"] == identities["auditor"]
            and snapshot["source_operator_id"] == retained.binding["company_operator_id"],
            "Explanation workroom, company, branch or attributed actors differ",
        )
        revision = snapshot["engagement"]["revision"]
        require(type(revision) is int and revision >= 0, "Strict bound revision required")
        history = inspect_history(
            retained.engine.store, identities["operator"], retained.engagement, revisions=[revision]
        )
        require(revision in history["selected"], "Explanation revision does not exist here")
        state = history["selected"][revision]["state"]
        require(
            digest(state) == snapshot["engagement"]["state_sha256"]
            and history["prefix_sha256"][revision] == snapshot["engagement"]["history_sha256"]
            and state["scope"] == snapshot["engagement"]["scope"]
            and _time(state["simulated_at"]) == _time(snapshot["engagement"]["simulated_at"]),
            "Explanation history prefix, scope or clock differs",
        )
        seen = set()
        with quiescent_read(retained.world.store.path) as db:
            for source in snapshot["sources"]:
                version = source["version"]
                require(
                    type(version) is int and version > 0,
                    "Strict explanation native version required",
                )
                key = tuple(source[k] for k in ("company", "branch", "system", "record", "version"))
                require(
                    key not in seen
                    and key[:2] == (retained.selected["company"], retained.selected["branch"]),
                    "Distinct same-branch explanation originals required",
                )
                seen.add(key)
                row = db.execute(
                    "SELECT sha256,event_at,available_at,imported_at,content FROM versions "
                    "WHERE company=? AND branch=? AND system=? AND record=? AND version=?",
                    key,
                ).fetchone()
                require(
                    row is not None
                    and all(
                        source[k] == row[k]
                        for k in ("sha256", "event_at", "available_at", "imported_at")
                    ),
                    "Explanation native original or clocks differ",
                )
                raw = (binding["path"] / source["path"]).read_bytes()
                require(raw == row["content"], "Explanation bytes differ from company original")
                require(
                    _time(row["available_at"]) <= _time(snapshot["operator_source_as_of"]),
                    "Explanation exceeds its operator source clock",
                )
                expected_artifacts = [
                    artifact["id"]
                    for artifact in state["artifacts"]
                    if all(
                        artifact.get("source", {}).get("receipt", {}).get("source", {}).get(k)
                        == source[k]
                        for k in ("company", "branch", "system", "record", "version", "sha256")
                    )
                ]
                require(
                    source["retained_audit_artifact_ids"] == expected_artifacts,
                    "Explanation retained-copy references differ",
                )
        require(seen, "Actual native explanation originals required")
        return bindings

    def guard(self, request):
        retained = self.retained
        allowed = re.fullmatch(
            "/api/engagements/"
            + re.escape(retained.engagement)
            + r"/(instructor-binding|instructor-comparison|instructor-key-views)(/.*)?",
            request.url.path,
        )
        if allowed is None:
            retained.guard(request)
            return
        retained.check_pins()
        bearer = request.headers.get("authorization", "")
        if bearer:
            if not bearer.startswith("Bearer "):
                raise DomainError("Bearer credential required", status=401)
            actor = retained.engine.store.authenticate(bearer[7:])
        else:
            cookie_name = (
                "sh_audit_session_"
                + hashlib.sha256(
                    str(retained.engine.store.root.resolve()).encode("utf-8")
                ).hexdigest()[:32]
            )
            actor = retained.engine.store.session(request.cookies.get(cookie_name, ""))
        if retained.engine.store.membership(actor["id"], retained.engagement) != "instruct":
            raise DomainError("Instructor membership required", status=403)
        # A damaged private explanation must not stop ordinary learner fieldwork.
        self.validate_explanation()


def create_explained_app(private_root, config_path, expected_sha256, *, repository, **options):
    """Enable existing protected views without adding routes or company overrides."""
    from .service import create_app

    require(
        not set(options)
        & {
            "engine_factory",
            "request_guard",
            "company_root",
            "company_bindings",
            "company_registry",
            "company_profile",
            "instructor_key_root",
            "instructor_bindings",
            "enable_instructor_writeback",
            "company_rights_factory",
            "company_native_rights_factory",
            "program_pack",
            "corpus_root",
        },
        "Explanation service cannot combine authority or Key overrides",
    )
    explained = ExplainedWorkroom(
        config_path,
        expected_sha256,
        private_root=private_root,
        repository=repository,
        **{key: options[key] for key in ("inference_config", "voice_config") if key in options},
    )
    return create_app(
        private_root,
        repository=repository,
        engine_factory=lambda: explained.retained.engine,
        request_guard=explained.guard,
        instructor_bindings=Path(explained.config["explanation_bindings"]["path"]),
        enable_instructor_writeback=False,
        **options,
    )
