# Runtime architecture and operating procedures

**Document ID:** SH-RT-ARCH-001
**Version:** 1.0.0
**State:** delegated implementation design; not deployed
**Effective / prepared:** 2026-09-11
**Owner:** Enterprise Technology Services; J2 retains information authority
**Authority:** September 11 runtime decisions and PR119 implementation mandate
**Structured companion:** runtime capital source, `implementation_assumptions`

## Architecture decisions

ADR-01: retain Switch Reno as the proposed transitional primary, independently
administered IDACORE Boise recovery, and a separate immutable/offline-copy boundary.
The owned Northern Nevada site is acquired/preconstruction in the synthetic case,
with no vertical construction, completed shell or commissioned plant. Its first
planned critical module is 250 kW, with a second 250 kW module conditional on
demand, utility design and funding. A 1 MW utility path and optional 2 MW route
are design requirements, not energized capacity.

ADR-02: use a small supported platform foundation: Linux/KVM hosts for separate
trust domains; containerized application processes inside those domains; PostgreSQL
for transactions and temporal metadata; customer-controlled object storage for
immutable source artifacts and backups; rebuildable search indexes; a dedicated
identity/PAM service and HSM-backed keys. Do not introduce a second authoritative
transaction store or let search indexes become the source of truth. PostgreSQL's
[published version policy](https://www.postgresql.org/support/versioning/) provides
a five-year major-version support model. Major 17 is the provisional database
baseline; supported point releases, exact OS/orchestrator/object-store versions
and signed images require a qualified bill of materials before deployment. The
model is deliberately not represented as a tested product integration.

ADR-03: separate enterprise shared services, Alexandria restricted records, Atlas
professional services, Atlas client tenants, Foundry central support/control,
development/evaluation, management/OOB, backup vault and recovery bootstrap.
Business product engineering retains product authority. Provider facility systems
cannot administer these planes. Production identities cannot administer backup
retention. Customer-controlled edge devices terminate transport; authenticated
management is isolated from application and provider networks.

ADR-04: workload-driven sizing replaces the inherited 75/85/120 and later kW
envelopes as an executable design sensitivity. Inputs include client hosting
share, active users, requests, CPU-seconds, memory, tokens/task, peak windows,
model weight/KV memory, accepted throughput assumptions, storage growth and
protection copies. Throughput and equipment costs remain synthetic configuration
classes. No benchmark, probability or supplier quote is implied. One host/system
spare per class and a 70% utilization ceiling are separate resilience and operating
reserves. A/B feeds do not double productive demand. Rack-space, power and weight
limits are enforced per rack by a deterministic placement model. The base Reno design requires eleven racks and Boise three. Thermal, connector and vendor acceptance remain distinct from this arithmetic.

ADR-05: the 2027 base case estimates Reno 96.4 kW peak, Boise 23.6 kW peak, with
typical synthetic draw 60.05/14.6 kW. Boise carries all 150 TiB durable data and
reduced compute/accelerator throughput. Search and basic records do not require
full Reno AI throughput. The inherited 25 kW envelope is adequate only for that
configuration-class arithmetic; later base demand needs expansion. A 10 Gbps
network cannot restore all 150 TiB within eight hours. Pre-positioned validated
copies, transaction logs, independent keys and bootstrap are mandatory prerequisites.

## Authorization contract and bounded disclosure

Every protected resource carries identity, tenant, source/license rights, permitted
purposes, information class, compartments, source restrictions, detail/existence
readers, expiry, restriction owner/reason, review and challenge route. Every request
has an authenticated principal, scoped purpose, action and evaluation time. Missing
protected rights deny detail. Open internal questions remain broadly visible.
Rank does not grant access; an entitled new ARU hire must not suffer unjustified
denial. Legal/source restrictions control whether even existence can be disclosed.

Apply policy before search results, snippets, counts, graph edges, citations,
vectors, exports, tool output and model context. Protected institutional discovery
can execute in a separate service boundary, but the user's model receives only
authorized context. An approved existence signal contains no title, identity,
quantity or protected inference. Aggregation must evaluate its complete source
lineage, suppressing any unentitled contribution before output. A model cannot be
the sole concealment mechanism after restricted text enters its context.

Daedalus cannot write authoritative records, promote its output or acquire
institutional authority. Persistent personal memory is segregated by user; shared
skills/templates carry no memory, extracts or conversations. No private common-model
training is authorized. Agent delegation narrows rights, tenant and purpose.
Declassification requires a named information owner, Legal/source-rights review
where applicable, reason, scope, authorized recipients, expiry and human record;
the reference has no automatic declassification path.

`security.py` tests this contract with synthetic identities. It is not a universal
semantic leakage detector or deployed authorization service. Protected payloads
are excluded before the reference disclosure path, including prompt-injection
strings. Additional deployed-model red teaming and access-inference evaluation
remain production gates.

## Retention, holds and restore suppression

Records/Legal and information owners approve class-specific obligations; Technology
implements them. Proposed operational/security logs: 90 days searchable plus
275 days restricted archive, subject to incident preservation and lawful limits.
Temporary model contexts: session-bound; no persistent reuse without explicit
user selection and rights. Personal workspace artifacts: user-controlled with
periodic rights review. Authoritative Canon and source-protection records follow
their own approved schedules; operational-log TTLs do not govern them. Raw collection
is purpose/rights-limited, not an indefinite event hoard. These periods are delegated
design proposals, not statements of universal legal requirements.

Deletion/revocation creates a versioned tombstone, invalidates caches, indexes,
replicas and derived outputs, and suppresses restoration from backups. Legal hold
retains protected bytes in a restricted preservation boundary while disabling
ordinary disclosure. Backups expire under their approved schedule; a restore must
replay current holds, tombstones and entitlements before serving traffic. Keep
minimal lawful lineage/timing without retaining prohibited content. Record the
affected population, job results, exceptions, owner and review; failed propagation
is an incident. `revoke_graph` and `restore` exercise this behavior, not real erasure.

## RT-OPS-01

**Installation and asset acceptance**

Prerequisites: accepted order/configuration, qualified personnel, asset list,
maintenance window, customer work authorization and rollback. Receiving records
serials, seals, custody and quarantine. Platform compares hardware/firmware to the
approved BOM; Security validates baseline, segmentation and management paths.
Procurement reconciles delivered quantities; Finance records asset class and
readiness separately from payment. Execute approved load and loss-of-component
tests, log results and obtain service-owner acceptance. Failed checks retain
quarantine and revert to the prior configuration; no production label is granted.

## RT-OPS-02

**Change, patch and rollback**

Owner opens a traceable change with affected services, risk, tests, rollback,
entitlements and window. A qualified peer reviews immutable artifact hashes and
configuration; emergency authority is scoped and retrospectively reviewed.
Deploy to a representative isolated environment, verify health and recovery,
then stage rollout. Check monitoring, transaction integrity and denied-access
cases. On breach of acceptance limits, restore the last accepted artifact and
reconcile transactions; escalate unresolved data changes. Preserve approvals,
diffs, execution identity, timestamps, outcomes and rollback evidence. Monthly
lifecycle review identifies unsupported software, vulnerabilities and exceptions.

## RT-OPS-03

**Access and key lifecycle**

IAM accepts authoritative joiner/mover/leaver/service requests and named owners.
Provision only scoped rights; separate privileged and break-glass identities.
Key custodians perform documented dual-control ceremonies and independent recovery
copies; never place real secrets in this repository. Quarterly and event-driven
reviews reconcile complete HR/vendor/identity populations. Test revocation against
application, cache and recovery paths. On unauthorized access revoke sessions,
preserve evidence and invoke Security incident command. Retain request, approval,
inventory, rotation/revocation proof and reviewer outcome.

## RT-OPS-04

**Incident, provider maintenance and environmental alarms**

Service owner or Security declares severity and incident commander; authority is
temporary and explicit. Record discovery, impact, affected dependencies and
notification deadlines. Coordinate provider access, customer notices and safe
containment. A temperature/power alarm, lost carrier or log pipeline failure
creates an incident even if service remains available. Never suppress loss of
redundancy because SLA credit is zero. Validate restored service, logging and
data integrity before closure. Preserve complete tickets, telemetry and decision
timestamps; track corrective actions and independent retest.

## RT-OPS-05

**Failed backup and independent restore**

Prerequisites: accepted recovery scope, off-primary runbooks/artifacts, independent
identity/DNS/time/key access, protected backup and transaction-log populations,
qualified on-call roles and authorized test window. Failed or missing backup jobs
alert Reliability, reconcile expected versus observed jobs, preserve prior copies
and retry under change control. Repeated failures escalate; replication is not
accepted as a substitute for immutable/offline copies.

Restore bootstrap first (target one hour, no loss of acknowledged key changes),
then prioritized production (four hours/15 minutes), Alexandria (eight hours/one
hour), and rebuildable development (24 hours/24 hours). Check each prerequisite,
recovery-point cutoff and integrity before starting dependent services. Record
start/stop clocks, excluded/degraded features, volume and failures. Rebuild indexes
from verified stores. Failback quiesces/diverges safely, reconciles transaction
identifiers and integrity, and retains a rollback copy before switching routing.
Missed objectives remain failed tests; no calendar or synthetic PASS verifies
production recovery. Annual integrated exercise and quarterly component tests are
the proposed cadence, with actual performance evidence outstanding.

## RT-OPS-06

**Capacity, hardware replacement, media and exit**

Monthly review compares measured load and available failure capacity with workload
drivers, lead times and funding. Approve expansion only with provider delivery,
architecture, recovery and Finance evidence. Hardware replacement uses authorized
remote hands, asset identifiers, custody and verified rebuild; unexpected data
or seal/serial discrepancies stop work. Encrypt media under customer keys; return,
reuse or destruction requires owner authorization and recorded custody/method.
Exit rehearses data/key portability, replacement operation, de-installation,
transport, access revocation and final financial/evidence reconciliation. No
provider may receive customer keys as an equipment-release condition.

## Evidence form common to procedures

Record procedure/version, boundary, actor/role, authorizer, effective/recorded
times, prerequisites, source population, exact configuration/hash, expected and
observed results, exceptions, rollback, retained artifact locations, reviewer and
next action. Empty or synthetic evidence stays explicitly classified. Management
owns execution and remediation; Internal Audit does not operate these controls.
