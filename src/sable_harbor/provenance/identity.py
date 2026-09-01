from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sable_harbor.core.ids import stable_id

GENERATOR_VERSION = "0.1.0"
ACTUAL_THROUGH = date(2026, 8, 31)
FORECAST_FROM = date(2026, 9, 1)


def normalize_profile_scenario(profile: str, scenario: str) -> tuple[str, str]:
    normalized_profile = profile.strip().lower().replace("-", "_")
    normalized_scenario = scenario.strip().lower().replace("-", "_")
    if normalized_profile == "stress":
        normalized_scenario = "stress"
    return normalized_profile, normalized_scenario


def _digest_paths(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path).encode())
        digest.update(path.read_bytes() if path.exists() else b"MISSING")
    return digest.hexdigest()


def generator_source_digest() -> str:
    root = Path(__file__).resolve().parents[1]
    return _digest_paths(tuple(sorted(root.rglob("*.py"))))


def assumptions_digest() -> str:
    return _digest_paths((Path("config/finance/assumptions/quantitative.yml"),))


def canon_source_lock_digest() -> str:
    return _digest_paths((Path("docs/finance/CANON_SOURCE_LOCK.json"),))


@dataclass(frozen=True)
class RunIdentity:
    profile: str
    scenario: str
    seed: int
    generator_version: str
    actual_through: date
    forecast_from: date

    @classmethod
    def build(cls, *, profile: str, scenario: str, seed: int) -> RunIdentity:
        profile, scenario = normalize_profile_scenario(profile, scenario)
        return cls(
            profile=profile,
            scenario=scenario,
            seed=seed,
            generator_version=GENERATOR_VERSION,
            actual_through=ACTUAL_THROUGH,
            forecast_from=FORECAST_FROM,
        )

    @property
    def run_id(self) -> str:
        payload = json.dumps(
            {
                "generator_version": self.generator_version,
                "profile": self.profile,
                "scenario": self.scenario,
                "seed": self.seed,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return stable_id("generation_run", payload)

    @property
    def actual_dataset_id(self) -> str:
        return stable_id(
            "actual_dataset",
            f"{self.generator_version}:{self.seed}:{self.actual_through.isoformat()}",
        )
