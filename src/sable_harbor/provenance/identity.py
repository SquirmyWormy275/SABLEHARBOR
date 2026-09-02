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
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

PROFILE_CONTRACTS: dict[str, frozenset[str]] = {
    "actual_common": frozenset({"actual_common"}),
    "baseline": frozenset({"base", "low", "high", "stress"}),
    "benchmark_private": frozenset({"base", "low", "high", "stress"}),
    "full": frozenset({"base", "low", "high", "stress"}),
    "full_history": frozenset({"base", "low", "high", "stress"}),
    "smoke": frozenset({"base"}),
    "standard": frozenset({"base", "low", "high", "stress"}),
    "stress": frozenset({"stress"}),
}

GENERATION_INPUT_GLOBS = (
    "config/finance/assumptions/**/*.yml",
    "config/finance/scenarios/**/*.yml",
    "db/migrations/versions/*.py",
    "docs/finance/CANON_SOURCE_LOCK.json",
    "src/sable_harbor/**/*.py",
)


def normalize_profile_scenario(profile: str, scenario: str) -> tuple[str, str]:
    normalized_profile = profile.strip().lower().replace("-", "_")
    normalized_scenario = scenario.strip().lower().replace("-", "_")
    if normalized_profile == "stress":
        normalized_scenario = "stress"
    allowed = PROFILE_CONTRACTS.get(normalized_profile)
    if allowed is None:
        raise ValueError(f"Unknown generation profile {normalized_profile!r}")
    if normalized_scenario not in allowed:
        raise ValueError(
            f"Scenario {normalized_scenario!r} is incompatible with profile "
            f"{normalized_profile!r}; expected one of {sorted(allowed)}"
        )
    return normalized_profile, normalized_scenario


def _repository_path(path: Path) -> Path:
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def _digest_paths(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        absolute = _repository_path(path)
        try:
            portable = absolute.relative_to(REPOSITORY_ROOT).as_posix()
        except ValueError as exc:
            raise ValueError(f"Generation input is outside the repository: {absolute}") from exc
        digest.update(portable.encode())
        digest.update(b"\0")
        digest.update(absolute.read_bytes() if absolute.exists() else b"MISSING")
        digest.update(b"\0")
    return digest.hexdigest()


def generation_input_paths() -> tuple[Path, ...]:
    paths = {
        path.relative_to(REPOSITORY_ROOT)
        for pattern in GENERATION_INPUT_GLOBS
        for path in REPOSITORY_ROOT.glob(pattern)
        if path.is_file()
    }
    return tuple(sorted(paths, key=lambda path: path.as_posix()))


def generation_input_manifest() -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "path": path.as_posix(),
            "sha256": hashlib.sha256(_repository_path(path).read_bytes()).hexdigest(),
        }
        for path in generation_input_paths()
    )


def generation_input_manifest_digest() -> str:
    payload = json.dumps(generation_input_manifest(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def generator_source_digest() -> str:
    return _digest_paths(tuple(path for path in generation_input_paths() if path.parts[0] == "src"))


def assumptions_digest() -> str:
    return _digest_paths(
        tuple(
            path
            for path in generation_input_paths()
            if path.parts[:3] == ("config", "finance", "assumptions")
        )
    )


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
    input_manifest_digest: str

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
            input_manifest_digest=generation_input_manifest_digest(),
        )

    @property
    def run_id(self) -> str:
        payload = json.dumps(
            {
                "generator_version": self.generator_version,
                "profile": self.profile,
                "scenario": self.scenario,
                "seed": self.seed,
                "input_manifest_digest": self.input_manifest_digest,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return stable_id("generation_run", payload)

    @property
    def actual_dataset_id(self) -> str:
        return stable_id(
            "actual_dataset",
            f"{self.generator_version}:{self.seed}:{self.actual_through.isoformat()}:"
            f"{self.input_manifest_digest}",
        )

    @property
    def build_id(self) -> str:
        return stable_id(
            "generation_build",
            self.run_id,
        )
