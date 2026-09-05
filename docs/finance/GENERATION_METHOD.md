# Generation method

Seed `20260831` is the default. UUIDv5 keys derive from stable natural keys. Randomness is isolated through a seeded `Random` instance.

Every generated 2023–2026 numeric record is synthetic scenario/calibration data. The persisted
cutoff separates a shared invariant calibration layer from scenario-specific forecast layers; it
does not distinguish observed company history from forecast.

- `smoke`: minimal opening-ledger fixture used by fast tests.
- `baseline`: deterministic FY2026 enterprise comparison profile.
- `standard`: 48 synthetic monthly scenario/calibration periods from 2023 through 2026, with a
  shared invariant pre-cutoff layer through August 2026 and scenario-specific forecast afterward.
- `full_history`: standard synthetic detail plus noncontrolling 2016–2022 calibration anchors; the
  profile name does not assert complete or observed history.
- scenarios: `base`, `low`, `high`, and correlated `stress` from versioned YAML.

Causal transaction services exist for the required commercial, workforce, procurement, asset, debt,
mining, logistics, recovery, Willow, and Atlas paths. The enterprise-scale monthly control generator
applies configured driver multipliers only to SHI, `RWH`, and ARU summary postings. Cradle, Research,
Advisory, and Capital inputs are recorded-only in v0.1 and carry no generated-output causal
attribution. Expanding every standard-profile record through every causal subledger remains work and
is not concealed.
