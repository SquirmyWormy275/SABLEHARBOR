# Public edition copy disposal — observed September 22, 2026

Reviewable implementation/evidence, pending repository acceptance. It does not change v1.0.0 or close the full runtime residual.

## Results

- 97 isolated runtime/recovery/service tests, one protected HTTP test and six graph tests passed at portal commit `5344bf76413ffe2cd378b957dbb5f7d56d04ea19`; no failures/skips.
- Six company adapter identity/bounds regression tests passed.
- Three exact public v1.0.0 originals were read from the pinned ZIP and copied into the runtime's own new private directory: capital register (15,699 bytes), equity bridge (1,264), payroll bridge (4,803).
- Local hold denied deletion; retention deadline denied early deletion. A deliberately interrupted durable intent retained all copies; a subsequent hold denied retry. Explicit later retry deleted the capital copy; after the retention deadline, the equity copy was deleted. The unselected payroll backup copy remained present. The package hash remained unchanged.
- Native receipt/state preserves each source hash, declared complete three-copy inventory, two verified unlinks and one remaining backup. This is a selected sample from 5,731 edition members, not the enterprise retention population.

Logical fixture events are May 1, 2027, following the committed runtime's scoped assignment fixture. Actual observation is September 22, 2026, retained in PUBLIC_COPY_RECEIPT.json. These are explicitly prospective simulated operating times, not September historical company deletion records. Runtime operator identity is a local trusted invocation assertion, not authenticated corporate approval.

## Reproduction

Use a new detached portal checkout at the exact commit and run `uv sync --extra dev --extra audit-suite --frozen` there. Do not point this exercise at active private runtime data. From a company checkout containing the adapter:

```sh
<portal-checkout>/.venv/bin/python tools/company_closeout/public_copy_disposal.py \
  --portal <portal-checkout> \
  --package <downloaded-public-v1.0.0.zip> \
  --package-sha256 1da616c00e6978a8d6a7b31fb9a2efed1203403672e2b4926b89e36a30a60367 \
  --output <new-private-output-directory>
```

The output directory must not exist. All deletion paths are generated and owned by the portal runtime; callers cannot select arbitrary existing deletion paths. The release ZIP is only read. Failure injection uses an in-process mock after durable intent; no portal source file is edited. The SHA-pinned release, its selected member hashes, and clean tracked portal commit are checked before creating copies.

Run `python -m pytest -q tools/company_closeout/test_public_copy_disposal.py` for duplicate member, mutated member/package hash, empty/oversize byte and permitted-original tests. See REVIEW.md for exact neutral test commands and the bounded claim matrix. source-hashes.json and installed.txt retain source/environment identity. Initial adapter execution rejected the release's actual ACCEPTED_SCOPED_EDITION status due to an overly narrow spelling; the preserved failure log and subsequent retests show the corrected accepted-scope check. Ruff and git diff --check passed.

## Remaining runtime limits

This advances owned-copy disposal evidence. It does not delete CompanyStore originals, establish corporate retention or legal hold release, perform secure erasure, replay later hold/disposal state into an older company backup, exercise every indirect-disclosure surface, deploy a production service, or provide an audit opinion. The payroll 'BACKUP' copy is one declared fixture copy, not a restored historical database. SH-RES-RUNTIME remains partial at those precise boundaries.

No private workroom evidence or grading payloads were inspected. Runtime databases are temporary outputs and are not committed; public metadata receipts and actual test logs are retained here.
