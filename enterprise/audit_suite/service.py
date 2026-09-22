"""Loopback training service. No external deployment is implied by this entrypoint."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import re
import time
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .artifacts import MAX_BYTES
from .engine import Engine, find
from .store import DomainError


class RequestLimits:
    """Bounded process-local abuse limits for this single-process local service."""

    def __init__(self):
        self.entries = OrderedDict()

    def check(self, bucket: str, identity: str, limit: int, window: int = 60):
        now = time.monotonic()
        key = (bucket, identity)
        started, count = self.entries.pop(key, (now, 0))
        if now - started >= window:
            started, count = now, 0
        self.entries[key] = (started, count + 1)
        while len(self.entries) > 2048:
            self.entries.popitem(last=False)
        if count >= limit:
            raise DomainError(
                "Local request rate exceeded; retry after one minute", code="RATE_LIMIT", status=429
            )


class BodyLimit:
    def __init__(self, app, limit: int = MAX_BYTES + 65536):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        declared = next(
            (v for k, v in scope.get("headers", []) if k.lower() == b"content-length"), b""
        )
        if declared.isdigit() and int(declared) > self.limit:
            return await JSONResponse(
                {"error": "Request exceeds upload limit", "code": "TOO_LARGE"}, status_code=413
            )(scope, receive, send)
        total = 0

        async def bounded_receive():
            nonlocal total
            message = await receive()
            total += len(message.get("body", b""))
            if total > self.limit:
                raise DomainError("Request exceeds upload limit", code="TOO_LARGE", status=413)
            return message

        await self.app(scope, bounded_receive, send)


def load_company_bindings(path: Path | None) -> dict:
    """Read operator-owned configuration, never HTTP input or caller identity claims."""
    if path is None:
        return {}
    import os
    import re
    import stat

    from .inference import _json

    path = Path(path).absolute()
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise DomainError("Company binding aliases forbidden")
    if not path.parent.is_dir() or path.parent.stat().st_mode & 0o077:
        raise DomainError("Company bindings require a private directory")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size > 1024 * 1024:
            raise DomainError("Company bindings require a bounded private regular file")
        try:
            value = _json(stream.read(1024 * 1024 + 1))
        except (ValueError, TypeError) as error:
            raise DomainError("Invalid company bindings JSON") from error
    pattern = r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}"
    if not isinstance(value, dict):
        raise DomainError("Company bindings must be an engagement mapping")
    for engagement, selected in value.items():
        if (
            not re.fullmatch(pattern, engagement)
            or not isinstance(selected, dict)
            or set(selected)
            not in ({"company", "branch"}, {"company", "branch", "registry_sha256"})
            or (
                "registry_sha256" in selected
                and not re.fullmatch(r"[0-9a-f]{64}", str(selected["registry_sha256"]))
            )
            or any(
                not isinstance(v, str) or not re.fullmatch(pattern, v) for v in selected.values()
            )
        ):
            raise DomainError("Invalid company binding schema")
    return value


def create_app(
    private_root: Path,
    *,
    repository: Path | None = None,
    web_root: Path | None = None,
    secure_cookie: bool = True,
    allowed_hosts: list[str] | None = None,
    inference_config: Path | None = None,
    voice_config: Path | None = None,
    corpus_root: Path | None = None,
    program_pack: Path | None = None,
    company_root: Path | None = None,
    company_bindings: Path | None = None,
    company_registry: Path | None = None,
    company_profile: str | None = None,
    instructor_key_root: Path | None = None,
    instructor_bindings: Path | None = None,
    background_jobs: bool = False,
    workspace_contexts: bool = False,
) -> FastAPI:
    if company_bindings is not None and company_root is None and company_registry is None:
        raise DomainError("Company root or registry required with bindings")
    from .bound_instructor import load_bindings as load_instructor_bindings

    protected_bindings = load_instructor_bindings(instructor_bindings)
    bindings = load_company_bindings(company_bindings)
    key_pin = None
    key_files = None

    def verified_keys():
        import hashlib
        import json
        import re

        from .instructor_key import verify_archive

        if instructor_key_root is None:
            raise DomainError("Instructor reference library is not configured", status=503)
        root = Path(instructor_key_root).absolute()
        try:
            if any(p.is_symlink() for p in [root, *root.parents]) or not root.is_dir():
                raise ValueError
            if root.stat().st_mode & 0o077:
                raise ValueError
            fingerprints = {}
            for path in root.rglob("*"):
                if path.is_symlink() or path.stat().st_mode & 0o077:
                    raise ValueError
                if not (path.is_dir() or path.is_file()):
                    raise ValueError
                if path.is_file():
                    fingerprints[path.relative_to(root).as_posix()] = hashlib.sha256(
                        path.read_bytes()
                    ).hexdigest()
            if key_files is not None and fingerprints != key_files:
                raise ValueError
            index = json.loads((root / "index.json").read_bytes())
            receipt = json.loads((root / "receipt.json").read_bytes())
            for entry in index["entries"]:
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", entry["id"]):
                    raise ValueError
            pin = hashlib.sha256((root / "receipt.json").read_bytes()).hexdigest()
            if key_pin is not None and pin != key_pin:
                raise ValueError
            if key_files is None:
                verify_archive(root)
            return root, index, receipt, pin, fingerprints
        except Exception as error:
            raise DomainError("Instructor reference integrity check failed", status=503) from error

    if instructor_key_root is not None:
        initial_keys = verified_keys()
        key_pin, key_files = initial_keys[3], initial_keys[4]
    limits = RequestLimits()
    engine = Engine(
        private_root,
        inference_config=inference_config,
        voice_config=voice_config,
        corpus_root=corpus_root,
        program_pack=program_pack,
        company_root=company_root,
        company_bindings=bindings,
        company_registry=company_registry,
        company_profile=company_profile,
        **({"repository": repository} if repository else {}),
    )
    # Cookies are scoped by host/path, not port. Separate local workrooms must
    # not overwrite each other's browser sessions. This is a stable namespace,
    # not a secret or an authorization decision; Store still validates tokens.
    session_cookie_name = (
        "sh_audit_session_"
        + hashlib.sha256(str(engine.store.root.resolve()).encode("utf-8")).hexdigest()[:32]
    )
    app = FastAPI(
        title="Sable Harbor audit training", docs_url=None, redoc_url=None, openapi_url=None
    )
    app.state.engine = engine
    jobs = None
    if background_jobs:
        from .background_jobs import BackgroundJobs

        job_root = engine.store.root / "background-jobs"
        job_root.mkdir(mode=0o700, exist_ok=True)
        jobs = BackgroundJobs(job_root, engine, max_workers=2, max_pending=32)
    contexts = None
    personal_views = None
    handoffs = None
    work_guidance = None
    if workspace_contexts:
        from .investigation_handoffs import InvestigationHandoffs
        from .personal_views import PersonalViews
        from .work_guidance import WorkGuidance
        from .workspace_context import WorkspaceContexts

        context_root = engine.store.root / "workspace-contexts"
        context_root.mkdir(mode=0o700, exist_ok=True)
        contexts = WorkspaceContexts(context_root, engine)
        view_root = engine.store.root / "personal-views"
        view_root.mkdir(mode=0o700, exist_ok=True)
        personal_views = PersonalViews(view_root, engine)
        handoff_root = engine.store.root / "investigation-handoffs"
        handoff_root.mkdir(mode=0o700, exist_ok=True)
        handoffs = InvestigationHandoffs(handoff_root, engine)
        guidance_root = engine.store.root / "work-guidance"
        guidance_root.mkdir(mode=0o700, exist_ok=True)
        work_guidance = WorkGuidance(guidance_root, engine)
    releases = None
    assessments = None
    if protected_bindings:
        from .instructor_assessments import InstructorAssessments
        from .instructor_releases import InstructorReleases

        release_root = engine.store.root / "instructor-releases"
        release_root.mkdir(mode=0o700, exist_ok=True)
        releases = InstructorReleases(release_root, engine, protected_bindings)
        assessment_root = engine.store.root / "instructor-assessments"
        assessment_root.mkdir(mode=0o700, exist_ok=True)
        assessments = InstructorAssessments(assessment_root, engine, protected_bindings)
    app.state.instructor_releases = releases
    app.state.instructor_assessments = assessments
    key_views = None
    if protected_bindings or instructor_key_root is not None:
        from .instructor_key_views import InstructorKeyViews

        key_view_root = engine.store.root / "instructor-key-views"
        key_view_root.mkdir(mode=0o700, exist_ok=True)
        key_views = InstructorKeyViews(
            key_view_root, engine, protected_bindings, archive_root=instructor_key_root
        )
    app.state.instructor_key_views = key_views
    app.state.workspace_contexts = contexts
    app.state.personal_views = personal_views
    app.state.investigation_handoffs = handoffs
    app.state.work_guidance = work_guidance
    app.state.background_jobs = jobs
    app.state.generation_jobs = {}
    app.add_middleware(BodyLimit)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=allowed_hosts or ["localhost", "127.0.0.1", "[::1]"]
    )

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return JSONResponse({"error": str(exc), "code": exc.code}, status_code=exc.status)

    @app.middleware("http")
    async def headers_and_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
            try:
                parsed = urlsplit(origin)
                if parsed.scheme != request.url.scheme or parsed.netloc != request.headers.get(
                    "host"
                ):
                    return JSONResponse(
                        {"error": "Cross-origin mutation rejected"}, status_code=403
                    )
            except ValueError:
                return JSONResponse({"error": "Invalid origin"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(self)"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    def actor(request: Request, *, mutation: bool = False) -> dict:
        bearer = request.headers.get("authorization", "")
        if bearer:
            if not bearer.startswith("Bearer "):
                raise DomainError("Bearer credential required", status=401)
            return engine.store.authenticate(bearer[7:])
        return engine.store.session(
            request.cookies.get(session_cookie_name, ""),
            csrf=request.headers.get("x-csrf-token"),
            mutation=mutation,
        )

    async def json_body(request: Request) -> dict:
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise DomainError("JSON content type required", status=415)
        try:
            from .inference import _json

            value = _json(await request.body())
        except DomainError:
            raise
        except ValueError as exc:
            raise DomainError("Invalid JSON") from exc
        if not isinstance(value, dict):
            raise DomainError("JSON object required")
        return value

    @app.post("/api/session")
    async def login(request: Request):
        limits.check("login", request.client.host if request.client else "local", 30)
        body = await json_body(request)
        credential = body.get("credential")
        if not isinstance(credential, str) or len(credential) > 512:
            raise DomainError("Credential required", status=401)
        session = await asyncio.to_thread(engine.store.login, credential)
        response = JSONResponse({"viewer": session["viewer"], "csrf_token": session["csrf"]})
        response.set_cookie(
            session_cookie_name,
            session["token"],
            httponly=True,
            secure=secure_cookie,
            samesite="strict",
            max_age=3600,
            path="/",
        )
        return response

    @app.post("/api/logout")
    async def logout(request: Request):
        actor(request, mutation=True)
        engine.store.logout(request.cookies.get(session_cookie_name, ""))
        response = JSONResponse({"logged_out": True})
        response.delete_cookie(session_cookie_name, path="/")
        return response

    @app.get("/api/bootstrap")
    async def bootstrap(request: Request):
        result = await asyncio.to_thread(engine.bootstrap, actor(request))
        result["capabilities"].update(
            work_status=True,
            workspace_contexts=contexts is not None,
            personal_views=personal_views is not None,
            investigation_handoffs=handoffs is not None,
            work_guidance=work_guidance is not None,
            background_jobs=jobs is not None,
            bound_instructor_keys=bool(protected_bindings),
            instructor_releases=releases is not None,
            instructor_debriefs=releases is not None,
            instructor_key_views=key_views is not None,
            instructor_assessments=assessments is not None,
            instructor_reference_library=instructor_key_root is not None,
        )
        result["background_command_kinds"] = jobs.supported_commands() if jobs is not None else []
        return result

    @app.get("/api/openapi.json")
    async def schema(request: Request):
        actor(request)
        return app.openapi()

    @app.post("/api/engagements")
    async def create(request: Request):
        principal = actor(request, mutation=True)
        payload = await json_body(request)
        return await asyncio.to_thread(engine.create, principal["id"], payload)

    @app.get("/api/engagements/{engagement_id}")
    async def get(engagement_id: str, request: Request):
        return await asyncio.to_thread(engine.get, actor(request)["id"], engagement_id)

    @app.get("/api/engagements/{engagement_id}/work-status")
    async def work_status(engagement_id: str, request: Request):
        from .audit_readiness import report

        return await asyncio.to_thread(report, engine, actor(request)["id"], engagement_id)

    def instructor_reference_value(principal, engagement_id, scenario_id=None):
        import hashlib
        import json
        import re

        if engine.store.membership(principal["id"], engagement_id) != "instruct":
            raise DomainError("Instructor membership required", status=403)
        if scenario_id is not None and not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", scenario_id
        ):
            raise DomainError("Instructor reference not found", status=404)
        root, index, receipt, _, _ = verified_keys()
        metadata = {
            "status": "UNBOUND_REFERENCE_LIBRARY",
            "binding": {"status": "NOT_BOUND", "engagement_id": engagement_id},
            "archive": {"sha256": receipt["archive_sha256"]},
        }
        if scenario_id is None:
            return {**index, **metadata}, None, None
        entry = next((entry for entry in index["entries"] if entry["id"] == scenario_id), None)
        if entry is None:
            raise DomainError("Instructor reference not found", status=404)
        try:
            raw = (root / entry["key"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["key_sha256"]:
                raise ValueError
            key = json.loads(raw)
        except Exception as error:
            raise DomainError("Instructor reference integrity check failed", status=503) from error
        return ({"key": key, **metadata}, entry["key_sha256"], key["source"]["raw_sha256"])

    def instructor_reference(principal, engagement_id, scenario_id=None):
        from .instructor_access import InstructorAccessLog

        log = InstructorAccessLog(engine.store.root / "instructor-key-access")
        try:
            value, key_pin, source_pin = instructor_reference_value(
                principal, engagement_id, scenario_id
            )
        except Exception as error:
            status = error.status if isinstance(error, DomainError) else 500
            outcome = {403: "DENIED", 404: "NOT_FOUND", 503: "UNAVAILABLE"}.get(status, "ERROR")
            log.append(
                actor=principal["id"],
                engagement=engagement_id,
                target=scenario_id,
                outcome=outcome,
                http_status=status,
            )
            raise
        log.append(
            actor=principal["id"],
            engagement=engagement_id,
            target=scenario_id,
            outcome="SUCCESS",
            http_status=200,
            archive_sha256=value["archive"]["sha256"],
            key_sha256=key_pin,
            source_sha256=source_pin,
        )
        return value

    @app.get("/api/engagements/{engagement_id}/drafts/{action}/{object_id}")
    async def get_personal_draft(engagement_id: str, action: str, object_id: str, request: Request):
        from .draft_store import DraftStore

        principal = actor(request)
        return await asyncio.to_thread(
            DraftStore(engine.store).get, principal["id"], engagement_id, action, object_id
        )

    @app.put("/api/engagements/{engagement_id}/drafts/{action}/{object_id}")
    async def put_personal_draft(engagement_id: str, action: str, object_id: str, request: Request):
        from .draft_store import DraftStore

        principal = actor(request, mutation=True)
        payload = await json_body(request)
        return await asyncio.to_thread(
            DraftStore(engine.store).write,
            principal["id"],
            engagement_id,
            action,
            object_id,
            payload,
        )

    @app.delete("/api/engagements/{engagement_id}/drafts/{action}/{object_id}")
    async def delete_personal_draft(
        engagement_id: str, action: str, object_id: str, request: Request
    ):
        from .draft_store import DraftStore

        principal = actor(request, mutation=True)
        payload = await json_body(request)
        return await asyncio.to_thread(
            DraftStore(engine.store).write,
            principal["id"],
            engagement_id,
            action,
            object_id,
            payload,
            discard=True,
        )

    @app.get("/api/engagements/{engagement_id}/instructor-comparison")
    async def instructor_comparison(engagement_id: str, revision: int, request: Request):
        from .instructor_comparison import compare

        principal = actor(request)
        limits.check("instructor-comparison", principal["id"], 60)
        return await asyncio.to_thread(
            compare, engine, principal, engagement_id, protected_bindings, revision=revision
        )

    def assessment_store(request: Request, *, mutation=False):
        principal = actor(request, mutation=mutation)
        if assessments is None:
            raise DomainError("Instructor assessments are not configured", status=503)
        limits.check("instructor-assessments", principal["id"], 60)
        return principal["id"], assessments

    @app.get("/api/engagements/{engagement_id}/instructor-assessments/options")
    async def assessment_options(engagement_id: str, revision: int, request: Request):
        principal, store = assessment_store(request)
        if (
            set(request.query_params) != {"revision"}
            or len(request.query_params.getlist("revision")) != 1
        ):
            raise DomainError("Choose one recorded work revision")
        return await asyncio.to_thread(store.options, principal, engagement_id, revision)

    @app.get("/api/engagements/{engagement_id}/instructor-assessments")
    async def assessment_history(engagement_id: str, request: Request):
        principal, store = assessment_store(request)
        if request.query_params:
            raise DomainError("Assessments use the current authenticated context")
        return await asyncio.to_thread(store.listing, principal, engagement_id)

    @app.get("/api/engagements/{engagement_id}/instructor-assessments/{assessment_id}")
    async def assessment_read(engagement_id: str, assessment_id: str, request: Request):
        principal, store = assessment_store(request)
        if request.query_params:
            raise DomainError("Assessments use the current authenticated context")
        return await asyncio.to_thread(store.read, principal, engagement_id, assessment_id)

    @app.post("/api/engagements/{engagement_id}/instructor-assessments")
    async def assessment_save(engagement_id: str, request: Request):
        principal, store = assessment_store(request, mutation=True)
        if request.query_params:
            raise DomainError("Assessments use the current authenticated context")
        return await asyncio.to_thread(
            store.save, principal, engagement_id, await json_body(request)
        )

    def key_view_store(request: Request, *, mutation=False):
        principal = actor(request, mutation=mutation)
        if key_views is None:
            raise DomainError("Saved instructor Key views are not configured", status=503)
        limits.check("instructor-key-views", principal["id"], 120)
        return principal["id"], key_views

    @app.get("/api/engagements/{engagement_id}/instructor-key-views")
    async def key_view_list(engagement_id: str, kind: str, request: Request):
        principal, store = key_view_store(request)
        if (
            list(request.query_params.keys()) != ["kind"]
            or len(request.query_params.getlist("kind")) != 1
        ):
            raise DomainError("Choose one saved Key view kind")
        return await asyncio.to_thread(store.listing, principal, engagement_id, kind)

    @app.post("/api/engagements/{engagement_id}/instructor-key-views")
    async def key_view_save(engagement_id: str, request: Request):
        principal, store = key_view_store(request, mutation=True)
        if request.query_params:
            raise DomainError("Saved Key views use the current authenticated context")
        body = await json_body(request)
        return await asyncio.to_thread(store.save, principal, engagement_id, body)

    @app.post("/api/engagements/{engagement_id}/instructor-key-views/{view_id}/{operation}")
    async def key_view_action(engagement_id: str, view_id: str, operation: str, request: Request):
        principal, store = key_view_store(request, mutation=True)
        if request.query_params or operation not in {"restore", "delete"}:
            raise DomainError("Invalid saved Key view operation")
        body = await json_body(request)
        return await asyncio.to_thread(
            getattr(store, operation), principal, engagement_id, view_id, body
        )

    def release_store(request: Request, *, mutation=False):
        principal = actor(request, mutation=mutation)
        if releases is None:
            raise DomainError("Instructor assistance is not configured", status=503)
        if request.query_params:
            raise DomainError("Assistance uses the current authenticated context")
        limits.check("instructor-assistance", principal["id"], 120)
        return principal["id"], releases

    @app.get("/api/engagements/{engagement_id}/instructor-releases")
    async def release_history(engagement_id: str, request: Request):
        principal, store = release_store(request)
        return await asyncio.to_thread(store.history, principal, engagement_id)

    @app.get("/api/engagements/{engagement_id}/instructor-releases/options")
    async def release_options(engagement_id: str, request: Request):
        principal, store = release_store(request)
        return await asyncio.to_thread(store.options, principal, engagement_id)

    @app.get("/api/engagements/{engagement_id}/instructor-releases/debrief-options")
    async def debrief_options(engagement_id: str, request: Request):
        principal, store = release_store(request)
        return await asyncio.to_thread(store.debrief_options, principal, engagement_id)

    @app.post("/api/engagements/{engagement_id}/instructor-releases/debrief-preview")
    async def debrief_preview(engagement_id: str, request: Request):
        principal, store = release_store(request, mutation=True)
        return await asyncio.to_thread(
            store.debrief_preview, principal, engagement_id, await json_body(request)
        )

    @app.post("/api/engagements/{engagement_id}/instructor-releases/preview")
    async def release_preview(engagement_id: str, request: Request):
        principal, store = release_store(request, mutation=True)
        return await asyncio.to_thread(
            store.preview, principal, engagement_id, await json_body(request)
        )

    @app.post("/api/engagements/{engagement_id}/instructor-releases")
    async def release_confirm(engagement_id: str, request: Request):
        principal, store = release_store(request, mutation=True)
        return await asyncio.to_thread(
            store.confirm, principal, engagement_id, await json_body(request)
        )

    @app.post("/api/engagements/{engagement_id}/instructor-releases/{release_id}/revoke")
    async def release_revoke(engagement_id: str, release_id: str, request: Request):
        principal, store = release_store(request, mutation=True)
        payload = await json_body(request)
        if payload.get("release_id") != release_id:
            raise DomainError("Exact release identity required")
        return await asyncio.to_thread(store.revoke, principal, engagement_id, payload)

    @app.get("/api/engagements/{engagement_id}/assistance")
    async def assistance_list(engagement_id: str, request: Request):
        principal, store = release_store(request)
        return await asyncio.to_thread(store.list, principal, engagement_id)

    @app.get("/api/engagements/{engagement_id}/assistance/{release_id}")
    async def assistance_read(engagement_id: str, release_id: str, request: Request):
        principal, store = release_store(request)
        return await asyncio.to_thread(store.read, principal, engagement_id, release_id)

    @app.post("/api/engagements/{engagement_id}/assistance/{release_id}/acknowledge")
    async def assistance_acknowledge(engagement_id: str, release_id: str, request: Request):
        principal, store = release_store(request, mutation=True)
        payload = await json_body(request)
        if payload.get("release_id") != release_id:
            raise DomainError("Exact release identity required")
        return await asyncio.to_thread(store.acknowledge, principal, engagement_id, payload)

    @app.post("/api/engagements/{engagement_id}/assistance/{release_id}/export-preview")
    async def debrief_export_preview(engagement_id: str, release_id: str, request: Request):
        principal, store = release_store(request, mutation=True)
        limits.check("debrief-export", principal, 12)
        return await asyncio.to_thread(
            store.export_preview, principal, engagement_id, release_id, await json_body(request)
        )

    @app.post("/api/engagements/{engagement_id}/assistance/{release_id}/export")
    async def debrief_export(engagement_id: str, release_id: str, request: Request):
        principal, store = release_store(request, mutation=True)
        limits.check("debrief-export", principal, 12)
        result = await asyncio.to_thread(
            store.export_confirm, principal, engagement_id, release_id, await json_body(request)
        )
        raw, filename, expected = result.get("bytes"), result.get("filename"), result.get("sha256")
        if (
            not isinstance(raw, bytes)
            or not 0 < len(raw) <= 20 * 1024 * 1024
            or not isinstance(filename, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,170}\.zip", filename) is None
            or hashlib.sha256(raw).hexdigest() != expected
        ):
            raise DomainError("Debrief export integrity check failed", status=503)
        return Response(
            raw,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(raw)),
                "X-Content-SHA256": expected,
                "Cache-Control": "no-store, private",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get("/api/engagements/{engagement_id}/instructor-binding")
    async def instructor_binding(engagement_id: str, request: Request):
        from .bound_instructor import read_binding

        return await asyncio.to_thread(
            read_binding, engine, actor(request), engagement_id, protected_bindings
        )

    @app.get("/api/engagements/{engagement_id}/instructor-key")
    async def instructor_key_index(engagement_id: str, request: Request):
        return await asyncio.to_thread(instructor_reference, actor(request), engagement_id)

    @app.get("/api/engagements/{engagement_id}/instructor-key/{scenario_id}")
    async def instructor_key_detail(engagement_id: str, scenario_id: str, request: Request):
        return await asyncio.to_thread(
            instructor_reference, actor(request), engagement_id, scenario_id
        )

    @app.get("/api/engagements/{engagement_id}/company/impact")
    async def company_impact(engagement_id: str, request: Request):
        principal = actor(request)
        if request.query_params:
            raise DomainError("Source impact uses the current engagement context")
        from .company_impact import report

        return await asyncio.to_thread(report, engine, principal["id"], engagement_id)

    @app.get("/api/engagements/{engagement_id}/company/systems")
    async def company_systems(engagement_id: str, request: Request):
        from .company_collection import binding
        from .company_store import CompanyStoreError

        principal = actor(request)
        if request.query_params:
            raise DomainError("System discovery accepts no query overrides")

        def discover_systems():
            state = engine.store.get(principal["id"], engagement_id)
            bound = binding(engine, state)
            try:
                return engine.company_store.list_systems(
                    principal["id"], engagement_id, bound["company"], bound["branch"]
                )
            except CompanyStoreError as error:
                raise DomainError("Company source unavailable", status=403) from error

        return await asyncio.to_thread(discover_systems)

    @app.get("/api/engagements/{engagement_id}/company/systems/{system_id}/records")
    async def company_records(engagement_id: str, system_id: str, request: Request):
        from .company_collection import discover

        principal = actor(request)
        query = request.query_params
        if set(query) - {"after_record", "limit"} or len(query.multi_items()) != len(query):
            raise DomainError("Only record cursor and bounded limit are accepted")
        try:
            limit = int(query.get("limit", "100"))
        except ValueError as error:
            raise DomainError("Invalid discovery limit") from error
        return await asyncio.to_thread(
            discover,
            engine,
            principal["id"],
            engagement_id,
            system_id,
            after_record=query.get("after_record"),
            limit=limit,
        )

    @app.get("/api/engagements/{engagement_id}/custom-drafts/{draft_id}")
    async def custom_draft(engagement_id: str, draft_id: str, request: Request):
        principal = actor(request)
        if engine.store.membership(principal["id"], engagement_id) != "instruct":
            raise DomainError("Custom drafts require instructor membership", status=403)
        from .custom import read

        state = engine.store.get(principal["id"], engagement_id)
        return await asyncio.to_thread(read, engine, state, draft_id)

    def enabled_contexts():
        if contexts is None:
            raise DomainError("Saved investigations are not configured", status=503)
        return contexts

    @app.get("/api/engagements/{engagement_id}/contexts")
    async def context_list(engagement_id: str, request: Request):
        principal = actor(request)
        return {
            "contexts": await asyncio.to_thread(
                enabled_contexts().listing, principal["id"], engagement_id
            )
        }

    @app.post("/api/engagements/{engagement_id}/contexts/link")
    async def context_link(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("contexts", principal["id"], 120)
        if set(body) != {"kind", "id", "version"}:
            raise DomainError("Choose an exact existing record link")
        return await asyncio.to_thread(
            enabled_contexts().make_link,
            principal["id"],
            engagement_id,
            kind=body["kind"],
            record_id=body["id"],
            version=body["version"],
        )

    @app.post("/api/engagements/{engagement_id}/contexts")
    async def context_create(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("contexts", principal["id"], 120)
        if set(body) != {"command_id", "payload"}:
            raise DomainError("Invalid investigation create request")
        return await asyncio.to_thread(
            enabled_contexts().create,
            principal["id"],
            engagement_id,
            body["payload"],
            command_id=body["command_id"],
        )

    @app.put("/api/engagements/{engagement_id}/contexts/{context_id}")
    async def context_save(engagement_id: str, context_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("contexts", principal["id"], 120)
        if set(body) != {"command_id", "expected_version", "payload"}:
            raise DomainError("Invalid investigation save request")
        return await asyncio.to_thread(
            enabled_contexts().save,
            principal["id"],
            engagement_id,
            context_id,
            body["payload"],
            expected_version=body["expected_version"],
            command_id=body["command_id"],
        )

    @app.post("/api/engagements/{engagement_id}/contexts/{context_id}/reset")
    async def context_reset(engagement_id: str, context_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("contexts", principal["id"], 120)
        if set(body) != {"command_id", "expected_version"}:
            raise DomainError("Invalid investigation reset request")
        return await asyncio.to_thread(
            enabled_contexts().reset,
            principal["id"],
            engagement_id,
            context_id,
            expected_version=body["expected_version"],
            command_id=body["command_id"],
        )

    def enabled_personal_views():
        if personal_views is None:
            raise DomainError("Personal views are not configured", status=503)
        return personal_views

    @app.get("/api/engagements/{engagement_id}/saved-views")
    async def personal_view_list(engagement_id: str, request: Request):
        principal = actor(request)
        return {
            "views": await asyncio.to_thread(
                enabled_personal_views().listing, principal["id"], engagement_id
            )
        }

    @app.post("/api/engagements/{engagement_id}/saved-views/link")
    async def personal_view_link(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("saved-views", principal["id"], 120)
        if set(body) != {"kind", "id", "version"}:
            raise DomainError("Choose an exact existing saved-view reference")
        return await asyncio.to_thread(
            enabled_personal_views().make_reference,
            principal["id"],
            engagement_id,
            kind=body["kind"],
            record_id=body["id"],
            version=body["version"],
        )

    @app.post("/api/engagements/{engagement_id}/saved-views")
    async def personal_view_create(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("saved-views", principal["id"], 120)
        if set(body) != {"command_id", "payload", "expected_engagement_revision"}:
            raise DomainError("Invalid personal view create request")
        return await asyncio.to_thread(
            enabled_personal_views().create,
            principal["id"],
            engagement_id,
            body["payload"],
            expected_engagement_revision=body["expected_engagement_revision"],
            command_id=body["command_id"],
        )

    @app.get("/api/engagements/{engagement_id}/saved-views/{view_id}")
    async def personal_view_read(engagement_id: str, view_id: str, request: Request):
        principal = actor(request)
        return await asyncio.to_thread(
            enabled_personal_views().read, principal["id"], engagement_id, view_id
        )

    @app.put("/api/engagements/{engagement_id}/saved-views/{view_id}")
    async def personal_view_save(engagement_id: str, view_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("saved-views", principal["id"], 120)
        if set(body) != {
            "command_id",
            "payload",
            "expected_version",
            "expected_engagement_revision",
        }:
            raise DomainError("Invalid personal view update request")
        return await asyncio.to_thread(
            enabled_personal_views().save,
            principal["id"],
            engagement_id,
            view_id,
            body["payload"],
            expected_version=body["expected_version"],
            expected_engagement_revision=body["expected_engagement_revision"],
            command_id=body["command_id"],
        )

    @app.post("/api/engagements/{engagement_id}/saved-views/{view_id}/clear")
    async def personal_view_clear(engagement_id: str, view_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("saved-views", principal["id"], 120)
        if set(body) != {"command_id", "expected_version", "expected_engagement_revision"}:
            raise DomainError("Invalid personal view clear request")
        return await asyncio.to_thread(
            enabled_personal_views().clear,
            principal["id"],
            engagement_id,
            view_id,
            expected_version=body["expected_version"],
            expected_engagement_revision=body["expected_engagement_revision"],
            command_id=body["command_id"],
        )

    @app.post("/api/engagements/{engagement_id}/saved-views/{view_id}/restore")
    async def personal_view_restore(engagement_id: str, view_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("saved-views", principal["id"], 120)
        if set(body) != {"expected_version", "expected_engagement_revision"}:
            raise DomainError("Invalid personal view restore request")
        return await asyncio.to_thread(
            enabled_personal_views().restore,
            principal["id"],
            engagement_id,
            view_id,
            expected_version=body["expected_version"],
            expected_engagement_revision=body["expected_engagement_revision"],
        )

    def enabled_handoffs():
        if handoffs is None:
            raise DomainError("Investigation handoffs are not configured", status=503)
        return handoffs

    @app.get("/api/engagements/{engagement_id}/handoffs/members")
    async def handoff_members(engagement_id: str, request: Request):
        principal = actor(request)
        return await asyncio.to_thread(enabled_handoffs().directory, principal["id"], engagement_id)

    @app.get("/api/engagements/{engagement_id}/handoffs")
    async def handoff_list(engagement_id: str, request: Request):
        principal = actor(request)
        return {
            "handoffs": await asyncio.to_thread(
                enabled_handoffs().listing, principal["id"], engagement_id
            )
        }

    @app.post("/api/engagements/{engagement_id}/handoffs/link")
    async def handoff_link(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("handoffs", principal["id"], 120)
        if set(body) != {"recipient_id", "kind", "id", "version"}:
            raise DomainError("Choose an exact shared investigation reference")
        return await asyncio.to_thread(
            enabled_handoffs().make_reference,
            principal["id"],
            engagement_id,
            recipient_id=body["recipient_id"],
            kind=body["kind"],
            record_id=body["id"],
            version=body["version"],
        )

    @app.post("/api/engagements/{engagement_id}/handoffs")
    async def handoff_offer(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("handoffs", principal["id"], 120)
        if set(body) != {"payload", "expected_engagement_revision", "command_id"}:
            raise DomainError("Invalid investigation handoff offer")
        return await asyncio.to_thread(
            enabled_handoffs().offer,
            principal["id"],
            engagement_id,
            body["payload"],
            expected_engagement_revision=body["expected_engagement_revision"],
            command_id=body["command_id"],
        )

    @app.get("/api/engagements/{engagement_id}/handoffs/{handoff_id}")
    async def handoff_read(engagement_id: str, handoff_id: str, request: Request):
        principal = actor(request)
        return await asyncio.to_thread(
            enabled_handoffs().read, principal["id"], engagement_id, handoff_id
        )

    @app.post("/api/engagements/{engagement_id}/handoffs/{handoff_id}/transition")
    async def handoff_transition(engagement_id: str, handoff_id: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("handoffs", principal["id"], 120)
        if set(body) != {
            "action",
            "response",
            "expected_version",
            "expected_engagement_revision",
            "command_id",
        }:
            raise DomainError("Invalid investigation handoff transition")
        return await asyncio.to_thread(
            enabled_handoffs().transition,
            principal["id"],
            engagement_id,
            handoff_id,
            action=body["action"],
            response=body["response"],
            expected_version=body["expected_version"],
            expected_engagement_revision=body["expected_engagement_revision"],
            command_id=body["command_id"],
        )

    def enabled_work_guidance():
        if work_guidance is None:
            raise DomainError("Personal work guidance is not configured", status=503)
        return work_guidance

    @app.get("/api/engagements/{engagement_id}/work-guidance")
    async def guidance_status(engagement_id: str, request: Request):
        principal = actor(request)
        return await asyncio.to_thread(
            enabled_work_guidance().status, principal["id"], engagement_id
        )

    @app.post("/api/engagements/{engagement_id}/work-guidance/{operation}")
    async def guidance_action(engagement_id: str, operation: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("work_guidance", principal["id"], 120)
        common = {"expected_engagement_revision", "command_id"}
        extra = {
            "preference": {"enabled", "rationale", "expected_version"},
            "reveal": {"context_ref"},
            "decision": {"candidate_id", "candidate_sha256", "action", "rationale"},
        }
        if operation not in extra or set(body) != common | extra[operation]:
            raise DomainError("Exact personal guidance operation required")
        guide = enabled_work_guidance()
        methods = {"preference": guide.opt_in, "reveal": guide.reveal, "decision": guide.decide}
        return await asyncio.to_thread(methods[operation], principal["id"], engagement_id, **body)

    def enabled_jobs():
        if jobs is None:
            raise DomainError("Background work is not configured", status=503)
        return jobs

    @app.get("/api/engagements/{engagement_id}/jobs")
    async def job_list(engagement_id: str, request: Request):
        principal = actor(request)
        return {
            "jobs": await asyncio.to_thread(enabled_jobs().listing, principal["id"], engagement_id)
        }

    @app.get("/api/engagements/{engagement_id}/jobs/{job_id}/input")
    async def job_input(engagement_id: str, job_id: str, request: Request):
        principal = actor(request)
        return await asyncio.to_thread(enabled_jobs().input, principal["id"], engagement_id, job_id)

    @app.post("/api/engagements/{engagement_id}/jobs")
    async def job_submit(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        payload = await json_body(request)
        limits.check("commands", principal["id"], 240)
        limits.check("inference", principal["id"], 20)
        runner = enabled_jobs()
        job = await asyncio.to_thread(runner.submit, principal["id"], engagement_id, payload)
        if job["status"] == "PENDING":
            try:
                job = await asyncio.to_thread(
                    runner.start, principal["id"], engagement_id, job["id"]
                )
            except DomainError as exc:
                if exc.status != 429:
                    raise
                job = await asyncio.to_thread(
                    runner.read, principal["id"], engagement_id, job["id"]
                )
        return job

    @app.post("/api/engagements/{engagement_id}/jobs/{job_id}/{operation}")
    async def job_action(engagement_id: str, job_id: str, operation: str, request: Request):
        principal = actor(request, mutation=True)
        body = await json_body(request)
        limits.check("inference", principal["id"], 20)
        runner = enabled_jobs()
        if operation == "start" and not body:
            return await asyncio.to_thread(runner.start, principal["id"], engagement_id, job_id)
        if operation == "retry" and set(body) == {"observed_job_revision"}:
            return await asyncio.to_thread(
                runner.retry,
                principal["id"],
                engagement_id,
                job_id,
                observed_job_revision=body["observed_job_revision"],
            )
        raise DomainError("Invalid background work operation")

    @app.post("/api/engagements/{engagement_id}/commands")
    async def command(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        payload = await json_body(request)
        limits.check("commands", principal["id"], 240)
        if payload.get("kind") in {
            "meeting.message",
            "review.experimental",
            "scenario.custom.author",
            "scenario.custom.edit",
        }:
            limits.check("inference", principal["id"], 20)
        state = await asyncio.to_thread(engine.command, principal["id"], engagement_id, payload)
        if state["phase"] == "GENERATING" and engagement_id not in app.state.generation_jobs:

            async def generate():
                from .generation import step

                try:
                    while True:
                        result = await asyncio.to_thread(
                            step, engine, principal["id"], engagement_id
                        )
                        if result["phase"] != "GENERATING":
                            break
                        await asyncio.sleep(0)
                finally:
                    app.state.generation_jobs.pop(engagement_id, None)

            app.state.generation_jobs[engagement_id] = asyncio.create_task(generate())
        return state

    @app.post("/api/engagements/{engagement_id}/uploads")
    async def upload(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        limits.check("uploads", principal["id"], 60)
        state = engine.get(principal["id"], engagement_id)
        if state["phase"] != "ACTIVE":
            raise DomainError("Open kickoff before uploading engagement work")
        async with request.form(max_files=1, max_fields=8, max_part_size=MAX_BYTES) as form:
            file = form.get("file")
            if file is None or not hasattr(file, "read"):
                raise DomainError("Upload file required")
            data = await file.read(MAX_BYTES + 1)
            kind, linked_id = str(form.get("kind", "workpaper")), str(form.get("linked_id", ""))
            try:
                revision = int(str(form.get("expected_revision", "")))
            except ValueError as exc:
                raise DomainError("Expected revision required") from exc
            if kind not in {"workpaper", "evidence", "selection", "population_revision"} or (
                kind in {"evidence", "selection", "population_revision"} and not linked_id
            ):
                raise DomainError("Choose workpaper or evidence linked to a PBC request")
            command_id = str(form.get("command_id", ""))
            if not command_id:
                raise DomainError("Upload command ID required")
            purpose, rationale = str(form.get("purpose", "")), str(form.get("rationale", ""))
            imported_ids = []
            if kind == "selection":
                if Path(file.filename or "").suffix.lower() not in {".txt", ".csv"}:
                    raise DomainError("Selected IDs require UTF-8 text or single-column CSV")
                try:
                    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
                except (UnicodeError, csv.Error) as exc:
                    raise DomainError("Invalid selected-ID text file") from exc
                if any(len(row) != 1 for row in rows if row):
                    raise DomainError("Selected-ID file must contain one ID per row")
                imported_ids = [row[0].strip() for row in rows if row and row[0].strip()]
                if imported_ids and imported_ids[0].lower() in {"id", "selected_id"}:
                    imported_ids.pop(0)
                if not purpose.strip() or not rationale.strip():
                    raise DomainError("Selection purpose and methodology rationale are required")
            revised_rows = []
            if kind == "population_revision":
                if Path(file.filename or "").suffix.lower() != ".csv":
                    raise DomainError("Population revision requires a UTF-8 CSV original")
                try:
                    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
                    if (
                        not reader.fieldnames
                        or "id" not in reader.fieldnames
                        or len(set(reader.fieldnames)) != len(reader.fieldnames)
                    ):
                        raise DomainError("Population CSV needs distinct column names including id")
                    revised_rows = list(reader)
                    if any(
                        None in row or any(v is None for v in row.values()) for row in revised_rows
                    ):
                        raise DomainError("Population CSV row width differs from its header")
                except (UnicodeError, csv.Error) as exc:
                    raise DomainError("Invalid population CSV") from exc
                if not purpose.strip() or not rationale.strip():
                    raise DomainError("Source query/representation and revision rationale required")
            command = {
                "kind": "artifact.upload",
                "command_id": command_id,
                "expected_revision": revision,
                "payload": {
                    "name": file.filename,
                    "kind": kind,
                    "linked_id": linked_id,
                    "purpose": purpose,
                    "rationale": rationale,
                    "sha256": hashlib.sha256(data).hexdigest(),
                },
            }

            def retain(s, c, who):
                if linked_id:
                    find(
                        s,
                        "populations"
                        if kind in {"selection", "population_revision"}
                        else ("workpapers" if kind == "workpaper" else "requests"),
                        linked_id,
                    )
                manifest = engine.artifacts.retain(
                    engagement_id,
                    file.filename,
                    data,
                    source={"kind": "LEARNER_UPLOAD", "actor": who},
                    coverage=s["scope"],
                )
                s["artifacts"].append(manifest)
                if kind == "workpaper":
                    if linked_id:
                        wp = find(s, "workpapers", linked_id)
                    else:
                        from .store import identifier

                        wp = {
                            "id": identifier("WP"),
                            "title": file.filename,
                            "versions": [],
                            "prepared_by": who,
                        }
                        s["workpapers"].append(wp)
                    wp["versions"].append(
                        {
                            "version": len(wp["versions"]) + 1,
                            "artifact_id": manifest["id"],
                            "actor": who,
                        }
                    )
                elif kind == "population_revision":
                    try:
                        engine._population_command(
                            s,
                            "population.revise",
                            {
                                "population_id": linked_id,
                                "artifact_id": manifest["id"],
                                "rows": revised_rows,
                                "rationale": rationale,
                                "source": {
                                    "source_id": manifest["id"],
                                    "query": purpose,
                                    "completeness_representation": purpose,
                                },
                            },
                            {
                                "actor": who,
                                "recorded_at": datetime.now(UTC).isoformat(),
                                "simulated_at": s["simulated_at"],
                            },
                        )
                    except (ValueError, KeyError, TypeError) as exc:
                        raise DomainError("Invalid population revision: " + str(exc)[:200]) from exc
                elif kind == "selection":
                    try:
                        engine._population_command(
                            s,
                            "population.select",
                            {
                                "population_id": linked_id,
                                "method": "MANUAL",
                                "selected_ids": imported_ids,
                                "purpose": purpose,
                                "rationale": rationale,
                            },
                            {
                                "actor": who,
                                "recorded_at": datetime.now(UTC).isoformat(),
                                "simulated_at": s["simulated_at"],
                            },
                        )
                    except (ValueError, KeyError, TypeError) as exc:
                        raise DomainError("Invalid selected IDs: " + str(exc)[:200]) from exc
                    s["selections"][-1]["import_artifact_id"] = manifest["id"]
                elif kind == "evidence" and linked_id:
                    find(s, "requests", linked_id)["artifact_ids"].append(manifest["id"])
                else:
                    raise DomainError("Uploads require workpaper or linked evidence purpose")
                return s

            saved = await asyncio.to_thread(
                engine.store.command,
                principal["id"],
                engagement_id,
                command,
                retain,
                permissions={"learn", "instruct"},
            )
            return engine._project(principal["id"], saved)

    @app.get("/api/engagements/{engagement_id}/artifacts/{artifact_id}/download")
    async def download(engagement_id: str, artifact_id: str, request: Request):
        state = engine.get(actor(request)["id"], engagement_id)
        manifest = find(state, "artifacts", artifact_id)
        data = engine.artifacts.read(manifest)
        return Response(
            data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(manifest['name'])}"
            },
        )

    @app.post("/api/engagements/{engagement_id}/voice/transcribe")
    async def transcribe(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        state = engine.get(principal["id"], engagement_id)
        if engine.store.membership(principal["id"], engagement_id) not in {"learn", "instruct"}:
            raise DomainError("This membership cannot submit meeting input", status=403)
        if state["phase"] != "ACTIVE" or not engine.voice_config:
            raise DomainError("Local voice requires an active configured engagement", status=503)
        async with request.form(max_files=1, max_fields=0, max_part_size=12000000) as form:
            file = form.get("file")
            if file is None or not hasattr(file, "read"):
                raise DomainError("Audio file required")
            data = await file.read(12000001)
            mime = file.content_type or "application/octet-stream"
        from .voice import LocalVoice

        result = await asyncio.to_thread(LocalVoice(engine.voice_config).transcribe, data, mime)
        # Recheck access after slow work; transcript is never submitted automatically.
        engine.store.membership(principal["id"], engagement_id)
        return result

    @app.post("/api/engagements/{engagement_id}/voice/synthesize")
    async def synthesize(engagement_id: str, request: Request):
        principal = actor(request, mutation=True)
        state = engine.get(principal["id"], engagement_id)
        body = await json_body(request)
        if set(body) != {"message_id"} or not isinstance(body["message_id"], str):
            raise DomainError("Choose an existing company message to read aloud")
        message = next(
            (
                m
                for meeting in state.get("meetings", [])
                for m in meeting["messages"]
                if m["id"] == body["message_id"] and m["role"] == "assistant"
            ),
            None,
        )
        if message is None:
            raise DomainError("Company message unavailable in this engagement", status=404)
        if not engine.voice_config:
            raise DomainError("Local speech synthesis is not configured", status=503)
        from .voice import LocalVoice

        result = await asyncio.to_thread(
            LocalVoice(engine.voice_config).synthesize, message["content"]
        )
        engine.store.membership(principal["id"], engagement_id)
        return Response(
            result["bytes"], media_type=result["mime"], headers={"X-Synthetic-Voice": "true"}
        )

    if web_root is not None:
        web_root = web_root.resolve()

        @app.get("/{path:path}")
        async def web(path: str):
            candidate = (web_root / (path or "index.html")).resolve()
            if not candidate.is_relative_to(web_root) or not candidate.is_file():
                if path.startswith("api/"):
                    return JSONResponse({"error": "Unknown endpoint"}, status_code=404)
                candidate = web_root / "index.html"
            return FileResponse(candidate)

    return app
