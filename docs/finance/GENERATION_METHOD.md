# Generation method

Seed `20260831` is the default. UUIDv5 keys derive from stable natural keys. Randomness is isolated through a seeded `Random` instance.

- `smoke`: minimal opening-ledger fixture used by fast tests.
- `baseline`: deterministic FY2026 enterprise comparison profile.
- `standard`: 48 monthly periods from 2023 through 2026, actual through August 2026 and forecast afterward.
- `full_history`: standard detail plus noncontrolling 2016–2022 annual anchors.
- scenarios: `base`, `low`, `high`, and correlated `stress` from versioned YAML.

Causal transaction services exist for the required commercial, workforce, procurement, asset, debt, mining, logistics, recovery, Willow, and Atlas paths. The enterprise-scale monthly control generator still uses driver-to-ledger summary postings; expanding every standard-profile record through every causal subledger is remaining work and is not concealed.
