"""One signed-identity HTTP rehearsal across collection, testing and durable review."""

import json
import threading
import time
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from wsgiref.simple_server import make_server

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from . import collection, examples, store
from .identity import Identity
from .service import Application, QuietHandler


def run(output, plans):
    output = Path(output)
    output.mkdir(parents=True, mode=0o700)
    plan = next(p for p in plans.values() if p["control_id"] == "SH-IAM-004")
    bounds = sorted({p["boundary_id"] for p in plans.values()})
    store.initialize(output / "workflow.sqlite3", plans, examples.principals(bounds))
    signing = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(signing.public_key()))
    jwk.update(kid="DEMO-KEY", alg="RS256", use="sig")
    issuer = "https://identity.example.invalid"
    identity = Identity(
        dict(
            issuer=issuer,
            audience="DEMO-CCF",
            required_claims={"token_use": "access"},
            jwks={"keys": [jwk]},
            bindings=[
                dict(issuer=issuer, subject=x, principal=x)
                for x in ("DEMO-PREPARER", "DEMO-REVIEWER")
            ],
        )
    )
    app = Application(
        output / "workflow.sqlite3",
        identity,
        "https://ccf.example.invalid",
        allow_loopback_http=True,
    )
    server = make_server("127.0.0.1", 0, app, handler_class=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks = []

    def request(actor, path, body=None, expected=200):
        at = int(time.time())
        token = jwt.encode(
            dict(
                iss=issuer,
                aud="DEMO-CCF",
                sub=actor,
                iat=at - 1,
                nbf=at - 1,
                exp=at + 300,
                token_use="access",
            ),
            signing,
            algorithm="RS256",
            headers={"kid": "DEMO-KEY"},
        )
        req = Request(
            f"http://127.0.0.1:{server.server_port}" + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Host": "ccf.example.invalid",
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=10) as response:
                status, response_body = response.status, response.read()
        except HTTPError as exc:
            status, response_body = exc.code, exc.read()
        if status != expected:
            raise ValueError(f"Integrated API expected {expected}, received {status}")
        checks.append(dict(path=path, actor=actor, status=status))
        return json.loads(response_body)

    def command(actor, action, payload, revision, expected=200):
        return request(
            actor,
            "/v1/command",
            dict(
                case_id="DEMO-INTEGRATED",
                action=action,
                payload=payload,
                expected_revision=revision,
            ),
            expected,
        )

    try:
        with patch.object(store, "now", return_value=examples.AT):
            request("UNMAPPED", "/v1/report", expected=401)
            command("DEMO-PREPARER", "create", dict(plan_id=plan["id"], scope=examples.scope()), 0)
            source = output / "evidence.json"
            census = output / "independent-census.json"
            rows = [examples.record("termination", plan["boundary_id"])]
            source.write_text(json.dumps(rows))
            source.chmod(0o600)
            census.write_text(json.dumps([{"id": r["id"]} for r in rows]))
            census.chmod(0o600)
            config = collection.config_template(
                source, census, dict(boundary_id=plan["boundary_id"], **examples.scope())
            )
            collected = collection.run_job(
                config, output / "schedule.sqlite3", output / "packets", at=examples.AT
            )
            if not collected["ready_for_review"]:
                raise ValueError("Integrated collection did not reconcile")
            retry = collection.run_job(
                config, output / "schedule.sqlite3", output / "packets", at=examples.AT
            )
            if retry["status"] != "ALREADY_COLLECTED":
                raise ValueError("Scheduled collection duplicated work")
            packet = json.loads(Path(collected["artifact"]).read_text())
            pop = packet["population"]
            pop["criteria_review"] = (
                "Explicit independent SYNTHETIC scope and criterion review; no actual authority or observations"
            )
            command("DEMO-PREPARER", "population", pop, 1, expected=400)
            command("DEMO-REVIEWER", "population", pop, 1)
            submitted = command("DEMO-PREPARER", "intake", packet["intake"], 2)
            if submitted["submissions"][-1]["result"]["outcome"] != "NOT_RUN":
                raise ValueError("Collection fabricated completed manual tests")
            review = dict(
                submission_id=submitted["submissions"][-1]["id"],
                decision="ACCEPT",
                rationale="Independent synthetic review confirms manual work missing",
            )
            opened = command("DEMO-REVIEWER", "review", review, 3)
            if opened["state"] != "FINDING_OPEN":
                raise ValueError("Incomplete tests did not create retained finding")
            command(
                "DEMO-PREPARER",
                "remediate",
                dict(
                    change_reference="DEMO-MANUAL-WORKPAPER",
                    action="Supply explicitly synthetic human observations",
                    due_at=examples.EXPIRY,
                ),
                4,
            )
            corrected = dict(
                packet["intake"], manual_tests=examples.submission(plan, rows)["manual_tests"]
            )
            submitted = command("DEMO-PREPARER", "intake", corrected, 5)
            review = dict(
                submission_id=submitted["submissions"][-1]["id"],
                decision="ACCEPT",
                rationale="Independent fixture review of all retained human criteria",
            )
            closed = command("DEMO-REVIEWER", "review", review, 6)
            if (
                closed["state"] != "CLOSED_CORRECTED_EVIDENCE"
                or closed["original_outcome"] != "NOT_RUN"
            ):
                raise ValueError("Correction did not preserve the original untested result")
            report = request("DEMO-REVIEWER", "/v1/report")
        result = dict(
            status="PASS",
            origin="SYNTHETIC",
            real_http_requests=True,
            checks=checks,
            collection_idempotent=True,
            manual_missing_stayed_not_run=True,
            independent_review_enforced=True,
            final_state=closed["state"],
            initial_outcome_retained=closed["original_outcome"],
            report=report,
            limitation="Ephemeral loopback HTTP and locally signed fixture identities exercise integration only. No live identity provider, TLS deployment, source account or assurance acceptance.",
        )
        p = output / "INTEGRATION_RESULT.json"
        p.write_text(json.dumps(result, indent=2) + "\n")
        p.chmod(0o600)
        return result
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
