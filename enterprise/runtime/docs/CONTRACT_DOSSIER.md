# Proposed colocation agreement and incorporated schedules

**Document ID:** SH-RT-CONTRACT-001
**Version:** 1.0.0
**Status:** CUSTOMER-PROPOSED DRAFT; unsigned; no real agreement or reservation
**Prepared:** 2026-09-11; effective only upon authorized execution and order acceptance
**Owner:** Procurement / Enterprise Technology Services
**Reviewers:** Legal, Finance, Security; Internal Audit may independently evaluate
**Authority:** PR119 owner mandate and September 11 runtime selection decision
**Structured companion:** `enterprise/services/source/runtime_sites_2026-09-11.json`

## Master agreement RT-MSA-001

Sable Harbor, LLC (SHI), as proposed customer, and the provider legal entity to be
verified in each site order would enter this agreement for facility services.
Switch and IDACORE are selected provider brands; neither brand alone establishes
the contracting subsidiary. No signature, incorporation number or provider
acknowledgment is represented. Each party acts only in its own legal capacity.

The provider would supply assigned enclosure space, metered power, cooling within
the accepted equipment envelope, building access, facility operation and scoped
remote hands. Sable Harbor retains equipment title, workloads, network boundaries,
identity administration, keys, data, application operations, backup policy,
classification, customer commitments and institutional authority. Facility access
does not authorize logical access or transfer J2's information authority.

An executed order would identify the building, enclosure, delivery points, power
and cooling configuration, measurement method and commercial lines. An order
would commence billing only after technical acceptance, except explicitly agreed
reservation charges. A purchase order cannot override this agreement. Precedence
would be: signed negotiated deviations identifying the affected clause; site order
for quantities/dates/price; this master; security and evidence schedules; other
incorporated schedules. A weaker order protection requires an express deviation
accepted by Legal and the accountable risk owner. Provider website changes would
not amend the agreement.

The proposed initial term is 12 months after acceptance for Boise and 24 months
for Reno, each subject to negotiation. Renewal would be by written agreement or
an expressly selected renewal mechanism with 90-day notice; no automatic extension
is assumed in finance. Material breach would allow written notice and 30 days to
cure where curable. An imminent security or safety incident requires immediate
containment coordination. Termination does not transfer customer property, keys
or confidential data and does not extinguish preservation duties.

## Site order RT-SO-RENO, revision 1.0.0

Customer: Sable Harbor, LLC. Selected provider/campus: Switch TAHOE RENO — The
Citadel Campus. Provider legal party, building, enclosure and commencement date:
unverified/unassigned. State: draft, procurement pending; zero reserved capacity.

Request 75 and 100 kW alternatives, expansion to 200–250 kW, dedicated controlled
enclosure, A/B delivery each capable of carrying the accepted load, two diverse
carrier entrances and 10 Gbps initial transport with 100 Gbps pathway. Power is
usable IT delivery, not summed redundant PSU ratings. High-density and future
liquid-cooling compatibility require provider confirmation; no campus-wide
marketing specification establishes this enclosure's capability.

The financial sensitivity uses $350/kW/month as an analyst assumption, not a Switch
quote, plus separately modeled connectivity and remote hands. Installation,
deposits, taxes, cabinet fees, expansion reservations and cancellation exposures
require itemized quotations before execution. An assumed commitment in the cost
model is not a commitment to Switch. The service order incorporates every schedule
below. Finance and Procurement approve commercial completeness; Legal approves the
legal party and negotiated instrument; Technology and Security accept delivery.

## Site order RT-SO-BOISE, revision 1.0.0

Customer: Sable Harbor, LLC. Selected facility: IDACORE Boise, 2653 S Victory View
Way, Boise, Idaho 83709. Legal party, enclosure, commencement and actual capacity
remain unverified/unassigned. State: draft, procurement pending.

The provisional recovery envelope is 25 kW with 50 and 100 kW expansion cases.
The previous unexplained 6 kW lower bound is superseded for this design. The base
2027 configuration estimates 23.6 kW peak and 14.6 kW synthetic typical draw;
later scenarios exceed 25 kW. No recovery objective is verified by these estimates.

Public pricing reports $300/kW/month, power included and actual-draw billing.
At 14.6 kW synthetic average this is $4,380/month before separate connectivity,
remote hands, taxes and other quoted lines. A hypothetical 25 kW committed case
would be $7,500/month; that is a sensitivity, not the public billing rule. Meter
interval, averaging, demand peaks, minimums and settlement must be specified in the
accepted order. The pricing page's short-term wording and 12-month FAQ require
explicit resolution. No cooling/power claims from IDACORE East are imported here.

## Schedule A — Commercial measurement and invoices

Every price line would identify currency, tax treatment, quantity, unit, included
service, rate source, escalation, start/stop dates and billing basis. The accepted
schedule must separately show cage/cabinet, metered or committed usable power,
cooling surcharge, setup, cross-connect, IP transit, private transport, OOB, remote
hands, receiving/storage, refundable deposit, prepayment, expansion option,
cancellation, de-installation and migration overlap. A zero line must explicitly
mean included or waived; blank means unquoted. A/B redundancy is not twice the
productive load. Power-inclusive rates cannot receive a second utility/PUE charge.

Meters would expose interval data and calibration records. An invoice would show
meter identifiers, interval completeness, actual draw, peak, committed quantity
if applicable, power factor where material and calculation. Customer may dispute
a supported discrepancy within 60 days, pay undisputed amounts, and request joint
re-performance. The parties would resolve meter failure through an agreed estimate
with disclosed dates; missing readings cannot silently become measured evidence.
Annual escalation requires a stated percentage/cap and anniversary; no unstated
pass-through or auto-reservation is approved.

## Schedule B — Availability and credits

Proposed critical-power target: 100% at each agreed customer delivery point under
the accepted usable load. An outage begins at first loss of required delivery and
ends at restored stable delivery documented by telemetry. Count intervals once
per affected service. A/B loss with surviving load is a redundancy incident even
when no qualifying outage occurs. Power, network and application availability
are measured separately; this schedule promises no application uptime.

Monthly availability equals (eligible minutes minus qualifying unavailable
minutes) / eligible minutes. Calculate each affected enclosure/service before
aggregation; unrelated healthy cabinets cannot dilute a failed enclosure. Agreed
maintenance exclusions would require the notice and approval record, precise
interval and reason. Emergency maintenance and force-majeure exclusions remain
visible in gross outage and risk reports even when excluded from credits.

Customer-proposed credits against affected monthly recurring facility charges:
any qualifying interruption with availability at least 99.9%: 5%; below 99.9% to
99%: 10%; below 99% to 95%: 25%; below 95%: 50%. Credit capped at 50% of that base;
taxes, unrelated services and one-time installation are excluded. A 60-minute
qualifying outage in 43,200 minutes yields 99.8611% and $1,000 on a $10,000 affected
base. No outage yields zero credit. Claims would be submitted within 60 days with
provider reconciliation; proposed automatic crediting remains a negotiation item.
Three qualifying breaches in a rolling six months would permit termination of the
affected order without early termination fees. Credits never establish acceptable
risk or substitute for corrective action.

## Schedule C — Remote hands, incidents and maintenance

P1 remote hands: acknowledgment within 15 minutes and qualified engagement within
30 minutes. Record ticket receipt, acknowledgment, dispatch, physical arrival,
hands-on start, restoration and closure separately. Engagement is not restoration.
Customer-caused stop clocks require a timestamped request and customer concurrence;
provider staffing shortages do not automatically stop the clock.

For qualifying availability P1s, initial notice would be within 30 minutes of
detection or reasonable awareness. Suspected or confirmed security impact would
be notified within one hour; confirmation cannot defer preliminary notice.
Use the agreed secure incident channel, scope/time/known-impact statement,
preservation action and next update time. Provide hourly P1 updates until stable,
initial cause analysis within five business days and a corrective-action plan
within ten, with uncertainty stated. Provider does not speak for customer to
regulators or clients without authority.

Ordinary planned maintenance requires 14 days notice; material electrical/network
work requires 30 where feasible. Describe affected delivery, redundancy loss,
qualified personnel, rollback, test plan and escalation. Emergency work prioritizes
safety and prompt notice, followed by retrospective review. Tenant personnel must
not pull live facility feeds or operate provider switchgear. Electrical tests require
provider approval, qualified operators and a written safety/rollback plan.

## Schedule D — Physical and logical security

Provider would maintain controlled perimeter, staffed/monitored entry, visitor
identity and escorts, anti-tailgating measures, alarm response, synchronized CCTV
and access logs. Customer supplies its named access list, role/purpose and expiry.
Provider would promptly execute authorized revocations and preserve the timestamp.
Quarterly reviews reconcile all approved people, provider master-access users,
visitors, expired contractors and emergency entries. Emergency access is logged,
bounded and retrospectively reviewed; it is not routine privileged access.

Remote hands requires an authenticated customer work order, asset identifiers,
permitted steps, maintenance window and explicit prohibition on data/key access.
Receiving uses chain of custody, package inspection, quarantine and inventory
reconciliation. Lost seals, serial mismatches or unauthorized work stop acceptance
and escalate. Provider facility management networks remain outside customer trust;
customer controls edge, OOB, identities, HSMs, segmentation and cryptographic policy.

## Schedule E — Confidentiality, records and assurance

Each party would use confidential information only for the contracted purpose,
restrict access to authorized personnel, protect transmission and storage, and
notify compelled disclosure where lawful. No model training, private-data reuse or
cross-customer sharing is granted. Equipment custody does not grant a data license.
Provider-held records follow agreed class-based retention, legal holds and secure
return/deletion; this is not a blanket retention period for Alexandria Canon.

Requested control evidence would be delivered within ten business days, subject to
documented lawful/confidentiality restrictions and agreed alternative evidence.
Monthly packs include incident populations, maintenance, access anomalies, metering,
capacity and credits. Annual assurance review requests report scope, auditor,
period, opinion, exceptions, subservice treatment and CUECs; absence stays an open
evidence dependency. A bridge letter is management representation, not an auditor
extension of the tested period. Secure reports must not enter this public repo.

## Schedule F — Continuity, concentration, title and exit

Provider would disclose material subcontracted facility services and changes that
affect agreed controls, concentration or recovery. Customer approval/escalation
would apply to material adverse changes under the negotiated order. Lists of
carriers or distinct provider brands do not establish route, identity or key
independence. Annual integrated DR and risk-based component tests require agreed
scope, prerequisites, recovery point, integrity checks and failback reconciliation.

Customer retains title to hardware, media, data and keys. Proposed terms prohibit
liens or access restrictions that prevent emergency recovery or orderly removal;
Legal must resolve actual enforceability and provider deviations. Exit would allow
90 days coordinated transition, continued paid service at agreed rates, inventory
and media custody, secure shipping, cross-connect cessation, access revocation,
retained evidence and final billing reconciliation. Keys are never surrendered as
an exit condition. Deletion confirmation identifies records, method, scope and
legal-hold exceptions rather than asserting deletion of held material.

## Schedule G — Liability, insurance and approval register

Proposed ordinary direct-damage cap is 12 months of affected fees; confidentiality,
unauthorized property disposal, intentional misconduct and gross negligence require
separate negotiated treatment. No enforceability opinion is supplied. Customer
requests provider general liability, cyber and property/custody coverage with
limits tied to equipment exposure; certificates, exclusions and cancellation
notice remain unreceived. Customer insures its equipment as separately arranged.
No indemnity, consequential-loss waiver or subrogation term is treated as accepted.

Negotiation register: legal counterparty verification (Legal); price/meter/minimum
and deposits (Finance/Procurement); rack/cooling/A-B/route acceptance (Technology);
access and evidence rights (Security); liability/lien/insurance terms (Legal);
recovery and exit (Reliability). All are OPEN FOR NEGOTIATION, not provider-choice
questions. Incompatible mandatory terms require owner disposition, not substitution.

Customer authorized signature: __________________  Date: __________
Verified provider legal entity: __________________
Provider authorized signature: __________________  Date: __________

**Blank draft blocks only. No signature, expenditure or real-world obligation is authorized by this artifact.**
