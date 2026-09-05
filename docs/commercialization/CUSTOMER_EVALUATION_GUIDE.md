# Customer evaluation guide

1. Generate the `standard` profile with the documented seed and record its explicit run ID.
2. Run enterprise financial validation and the named-query cookbook for that run ID.
3. Build the public package for that same run and inspect the allowlisted SQLite evidence extract,
   CSV row counts, workbook checks, financial-validation registry, artifact-safety result, and
   manifest digests.
4. Trace selected source events to journals and reports.
5. Evaluate domain coverage and known limitations against the intended use.

Do not treat synthetic identities, economics, legal structures, mine parameters, or acquisition values as real-world information or accepted Sable Harbor canon.
