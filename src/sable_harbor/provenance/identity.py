from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath

from sable_harbor.core.ids import stable_id

GENERATOR_VERSION = "0.1.0"
SYNTHETIC_CALIBRATION_THROUGH = date(2026, 8, 31)
FORECAST_FROM = date(2026, 9, 1)
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

PROFILE_CONTRACTS: dict[str, frozenset[str]] = {
    "synthetic_common": frozenset({"synthetic_common"}),
    "baseline": frozenset({"base", "low", "high", "stress"}),
    "full": frozenset({"base", "low", "high", "stress"}),
    "full_history": frozenset({"base", "low", "high", "stress"}),
    "smoke": frozenset({"base"}),
    "standard": frozenset({"base", "low", "high", "stress"}),
    "stress": frozenset({"stress"}),
}

GENERATION_INPUT_GLOBS = (
    "config/finance/**/*.json",
    "config/finance/**/*.yml",
    "config/releases/**/*.json",
    "db/migrations/versions/*.py",
    "db/sql/*.sql",
    "docs/finance/CANON_SOURCE_LOCK.json",
    "docs/finance/KNOWN_LIMITATIONS.md",
    "pyproject.toml",
    "releases/manifests/*.schema.json",
    "src/sable_harbor/**/*.py",
    "uv.lock",
)
SOURCE_LOCK_SECTIONS = (
    "controlling_source",
    "historical_knowledge_snapshot",
    "noncontrolling_reference",
)
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


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


def _source_lock_document() -> dict[str, object]:
    path = REPOSITORY_ROOT / "docs/finance/CANON_SOURCE_LOCK.json"
    document = json.loads(path.read_text())
    if not isinstance(document, dict):
        raise ValueError("Canon source lock must be a JSON object")
    return document


def _require_governed_git_checkout() -> None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or Path(result.stdout.strip()).resolve() != REPOSITORY_ROOT.resolve():
        raise ValueError(
            "Finance generation requires a full governed SABLEHARBOR Git checkout; "
            "standalone or shallow source installations cannot resolve the pinned canon snapshots"
        )


def repository_head() -> str:
    """Resolve the governed SABLEHARBOR checkout HEAD, independent of caller CWD."""
    _require_governed_git_checkout()
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    if result.returncode != 0 or COMMIT_SHA.fullmatch(commit) is None:
        diagnostic = result.stderr.strip()
        raise ValueError(f"Cannot resolve governed SABLEHARBOR source commit: {diagnostic}")
    return commit


def _git_blob(commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{path}"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        diagnostic = result.stderr.decode(errors="replace").strip()
        raise ValueError(f"Unresolvable canon source snapshot {commit}:{path}: {diagnostic}")
    return result.stdout


def canon_source_snapshot_manifest() -> tuple[dict[str, str], ...]:
    """Resolve and hash every governed Git blob named by the canon source lock."""
    _require_governed_git_checkout()
    document = _source_lock_document()
    entries: list[dict[str, str]] = []
    for section_name in SOURCE_LOCK_SECTIONS:
        section = document.get(section_name)
        if not isinstance(section, dict):
            raise ValueError(f"Canon source lock must define object {section_name!r}")
        commit = section.get("commit")
        files = section.get("files")
        if not isinstance(commit, str) or COMMIT_SHA.fullmatch(commit) is None:
            raise ValueError(f"Canon source lock {section_name!r} requires a full commit SHA")
        if not isinstance(files, list) or not files:
            raise ValueError(f"Canon source lock {section_name!r} requires a nonempty file list")
        for raw_path in files:
            if not isinstance(raw_path, str):
                raise ValueError(f"Canon source lock {section_name!r} has a non-string path")
            portable_path = PurePosixPath(raw_path)
            if portable_path.is_absolute() or ".." in portable_path.parts:
                raise ValueError(
                    f"Canon source lock {section_name!r} has an unsafe path {raw_path!r}"
                )
            blob = _git_blob(commit, raw_path)
            if section_name == "controlling_source":
                live_path = REPOSITORY_ROOT / raw_path
                if not live_path.is_file():
                    raise ValueError(f"Current controlling source is absent: {raw_path}")
                if live_path.read_bytes() != blob:
                    raise ValueError(
                        "Current controlling source differs from its pinned Git snapshot: "
                        f"{commit}:{raw_path}"
                    )
            entries.append(
                {
                    "path": f"git-snapshot/{section_name}/{commit}/{raw_path}",
                    "sha256": hashlib.sha256(blob).hexdigest(),
                }
            )
    return tuple(sorted(entries, key=lambda item: item["path"]))


def canon_source_snapshot_digests() -> dict[str, str]:
    manifest = canon_source_snapshot_manifest()
    output: dict[str, str] = {}
    for section_name in SOURCE_LOCK_SECTIONS:
        prefix = f"git-snapshot/{section_name}/"
        section_entries = [entry for entry in manifest if entry["path"].startswith(prefix)]
        payload = json.dumps(section_entries, sort_keys=True, separators=(",", ":"))
        output[section_name] = hashlib.sha256(payload.encode()).hexdigest()
    return output


def generation_input_paths() -> tuple[Path, ...]:
    paths = {
        path.relative_to(REPOSITORY_ROOT)
        for pattern in GENERATION_INPUT_GLOBS
        for path in REPOSITORY_ROOT.glob(pattern)
        if path.is_file()
    }
    source_lock = _source_lock_document()
    controlling = source_lock.get("controlling_source")
    if not isinstance(controlling, dict):
        raise ValueError("Canon source lock must define object 'controlling_source'")
    for source_path in controlling.get("files", []):
        candidate = REPOSITORY_ROOT / str(source_path)
        if candidate.is_file():
            paths.add(candidate.relative_to(REPOSITORY_ROOT))
    return tuple(sorted(paths, key=lambda path: path.as_posix()))


def generation_input_manifest() -> tuple[dict[str, str], ...]:
    live_manifest = tuple(
        {
            "path": path.as_posix(),
            "sha256": hashlib.sha256(_repository_path(path).read_bytes()).hexdigest(),
        }
        for path in generation_input_paths()
    )
    return tuple(
        sorted((*live_manifest, *canon_source_snapshot_manifest()), key=lambda item: item["path"])
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
    synthetic_calibration_through: date
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
            synthetic_calibration_through=SYNTHETIC_CALIBRATION_THROUGH,
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
    def synthetic_calibration_dataset_id(self) -> str:
        return stable_id(
            "synthetic_calibration_dataset",
            f"{self.generator_version}:{self.seed}:"
            f"{self.synthetic_calibration_through.isoformat()}:"
            f"{self.input_manifest_digest}",
        )

    @property
    def build_id(self) -> str:
        return stable_id(
            "generation_build",
            self.run_id,
        )
