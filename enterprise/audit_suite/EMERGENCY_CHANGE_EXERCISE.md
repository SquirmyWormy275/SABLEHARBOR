# Prospective local emergency-change exercise

`company_emergency_change_activity.py` creates a new private CompanyStore source pair for SH-ENG-005. It does not execute a production change, call a service, install software, collect audit evidence, or touch the existing A/B engagement. The only changing target is an in-memory reference configuration. Its authored 2027 event times are future simulation relative to September 29, 2026; `imported_at` records actual generation time separately.

The Clean branch records a local simulated timeout trigger, candidate, arithmetic test, and missing emergency-authority evidence. The gate blocks application. A distinct proposed management review contact records a local observation, not corporate approval. The Messy branch starts from the same baseline and blocked gate, then records a simulated **invalid** temporary bypass, changes the in-memory fixture, observes it, rolls it back, and leaves one exception open. The temporary bypass never becomes authorized through later review or rollback. The canonical control assignment supplies proposed contacts; it does not establish an emergency approver or deployed service.

The trusted operator supplies an exact private JSON recipe with `company`, `clean_branch`, `messy_branch`, `exercise_id`, `start_at`, and `local_rule`, then runs:

```bash
uv run --extra audit-suite python tools/audit_suite/emergency_change_exercise.py \
  --config /absolute/private/recipe.json \
  --output /absolute/private/NEW-source-pair
```

The output parent must already be private (0700), and the destination must be new. The source database, source receipt, and run manifest are private (0600). Native versions pin their source code and canon inputs, carry causal predecessor hashes, and retain real import time separately from simulated event and availability time. No grants or collections are created. The manifest hashes the native database and receipt. Source collection into a future audit requires its own explicit registry, owner route, authorization, temporal assessment, and independent review.
