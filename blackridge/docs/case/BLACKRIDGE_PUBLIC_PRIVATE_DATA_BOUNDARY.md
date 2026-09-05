# Blackridge Public/Private Data Boundary

The public repository contains schemas, deterministic public generators, participant-visible data,
workbooks, validation, and manifests. It must never contain private control-plane tables, answer
keys, hidden component health, exact hidden provenance, evaluator scoring, or causal truth. Private
generation is intentionally not published here. The private evaluator control plane exists at
`SquirmyWormy275/SABLEHARBOR-ALEXANDRIA-CONTROL`. Public metadata records its existence without
copying hidden truth. A boundary scan of the public working tree, public workbook, and public schema
checks that restricted evaluator payloads are absent.
