# Advisory matter operating histories

This successor adds six explicit synthetic 2027 case files to the existing Advisory fee model. It represents scenario assumptions and repeatable software evidence. It does not represent a production engagement, client consent, a legal opinion, or a deployed Alexandria permission system.

| Matter | Operating history | Financial consequence |
|---|---|---|
| ADV-2027-01 | Independently accepted scope | Existing milestone and value mechanics apply |
| ADV-2027-02 | Source rights missing in January; cleared in March | Committed billing and delivery cannot start before March |
| ADV-2027-03 | Independent review fails in April; correction accepted in June | Work and subsequent recognition pause during April–May; fixed Decision fee remains fixed |
| ADV-2027-04 | Client dependency causes April stop; July resumption | Work, new billing, and recognition pause during April–June |
| ADV-2027-05 | May material scope change; August re-acceptance | Work, new billing, and recognition pause during May–July; original fee ceiling remains |
| ADV-2027-06 | Client seeks a predetermined conclusion; declined | No work, committed invoice, recognition, or transfer |

`MatterMixin.outcomes` determines monthly permission before calling the existing `enterprise.business.advisory.run_matters` fee engine. The adapter does not change prices, target value, committed fractions, payout curves, capacity costs, milestone shares, payment terms, or certification lags. Source engagements are restored even if the fee engine raises. Amounts earned before a hold are preserved; settling an existing invoice remains possible during a hold. Delayed work resumes only when the corresponding independent correction, restoration, or re-acceptance is recorded. Correction earns no additional fee. These six histories apply in each of the three existing financial scenarios.

The register retains each decision, responsible role and synthetic person, stated reason, monthly control state, and work/billing/recognition gate. A control `PASS` means that the case permits the activity; it does not claim a production control test passed. The source acceptance determination covers scope, competence, conflicts, rights and economics. Independent review failure and correction receive separate explicit determinations. Missing gate history fails validation. Other matters retain the earlier release's evidence granularity and should not be presented as equally detailed case files.

Five accepted selected matters in three scenarios produce 15 deterministic client packages. Each contains exactly eight files: a client-owned Python review aid, seven disclosed executable tests, a runbook, README, scoped contract, dependency and rights record, execution proof, and SHA-256 manifest. The aid reads only its own contract, checks client and asset identity, rejects invalid readings, and returns MONITOR, REVIEW or STOP. It never operates equipment, ingests external sources, contacts services, or supplies professional-plane methods. An Atlas product license remains a separate contract.

The generator executes the tests in an isolated Python subprocess, records their exact count and payload hashes, and verifies the completed package. Verification checks the file allowlist, reviewed payload bytes, declared client identity, manifest hashes and executed proof, and then independently reruns all seven tests. Modified or additional files, absent proof, wrong expected client, and a changed payload with a newly signed manifest fail verification. Package hashes provide reproducibility; they do not establish external client approval or a digital-signature identity.

`matter_determinations`, `matter_controls`, `matter_gate_decisions` and `matter_handover_evidence` supplement the unchanged source events, financial journals, invoices, value certifications, and matter rollforward. The handover evidence ties the client package to its accepted event and period. Prior business-finance releases and 2026 reconstruction remain intact.

Validation: `python -m pytest enterprise/operations/tests/test_matters.py`.
