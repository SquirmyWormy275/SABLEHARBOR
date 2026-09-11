# Commercial operations and contract economics

Status: implemented conditional planning histories. All customer decisions,
approvals, incidents and future dates are public synthetic assumptions for
2027–2031. They are not operating records or executed agreements.

The successor retains the accepted business model's 75 contract sources and
three scenarios. `source/commercial.json` supplies additional events; it never
rewrites baseline contract values. Annual subscriptions remain prepaid billed
terms, recognized monthly when service occurs. Deployment fees remain separate
accepted work. Atlas licenses remain product revenue, with its outcome delivery
capacity reserved separately from its commercial service pool.

## Pipeline, capacity and service

Every eligible contract produces dated pipeline evidence until activation. The
default synthetic outcome is won on its original start date. Explicit overrides
exercise lost opportunities, permanently held opportunities, and decisions
delayed beyond the planned start. A won opportunity still needs the scenario's
acceptance delay and available deployment capacity; neither a planned start nor
a customer decision bypasses capacity.

Each product unit dedicates 20% of its workforce-derived delivery capacity to one
shared monthly service pool. Opening customers reserve routine support first,
incident work consumes the remainder next, and deployments use what remains.
Newly activated customers also reserve their current month's support. Individual
support tickets, incident movements and deployment acceptance records support
the capacity rollforward. No hour in this pool is allocated twice. Opening
customer support reservations include that month's renewal/exit administration;
they may therefore remain for a customer whose service ends during the month.
Routine unmet monthly demand is reported as backlog for that service month;
incident remediation hours carry forward until resolved.

Incident demand is an explicit source assumption. Failure to finish that month's
incident demand records a service breach, creates a single earned-service credit,
and enters the contract's renewal review. A breach in the preceding 12 months
causes modeled nonrenewal at the configured threshold. Resolving the incident
does not erase the original breach. Increasing service capacity can avoid the
breach, its credit and the later customer loss. The original scenario churn rule
remains as a separately identified renewal cause.

These are monthly planning mechanics, not a claim that support hours establish
production uptime or a particular contractual SLA. The model grants no live
customer entitlement and does not choose a deployment/runtime architecture.

## Versions, amendments and customer credits

Activation, renewal, expansion, price amendments, contraction and cancellation
create immutable version rows. Each retains its applied month, original
effective month and synthetic approval identifier. A change that becomes due
before delayed activation is held and retried; it is applied once after actual
activation. A change for a lost or closed customer receives an explicit
nonapplicable disposition. Delays do not silently erase amendments.

Positive changes bill the additional monthly rate for the unexpired part of the
existing annual term. Contractions credit the unearned portion of the same
term. Cancellation credits the entire unearned balance, ends recurring revenue,
and prevents future service recognition. Amendments change seats and actual
monthly recognized revenue as well as the reported ARR. Annual renewal
escalation applies to the effective rate, including earlier changes.

Each billed invoice retains an unearned claim. Recognition consumes claims in
order; reductions consume remaining claims from newest to oldest. Earned-service
credits use earned invoice capacity and cannot consume the unearned balance.
The credit module applies credits to open AR, surviving written-off claims, and
only then refundable collected cash. Commercial code does not bypass those
collection, credit or refund controls.

## Reconciliations and review tables

| Table | Purpose |
| --- | --- |
| `commercial_pipeline` | Customer decision, planned activation and capacity/acceptance holds |
| `contract_versions` | Effective rate, seats, term and approval history |
| `commercial_changes` | Applied, held or nonapplicable amendment disposition |
| `commercial_service_tickets` | Monthly routine support demand and service |
| `service_incidents` | Incident demand, work performed, open hours and preserved breach |
| `commercial_renewals` | Renewal decision and service/scenario cause |
| `commercial_capacity` | Shared capacity, support, incident, deployment and unused hours |
| `commercial_metrics` | Active customers, concentration, ARR and support backlog |
| `commercial_arr_bridge` | Opening + new + expansion + price − contraction − churn = closing ARR |
| `commercial_deferred_rollforward` | Opening + billings − unearned credits − recognition = closing deferred revenue |

All scenarios cover every month. Every baseline contract has a deferred
rollforward, including zero balances before activation and after closure. These
balances reconcile to invoice claims and the product unit's general ledger.
Earned-service credits reduce revenue through credit-note journals; they do not
reduce gross contractual ARR or deferred revenue a second time.

Validation independently checks complete, unique monthly populations, continuous
opening/closing balances, aggregate ARR, deferred balances against month-end
books, capacity allocation, approval timing and nonnegative balances. Tests also
exercise changes in capacity, lost opportunities, delayed amendments, actual
invoices and journal consequences, cancellation, and deliberately corrupted
exported bridges.
