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
from .explanation_binding import _authored, verify_snapshot
from .fresh_sec003_procedure import require
from .history_integrity_reference import inspect_selected_integrity
from .persistent_company_journey import PersistentCompany
from .persistent_company_service import RetainedEngine, RetainedWorkroom, absolute_path, pinned_json
from .source_library_audit import file_sha, private_file, quiescent_read
from .store import DomainError, Store, digest

SCHEMA = "SH_RETAINED_COMPANY_EXPLANATION_SERVICE_CONFIG_V1"
ACTIVE_SCHEMA = "SH_RETAINED_COMPANY_EXPLANATION_SERVICE_CONFIG_V2"
REFERENCE_SCHEMA = "SH_RETAINED_COMPANY_EXPLANATION_SERVICE_CONFIG_V3"
MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024
MODULES = (
    "retained_explanation_service.py",
    "bound_instructor.py",
    "explanation_binding.py",
    "history_inspection.py",
    "portfolio_explanation.py",
    "instructor_comparison.py",
    "instructor_access.py",
    "instructor_key_views.py",
    "expectation_links.py",
)

# Exact local dependency closure for the manual writers and deferred Engine
# source/model commands. This pins code origins; it grants no outcome approval.
ACTIVE_MODULES = tuple(
    sorted(
        set(MODULES)
        | {
            "artifact_inspection.py",
            "artifacts.py",
            "background_jobs.py",
            "behavior_composition.py",
            "bound_instructor.py",
            "causal_composition.py",
            "change_volume.py",
            "clean.py",
            "company_collection.py",
            "company_consultation.py",
            "company_federation.py",
            "company_impact.py",
            "company_persona.py",
            "company_population.py",
            "company_population_collection.py",
            "company_source_census.py",
            "company_source_census_collection.py",
            "company_store.py",
            "composition.py",
            "configuration.py",
            "corpus.py",
            "custom.py",
            "deterministic_review.py",
            "encounters.py",
            "engine.py",
            "evidence_transform.py",
            "expectation_links.py",
            "explanation_binding.py",
            "generation.py",
            "history_export.py",
            "history_inspection.py",
            "history_locators.py",
            "inference.py",
            "instructor_access.py",
            "instructor_assessments.py",
            "instructor_comparison.py",
            "instructor_debrief.py",
            "instructor_key.py",
            "instructor_key_views.py",
            "instructor_releases.py",
            "instructor_work_links.py",
            "operating_source_bridge.py",
            "organization.py",
            "parameters.py",
            "parent_support.py",
            "parser_sandbox.py",
            "personal_views.py",
            "personal_views_recovery.py",
            "population_lifecycle.py",
            "populations.py",
            "portable_composition.py",
            "portfolio_explanation.py",
            "private_publication.py",
            "private_review_export.py",
            "programs.py",
            "review.py",
            "review_anchor.py",
            "review_layers.py",
            "sample_execution.py",
            "scope.py",
            "scope_reconciliation.py",
            "serialized_json.py",
            "source_impact_disposition.py",
            "store.py",
            "supporting_sources.py",
            "task_gap.py",
            "temporal.py",
            "temporal_workflow.py",
            "voice.py",
            "workpaper_links.py",
            "workspace_context.py",
        }
    )
)
REFERENCE_MODULES = tuple(
    sorted(
        set(ACTIVE_MODULES)
        | {
            "instructor_reference_crosswalk.py",
            "instructor_original.py",
        }
    )
)


def _require_authority(condition, message, status):
    if not condition:
        raise DomainError(message, status=status)


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


def active_configuration(
    workroom_path,
    workroom_sha256,
    bindings_path,
    bindings_sha256,
    *,
    repository,
    instructor_writeback,
    background_jobs,
    artifact_option_limit=5000,
):
    """Explicit pinned activation of existing local manual training functions."""
    require(
        type(instructor_writeback) is bool
        and type(background_jobs) is bool
        and type(artifact_option_limit) is int
        and 2000 <= artifact_option_limit <= 5000,
        "Typed explicit local activation required",
    )
    value = configuration(
        workroom_path, workroom_sha256, bindings_path, bindings_sha256, repository=repository
    )
    value.update(
        schema=ACTIVE_SCHEMA,
        features={
            "instructor_writeback": instructor_writeback,
            "background_jobs": background_jobs,
            "artifact_option_limit": artifact_option_limit,
        },
        code_pins={
            name: file_sha(Path(repository) / "enterprise/audit_suite" / name)
            for name in ACTIVE_MODULES
        },
    )
    return value


def reference_configuration(
    workroom_path,
    workroom_sha256,
    bindings_path,
    bindings_sha256,
    *,
    repository,
    instructor_writeback,
    background_jobs,
    reference_archive,
    reference_crosswalk,
    artifact_option_limit=5000,
):
    """Explicit optional unbound archive; current bound Key remains primary.

    Serializing operator choices neither accepts the crosswalk nor activates it.
    Existing V1/V2 configurations and their exact source vectors are unchanged.
    """
    from .instructor_reference_crosswalk import ReferenceLibrary

    value = active_configuration(
        workroom_path,
        workroom_sha256,
        bindings_path,
        bindings_sha256,
        repository=repository,
        instructor_writeback=instructor_writeback,
        background_jobs=background_jobs,
        artifact_option_limit=artifact_option_limit,
    )
    bindings = load_bindings(Path(bindings_path))
    require(len(bindings) == 1, "Single current engagement reference configuration required")
    binding = next(iter(bindings.values()))
    manifest = pinned_json(binding["path"] / "manifest.json", binding["manifest_sha256"])
    snapshot = pinned_json(
        binding["path"] / "snapshot.json",
        manifest["files"]["snapshot.json"],
        max_bytes=MAX_SNAPSHOT_BYTES,
    )
    ReferenceLibrary(reference_archive, reference_crosswalk, snapshot)
    value.update(
        schema=REFERENCE_SCHEMA,
        reference_archive=reference_archive,
        reference_crosswalk=reference_crosswalk,
        code_pins={
            name: file_sha(Path(repository) / "enterprise/audit_suite" / name)
            for name in REFERENCE_MODULES
        },
    )
    return value


def _reuse_retained_workroom(
    config_path, expected_sha256, *, private_root, repository, retained_workroom, **settings
):
    """Reuse a completed live object, with fresh ordinary integrity and authority.

    This is a trusted local Python object contract, not memory attestation. No
    serialized object, persisted proof, evidence or outcome is admitted here.
    """
    room = retained_workroom
    require(type(room) is RetainedWorkroom, "Exact initialized live RetainedWorkroom required")
    required = {
        "path",
        "expected_sha256",
        "repository",
        "config",
        "root",
        "engine",
        "world",
        "binding",
        "binding_path",
        "binding_sha256",
        "selected",
        "engagement",
        "sealed",
        "sealed_store",
        "_integrity_lock",
    }
    require(
        required <= vars(room).keys()
        and not any(name.startswith("_pending_") for name in vars(room)),
        "Completed live retained initialization required",
    )
    path = absolute_path(str(config_path))
    root = absolute_path(str(private_root))
    repository = absolute_path(str(repository))
    require(
        room.path == path
        and room.expected_sha256 == expected_sha256
        and room.repository == repository
        and room.root == root
        and digest(room.config) == digest(pinned_json(path, expected_sha256))
        and type(room.engine) is RetainedEngine
        and type(room.world) is PersistentCompany
        and room.engine.repository == repository
        and room.engine.store.root == root
        and room.engine.company_store is room.world.store
        and room.engine.company_bindings == {room.engagement: room.selected}
        and room.config["workroom_binding"]
        == {"path": str(room.binding_path), "sha256": room.binding_sha256}
        and digest(room.binding) == digest(pinned_json(room.binding_path, room.binding_sha256)),
        "Live retained configuration, roots, binding or engine differs",
    )
    require(set(settings) <= {"inference_config", "voice_config"}, "Live engine settings differ")
    for key, value in settings.items():
        actual = getattr(room.engine, key)
        require(
            (value is None and actual is None)
            or (
                isinstance(value, (str, Path))
                and isinstance(actual, (str, Path))
                and Path(value).absolute() == Path(actual).absolute()
            ),
            "Live engine settings differ",
        )
    if room.sealed:
        from .sealed_history_store import SealedHistoryStore
        managed = getattr(room.sealed_store, "_managed_history_integrity", None)
        if managed is not None:
            from .managed_history_integrity import ManagedHistoryRuntime
            require(type(room.sealed_store) is SealedHistoryStore
                and room.engine.store is room.sealed_store and type(managed) is ManagedHistoryRuntime
                and managed.room is room and managed.store is room.sealed_store
                and managed._startup_completed is True
                and room.config.get("history_integrity")
                == managed.choice,
                "Completed exact configured managed history lifetime required")
            managed.validate_current(room.binding["identities"]["operator"], room.engagement)
            require(room.engine.store._retained_typed_stamp == room.integrity_stamp(),
                    "Completed managed typed image closure differs")
        else:
            require(
                type(room.sealed_store) is SealedHistoryStore
                and room.engine.store is room.sealed_store
                and isinstance(getattr(room.sealed_store, "_prefix_integrity", None), dict)
                and isinstance(getattr(room, "_prefix_custody", None), dict)
                and isinstance(getattr(room, "_tail_integrity", None), dict),
                "Completed live sealed-prefix validation required",
            )
    else:
        require(
            room.sealed_store is None
            and type(room.engine.store) is Store
            and isinstance(getattr(room, "_retained_integrity", None), dict),
            "Completed live retained history validation required",
        )
    room.check_pins()
    operator = room.binding["identities"]["operator"]
    room.refresh_integrity(operator)
    expected = room.engine.store._retained_typed_stamp
    require(
        room.engine.store.membership(operator, room.engagement) == "instruct",
        "Current original instructor authority required for live reuse",
    )
    room.close_protected_read(operator, expected)
    return room


class ExplainedWorkroom:
    def __init__(
        self,
        config_path,
        expected_sha256,
        *,
        private_root,
        repository,
        retained_workroom=None,
        **settings,
    ):
        self.repository = Path(repository).absolute()
        self.path = absolute_path(str(config_path))
        self.pin = expected_sha256
        self.config = pinned_json(self.path, self.pin)
        self.active = self.config.get("schema") in (ACTIVE_SCHEMA, REFERENCE_SCHEMA)
        self.reference = None
        self.has_reference = self.config.get("schema") == REFERENCE_SCHEMA
        require(
            set(self.config)
            == {"schema", "retained_workroom", "explanation_bindings", "code_pins"}
            | ({"features"} if self.active else set())
            | ({"reference_archive", "reference_crosswalk"} if self.has_reference else set())
            and self.config["schema"] in (SCHEMA, ACTIVE_SCHEMA, REFERENCE_SCHEMA),
            "Exact retained explanation configuration required",
        )
        self.features = {
            "instructor_writeback": False,
            "background_jobs": False,
            "artifact_option_limit": 2000,
        }
        if self.active:
            value = self.config["features"]
            require(
                isinstance(value, dict)
                and set(value) == set(self.features)
                and type(value["instructor_writeback"]) is bool
                and type(value["background_jobs"]) is bool
                and type(value["artifact_option_limit"]) is int
                and 2000 <= value["artifact_option_limit"] <= 5000,
                "Exact typed local feature configuration required",
            )
            self.features = dict(value)
        self.check_code()
        for key in ("retained_workroom", "explanation_bindings"):
            item = self.config[key]
            require(
                isinstance(item, dict) and set(item) == {"path", "sha256"},
                "Exact operator pins required",
            )
            absolute_path(item["path"])
        item = self.config["retained_workroom"]
        if retained_workroom is None:
            self.retained = RetainedWorkroom(
                Path(item["path"]),
                item["sha256"],
                private_root=private_root,
                repository=repository,
                **settings,
            )
        else:
            self.retained = _reuse_retained_workroom(
                Path(item["path"]),
                item["sha256"],
                private_root=private_root,
                repository=repository,
                retained_workroom=retained_workroom,
                **settings,
            )
        bindings = self.validate_explanation()
        if self.has_reference:
            from .instructor_reference_crosswalk import ReferenceLibrary

            binding = bindings[self.retained.engagement]
            manifest = pinned_json(binding["path"] / "manifest.json", binding["manifest_sha256"])
            snapshot = pinned_json(
                binding["path"] / "snapshot.json",
                manifest["files"]["snapshot.json"],
                max_bytes=MAX_SNAPSHOT_BYTES,
            )
            self.reference = ReferenceLibrary(
                self.config["reference_archive"], self.config["reference_crosswalk"], snapshot
            )
        if retained_workroom is not None:
            operator = self.retained.binding["identities"]["operator"]
            expected = self.retained.engine.store._retained_typed_stamp
            self.retained.close_protected_read(operator, expected)
            require(
                self.retained.engine.store.membership(operator, self.retained.engagement)
                == "instruct"
                and digest(pinned_json(self.path, self.pin)) == digest(self.config),
                "Live explanation authority or configuration changed",
            )
            self.check_code()
            item = self.config["explanation_bindings"]
            pinned_json(Path(item["path"]), item["sha256"])
            for binding in bindings.values():
                manifest = pinned_json(
                    binding["path"] / "manifest.json", binding["manifest_sha256"]
                )
                for name, sha256 in manifest["files"].items():
                    member = binding["path"] / name
                    private_file(member)
                    require(file_sha(member) == sha256, "Live explanation member changed")

    def check_code(self):
        pins = self.config["code_pins"]
        require(
            isinstance(pins, dict)
            and set(pins)
            == set(
                REFERENCE_MODULES
                if self.has_reference
                else ACTIVE_MODULES
                if self.active
                else MODULES
            ),
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
        manifest = pinned_json(binding["path"] / "manifest.json", binding["manifest_sha256"])
        require(
            set(manifest) == {"schema_version", "files", "engagement_id", "engagement_revision"}
            and manifest["schema_version"] == "1.0"
            and manifest["engagement_id"] == retained.engagement
            and type(manifest["engagement_revision"]) is int
            and manifest["engagement_revision"] >= 0
            and isinstance(manifest["files"], dict)
            and "snapshot.json" in manifest["files"]
            and all(
                isinstance(name, str)
                and isinstance(pin, str)
                and re.fullmatch(r"[0-9a-f]{64}", pin)
                for name, pin in manifest["files"].items()
            ),
            "Exact same-engagement explanation manifest with a pinned snapshot required",
        )
        snapshot = pinned_json(
            binding["path"] / "snapshot.json",
            manifest["files"]["snapshot.json"],
            max_bytes=MAX_SNAPSHOT_BYTES,
        )
        require(
            set(snapshot)
            == {
                "schema_version",
                "status",
                "created_at",
                "instructor_id",
                "audited_actor_id",
                "source_operator_id",
                "operator_source_as_of",
                "company_binding",
                "engagement",
                "access_event_watermark",
                "sources",
                "software_verified",
                "authored",
                "authored_status",
                "professional_validation",
                "grading",
                "limits",
            }
            and snapshot["schema_version"] == "1.0"
            and snapshot["status"] == "BOUND_INSTRUCTOR_AUTHORED_UNVALIDATED"
            and snapshot["authored_status"] == "INSTRUCTOR_AUTHORED_INFERENCE"
            and snapshot["professional_validation"] == "UNVALIDATED"
            and snapshot["grading"] == "NOT_PERFORMED"
            and snapshot["software_verified"]
            == [
                "Source byte identity",
                "Source availability timestamps",
                "Actor grant state at binding",
                "Exact retained audit-copy hashes",
            ]
            and isinstance(snapshot["limits"], list)
            and snapshot["limits"]
            and all(isinstance(x, str) and x.strip() for x in snapshot["limits"]),
            "Exact unvalidated explanation status and software fact boundaries required",
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
        require(
            type(revision) is int and revision >= 0 and manifest["engagement_revision"] == revision,
            "Strict matching bound and manifest revision required",
        )
        # Ordinary Store construction/session writes can change the journal
        # stamp. Establish the same fresh typed boundary before inspection;
        # sealed graphs reuse only this invocation's verified node bytes.
        retained.refresh_integrity(identities["operator"])
        history = inspect_selected_integrity(
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
        sources = snapshot["sources"]
        require(
            isinstance(sources, list)
            and sources
            and all(
                isinstance(s, dict) and isinstance(s.get("id"), str) and s["id"] for s in sources
            )
            and len({s["id"] for s in sources}) == len(sources),
            "Distinct typed bound explanation source IDs required",
        )
        require(
            set(manifest["files"])
            == {"snapshot.json", *[f"sources/{index:05d}.json" for index in range(len(sources))]}
            and verify_snapshot(
                binding["path"], expected_manifest_sha256=binding["manifest_sha256"]
            )
            == snapshot,
            "Exact complete explanation snapshot and original member set required",
        )
        require(
            _authored(
                snapshot["authored"],
                {s["id"] for s in sources},
                {c["id"] for c in state["controls"]},
                self.repository,
                state=state,
            )
            == snapshot["authored"],
            "Exact authored source, scoped control and task links required",
        )
        watermark = snapshot["access_event_watermark"]
        require(type(watermark) is int and watermark >= 0, "Strict access event watermark required")
        seen = set()
        with quiescent_read(retained.world.store.path) as db:
            require(
                watermark
                <= db.execute("SELECT COALESCE(MAX(id),0) FROM access_events").fetchone()[0]
                and (
                    watermark == 0
                    or db.execute("SELECT 1 FROM access_events WHERE id=?", (watermark,)).fetchone()
                    is not None
                ),
                "Explanation access watermark does not exist in this company history",
            )
            for index, source in enumerate(snapshot["sources"]):
                require(
                    set(source)
                    == {
                        "id",
                        "company",
                        "branch",
                        "system",
                        "record",
                        "version",
                        "sha256",
                        "path",
                        "event_at",
                        "available_at",
                        "imported_at",
                        "actor_granted_at_binding",
                        "actor_visibility_at_binding",
                        "retained_audit_artifact_ids",
                        "fact_verification",
                    }
                    and source["fact_verification"]
                    == "EXACT_EXISTING_SOURCE_BYTES_AND_ACCESS_STATE_ONLY",
                    "Exact explanation source fact boundary required",
                )
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
                access = db.execute(
                    "SELECT active FROM access_events WHERE id<=? AND principal=? AND engagement=? "
                    "AND company=? AND branch=? AND system=? ORDER BY id DESC LIMIT 1",
                    (watermark, identities["auditor"], retained.engagement, *key[:3]),
                ).fetchone()
                granted = bool(access and access["active"] == 1)
                clock = _time(state["simulated_at"])
                exists = _time(row["available_at"]) <= clock and (
                    row["event_at"] is None or _time(row["event_at"]) <= clock
                )
                latest = db.execute(
                    "SELECT MAX(version) FROM versions WHERE company=? AND branch=? AND system=? "
                    "AND record=? AND available_at<=? AND (event_at IS NULL OR event_at<=?)",
                    (*key[:4], clock, clock),
                ).fetchone()[0]
                visibility = (
                    "FUTURE_UNAVAILABLE"
                    if not exists
                    else "ACCESS_NOT_GRANTED"
                    if not granted
                    else "DISCOVERABLE_LATEST"
                    if latest == version
                    else "READABLE_PRIOR_VERSION"
                )
                require(
                    type(source["actor_granted_at_binding"]) is bool
                    and source["actor_granted_at_binding"] == granted
                    and source["actor_visibility_at_binding"] == visibility,
                    "Explanation captured grant or visibility differs from actual access history",
                )
                require(
                    source["path"] == f"sources/{index:05d}.json"
                    and source["path"] in manifest["files"]
                    and manifest["files"][source["path"]] == source["sha256"],
                    "Exact declared relative explanation source member required",
                )
                member = binding["path"] / source["path"]
                private_file(member)
                raw = member.read_bytes()
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

    def actor(self, request):
        retained = self.retained
        bearer = request.headers.get("authorization", "")
        if bearer:
            if not bearer.startswith("Bearer "):
                raise DomainError("Bearer credential required", status=401)
            return retained.engine.store.authenticate(bearer[7:])
        else:
            cookie_name = (
                "sh_audit_session_"
                + hashlib.sha256(
                    str(retained.engine.store.root.resolve()).encode("utf-8")
                ).hexdigest()[:32]
            )
            return retained.engine.store.session(request.cookies.get(cookie_name, ""))

    def background_guard(self, actor, engagement):
        """Deferred work receives fresh public/native authority, never Key contents."""
        _require_authority(engagement == self.retained.engagement, "Worker engagement differs", 403)
        self.check_code()
        self.retained.check_pins()
        self.retained.refresh_integrity(actor)
        _require_authority(
            self.retained.engine.store.membership(actor, engagement) in {"learn", "instruct"},
            "Current worker membership required",
            403,
        )

    def guard(self, request):
        retained = self.retained
        prefix = "/api/engagements/" + re.escape(retained.engagement)
        instructor_paths = r"instructor-binding|instructor-comparison|instructor-key-views"
        if self.has_reference:
            instructor_paths += r"|instructor-key"
        if self.features["instructor_writeback"]:
            instructor_paths += r"|instructor-assessments|instructor-releases"
        private = re.fullmatch(prefix + r"/(" + instructor_paths + r")(/.*)?", request.url.path)
        assistance = self.features["instructor_writeback"] and re.fullmatch(
            prefix + r"/assistance(/.*)?", request.url.path
        )
        if private is None and not assistance:
            retained.guard(request)
            # A current scoped metadata response must not deliver a stale
            # representation after an in-handler journal/auth/native mutation.
            ordinary = request.method == "GET" and (
                request.url.path in {"/api/bootstrap", "/api/engagements"}
                or re.fullmatch(prefix + r"(/.*)?", request.url.path)
            )
            if not ordinary:
                return
            self.check_code()
            actor = self.actor(request)
            retained.refresh_integrity(actor["id"])
            expected = retained.engine.store._retained_typed_stamp

            def close_ordinary_read():
                _require_authority(
                    self.actor(request)["id"] == actor["id"], "Response actor changed", 403
                )
                retained.close_protected_read(actor["id"], expected)
                self.check_code()

            return close_ordinary_read
        retained.check_pins()
        actor = self.actor(request)
        if (
            private
            and retained.engine.store.membership(actor["id"], retained.engagement) != "instruct"
        ):
            raise DomainError("Instructor membership required", status=403)
        if assistance:
            _require_authority(
                retained.engine.store.membership(actor["id"], retained.engagement)
                in {"learn", "instruct"},
                "Current selected assistance membership required",
                403,
            )
        # A damaged private explanation must not stop ordinary learner fieldwork.
        bindings = self.validate_explanation()
        if self.reference is not None:
            self.reference.check()
        expected = retained.engine.store._retained_typed_stamp

        def close_private_read():
            # A response cannot cross a different journal, credential/session,
            # current membership or authored-member boundary from validation.
            current_actor = self.actor(request)
            require(current_actor["id"] == actor["id"], "Private response actor changed")
            retained.close_protected_read(actor["id"], expected)
            require(
                pinned_json(self.path, self.pin) == self.config,
                "Explanation configuration changed before response closure",
            )
            self.check_code()
            item = self.config["explanation_bindings"]
            pinned_json(Path(item["path"]), item["sha256"])
            for binding in bindings.values():
                manifest = pinned_json(
                    binding["path"] / "manifest.json", binding["manifest_sha256"]
                )
                for name, sha256 in manifest["files"].items():
                    member = binding["path"] / name
                    private_file(member)
                    require(
                        file_sha(member) == sha256,
                        "Explanation member changed before response closure",
                    )
            if self.reference is not None:
                self.reference.check()

        return close_private_read

    def reference_view(self, engagement_id):
        require(
            self.reference is not None and engagement_id == self.retained.engagement,
            "Same-engagement configured reference required",
        )
        return self.reference.check()


def create_explained_app(
    private_root, config_path, expected_sha256, *, repository, retained_workroom=None, **options
):
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
            "instructor_reference_crosswalk",
            "instructor_bindings",
            "enable_instructor_writeback",
            "instructor_artifact_option_limit",
            "background_job_guard",
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
        retained_workroom=retained_workroom,
        **{key: options[key] for key in ("inference_config", "voice_config") if key in options},
    )
    if explained.active:
        require(
            "background_jobs" not in options,
            "Active background work is determined by the pinned configuration",
        )
        options["background_jobs"] = explained.features["background_jobs"]
    return create_app(
        private_root,
        repository=repository,
        engine_factory=lambda: explained.retained.engine,
        request_guard=explained.guard,
        instructor_bindings=Path(explained.config["explanation_bindings"]["path"]),
        instructor_key_root=explained.reference.root if explained.reference is not None else None,
        instructor_reference_crosswalk=explained.reference_view
        if explained.reference is not None
        else None,
        enable_instructor_writeback=explained.features["instructor_writeback"],
        instructor_artifact_option_limit=explained.features["artifact_option_limit"],
        background_job_guard=explained.background_guard if explained.active else None,
        **options,
    )
