"""Authorized engagement commands shared by browser and machine clients."""

from __future__ import annotations

import copy
import csv
import html
import io
import json
import zipfile
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import populations
from .artifacts import Artifacts
from .configuration import validate_configuration
from .organization import snapshot
from .scope import PROGRAMS, ROOT, control_projection, validate_scope
from .store import DomainError, Store, canonical, digest, identifier
from .temporal import ScheduledEvent, SimulationClock, advance


def scoped_datetime(value: str, scope: dict, *, hour: int = 9) -> str:
    """Interpret calendar dates in scope time; preserve explicit-offset timestamps."""
    try:
        if not isinstance(value, str):
            raise ValueError
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if len(value) == 10:
            return parsed.replace(
                hour=hour, tzinfo=ZoneInfo(scope.get("timezone", "UTC"))
            ).isoformat()
        if parsed.tzinfo is None:
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise DomainError(
            "Use an ISO calendar date or a timestamp with an explicit UTC offset"
        ) from None


COLLECTIONS = (
    "controls",
    "people",
    "tasks",
    "requests",
    "artifacts",
    "meetings",
    "notes",
    "populations",
    "selections",
    "sample_executions",
    "calendar",
    "findings",
    "workpapers",
    "reviews",
    "surveys",
    "events",
)
CAPABILITIES = {
    "custom_authoring": False,
    "experimental_review": False,
    "review_feedback": True,
    "review_independent_resolution": True,
    "review_passage_anchors": True,
    "sample_executions": True,
    "work_guidance_policy": True,
    "voice": False,
}
REVIEW_COMMANDS = {"review.comment", "review.resolve"}


def require_text(payload: dict, key: str, *, maximum: int = 20000) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise DomainError(f"{key} requires nonempty text up to {maximum} characters")
    return value.strip()


def find(state: dict, collection: str, row_id: str) -> dict:
    row = next((r for r in state[collection] if r["id"] == row_id), None)
    if row is None:
        raise DomainError(f"Unknown {collection} item in this engagement", status=404)
    return row


def exchange_note(meeting, user_message, company_message, result, stamped):
    """Bind extracted statements to actual message identities and distinct speakers."""
    extraction = result.get("extracted_notes")
    aliases = {
        "USER-MESSAGE": user_message,
        "COMPANY-MESSAGE": company_message,
        user_message["id"]: user_message,
        company_message["id"]: company_message,
    }

    def references(refs):
        if not isinstance(refs, list) or any(ref not in aliases for ref in refs):
            raise DomainError("Note extraction cites an unknown exchange message")
        output = []
        for ref in refs:
            message = aliases[ref]
            if any(row["message_id"] == message["id"] for row in output):
                continue
            output.append(
                {
                    "message_id": message["id"],
                    "start": 0,
                    "end": len(message["content"]),
                    "speaker_role": "LEARNER" if message["role"] == "user" else "COMPANY",
                    "speaker_id": message.get("person_id", message.get("actor")),
                    "original_text": message["content"],
                }
            )
        return output

    refs = (
        references(extraction.get("source_refs", []))
        if extraction
        else references([company_message["id"]])
    )
    bullets = []
    for claim in (extraction or {}).get("claims", []):
        claim_refs = references(claim.get("source_refs", []))
        bullets.append(
            {
                "text": claim["text"],
                "source_refs": claim_refs,
                "classification": "ATTRIBUTED_EXCHANGE_STATEMENT"
                if claim_refs
                else "UNATTRIBUTED_PROPOSAL",
            }
        )
    company_only = bool(refs) and all(ref["speaker_role"] == "COMPANY" for ref in refs)
    return {
        "id": identifier("NOTE"),
        "text": extraction.get("text", "") if extraction else company_message["content"],
        "extraction": extraction,
        "attributed_bullets": bullets,
        "control_id": meeting.get("control_id"),
        "meeting_id": meeting["id"],
        "person_id": meeting["person_id"] if company_only else None,
        "classification": "ATTRIBUTED_EXCHANGE_STATEMENT" if refs else "UNATTRIBUTED_PROPOSAL",
        "source_refs": refs,
        "confirmation": "UNCONFIRMED_EXTRACTION",
        **(
            {"consultation": copy.deepcopy(company_message["consultation"])}
            if "consultation" in company_message
            else {}
        ),
        "history": [],
        **stamped,
    }


class Engine:
    def __init__(
        self,
        private_root: Path,
        *,
        repository: Path = ROOT,
        corpus_root: Path | None = None,
        program_pack: Path | None = None,
        inference_config: Path | None = None,
        voice_config: Path | None = None,
        company_root: Path | None = None,
        company_bindings: dict | None = None,
        company_registry: Path | None = None,
        company_profile: str | None = None,
    ):
        if company_root is not None and company_registry is not None:
            raise DomainError("Choose one concrete company store or source registry")
        if (company_registry is None) != (company_profile is None):
            raise DomainError("Company registry and profile must be configured together")
        self.store = Store(private_root)
        self.artifacts = Artifacts(private_root)
        self.repository = repository
        from .company_store import CompanyStore

        if company_registry is not None:
            from .company_federation import FederatedCompanyStore

            self.company_store = FederatedCompanyStore(company_registry, company_profile)
        else:
            self.company_store = CompanyStore(company_root) if company_root else None
        self.company_bindings = json.loads(json.dumps(company_bindings or {}))
        self.corpus_root = (
            corpus_root or repository / "enterprise/generated/audit-suite/private-corpus"
        )
        pack_path = program_pack or private_root / "program-pack.json"
        self.program_pack = json.loads(pack_path.read_text()) if pack_path.is_file() else None
        self.scenario_delivery_ready = True
        self.inference_config = inference_config
        self.voice_config = voice_config
        from enterprise.ccf.registry import compile_registry

        from .organization import financial_model

        native = compile_registry(repository)
        self.setup_controls = [
            {"id": r["id"], "title": r["data"]["title"]}
            for r in native["records"]
            if r["kind"] == "control"
        ]
        self.setup_boundaries = [
            {"id": r["id"], "title": r["data"]["title"]}
            for r in native["records"]
            if r["kind"] == "boundary"
        ]
        model = financial_model(repository, native=native)
        self.setup_accounts = [
            {k: a[k] for k in ("id", "name", "model", "candidate_assertions")}
            for a in model["accounts"]
        ]
        from .programs import ism_catalog

        try:
            self.setup_ism = ism_catalog(repository)
        except DomainError as exc:
            self.setup_ism = {
                "requirements": [],
                "status": "BLOCKED_SOURCE_OR_LICENSE",
                "reason": str(exc),
            }
        self.capabilities = {
            **CAPABILITIES,
            "personal_drafts": True,
            "workpaper_procedure_links": True,
            "company_sources": self.company_store is not None,
            "company_message_sources": self.company_store is not None,
            "company_consultations": self.company_store is not None,
            "company_source_census": self.company_store is not None,
            "company_populations": self.company_store is not None
            and getattr(self.company_store, "capabilities", {}).get("company_populations", True),
            "company_source_impact": self.company_store is not None
            and getattr(self.company_store, "capabilities", {}).get("source_impact", True),
            "custom_authoring": inference_config is not None,
            "experimental_review": inference_config is not None,
            "voice": voice_config is not None,
        }

    @staticmethod
    def _identifier_list(value) -> list[str]:
        if isinstance(value, str):
            value = value.replace(",", " ").split()
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            raise DomainError("References must be a list of identifiers")
        return value

    @staticmethod
    def learner_snapshot(state: dict) -> dict:
        projected = copy.deepcopy(state)
        for key in (
            "custom_drafts",
            "private_truth",
            "private_seed",
            "selected_variants",
            "trainer_encounter_counts",
            "rubrics",
        ):
            projected.pop(key, None)
        projected.pop("configuration", None)
        for request in projected.get("requests", []):
            for key in (
                "plan_unit",
                "plan_request",
                "scenario_progress",
                "scenario_released",
                "parent_support",
            ):
                request.pop(key, None)
        projected["artifacts"] = [
            m for m in projected.get("artifacts", []) if m.get("audience", "LEARNER") == "LEARNER"
        ]
        return projected

    def provider_status(self) -> dict:
        result = {
            "inference": {"configured": False, "ready": False, "local": True},
            "voice": {"configured": False, "ready": False, "local": True},
        }
        if self.inference_config:
            from .inference import LocalInference

            try:
                result["inference"] = LocalInference(self.inference_config).status()
            except (DomainError, OSError, ValueError):
                result["inference"] = {"configured": True, "ready": False, "local": True}
        if self.voice_config:
            from .voice import LocalVoice

            try:
                LocalVoice(self.voice_config)
                result["voice"] = {
                    "configured": True,
                    "ready": True,
                    "local": True,
                    "asr": "faster-whisper-base.en",
                    "tts": "Piper LJSpeech",
                    "language": "English",
                    "paid_service": False,
                }
            except (DomainError, OSError, ValueError, KeyError):
                result["voice"] = {"configured": True, "ready": False, "local": True}
        return result

    def bootstrap(self, actor: dict) -> dict:
        providers = self.provider_status()
        return {
            "providers": providers,
            "viewer": {k: actor[k] for k in ("id", "display_name", "roles")},
            "csrf_token": actor.get("csrf_token", ""),
            "engagements": [
                {
                    k: e[k]
                    for k in (
                        "id",
                        "title",
                        "discipline",
                        "mode",
                        "phase",
                        "revision",
                        "simulated_at",
                    )
                }
                for e in self.store.listing(actor["id"])
            ],
            "capabilities": {
                **self.capabilities,
                "custom_authoring": providers["inference"]["ready"],
                "experimental_review": providers["inference"]["ready"],
                "voice": providers["voice"]["ready"],
            },
            "programs": [
                {
                    **program,
                    "status": "BLOCKED_SOURCE_OR_LICENSE",
                    "reason": self.setup_ism.get("reason"),
                }
                if program["id"] == "IRAP" and not self.setup_ism.get("requirements")
                else program
                for program in PROGRAMS
            ],
            "people": [],
            "controls": self.setup_controls,
            "boundaries": self.setup_boundaries,
            "financial_accounts": self.setup_accounts,
            "ism_catalog": self.setup_ism,
        }

    def create(self, actor: str, payload: dict) -> dict:
        allowed = {"command_id", "title", "discipline", "mode", "scope", "configuration"}
        if set(payload) - allowed:
            raise DomainError("Unexpected engagement creation fields")
        discipline, mode = (
            str(payload.get("discipline", "")).upper(),
            str(payload.get("mode", "")).upper(),
        )
        title = require_text(payload, "title", maximum=200)
        configuration = payload.get("configuration", {})
        if isinstance(configuration, dict) and {
            "work_guidance_allowed",
            "work_guidance_policy_revision",
        } & set(configuration):
            raise DomainError(
                "Assistance policy requires an explicit instructor command", status=403
            )
        validate_configuration(configuration, mode)
        scope = validate_scope(payload.get("scope", {}), discipline, repository=self.repository)
        org = snapshot(self.repository, as_of=scope["period_start"])
        controls = control_projection(
            scope, repository=self.repository, program_pack=self.program_pack
        )
        if scope["programs"] == ["FINANCIAL"] and not scope.get("control_ids"):
            selected_accounts = {a["id"] for a in scope["accounts"]}
            candidate_ids = {
                cid
                for process in org["financial_model"]["processes"]
                if selected_accounts.intersection(process["account_ids"])
                for cid in process["candidate_control_ids"]
            }
            controls = [c for c in controls if c["id"] in candidate_ids]
            scope["financial_control_basis"] = (
                "CANDIDATE_ACCOUNT_PROCESS_ROUTE_NOT_PROFESSIONAL_SELECTION"
            )
        if self.program_pack:
            scope["program_pack_digest"] = self.program_pack["digest"]
        assignments = {a["control_id"]: a for a in org["control_assignments"]}
        people = [
            {
                **p,
                "id": p["person_id"],
                "name": p.get("name", p.get("display_name", p["person_id"])),
                "title": p.get("title", p.get("role_title", "")),
            }
            for p in org["canonical_people"] + org["proposed_people"]
        ]
        from .programs import dependency_tasks, ism_tasks

        tasks = ism_tasks(scope, self.repository)
        tasks.extend(dependency_tasks(scope, self.program_pack))
        for control in controls:
            assignment = assignments[control["id"]]
            control["owner_ids"] = (
                [assignment["primary_person_id"]] if assignment["primary_person_id"] else []
            )
            control["assignment"] = assignment
            for boundary in scope["boundaries"]:
                kinds = ["TOD", "IMPLEMENTATION"] + (
                    [] if scope["temporal_basis"] == "POINT_IN_TIME" else ["TOE"]
                )
                for kind in kinds:
                    tasks.append(
                        {
                            "id": f"TASK-{control['id']}-{boundary}-{kind}",
                            "control_id": control["id"],
                            "boundary_id": boundary,
                            "title": f"{kind}: {control['title']}",
                            "kind": kind,
                            "status": "NOT_STARTED",
                            "conclusion": "NOT_RUN",
                            "note": "",
                            "owner_id": assignment["primary_person_id"],
                            "history": [],
                        }
                    )
                for duty in control.get("additional_duties", []):
                    tasks.append(
                        {
                            "id": f"TASK-{control['id']}-{boundary}-{duty['id']}",
                            "control_id": control["id"],
                            "boundary_id": boundary,
                            "title": duty["procedure"],
                            "kind": "ADDITIONAL_DUTY",
                            "status": "NOT_STARTED",
                            "conclusion": "NOT_RUN",
                            "requirement_ids": duty["requirement_ids"],
                            "test": duty["acceptance_test"],
                            "owner_id": assignment["primary_person_id"],
                            "history": [],
                        }
                    )
        if "FINANCIAL" in scope["programs"]:
            from .organization import ASSERTIONS

            for account in scope["accounts"]:
                for assertion in account["assertions"]:
                    tasks.append(
                        {
                            "id": f"TASK-{account['id']}-{assertion}",
                            "title": f"{account['name']} — {ASSERTIONS[assertion]}",
                            "account_id": account["id"],
                            "assertion": assertion,
                            "kind": "SUBSTANTIVE",
                            "frameworks": ["FINANCIAL"],
                            "risk_rationale": account["risk_rationale"],
                            "planned_procedures": account["planned_procedures"],
                            "jurisdiction": scope["financial_audit_jurisdiction"],
                            "status": "NOT_STARTED",
                            "conclusion": "NOT_RUN",
                            "note": "",
                            "history": [],
                        }
                    )
        state = {key: [] for key in COLLECTIONS}
        state.update(
            title=title,
            discipline=discipline,
            mode=mode,
            scope=scope,
            configuration=configuration,
            phase="CONFIGURING",
            simulated_at=scoped_datetime(scope["fieldwork_start"], scope),
            controls=controls,
            tasks=tasks,
            people=people,
            capabilities=self.capabilities,
            organization={
                "snapshot_digest": org["snapshot_digest"],
                "source_revision": org["source_revision"],
                "repository_acceptance_status": org["repository_acceptance_status"],
                "reconciliation": org["reconciliation"],
            },
            financial_model=org["financial_model"],
            generation={
                "state": "NOT_STARTED",
                "completed": 0,
                "total": len(controls) * len(scope["boundaries"]),
                "errors": [],
            },
        )
        return self.store.create(actor, state, payload.get("command_id") or identifier("CREATE"))

    def get(self, actor: str, engagement_id: str) -> dict:
        return self._project(actor, self.store.get(actor, engagement_id))

    def _project(self, actor: str, state: dict) -> dict:
        permission = self.store.membership(actor, state["id"])
        state["capabilities"] = self.capabilities
        policy = state.get("configuration", {})
        state["work_guidance_policy"] = {
            "allowed": policy.get("work_guidance_allowed") is True,
            "version": policy.get("work_guidance_policy_revision", 0),
        }
        if state.get("scope", {}).get("temporal_basis") and all(
            c.get("owner_ids") and c.get("implementation_version")
            for c in state.get("controls", [])
        ):
            from .temporal_workflow import current, reports

            state["temporal_current"] = current(state)
            state["temporal_reports"] = reports(state)
        if permission != "instruct":
            state.pop("trainer_encounter_counts", None)
        if permission == "learn":
            if state.get("created_by") != actor:
                state.pop("configuration", None)
            state.pop("custom_drafts", None)
            state["artifacts"] = [
                m for m in state["artifacts"] if m.get("audience", "LEARNER") == "LEARNER"
            ]
        for request in state.get("requests", []):
            for key in (
                "plan_unit",
                "plan_request",
                "scenario_progress",
                "scenario_released",
                "parent_support",
            ):
                request.pop(key, None)
        from .sample_execution import input_pins

        state["sample_execution_inputs"] = input_pins(state)
        from .company_consultation import input_pins as consultation_inputs

        state["company_consultation_inputs"] = consultation_inputs(state)
        state["permissions"] = [permission]
        return state

    def command(self, actor: str, engagement_id: str, command: dict) -> dict:
        if (
            not isinstance(command, dict)
            or not isinstance(command.get("kind"), str)
            or not isinstance(command.get("payload"), dict)
        ):
            raise DomainError("Command requires a string kind and object payload")
        if command["kind"] == "review.export" and not isinstance(
            command["payload"].get("edition", "LEARNER"), str
        ):
            raise DomainError("Export edition must be a string")
        permissions = (
            {"review", "instruct"}
            if command.get("kind") in REVIEW_COMMANDS
            else {"learn", "instruct"}
        )
        if (
            command.get("kind") == "review.export"
            and command.get("payload", {}).get("edition", "").upper() == "REVIEWER"
        ):
            permissions = {"review", "instruct"}
        kind = command.get("kind", "")
        if kind.startswith("scenario.custom.") or kind in {
            "company.activate",
            "assistance.configure",
        }:
            permissions = {"instruct"}
        if kind == "review.resolve" and "disposition" in command.get("payload", {}):
            permissions = {"learn", "review", "instruct"}
        if kind in {"review.prepare", "review.experimental"}:
            permissions = {"learn", "review", "instruct"}
        replay = self.store.preflight(actor, engagement_id, command, permissions=permissions)
        if replay is not None:
            return self._project(actor, replay)
        inference_result = None
        if kind in {"meeting.message", "review.prepare", "review.experimental"} or kind.startswith(
            "scenario.custom."
        ):
            current = self.store.get(actor, engagement_id)
            if current["revision"] != command.get("expected_revision"):
                raise DomainError("Engagement changed; reload before continuing", status=409)
            if kind.startswith("scenario.custom."):
                from .custom import prepare as prepare_custom

                inference_result = prepare_custom(self, current, kind, command["payload"])
            elif kind == "meeting.message":
                inference_result = self._conversation(current, command.get("payload", {}), actor)
            elif kind == "review.prepare":
                from .review import prepare, public_prepared
                from .store import digest

                prepared = prepare(
                    current,
                    self.artifacts,
                    selected_workpapers=command["payload"].get("workpaper_ids"),
                    engine=self,
                )
                prepared = public_prepared(prepared)
                inference_result = {"prepared": prepared, "input_digest": digest(prepared)}
            else:
                if not self.inference_config:
                    raise DomainError("Local review model is not configured", status=503)
                from .review import run

                inference_result = run(
                    current,
                    self.artifacts,
                    self.inference_config,
                    command["payload"],
                    engine=self,
                )
        try:

            def reducer(s, c, who):
                return self._reduce(s, c, who, inference_result=inference_result)

            state = self.store.command(
                actor, engagement_id, command, reducer, permissions=permissions
            )
        except DomainError:
            raise
        except (ValueError, KeyError, TypeError) as exc:
            raise DomainError("Invalid command input: " + str(exc)[:300]) from exc
        return self._project(actor, state)

    def _reduce(
        self, state: dict, command: dict, actor: str, *, inference_result: dict | None = None
    ) -> dict:
        kind, p = command["kind"], command["payload"]
        stamped = {
            "actor": actor,
            "recorded_at": datetime.now(UTC).isoformat(),
            "simulated_at": state["simulated_at"],
        }
        from .temporal_workflow import COMMANDS as TEMPORAL_COMMANDS
        from .temporal_workflow import handle as temporal_handle

        if kind == "assistance.configure":
            if (
                set(p) != {"work_guidance_allowed", "rationale"}
                or type(p.get("work_guidance_allowed")) is not bool
            ):
                raise DomainError("Explicit guidance permission and rationale required")
            if state["phase"] not in {"CONFIGURING", "READY", "KICKOFF", "ACTIVE"}:
                raise DomainError("Assistance policy cannot change during generation")
            rationale = require_text(p, "rationale", maximum=2000)
            configuration = state.setdefault("configuration", {})
            previous = configuration.get("work_guidance_allowed") is True
            version = state["revision"] + 1
            configuration.update(
                work_guidance_allowed=p["work_guidance_allowed"],
                work_guidance_policy_revision=version,
            )
            state.setdefault("assistance_policy_history", []).append(
                {
                    "kind": "ADMINISTRATIVE_WORK_GUIDANCE",
                    "previous_allowed": previous,
                    "allowed": p["work_guidance_allowed"],
                    "policy_version": version,
                    "rationale": rationale,
                    **stamped,
                }
            )
        elif kind == "company.activate":
            from .company_collection import activate

            activate(self, state, p, stamped)
        elif kind == "company.census.collect":
            from .company_source_census_collection import collect as collect_census

            collect_census(self, state, p, stamped, command["command_id"])
        elif kind == "company.population.collect":
            from .company_population_collection import collect as collect_population

            collect_population(self, state, p, stamped, command["command_id"])
        elif kind == "company.collect":
            from .company_collection import collect

            collect(self, state, p, stamped, command["command_id"])
        elif kind in {"sample.execution.record", "sample.execution.correct"}:
            from .sample_execution import handle as handle_sample_execution

            handle_sample_execution(state, kind, p, stamped, self.artifacts)
        elif kind in TEMPORAL_COMMANDS:
            temporal_handle(self, state, kind, p, stamped)
        elif kind == "scenario.validate":
            validate_configuration(state["configuration"], state["mode"])
            validate_scope(state["scope"], state["discipline"], repository=self.repository)
            unresolved = [c["id"] for c in state["controls"] if not c["owner_ids"]]
            state["generation"]["errors"] = [
                "Period-appropriate owner assignment required: " + c for c in unresolved
            ]
            state["generation"]["state"] = "VALIDATED" if not unresolved else "INVALID"
        elif kind in {"scenario.build", "generation.retry"}:
            if state["phase"] not in {"CONFIGURING", "GENERATION_FAILED", "GENERATION_CANCELLED"}:
                raise DomainError("Generation cannot overwrite an active engagement")
            if any(not c["owner_ids"] for c in state["controls"]):
                raise DomainError("Resolve period-appropriate ownership before generation")
            state["phase"] = "GENERATING"
            state["generation"].update(state="RUNNING", errors=[], stage="Binding evidence plans")
        elif kind == "generation.cancel":
            if state["phase"] != "GENERATING":
                raise DomainError("No generation is running")
            state["phase"] = "GENERATION_CANCELLED"
            state["generation"]["state"] = "CANCELLED"
        elif kind == "scope.update":
            if state["phase"] not in {"CONFIGURING", "ACTIVE"}:
                raise DomainError("Scope cannot change during generation")
            revised = validate_scope(
                p.get("scope", {}), state["discipline"], repository=self.repository
            )
            rationale = require_text(p, "rationale")
            from .scope_reconciliation import apply as reconcile_scope

            reconcile_scope(self, state, revised, rationale, stamped)
        elif kind == "kickoff.start":
            if state["phase"] not in {"READY", "KICKOFF", "ACTIVE"}:
                raise DomainError(
                    "Complete scope binding and generation before company interaction"
                )
            if not any(m.get("kind") == "KICKOFF" for m in state["meetings"]):
                owners = [c["owner_ids"][0] for c in state["controls"] if c["owner_ids"]]
                coordinator = next(
                    (p["id"] for p in state["people"] if p["id"] == "AS-P005"), owners[0]
                )
                state["meetings"].append(
                    {
                        "id": identifier("MTG"),
                        "title": "Engagement kickoff",
                        "kind": "KICKOFF",
                        "person_id": coordinator,
                        "status": "OPEN",
                        "messages": [],
                        "control_ids": [],
                        **stamped,
                    }
                )
            state["phase"] = "ACTIVE"
        elif kind.startswith("population.") or kind.startswith("selection."):
            self._population_command(state, kind, p, stamped)
        elif kind == "clock.advance":
            self._advance(state, p, stamped)
        elif kind in {"pbc.issue", "pbc.followup", "pbc.read"}:
            self._request_command(state, kind, p, stamped)
        elif kind == "meeting.message":
            if inference_result is None:
                raise DomainError("Conversation result unavailable")
            meeting = find(state, "meetings", p.get("meeting_id"))
            if "source_records" in p:
                from .company_persona import validate_selection

                validate_selection(self, actor, state, meeting["person_id"], p["source_records"])
            consultation_prepared = inference_result.get("consultation_prepared")
            if "consultation" in p:
                from . import company_consultation

                if consultation_prepared is None:
                    raise DomainError("Consultation result unavailable")
                company_consultation.revalidate(
                    self,
                    actor,
                    state,
                    p,
                    consultation_prepared,
                    inference_result.get("consultation_source_manifest", []),
                )
            user_message = {
                "id": inference_result.get("message_ids", {}).get("user") or identifier("MSG"),
                "role": "user",
                "content": require_text(p, "content", maximum=8000),
                **stamped,
            }
            if "source_records" in p:
                user_message["source_records"] = json.loads(json.dumps(p["source_records"]))
            company_message = {
                "id": inference_result.get("message_ids", {}).get("company") or identifier("MSG"),
                "role": "assistant",
                "person_id": meeting["person_id"],
                "content": inference_result["text"],
                "claim_type": "PERSONA_STATEMENT",
                "source_refs": inference_result["source_refs"],
                "model": inference_result.get("model"),
                **stamped,
            }
            if "consultation" in p:
                user_message["consultation"] = company_consultation.stored(consultation_prepared)
                company_message["consultation"] = company_consultation.stored(
                    consultation_prepared,
                    result=inference_result,
                    manifest=inference_result.get("consultation_source_manifest", []),
                )
            actions = inference_result.get("proposed_actions", [])
            from .inference import _validate_actions

            action_context = self._action_context(state, meeting)
            _validate_actions("persona", actions, action_context)
            receipts = []
            for action in actions:
                payload = dict(action["payload"])
                if action["kind"] == "pbc.create":
                    if payload.get("control_id"):
                        control = find(state, "controls", payload["control_id"])
                        contacts = set(control.get("owner_ids", [])) | set(
                            control.get("assignment", {}).get("proposed_contact_ids", [])
                        )
                        payload.setdefault(
                            "person_id", next(iter(sorted(contacts)), meeting["person_id"])
                        )
                        if payload["person_id"] not in contacts:
                            raise DomainError(
                                "Proposed recipient is not assigned to this control", status=403
                            )
                    else:
                        payload.setdefault("person_id", meeting["person_id"])
                    self._workspace_command(state, "pbc.create", payload, stamped)
                    affected = state["requests"][-1]
                else:
                    self._request_command(state, action["kind"], payload, stamped)
                    affected = find(state, "requests", payload["request_id"])
                receipts.append(
                    {
                        "kind": action["kind"],
                        "request_id": affected["id"],
                        "status": affected["status"],
                        "reason": action["reason"],
                        "executed": True,
                        "authority": "SCOPED_ENGINE_COMMAND",
                    }
                )
            company_message["action_receipts"] = receipts
            meeting["messages"].extend([user_message, company_message])
            state["notes"].append(
                exchange_note(meeting, user_message, company_message, inference_result, stamped)
            )
        elif kind in {
            "task.create",
            "task.update",
            "note.create",
            "note.correct",
            "finding.create",
            "finding.update",
            "remediation.record",
            "remediation.retest",
            "workpaper.add",
            "workpaper.update",
            "review.comment",
            "review.resolve",
            "survey.submit",
            "meeting.create",
            "pbc.create",
            "pbc.update",
        }:
            self._workspace_command(state, kind, p, stamped)
        elif kind == "review.export":
            self._export(state, p, stamped)
        elif kind == "review.prepare":
            if state["phase"] != "ACTIVE" or inference_result is None:
                raise DomainError("Review preparation requires an active engagement")
            prepared = inference_result["prepared"]
            state["reviews"].append(
                {
                    "id": identifier("REVIEW-INPUT"),
                    "kind": "EXPERIMENTAL_INPUT",
                    "status": "PREPARED",
                    "input_digest": inference_result["input_digest"],
                    "workpaper_ids": prepared["observable_layer"]["workpaper_ids"],
                    "sources": prepared["observable_layer"]["sources"],
                    "omitted_source_locations": prepared["observable_layer"][
                        "omitted_source_locations"
                    ],
                    "checks": prepared["checks"],
                    "five_layer_review": prepared["five_layer_review"],
                    "experimental": True,
                    **stamped,
                }
            )
        elif kind == "review.experimental":
            if state["phase"] != "ACTIVE" or inference_result is None:
                raise DomainError("Experimental review requires an active engagement")
            state["reviews"].append({**inference_result, "experimental": True, **stamped})
        elif kind.startswith("scenario.custom."):
            from .custom import apply as apply_custom

            if state["phase"] != "CONFIGURING" or inference_result is None:
                raise DomainError("Custom authoring requires a configuring engagement")
            apply_custom(state, kind, inference_result)
        elif kind in {"scenario.custom", "voice.start"}:
            raise DomainError(
                "The requested inference adapter has not been configured",
                code="CAPABILITY_UNAVAILABLE",
                status=503,
            )
        else:
            raise DomainError(
                "Unsupported engagement command: " + str(kind), code="UNKNOWN_COMMAND"
            )
        state["events"].append(
            {"id": identifier("EV"), "kind": kind, "summary": kind.replace(".", " "), **stamped}
        )
        return state

    def _workspace_command(self, state: dict, kind: str, p: dict, stamped: dict) -> None:
        if state["phase"] != "ACTIVE":
            raise DomainError("Start the scoped kickoff before working with the company")
        actor = stamped["actor"]
        for field, collection in (
            ("control_id", "controls"),
            ("person_id", "people"),
            ("artifact_id", "artifacts"),
            ("request_id", "requests"),
        ):
            if p.get(field):
                find(state, collection, p[field])
        for artifact_id in self._identifier_list(p.get("evidence_ids", [])):
            find(state, "artifacts", artifact_id)
        if kind in {"task.create", "task.update"}:
            if kind.endswith("create"):
                work_type = p.get("test_type", "OTHER")
                if work_type not in {
                    "TOD",
                    "IMPLEMENTATION",
                    "TOE",
                    "SUBSTANTIVE",
                    "INTERIM",
                    "ROLL_FORWARD",
                    "OTHER",
                }:
                    raise DomainError("Invalid manually planned work type")
                row = {
                    "id": identifier("TASK"),
                    "title": require_text(p, "title"),
                    "status": "NOT_STARTED",
                    "conclusion": "NOT_RUN",
                    "history": [],
                    "control_id": p.get("control_id"),
                    "kind": work_type,
                    "test_type": work_type,
                    "rationale": p.get("rationale", ""),
                }
                state["tasks"].append(row)
            else:
                row = find(state, "tasks", p.get("id", p.get("task_id")))
            row["history"].append(
                {"status": row["status"], "conclusion": row["conclusion"], **stamped}
            )
            if "status" in p:
                if p["status"] not in {"NOT_STARTED", "IN_PROGRESS", "COMPLETE", "NOT_APPLICABLE"}:
                    raise DomainError("Invalid task progress")
                if p["status"] == "NOT_APPLICABLE":
                    row["rationale"] = require_text(p, "rationale")
                row["status"] = p["status"]
            if "conclusion" in p:
                if p["conclusion"] not in {
                    "NOT_RUN",
                    "PASS",
                    "FAIL",
                    "LIMITATION",
                    "NOT_APPLICABLE",
                }:
                    raise DomainError("Invalid manually recorded conclusion")
                require_text(p, "rationale")
                row["conclusion"], row["rationale"] = p["conclusion"], p["rationale"]
            if "note" in p:
                row["note"] = str(p["note"])[:20000]
            row.update(stamped)
        elif kind in {"note.create", "note.correct"}:
            text = require_text(p, "text")
            if kind.endswith("create"):
                source_message = p.get("source_message_id")
                known_messages = {
                    message["id"]
                    for meeting in state["meetings"]
                    for message in meeting.get("messages", [])
                }
                if source_message and source_message not in known_messages:
                    raise DomainError("Note source must be an existing engagement message")
                row = {
                    "id": identifier("NOTE"),
                    "text": text,
                    "title": p.get("title", ""),
                    "source_message_id": source_message,
                    "control_id": p.get("control_id"),
                    "person_id": p.get("person_id"),
                    "source_refs": [source_message] if source_message else [],
                    "classification": "LEARNER_NOTE",
                    "history": [],
                }
                state["notes"].append(row)
            else:
                row = find(state, "notes", p.get("id", p.get("note_id")))
                row["history"].append(
                    {"text": row["text"], "rationale": p.get("rationale", ""), **stamped}
                )
                row["text"] = text
            row.update(stamped)
        elif kind == "remediation.retest":
            finding = find(state, "findings", p.get("finding_id"))
            remediation = next(
                (r for r in finding.get("remediations", []) if r["id"] == p.get("remediation_id")),
                None,
            )
            if remediation is None:
                raise DomainError("Choose an existing remediation for this finding")
            test_date = date.fromisoformat(require_text(p, "test_date"))
            start, end = (
                date.fromisoformat(require_text(p, "period_start")),
                date.fromisoformat(require_text(p, "period_end")),
            )
            earliest = date.fromisoformat(remediation["simulated_at"][:10])
            today = date.fromisoformat(state["simulated_at"][:10])
            if not earliest <= start <= end <= test_date <= today:
                raise DomainError(
                    "Retest coverage must follow recorded remediation "
                    "and end by the actual simulation test date"
                )
            evidence_ids = self._identifier_list(p.get("evidence_ids", []))
            if not evidence_ids or any(
                find(state, "artifacts", a)["status"] != "AVAILABLE" for a in evidence_ids
            ):
                raise DomainError("Retesting requires available original evidence")
            result = require_text(p, "result")
            if result not in {"SUPPORTED_FOR_RETEST_PERIOD", "EXCEPTION_REMAINS", "INCONCLUSIVE"}:
                raise DomainError("Choose a prospective retest disposition")
            finding.setdefault("retests", []).append(
                {
                    "id": identifier("RETEST"),
                    "remediation_id": remediation["id"],
                    "test_date": test_date.isoformat(),
                    "coverage": {"period_start": start.isoformat(), "period_end": end.isoformat()},
                    "procedures": require_text(p, "procedures"),
                    "rationale": require_text(p, "rationale"),
                    "result": result,
                    "evidence_ids": evidence_ids,
                    "professional_sufficiency": "NOT_ASSERTED",
                    "original_finding_unchanged": True,
                    **stamped,
                }
            )
        elif kind in {"finding.create", "finding.update", "remediation.record"}:
            if kind == "finding.create":
                row = {
                    "id": identifier("FIND"),
                    "title": require_text(p, "title"),
                    "condition": require_text(p, "condition"),
                    "control_id": p.get("control_id"),
                    "criterion": p.get("criterion"),
                    "classification": p.get("classification"),
                    "evidence_ids": self._identifier_list(p.get("evidence_ids", [])),
                    "status": "OPEN",
                    "history": [],
                    "remediations": [],
                    "original_period": state["scope"],
                }
                state["findings"].append(row)
            else:
                row = find(state, "findings", p.get("id", p.get("finding_id")))
                row["history"].append({"status": row["status"], **stamped})
                if kind == "remediation.record":
                    row["remediations"].append(
                        {
                            "id": identifier("REM"),
                            "action": require_text(p, "action"),
                            "due_at": p.get("due_at"),
                            "retest_result": "NOT_RUN",
                            "claimed_status": p.get("status", "proposed"),
                            "evidence_ids": self._identifier_list(p.get("evidence_ids", [])),
                            "prospective_coverage": p.get("prospective_coverage"),
                            **stamped,
                        }
                    )
                    row["status"] = "REMEDIATION_PLANNED"
                else:
                    row["management_response"] = require_text(p, "response")
            row.update(stamped)
        elif kind in {"workpaper.add", "workpaper.update"}:
            from .workpaper_links import validate_task_ids

            prior = (
                None
                if kind.endswith("add")
                else find(state, "workpapers", p.get("id", p.get("workpaper_id")))
            )
            control_id = p.get("control_id") if prior is None else prior.get("control_id")
            previous_tasks = (
                prior["versions"][-1].get("task_ids", []) if prior and prior["versions"] else []
            )
            task_ids = validate_task_ids(state, control_id, p.get("task_ids", previous_tasks))
            if kind.endswith("add"):
                row = {
                    "id": identifier("WP"),
                    "title": require_text(p, "title"),
                    "versions": [],
                    "control_id": p.get("control_id"),
                    "prepared_by": actor,
                }
                state["workpapers"].append(row)
            else:
                row = find(state, "workpapers", p.get("id", p.get("workpaper_id")))
            row["versions"].append(
                {
                    "version": len(row["versions"]) + 1,
                    "task_ids": task_ids,
                    "text": p.get("text", ""),
                    "artifact_id": p.get("artifact_id"),
                    "section": p.get("section"),
                    "objective": p.get("objective"),
                    "procedures": p.get("procedures"),
                    "evidence_ids": self._identifier_list(p.get("evidence_ids", [])),
                    "conclusion": p.get("conclusion"),
                    **stamped,
                }
            )
            row.update(stamped)
        elif kind in {"review.comment", "review.resolve"}:
            if kind.endswith("comment"):
                workpaper = find(state, "workpapers", p.get("workpaper_id"))
                if workpaper["prepared_by"] == actor:
                    raise DomainError(
                        "Preparer cannot independently review their own work", status=403
                    )
                version_number = p.get("workpaper_version", workpaper["versions"][-1]["version"])
                reviewed = next(
                    (
                        version
                        for version in workpaper["versions"]
                        if version["version"] == version_number
                    ),
                    None,
                )
                if type(version_number) is not int or reviewed is None:
                    raise DomainError("Review must identify an existing workpaper version")
                if any(
                    version.get("actor") == actor and version["version"] <= version_number
                    for version in workpaper["versions"]
                ):
                    raise DomainError(
                        "A version contributor cannot independently review their own work",
                        status=403,
                    )
                from .review_anchor import normalize_anchor

                anchor = (
                    {"anchor": normalize_anchor(p["anchor"], reviewed)} if "anchor" in p else {}
                )
                state["reviews"].append(
                    {
                        "id": identifier("REVIEW"),
                        "workpaper_id": workpaper["id"],
                        "workpaper_version": version_number,
                        "workpaper_version_digest": digest(reviewed),
                        "comment": require_text(p, "comment"),
                        "status": "OPEN",
                        "kind": "HUMAN",
                        "history": [],
                        **anchor,
                        **stamped,
                    }
                )
            else:
                row = find(state, "reviews", p.get("id", p.get("review_id")))
                explicit_feedback = "disposition" in p
                disposition = p.get("disposition")
                if explicit_feedback and disposition not in (
                    "agree",
                    "disagree",
                    "correct",
                    "missing_context",
                    "human_review",
                ):
                    raise DomainError("Choose a supported review response disposition")
                response = require_text(p, "response")
                if row.get("kind") == "EXPERIMENTAL_AI":
                    if not explicit_feedback:
                        raise DomainError("Experimental suggestions require explicit feedback")
                    if "input_digest" in p and p["input_digest"] != row.get("input_digest"):
                        raise DomainError("Review input digest changed", status=409)
                    selected = (
                        row.get("input_layers", {})
                        .get("observable_layer", {})
                        .get("workpaper_ids", [])
                    )
                    papers = [find(state, "workpapers", paper_id) for paper_id in selected]
                    row.setdefault("appeals", []).append(
                        {
                            "disposition": disposition,
                            "response": response,
                            "input_digest": row.get("input_digest"),
                            "review_result_digest": digest(row.get("result")),
                            "response_workpaper_versions": [
                                {
                                    "workpaper_id": paper["id"],
                                    "version": paper["versions"][-1]["version"],
                                    "digest": digest(paper["versions"][-1]),
                                }
                                for paper in papers
                            ],
                            "professional_acceptance": "NOT_ASSERTED",
                            **stamped,
                        }
                    )
                    # Feedback never changes the suggestion, acceptance or original input pins.
                else:
                    if row.get("kind", "HUMAN") != "HUMAN" or not row.get("workpaper_id"):
                        raise DomainError("Only human comments or AI suggestions accept responses")
                    workpaper = find(state, "workpapers", row["workpaper_id"])
                    latest = workpaper["versions"][-1]
                    if not explicit_feedback and row.get("status") != "OPEN":
                        raise DomainError("Only an open human review can be resolved", status=409)
                    if not explicit_feedback and (
                        workpaper.get("prepared_by") == actor
                        or any(version.get("actor") == actor for version in workpaper["versions"])
                    ):
                        raise DomainError(
                            "A preparer or version contributor cannot independently resolve "
                            "a review of their own work",
                            status=403,
                        )
                    if "response_workpaper_version" in p and (
                        type(p["response_workpaper_version"]) is not int
                        or p["response_workpaper_version"] != latest["version"]
                    ):
                        raise DomainError("Response workpaper version changed", status=409)
                    entry = {
                        "status": row["status"],
                        "response": response,
                        "response_workpaper_version": latest["version"],
                        "response_workpaper_version_digest": digest(latest),
                        **stamped,
                    }
                    if explicit_feedback:
                        entry.update(
                            disposition=disposition, professional_acceptance="NOT_ASSERTED"
                        )
                    row.setdefault("history", []).append(entry)
                    # Omitted disposition preserves the existing independently role-gated action.
                    if not explicit_feedback:
                        row["status"] = "RESOLVED"
                if explicit_feedback:
                    row["latest_response_disposition"] = disposition
                    row["feedback_status"] = (
                        "HUMAN_REVIEW_REQUESTED"
                        if disposition == "human_review"
                        else "FEEDBACK_RECORDED"
                    )
        elif kind == "survey.submit":
            state["surveys"].append(
                {
                    "id": identifier("SURVEY"),
                    "feedback": require_text(p, "feedback"),
                    "realism": p.get("realism"),
                    "challenge": p.get("challenge"),
                    "clarity": p.get("clarity"),
                    "usability": p.get("usability"),
                    "evidence_quality": p.get("evidence_quality"),
                    "persona_consistency": p.get("persona_consistency"),
                    "feedback_usefulness": p.get("feedback_usefulness"),
                    "defect_reference": p.get("defect_reference"),
                    "external_telemetry": False,
                    "training_consent": False,
                    **stamped,
                }
            )
        elif kind == "meeting.create":
            person = find(state, "people", p.get("person_id"))
            if person.get("status") == "former_employee":
                raise DomainError("Former employee is not a current company contact")
            state["meetings"].append(
                {
                    "id": identifier("MTG"),
                    "title": require_text(p, "title"),
                    "person_id": person["id"],
                    "control_id": p.get("control_id"),
                    "scheduled_at": scoped_datetime(
                        p.get("scheduled_at") or state["simulated_at"], state["scope"]
                    ),
                    "messages": [],
                    "status": "OPEN",
                    "kind": "WALKTHROUGH",
                    **stamped,
                }
            )
        elif kind == "pbc.create":
            boundaries = state["scope"].get("boundaries", [])
            boundary = p.get("boundary_id") or (boundaries[0] if len(boundaries) == 1 else None)
            if boundary is not None and boundary not in boundaries:
                raise DomainError("Request boundary must be inside the engagement scope")
            state["requests"].append(
                {
                    "id": identifier("PBC"),
                    "title": require_text(p, "title"),
                    "purpose": require_text(p, "purpose"),
                    "boundary_id": boundary,
                    "control_id": p.get("control_id"),
                    "person_id": p.get("person_id"),
                    "status": "DRAFT",
                    "history": [],
                    "artifact_ids": [],
                    "due_at": p.get("due_at"),
                    **stamped,
                }
            )
        elif kind == "pbc.update":
            row = find(state, "requests", p.get("id", p.get("request_id")))
            status = p.get("status")
            if status not in {"CLARIFICATION", "ACCEPTED_FOR_PURPOSE", "WITHDRAWN", "CLOSED"}:
                raise DomainError("Invalid learner request disposition")
            rationale = require_text(p, "rationale")
            row["history"].append({"status": row["status"], "rationale": rationale, **stamped})
            row["status"] = status

    def _action_context(self, state: dict, meeting: dict) -> dict:
        coordinator = meeting.get("kind") == "KICKOFF"
        controls = [
            c
            for c in state["controls"]
            if coordinator or meeting["person_id"] in c.get("owner_ids", [])
        ]
        if meeting.get("control_id"):
            controls = [c for c in controls if c["id"] == meeting["control_id"]]
        control_ids = [c["id"] for c in controls]
        requests = [
            r
            for r in state["requests"]
            if r.get("control_id") in control_ids and r.get("status") not in {"CLOSED", "WITHDRAWN"}
        ][:30]
        people = sorted(
            {meeting["person_id"], *[p for c in controls for p in c.get("owner_ids", [])]}
        )
        drafts = [r["id"] for r in requests if r.get("status") == "DRAFT"]
        issued = [r["id"] for r in requests if r.get("status") != "DRAFT" and r.get("issued_at")]
        return {
            "allowed_actions": [
                "pbc.create",
                *(["pbc.issue"] if drafts else []),
                *(["pbc.followup"] if issued else []),
            ],
            "action_scope_by_kind": {
                "pbc.issue": {"request_ids": drafts},
                "pbc.followup": {"request_ids": issued},
                "pbc.create": {"control_ids": control_ids[:40], "person_ids": people[:40]},
            },
            "action_scope": {
                "control_ids": control_ids[:40],
                "person_ids": people[:40],
                "request_ids": [r["id"] for r in requests],
            },
            "requests": [
                {k: r.get(k) for k in ("id", "title", "status", "person_id", "control_id")}
                for r in requests
            ],
        }

    def _conversation(self, state: dict, p: dict, actor_id: str | None = None) -> dict:
        if state["phase"] != "ACTIVE":
            raise DomainError("Kickoff and scoped generation must precede company dialogue")
        text = require_text(p, "content", maximum=8000)
        meeting = find(state, "meetings", p.get("meeting_id"))
        consultation = None
        if "consultation" in p:
            from . import company_consultation

            consultation = company_consultation.prepare(self, actor_id, state, p)
        if meeting.get("scheduled_at") and datetime.fromisoformat(
            scoped_datetime(meeting["scheduled_at"], state["scope"]).replace("Z", "+00:00")
        ) > datetime.fromisoformat(state["simulated_at"].replace("Z", "+00:00")):
            raise DomainError("Advance simulation to the scheduled meeting")
        person = find(state, "people", meeting["person_id"])
        sources = [
            {"id": "ENGAGEMENT-SCOPE", "kind": "AGREED_TRAINING_SCOPE", "value": state["scope"]},
            {
                "id": "CONTACT-" + person["id"],
                "kind": "SCOPED_CONTACT",
                "value": {
                    "name": person["name"],
                    "title": person["title"],
                    "appointment_status": person.get("authority_status"),
                },
            },
        ]
        source_mode = state.get("evidence_acquisition") == "COMPANY_SOURCE_COLLECTION"
        if source_mode:
            if actor_id is None:
                raise DomainError("Authenticated company-source context required", status=403)
            from .company_persona import sources as company_sources

            if "source_records" in p and p["source_records"] is None:
                raise DomainError(
                    "Explicit source selection cannot be null", code="INVALID_SOURCE_SELECTION"
                )
            if consultation is not None and "source_records" not in p:
                from .company_persona import _notice

                sources.append(_notice())
            else:
                sources.extend(
                    company_sources(
                        self,
                        actor_id,
                        state,
                        person["id"],
                        selected_records=p.get("source_records"),
                    )
                )
        elif "source_records" in p:
            raise DomainError(
                "Explicit originals require company-source collection mode",
                code="INVALID_SOURCE_SELECTION",
            )
        if meeting.get("kind") == "KICKOFF":
            sources.append(
                {
                    "id": "REQUEST-PROTOCOL",
                    "kind": "ENGAGEMENT_FACT",
                    "value": {
                        "request_count": len(state["requests"]),
                        "protocol": (
                            "Issue requests in PBC and obtain existing company source records; "
                            "receipt is not acceptance."
                            if source_mode
                            else "Issue requests in PBC; original files arrive at their scheduled "
                            "availability. Receipt is not acceptance."
                        ),
                        "company_contacts": [
                            {"name": p["name"], "title": p["title"]}
                            for p in state["people"]
                            if p["id"].startswith("AS-")
                        ],
                        "period_end": state["scope"]["period_end"],
                        "simulated_at": state["simulated_at"],
                    },
                }
            )
        elif not source_mode:
            from .generation import epoch_directory, read_plan

            root = epoch_directory(self, state["id"], state.get("generation_epoch", 0))
            selected = [
                c
                for c in state["controls"]
                if person["id"] in c["assignment"]["proposed_contact_ids"]
                and (not meeting.get("control_id") or c["id"] == meeting["control_id"])
            ]
            for control in selected[:8]:
                sources.append(
                    {
                        "id": control["id"],
                        "kind": "CONTROL_RECORD",
                        "value": {
                            "statement": control["description"],
                            "frequency": control["frequency"],
                            "ownership": control["assignment"],
                        },
                    }
                )
                for request in state["requests"]:
                    if (
                        request.get("control_id") == control["id"]
                        and "plan_unit" in request
                        and request.get("plan_epoch", 0) == state.get("generation_epoch", 0)
                    ):
                        plan = read_plan(root / f"unit-{request['plan_unit']:05}.json")
                        for item in plan.get("actor_knowledge", []):
                            if item.get("person_id") == person["id"] and datetime.fromisoformat(
                                scoped_datetime(
                                    item.get("available_by", state["simulated_at"]),
                                    state["scope"],
                                    hour=0,
                                )
                            ) <= datetime.fromisoformat(
                                state["simulated_at"].replace("Z", "+00:00")
                            ):
                                sources.append(
                                    {
                                        "id": "KNOWLEDGE-" + request["id"],
                                        "kind": "PERSONA_KNOWLEDGE",
                                        "value": item["summary"],
                                    }
                                )
                        break
        if consultation is not None:
            sources.extend(company_consultation.context_sources(consultation))
        context = {
            **self._action_context(state, meeting),
            "allowed_roles": ["persona"],
            "source_ids": [s["id"] for s in sources],
            "sources": sources,
            "simulated_at": state["simulated_at"],
            "person": {"name": person["name"], "title": person["title"]},
            "action_boundary": (
                "You may propose only listed scoped commands. Do not claim "
                "success: the engine independently revalidates and applies them, "
                "then supplies separate actual receipts."
            ),
        }
        if consultation is not None:
            context["allowed_actions"] = []
            context["consultation"] = {
                "kind": consultation["requested"]["kind"],
                "has_prior_response": consultation["response"] is not None,
                "request_authorship": "LEARNER_REQUESTED_COMPANY_CONSULTATION",
                "boundary": "Historical statements are attributed context. "
                "They are not newly verified facts. "
                "Choose the explicit reply relation; a correction remains your company statement. "
                "Unsupported facts remain unknown. "
                "Do not claim nonexistent sources or staff absence.",
            }
        if self.inference_config is None:
            raise DomainError(
                "Company dialogue requires the configured local inference runtime",
                code="CAPABILITY_UNAVAILABLE",
                status=503,
            )
        from .inference import LocalInference

        messages = [{"role": m["role"], "content": m["content"]} for m in meeting["messages"][-8:]]
        messages.append({"role": "user", "content": text})
        provider = LocalInference(self.inference_config)
        result = provider.generate("persona", context, messages)
        if consultation is not None:
            company_consultation.validate_reply(result, consultation)
            company_consultation.revalidate(
                self,
                actor_id,
                state,
                p,
                consultation,
                company_consultation.source_manifest(sources),
            )
        message_ids = {"user": identifier("MSG"), "company": identifier("MSG")}
        result["message_ids"] = message_ids
        result["extracted_notes"] = provider.generate(
            "note_extraction",
            {
                "allowed_roles": ["note_extraction"],
                **(
                    {
                        "attributed_consultation": {
                            **consultation["requested"],
                            "relation": result["consultation_relation"],
                            "authority": "ATTRIBUTED_STATEMENT_NOT_VERIFIED_CORRECTION",
                        }
                    }
                    if consultation is not None
                    else {}
                ),
                "source_ids": list(message_ids.values()),
                "sources": [
                    {"id": message_ids["user"], "text": text, "speaker_role": "LEARNER"},
                    {
                        "id": message_ids["company"],
                        "text": result["text"],
                        "speaker_role": "COMPANY",
                        "person_id": person["id"],
                    },
                ],
            },
            [
                {
                    "role": "user",
                    "content": (
                        "Summarize the exchange as attributed statements, preserving uncertainty. "
                        "Each material claim must cite its actual message ID. Preserve the learner "
                        "and company speakers separately. Do not infer no-change from silence. "
                        "Do not treat a company claim as verified evidence. "
                        "If an attributed consultation relation is supplied, retain its "
                        "explicit historical-question/response linkage and speaker distinction."
                    ),
                }
            ],
        )
        if consultation is not None:
            manifest = company_consultation.source_manifest(sources)
            company_consultation.revalidate(self, actor_id, state, p, consultation, manifest)
            result["consultation_prepared"] = consultation
            result["consultation_source_manifest"] = manifest
        return result

    def _export(self, state: dict, p: dict, stamped: dict) -> None:
        if p.get("edition", "LEARNER").upper() == "REVIEWER":
            from .private_review_export import build

            manifest = build(self, state, stamped["actor"])
            manifest.update(
                kind="export",
                edition="REVIEWER",
                audience="REVIEWER",
                created_at=stamped.get("recorded_at"),
            )
            state["artifacts"].append(manifest)
            return
        if p.get("edition", "LEARNER").upper() not in {"LEARNER", "EVIDENCE"}:
            raise DomainError(
                "Private reviewer export requires separately authorized instructor route",
                status=403,
            )
        snapshot = self.learner_snapshot(state)
        manifests = list(snapshot["artifacts"])
        history = self.store.history(stamped["actor"], state["id"])
        history = copy.deepcopy(history)
        for entry in history:
            entry["state"] = self.learner_snapshot(entry["state"])
            if entry.get("command", {}).get("kind", "").startswith("scenario.custom."):
                entry["command"] = {"kind": "private_authoring", "payload": "WITHHELD"}
            elif isinstance(entry.get("command", {}).get("payload"), dict):
                for private_key in (
                    "configuration",
                    "custom_drafts",
                    "private_seed",
                    "selected_variants",
                ):
                    entry["command"]["payload"].pop(private_key, None)
            entry["projection"] = (
                "LEARNER; original full-state hash retained, not a hash of this projection"
            )

        # The export snapshot precedes its own export event; that boundary is explicit.
        buf = io.BytesIO(
            self.artifacts.bundle(
                manifests, index={"engagement": state["id"], "revision": state["revision"]}
            )
        )
        with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("engagement.json", canonical(snapshot))
            archive.writestr("history.json", canonical(history))
            links = "".join(
                f"<li><a href='files/{html.escape(m['id'])}/{html.escape(m['name'])}'>"
                f"{html.escape(m['name'])}</a> — {html.escape(m['sha256'])}</li>"
                for m in manifests
            )
            archive.writestr(
                "index.html",
                "<!doctype html><meta charset='utf-8'><title>Training review</title>"
                f"<h1>{html.escape(state['title'])}</h1>"
                "<p>Synthetic training record. Human review edition. "
                "No issued professional opinion or objective audit grade.</p>"
                "<p><a href='engagement.json'>Full engagement</a> · <a "
                "href='history.json'>Retained history</a>"
                " · <a href='manifest.json'>Original-file manifest</a></p><ul>" + links + "</ul>",
            )
        data = buf.getvalue()
        # ZIP is an app-produced download, never previewed or treated as an imported workbook.
        manifest = self.artifacts.retain_export(
            state["id"],
            f"{state['id']}-review-r{state['revision']}.zip",
            data,
            source={"kind": "HUMAN_REVIEW_EXPORT", "revision": state["revision"]},
            coverage=state["scope"],
        )
        manifest.update(
            status="AVAILABLE",
            quarantine_reason=None,
            mime="application/zip",
            kind="export",
            edition=p.get("edition", "LEARNER").upper(),
            created_at=stamped.get("recorded_at"),
        )
        state["artifacts"].append(manifest)

    @staticmethod
    def _population(row: dict) -> populations.Population:
        data = row["immutable"]
        return populations.Population(**{**data, "records_json": tuple(data["records_json"])})

    @staticmethod
    def _selection(row: dict) -> populations.Selection:
        data = row["immutable"]
        return populations.Selection(
            **{
                **data,
                "selected_ids": tuple(data["selected_ids"]),
                "targeted_ids": tuple(data["targeted_ids"]),
            }
        )

    def _population_command(self, state: dict, kind: str, p: dict, stamped: dict) -> None:
        if state["phase"] != "ACTIVE":
            raise DomainError("Kickoff must precede population work")
        from .population_lifecycle import COMMANDS, handle

        if kind == "population.request_support":
            from .parent_support import create_request

            state["requests"].append(create_request(self, state, p, stamped))
            return
        if kind in COMMANDS:
            if kind == "population.assess":
                p = {
                    **p,
                    "observable_artifact_ids": self._identifier_list(
                        p.get("observable_artifact_ids", [])
                    ),
                }
            handle(state, kind, p, stamped, self.artifacts)
            return
        if kind == "population.calculate":
            rationale = require_text(p, "rationale")
            if p.get("method") == "manual_methodology":
                result = {
                    "method": "EXTERNAL_METHODOLOGY",
                    "sample_size": None,
                    "limitation": (
                        "Record the selected external method and its calculation separately"
                    ),
                }
            elif p.get("method") == "zero_deviation_attribute":
                from decimal import Decimal

                result = populations.attribute_size(
                    1 - Decimal(str(p.get("confidence"))),
                    p.get("tolerable_rate"),
                    population_size=int(p["population_size"]),
                )
            elif p.get("method") == "monetary":
                result = populations.monetary_size(
                    p["total_book_value"],
                    p["tolerable_misstatement"],
                    p["alpha"],
                    expected_misstatement=p.get("expected_misstatement", "0"),
                )
            else:
                raise DomainError("Unknown calculation method")
            state.setdefault("calculations", []).append(
                {
                    "id": identifier("CALC"),
                    "inputs": p,
                    "result": result,
                    "rationale": rationale,
                    **stamped,
                }
            )
        elif kind == "population.import":
            artifact = find(state, "artifacts", p.get("artifact_id"))
            if artifact["status"] != "AVAILABLE":
                raise DomainError("Quarantined content cannot become a working population")
            # The supplied rows and authority representation remain learner assertions;
            # hidden census rows are neither compared nor revealed here.
            parent = parent_selection = None
            if p.get("parent_selection_id"):
                selected = find(state, "selections", p["parent_selection_id"])
                parent_selection = self._selection(selected)
                parent = self._population(find(state, "populations", selected["population_id"]))
            obj = populations.create_population(
                identifier("POP"),
                1,
                p.get("rows", []),
                scope=p.get("scope", {}),
                source={**p.get("source", {}), "original_sha256": artifact["sha256"]},
                parent_population=parent,
                parent_selection=parent_selection,
                parent_key=p.get("parent_key"),
            )
            state["populations"].append(
                {
                    "id": obj.id,
                    "title": require_text(p, "title"),
                    "version": obj.version,
                    "count": len(obj.rows),
                    "rows": list(obj.rows),
                    "status": obj.status,
                    "artifact_id": artifact["id"],
                    "parent_selection_id": p.get("parent_selection_id"),
                    "immutable": asdict(obj),
                    **stamped,
                }
            )
        elif kind == "population.select":
            row = find(state, "populations", p.get("population_id"))
            obj = self._population(row)
            method = str(p.get("method", "")).upper()
            method = {"ENTIRE_POPULATION": "ENTIRE", "NESTED": "SIMPLE_RANDOM"}.get(method, method)
            supplied_ids = p.get("selected_ids", p.get("ids", []))
            if isinstance(supplied_ids, str):
                supplied_ids = [i.strip() for i in supplied_ids.splitlines() if i.strip()]
            targeted = p.get("targeted_ids", [])
            if isinstance(targeted, str):
                targeted = [i.strip() for i in targeted.splitlines() if i.strip()]
            if p.get("parent_selection_id") != row.get("parent_selection_id") and p.get(
                "parent_selection_id"
            ):
                raise DomainError("Selection parent differs from supplied population lineage")
            selected = populations.select(
                obj,
                selection_id=identifier("SEL"),
                method=method,
                purpose=require_text(p, "purpose"),
                rationale=p.get("rationale") or require_text(p, "purpose"),
                seed=p.get("seed") or None,
                size=int(p["size"]) if p.get("size") else None,
                ids=supplied_ids,
                targeted_ids=targeted,
                strata=p.get("strata"),
                amount_field=p.get("amount_field"),
            )
            state["selections"].append(
                {
                    "id": selected.id,
                    "population_id": obj.id,
                    "population_version": obj.version,
                    "selected_ids": list(selected.selected_ids),
                    "targeted_ids": list(selected.targeted_ids),
                    "method": selected.method,
                    "purpose": selected.purpose,
                    "rationale": selected.rationale,
                    "provisional": selected.provisional,
                    "parent_selection_id": row.get("parent_selection_id"),
                    "immutable": asdict(selected),
                    **stamped,
                }
            )
        elif kind == "selection.revise":
            row = find(state, "selections", p.get("selection_id"))
            obj = self._population(find(state, "populations", row["population_id"]))
            revised = populations.revise_selection(
                obj,
                self._selection(row),
                selection_id=identifier("SEL"),
                add_ids=p.get("add_ids", []),
                remove_ids=p.get("remove_ids", []),
                rationale=require_text(p, "rationale"),
                methodology_authorizes_replacement=p.get("methodology_authorizes_replacement")
                is True,
            )
            state["selections"].append(
                {
                    **row,
                    "id": revised.id,
                    "selected_ids": list(revised.selected_ids),
                    "targeted_ids": list(revised.targeted_ids),
                    "immutable": asdict(revised),
                    "predecessor_id": row["id"],
                    **stamped,
                }
            )
        else:
            raise DomainError("Unsupported population operation")

    def _advance(self, state: dict, p: dict, stamped: dict) -> None:
        if state["phase"] != "ACTIVE":
            raise DomainError("Start kickoff before advancing company time")
        data = state.get("clock", {"simulated_at": state["simulated_at"]})
        clock = SimulationClock(
            data["simulated_at"],
            tuple(tuple(v) for v in data.get("completed", [])),
            data.get("plan_digest"),
            tuple(tuple(v) for v in data.get("requests", [])),
        )
        events = [
            ScheduledEvent(
                e["id"],
                scoped_datetime(e["scheduled_at"], state["scope"]),
                tuple(e.get("requires", [])),
                canonical(e.get("effects", {})),
            )
            for e in state.get("scheduled_events", [])
        ]
        mode = str(p.get("mode", p.get("action", ""))).upper()
        mode = {"BUSINESS_DAY": "ONE_BUSINESS_DAY", "DATE": "TARGET_DATE"}.get(mode, mode)
        target = p.get("target")
        if mode == "NEXT_EVENT":
            due = [r["next_available_at"] for r in state["requests"] if r.get("next_available_at")]
            if due:
                target = min(
                    due, key=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
                )
                mode = "TARGET_DATE"
        if target:
            target = scoped_datetime(target, state["scope"])
        advanced, emitted = advance(
            clock,
            events,
            action=mode,
            target=target,
            milestones=state.get("milestones", {}),
            timezone_name=state["scope"].get("timezone", "UTC"),
        )
        state["clock"] = asdict(advanced)
        state["simulated_at"] = advanced.simulated_at
        for event in emitted:
            state["calendar"].append(
                {
                    "id": event["event_id"],
                    "title": "Scheduled company event",
                    "status": "COMPLETED",
                    **event,
                }
            )
        self._deliver_due(state, stamped)

    def _request_command(self, state: dict, kind: str, p: dict, stamped: dict) -> None:
        if state["phase"] != "ACTIVE":
            raise DomainError("Kickoff must precede evidence exchange")
        request = find(state, "requests", p.get("request_id", p.get("id")))
        if kind == "pbc.read":
            request["unread"] = False
            return
        if request["status"] in {"CLOSED", "WITHDRAWN"}:
            raise DomainError("Reopen or issue a new request before additional exchange")
        if kind == "pbc.issue" and request["status"] != "DRAFT":
            raise DomainError("Request is already issued; use follow-up")
        if kind == "pbc.followup" and (
            request["status"] == "DRAFT" or not request.get("issued_at")
        ):
            raise DomainError("Issue the initial request before following up")
        request["history"].append(
            {"status": request["status"], "message": p.get("message", "Issued request"), **stamped}
        )
        request["status"] = "ISSUED" if kind == "pbc.issue" else "CLARIFICATION"
        if not request.get("issued_at"):
            request["issued_at"] = state["simulated_at"]
        if kind == "pbc.followup":
            require_text(p, "message")
            request["followup_count"] = request.get("followup_count", 0) + 1
        if p.get("due_at"):
            request["due_at"] = p["due_at"]
        self._deliver_due(
            state,
            stamped,
            triggered_request=request["id"],
            trigger="REQUEST" if kind == "pbc.issue" else "FOLLOWUP",
        )

    def _deliver_due(
        self,
        state: dict,
        stamped: dict,
        *,
        triggered_request: str | None = None,
        trigger: str = "CLOCK",
    ) -> None:
        from .generation import request_plan

        now = datetime.fromisoformat(state["simulated_at"].replace("Z", "+00:00"))
        for request in state["requests"]:
            if request["status"] not in {"ISSUED", "CLARIFICATION", "IN_PROGRESS", "ACKNOWLEDGED"}:
                continue
            if request.get("parent_support"):
                from .parent_support import request_plan as support_plan

                plan = support_plan(self, state, request)
            else:
                plan = request_plan(self, state, request)
            if plan is None:
                request["status"] = "ACKNOWLEDGED"
                request["client_response"] = (
                    "The request is recorded. Identify its source or linked control "
                    "to route supporting records."
                )
                continue
            arrived, pending = [], []
            definition = plan.get("scenario_definition")
            if definition:
                from .composition import advance_events, observable_effects

                progress, effects = advance_events(
                    definition,
                    request.get("scenario_progress"),
                    trigger=trigger if request["id"] == triggered_request else "CLOCK",
                    now=state["simulated_at"],
                    timezone=state["scope"].get("timezone", "UTC"),
                    holidays=state["scope"].get("holidays", []),
                )
                if any(e["operation"] == "availability" for e in effects):
                    raise DomainError(
                        "This availability rule requires an implemented adapter",
                        code="UNSUPPORTED_SCENARIO_OPERATION",
                    )
                request["scenario_progress"] = progress
                released = set(request.get("scenario_released", []))
                released.update(
                    e["target"] for e in effects if e["operation"] == "release_artifact"
                )
                request["scenario_released"] = sorted(released)
                pending.extend(
                    value
                    for key, value in progress["armed"].items()
                    if key not in progress["completed"]
                )
                for notice in observable_effects(effects):
                    row = {
                        "id": identifier("NOTICE"),
                        "request_id": request["id"],
                        "control_id": request.get("control_id"),
                        "classification": "COMPANY_NOTICE",
                        "source_refs": [],
                        "history": [],
                        **notice,
                        **stamped,
                    }
                    state["notes"].append(row)
                    if notice["kind"] == "scope_change":
                        state.setdefault("scope_change_proposals", []).append(
                            {**row, "status": "PROPOSED"}
                        )

            for manifest in plan["prepared_artifacts"]:
                if definition and manifest.get("scenario_artifact_id") not in request.get(
                    "scenario_released", []
                ):
                    continue
                if manifest["id"] in request["artifact_ids"]:
                    continue
                available = (
                    manifest.get("available_at")
                    or request.get("issued_at")
                    or state["simulated_at"]
                )
                if len(available) == 10:
                    available = scoped_datetime(available, state["scope"], hour=0)
                if datetime.fromisoformat(available.replace("Z", "+00:00")) > now:
                    pending.append(available)
                    continue
                state["artifacts"].append(
                    {
                        **{
                            k: v
                            for k, v in manifest.items()
                            if k not in {"scenario_artifact_id", "stage"}
                        },
                        "received_at": state["simulated_at"],
                        "request_id": request["id"],
                    }
                )
                request["artifact_ids"].append(manifest["id"])
                arrived.append(manifest["id"])
                if request.get("parent_support"):
                    from .parent_support import import_delivered_population

                    import_delivered_population(self, state, manifest, request, stamped)
                elif manifest["name"] == "occurrence-population.csv":
                    self._population_from_artifact(state, manifest, request, stamped)
            if arrived:
                request["unread"] = True
                request["history"].append(
                    {"status": "SUBMITTED", "artifact_ids": arrived, **stamped}
                )
            request["status"] = (
                "IN_PROGRESS"
                if pending
                else ("SUBMITTED" if request["artifact_ids"] else "ACKNOWLEDGED")
            )
            request["client_response"] = (
                "The records are not yet available for the requested period."
                if pending
                else (
                    "The currently released records have been supplied for your evaluation."
                    if request["artifact_ids"]
                    else "The request is acknowledged; no record has been released yet."
                )
            )
            request["next_available_at"] = min(pending) if pending else None

    def _population_from_artifact(
        self, state: dict, manifest: dict, request: dict, stamped: dict
    ) -> None:
        if manifest["status"] != "AVAILABLE" or any(
            p.get("artifact_id") == manifest["id"] for p in state["populations"]
        ):
            return
        rows = list(csv.DictReader(io.StringIO(self.artifacts.read(manifest).decode("utf-8-sig"))))
        if not rows or not all(r.get("record_id") or r.get("id") for r in rows):
            request["population_import_error"] = "Source rows require stable item identifiers"
            return
        rows = [{**r, "id": r.get("id") or r["record_id"]} for r in rows]
        scope = {
            "boundary_id": request["boundary_id"],
            "unit": request["control_id"] + " occurrence",
            "timezone": state["scope"].get("timezone", "UTC"),
            "period_start": scoped_datetime(state["scope"]["period_start"], state["scope"], hour=0),
            "period_end": datetime.fromisoformat(
                scoped_datetime(state["scope"]["period_end"], state["scope"], hour=23)
            )
            .replace(minute=59, second=59)
            .isoformat(),
        }
        source = {
            "source_id": manifest["id"],
            "query": request["purpose"],
            "original_sha256": manifest["sha256"],
            "completeness_representation": (
                "Client-supplied occurrence export; learner has not established completeness"
            ),
        }
        try:
            obj = populations.create_population(
                identifier("POP"), 1, rows, scope=scope, source=source
            )
        except ValueError as exc:
            request["population_import_error"] = str(exc)
            return
        state["populations"].append(
            {
                "id": obj.id,
                "title": scope["unit"],
                "version": 1,
                "count": len(rows),
                "rows": rows,
                "status": obj.status,
                "artifact_id": manifest["id"],
                "request_id": request["id"],
                "immutable": asdict(obj),
                **stamped,
            }
        )
