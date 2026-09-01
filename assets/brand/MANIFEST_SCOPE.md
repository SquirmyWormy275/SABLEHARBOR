# Brand Manifest Scope

The original v0.2 build manifest is preserved as `manifest.v0.2.0-legacy.json`. It records the immutable build snapshot, including publication pages generated at that time.

The current `manifest.json` governs the brand system itself and delegates current company, business-line, and wiki publication structure to:

- `docs/company/README.md`;
- `docs/business-lines/registry.json`;
- `docs/wiki/`.

Publication-page hashes in the legacy manifest are historical build evidence, not current authority after the enterprise portal reorganization. The brand validator checks only the legacy records within `assets/brand/` and separately verifies the present identity matrix and required collateral.
