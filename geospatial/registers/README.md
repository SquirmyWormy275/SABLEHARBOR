# Geographic registers

`SITE_REGISTER_CURRENT.csv` is the generated current site register, derived from the governed catalog and delegated geographic addendum. Current readers also expose the complete decisions in `geospatial/finalization/DECISIONS.json` and `geospatial/completion/SITE_DOCKET.json`.

`SITE_REGISTER.csv` preserves the exact accepted PR162 snapshot used by the legal host-rights publication. Its SHA-256 is `d9d445d6ebab15bad40186a7de742ddd881b3971119ae7da3ae95cb1886f6720`. It is historical source evidence, not the current geographic decision register. The geographic builder verifies this pin and writes current records to the separately named file. This preserves the other session's legal publication and its exact dependency acceptance without changing its validator or silently rewriting its source evidence.

`SOURCE_COVERAGE.csv` and `CENSUS_MANIFEST.json` remain the original discovery census. Later review increments retain their own revisions; the final source ledger does not rewrite the original extraction history.
