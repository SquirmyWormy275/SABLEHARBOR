"""Local operator entry point; authentication credentials never go to stdout."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .store import DomainError, Store


def main(argv=None):
    parser = argparse.ArgumentParser(description="Private SABLE HARBOR audit training workroom")
    commands = parser.add_subparsers(dest="command", required=True)
    provision = commands.add_parser(
        "provision", help="Create a private local principal credential file"
    )
    provision.add_argument("--private-root", type=Path, required=True)
    provision.add_argument("--name", required=True)
    provision.add_argument("--role", choices=["learner", "instructor", "reviewer"], required=True)
    provision.add_argument("--credential-file", type=Path, required=True)
    provision.add_argument("--lifetime-hours", type=int, default=24)
    serve = commands.add_parser("serve", help="Run a single local loopback workroom process")
    serve.add_argument("--private-root", type=Path, required=True)
    serve.add_argument("--web-root", type=Path, required=True)
    serve.add_argument("--port", type=int, default=8780)
    serve.add_argument("--inference-config", type=Path)
    serve.add_argument("--voice-config", type=Path)
    serve.add_argument("--company-root", type=Path)
    serve.add_argument("--company-bindings", type=Path)
    serve.add_argument("--company-registry", type=Path)
    serve.add_argument("--company-profile")
    serve.add_argument(
        "--company-rights-config", type=Path,
        help="Private, hash-pinned protected company rights configuration",
    )
    serve.add_argument("--company-rights-config-sha256")
    serve.add_argument("--instructor-key-root", type=Path)
    serve.add_argument("--instructor-bindings", type=Path)
    serve.add_argument(
        "--disable-instructor-writeback",
        action="store_true",
        help="Show bound instructor Keys without enabling assessments, releases, or debriefs",
    )
    serve.add_argument("--background-jobs", action="store_true")
    serve.add_argument("--workspace-contexts", action="store_true")
    serve.add_argument("--corpus-root", type=Path)
    serve.add_argument("--program-pack", type=Path)
    serve.add_argument("--tls-cert", type=Path)
    serve.add_argument("--tls-key", type=Path)
    serve.add_argument(
        "--local-http",
        action="store_true",
        help="Explicit local-only development HTTP with non-secure cookie",
    )
    backup_command = commands.add_parser("backup", help="Create a new private state backup")
    backup_command.add_argument("--private-root", type=Path, required=True)
    backup_command.add_argument("--destination", type=Path, required=True)
    restore_command = commands.add_parser(
        "restore", help="Restore into a new private root; revoke old credentials"
    )
    restore_command.add_argument("--source", type=Path, required=True)
    restore_command.add_argument("--destination", type=Path, required=True)
    grant = commands.add_parser(
        "grant", help="Local operator grants explicit engagement membership"
    )
    grant.add_argument("--private-root", type=Path, required=True)
    grant.add_argument("--engagement", required=True)
    grant.add_argument("--principal", required=True)
    grant.add_argument("--permission", choices=["learn", "review", "instruct"], required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            from .recovery import backup

            receipt = backup(Store(args.private_root), args.destination)
            print(
                json.dumps(
                    {
                        "status": receipt["status"],
                        "private_backup": True,
                        "files": len(receipt["files"]),
                        "engagements": len(receipt["engagements"]),
                    }
                )
            )
            return
        if args.command == "restore":
            from .recovery import restore

            receipt = restore(args.source, args.destination)
            print(
                json.dumps(
                    {
                        key: receipt[key]
                        for key in ("status", "prior_credentials", "prior_sessions", "next_step")
                    }
                )
            )
            return
        if args.command == "grant":
            Store(args.private_root).grant(args.engagement, args.principal, args.permission)
            print("Explicit local engagement membership granted.")
            return
        if args.command == "provision":
            parent = args.credential_file.absolute().parent
            if parent.is_symlink() or not parent.is_dir() or parent.stat().st_mode & 0o077:
                raise DomainError(
                    "Credential file parent must be an existing private mode-0700 directory"
                )
            fd = os.open(args.credential_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                value = Store(args.private_root).provision(
                    args.name, [args.role], lifetime=args.lifetime_hours * 3600
                )
                with os.fdopen(fd, "w") as stream:
                    stream.write(json.dumps(value, indent=2))
            except BaseException:
                try:
                    os.close(fd)
                except OSError:
                    pass
                args.credential_file.unlink(missing_ok=True)
                raise
            print(
                "Private principal credential file created. No external identity was provisioned."
            )
            return
        if not 1024 <= args.port <= 65535:
            raise DomainError("Choose an unprivileged local port")
        if args.local_http:
            if args.tls_cert or args.tls_key:
                raise DomainError("Choose explicit local HTTP or TLS")
        elif not args.tls_cert or not args.tls_key:
            raise DomainError("TLS certificate/key required unless --local-http is explicit")
        if args.tls_key and (args.tls_key.is_symlink() or args.tls_key.stat().st_mode & 0o077):
            raise DomainError("TLS key must be a private regular file")
        if not (args.web_root / "index.html").is_file():
            raise DomainError("Build the web workroom before serving")
        if bool(args.company_rights_config) != bool(args.company_rights_config_sha256):
            raise DomainError("Protected company config path and exact SHA-256 required together")
        company_rights_factory = None
        company_native_rights_factory = None
        if args.company_rights_config:
            from .company_rights_launch import reviewed_company_factories

            company_rights_factory, company_native_rights_factory = reviewed_company_factories(
                args.company_rights_config, args.company_rights_config_sha256
            )
        import uvicorn

        from .service import create_app

        app = create_app(
            args.private_root,
            web_root=args.web_root,
            secure_cookie=not args.local_http,
            allowed_hosts=["localhost", "127.0.0.1"],
            inference_config=args.inference_config,
            voice_config=args.voice_config,
            company_root=args.company_root,
            company_bindings=args.company_bindings,
            company_registry=args.company_registry,
            company_profile=args.company_profile,
            instructor_key_root=args.instructor_key_root,
            instructor_bindings=args.instructor_bindings,
            enable_instructor_writeback=not args.disable_instructor_writeback,
            background_jobs=args.background_jobs,
            workspace_contexts=args.workspace_contexts,
            corpus_root=args.corpus_root,
            program_pack=args.program_pack,
            company_rights_factory=company_rights_factory,
            company_native_rights_factory=company_native_rights_factory,
        )
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=args.port,
            access_log=False,
            proxy_headers=False,
            ssl_certfile=str(args.tls_cert) if args.tls_cert else None,
            ssl_keyfile=str(args.tls_key) if args.tls_key else None,
        )
    except (DomainError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
