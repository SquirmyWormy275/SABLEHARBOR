# Tier 1 Advisory policy integration

`OperatingModel` applies `source/advisory_policy.json`, implementing `SH-ADV-009`
section 6 and decision `ADV-217`. Measurable-value payout is zero below 70%
achievement, 25% at 70%, 60% at 85%, 100% at target, and at most 125% at 120% or
above, with linear interpolation. A lower contractual cap still wins. Capability
acceptance and fixed Decision pricing retain their existing mechanisms.

The execution policy is a deep copy. Original business source files, input objects,
and the `BusinessModel` baseline remain unchanged. The overlay is included in the
operating input fingerprint and its controlling documents in the source inventory.
All operating certifications are reperformed against it before model acceptance.
The matter-gate adapter itself does not rewrite contracts or the finance engine.

Carry plan direction is locked by the Tier 1 addendum. Individual awards and
professional implementation are still gated. This model neither grants units nor
accrues a personal carry award. Operating rollforwards state that distinction; they
do not repeat the predecessor's obsolete claim that plan mechanics remain open.

The original pricing and contract populations remain synthetic calibration. This
overlay does not invent new client agreements or update every quoted rate. Earlier
release bytes and the retained 2026 reconstruction are not restated.

Regression tests: `enterprise/operations/tests/test_advisory_policy.py`.
