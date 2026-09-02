# Blackridge Data Architecture

Blackridge is a deterministic repository-local data product. SQLite is the canonical public
representation; generated workbooks and reports are downstream interfaces. Stable UUID5 keys,
source identifiers, event/record/availability timestamps, provenance, and hashes support replay
and cutoff-aware analysis. The public schema excludes hidden causal truth.

```mermaid
flowchart LR
  C[Canon and profile] --> G[Deterministic generator]
  G --> D[(Public SQLite)]
  D --> V[Validation and reconciliation]
  D --> X[Excel and extracts]
  V --> M[Manifest and checksums]
  X --> M
```

