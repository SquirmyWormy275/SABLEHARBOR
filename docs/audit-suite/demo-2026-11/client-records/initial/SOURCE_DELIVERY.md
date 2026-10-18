# Opening the company records

Read SCOPE.md and manifest.json, then open the JSON, CSV and Markdown files with ordinary tools. The video and timestamped VTT are in walkthrough/. The manifest names each artifact version, source locator, availability, byte count and SHA-256 hash. A derivative is a readable company export with an original relationship; it is not a vendor original. Contact the company with the locator and original hash to inspect the retained original.

Keep each received directory separately. A successor identifies the exact earlier artifact ID, version and hash in supersedes. Earlier deliveries remain historical records. A later directory is an incremental client submission and must be retained alongside earlier ones; it does not replace every file. The manifest describes company source relationships and makes no requirement about your tools or audit conclusions.

Verify a received directory with the separately supplied standard-library verifier: `python demo_source_delivery.py verify DIRECTORY`. It rejects hash changes, missing files, escaping paths, aliases and unexpected members. You need Python 3.11 or newer, not the company implementation. Supply only the directory actually received to a consumer; credentials and authoring state are unnecessary.
