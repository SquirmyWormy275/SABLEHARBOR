# Blackridge Generation Guide

Install with `python -m pip install -e 'blackridge[dev]'`. Generate `smoke`, `m00`, or `full_2015`
with `python -m blackridge generate --profile PROFILE --seed 20150112`. Generation uses separate
deterministic table streams, UUID5 identities, chronological event ordering, and fixed profile
scales. Repeating a build with the same commit, profile, seed, and configuration produces the same
database hash.

