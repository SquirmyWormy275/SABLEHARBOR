"""Portable publication boundaries and independent source calculations."""

import copy
import os
from pathlib import Path

import pytest

from tools.audit_suite import demo_source_delivery as delivery


def edition(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    content = b'{"setting":30}\n'
    (inputs / "record.json").write_bytes(content)
    spec = {
        "artifact_id": "OBS-01",
        "version": 1,
        "input_path": "record.json",
        "allowed": True,
        "path": "records/observation.json",
        "media_type": "application/json",
        "bytes": len(content),
        "sha256": delivery.digest(content),
        "source_locator": "sh-source:observation-01",
        "source_sha256": delivery.digest(content),
        "event_at": "2027-02-01T00:00:00Z",
        "available_at": "2027-02-01T00:00:00Z",
        "classification": "original",
        "derives_from": [],
        "supersedes": [],
    }
    package = {
        "edition": "test-v1",
        "company": "Synthetic Company",
        "boundary": "local",
        "period_start": "2027-01-01",
        "period_end": "2027-03-31",
        "cutoff": "2028-01-10T00:00:00Z",
        "generated_at": "2026-10-12T00:00:00Z",
    }
    config = {
        "schema": delivery.SCHEMA,
        "deny_tokens": ["private-example"],
        "stages": {
            "initial": {"package": package, "artifacts": [spec]},
            "later": {
                "package": {**package, "edition": "test-v2"},
                "artifacts": [{**spec, "version": 2}],
            },
        },
    }
    descriptor = tmp_path / "edition.json"
    descriptor.write_bytes(delivery.encode(config))
    return descriptor, inputs, config


def test_repeatable_isolated_consumer_and_stage(tmp_path):
    descriptor, inputs, _ = edition(tmp_path)
    first, second = tmp_path / "consumer1", tmp_path / "consumer2"
    delivery.publish(descriptor, inputs, "initial", first)
    delivery.publish(descriptor, inputs, "initial", second)
    assert delivery.verify(first) == delivery.verify(second)
    assert {
        p.relative_to(first).as_posix(): p.read_bytes() for p in first.rglob("*") if p.is_file()
    } == {
        p.relative_to(second).as_posix(): p.read_bytes() for p in second.rglob("*") if p.is_file()
    }
    assert len(delivery.verify(first)["artifacts"]) == 1
    assert '"version": 2' not in (first / "manifest.json").read_text()
    with pytest.raises(ValueError, match="New destination"):
        delivery.publish(descriptor, inputs, "initial", first)
    with pytest.raises(ValueError, match="Stage unavailable"):
        delivery.publish(descriptor, inputs, "unknown", tmp_path / "absent")
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize(
    "mutation",
    ["escape", "absolute", "alias", "changed", "denied", "future", "duplicate", "private", "extra"],
)
def test_fail_closed_before_publication(tmp_path, mutation):
    descriptor, inputs, config = edition(tmp_path)
    spec = config["stages"]["initial"]["artifacts"][0]
    if mutation == "escape":
        spec["path"] = "../outside.json"
    elif mutation == "absolute":
        spec["input_path"] = "/etc/passwd"
    elif mutation == "alias":
        (inputs / "link.json").symlink_to(inputs / "record.json")
        spec["input_path"] = "link.json"
    elif mutation == "changed":
        (inputs / "record.json").write_text("altered")
    elif mutation == "denied":
        spec["allowed"] = False
    elif mutation == "future":
        spec["available_at"] = "2029-01-01T00:00:00Z"
    elif mutation == "duplicate":
        config["stages"]["initial"]["artifacts"].append(copy.deepcopy(spec))
    elif mutation == "private":
        data = b'{"note":"private-example"}'
        (inputs / "record.json").write_bytes(data)
        spec.update(
            bytes=len(data), sha256=delivery.digest(data), source_sha256=delivery.digest(data)
        )
    elif mutation == "extra":
        spec["instructor_key"] = "withheld"
    descriptor.write_bytes(delivery.encode(config))
    destination = tmp_path / "release"
    with pytest.raises(ValueError):
        delivery.publish(descriptor, inputs, "initial", destination)
    assert not destination.exists()


def test_interrupted_publication_is_not_complete(tmp_path, monkeypatch):
    descriptor, inputs, _ = edition(tmp_path)
    original = delivery.verify

    def interrupted(root):
        original(root)
        raise InterruptedError("interrupted before publication")

    monkeypatch.setattr(delivery, "verify", interrupted)
    with pytest.raises(InterruptedError):
        delivery.publish(descriptor, inputs, "initial", tmp_path / "release")
    assert not (tmp_path / "release").exists()
    assert not list(tmp_path.glob(".pending-*"))


def test_reader_rejects_tamper_unexpected_and_alias(tmp_path):
    descriptor, inputs, _ = edition(tmp_path)
    root = tmp_path / "release"
    delivery.publish(descriptor, inputs, "initial", root)
    rogue = root / "later.json"
    rogue.write_text("future")
    with pytest.raises(ValueError, match="Unexpected"):
        delivery.verify(root)
    rogue.unlink()
    target = root / "records/observation.json"
    original = target.read_bytes()
    target.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash/size"):
        delivery.verify(root)
    target.unlink()
    target.symlink_to(inputs / "record.json")
    with pytest.raises(ValueError, match="alias"):
        delivery.verify(root)
    target.unlink()
    target.write_bytes(original)
    assert delivery.verify(root)


def test_reject_duplicate_json_and_unlabeled_derivative(tmp_path):
    descriptor, inputs, config = edition(tmp_path)
    descriptor.write_text('{"schema":"a","schema":"b"}')
    with pytest.raises(ValueError, match="Duplicate JSON"):
        delivery.publish(descriptor, inputs, "initial", tmp_path / "release")
    config["stages"]["initial"]["artifacts"][0]["classification"] = "derivative"
    descriptor.write_bytes(delivery.encode(config))
    with pytest.raises(ValueError, match="source relationship"):
        delivery.publish(descriptor, inputs, "initial", tmp_path / "release")


def test_population_join_distinguishes_denominators():
    population = {
        "members": [
            {
                "subject_id": "S1",
                "relationship_kind": "CONTRACTOR",
                "accounts": [
                    {
                        "state": {
                            "account_id": "S1:application",
                            "subject_id": "S1",
                            "rights": ["read", "write"],
                        }
                    },
                    {
                        "state": {
                            "account_id": "S1:directory",
                            "subject_id": "S1",
                            "rights": ["read"],
                        }
                    },
                ],
            }
        ]
    }
    rows = delivery.flatten_population(population)
    assert len(rows) == 2
    assert sum(len(r["rights"]) for r in rows) == 3
    broken = copy.deepcopy(population)
    broken["members"][0]["accounts"][1]["state"]["account_id"] = "S1:application"
    with pytest.raises(ValueError, match="Duplicate account"):
        delivery.flatten_population(broken)
    broken = copy.deepcopy(population)
    broken["members"][0]["accounts"][1]["state"]["subject_id"] = "S2"
    with pytest.raises(ValueError, match="mismatched join"):
        delivery.flatten_population(broken)


def test_configuration_comparison_preserves_prior_condition():
    baseline = {"timeout_ms": 40, "attempts": 3, "max_total_ms": 120}
    prior = {**baseline, "timeout_ms": 30}
    assert delivery.configuration_differences(baseline, prior) == [
        {"field": "timeout_ms", "approved": 40, "observed": 30}
    ]
    assert prior["timeout_ms"] * prior["attempts"] == 90
    assert delivery.configuration_differences(baseline, baseline) == []
    assert prior["timeout_ms"] == 30


@pytest.mark.parametrize("kind", ["", "RSA ", "EC "])
def test_private_key_detection_without_tracked_secret_marker(kind):
    marker = "BEGIN " + kind + "PRIVATE " + "KEY"
    with pytest.raises(ValueError, match="private key"):
        delivery.safe_text(marker.encode())


def test_concurrent_empty_destination_is_not_overwritten(tmp_path, monkeypatch):
    descriptor, inputs, _ = edition(tmp_path)
    original = delivery.rename_new
    destination = tmp_path / "release"

    def collision(source, target):
        target.mkdir()
        original(source, target)

    monkeypatch.setattr(delivery, "rename_new", collision)
    with pytest.raises(FileExistsError):
        delivery.publish(descriptor, inputs, "initial", destination)
    assert destination.is_dir()
    assert not list(destination.iterdir())
    assert not list(tmp_path.glob(".pending-*"))


def test_missing_input_does_not_publish(tmp_path):
    descriptor, inputs, _ = edition(tmp_path)
    (inputs / "record.json").unlink()
    with pytest.raises(ValueError, match="missing"):
        delivery.publish(descriptor, inputs, "initial", tmp_path / "release")
    assert not (tmp_path / "release").exists()


@pytest.mark.parametrize(
    "content",
    [
        b'{"password":"unwanted-value"}',
        ("github_" + "pat_" + "x" * 30).encode(),
        ("sk-" + "proj-" + "x" * 30).encode(),
    ],
)
def test_credential_patterns_cover_json_and_current_prefixes(content):
    with pytest.raises(ValueError, match="credential"):
        delivery.safe_text(content)


def test_error_after_rename_preserves_complete_destination(tmp_path, monkeypatch):
    descriptor, inputs, _ = edition(tmp_path)
    original = delivery.os.fsync

    def interrupted(fd):
        if delivery.os.fstat(fd).st_ino == tmp_path.stat().st_ino:
            raise InterruptedError("parent directory durability interrupted")
        original(fd)

    monkeypatch.setattr(delivery.os, "fsync", interrupted)
    destination = tmp_path / "release"
    with pytest.raises(InterruptedError, match="durability"):
        delivery.publish(descriptor, inputs, "initial", destination)
    assert delivery.verify(destination)
    assert not list(tmp_path.glob(".pending-*"))


@pytest.mark.parametrize(
    "media_type",
    [
        "application/json; charset=utf-8",
        "Application/JSON",
        "Text/Plain; charset=utf-8",
        "application/vnd.company+json",
    ],
)
@pytest.mark.parametrize(
    "content", [b'{"route":"/home/private"}', b'{"password":"unwanted-value"}']
)
def test_normalized_text_media_scans_publisher_and_reader(tmp_path, media_type, content):
    descriptor, inputs, config = edition(tmp_path)
    spec = config["stages"]["initial"]["artifacts"][0]
    spec["media_type"] = media_type
    descriptor.write_bytes(delivery.encode(config))
    release = tmp_path / "release"
    delivery.publish(descriptor, inputs, "initial", release)
    (inputs / "record.json").write_bytes(content)
    spec.update(
        bytes=len(content), sha256=delivery.digest(content), source_sha256=delivery.digest(content)
    )
    descriptor.write_bytes(delivery.encode(config))
    with pytest.raises(ValueError, match="release"):
        delivery.publish(descriptor, inputs, "initial", tmp_path / "denied")
    assert not (tmp_path / "denied").exists()
    assert not list(tmp_path.glob(".pending-*"))
    manifest = delivery.read_json(release / "manifest.json")
    manifest["artifacts"][0].update({k: spec[k] for k in delivery.ARTIFACT_FIELDS})
    (release / "records/observation.json").write_bytes(content)
    (release / "manifest.json").write_bytes(delivery.encode(manifest))
    with pytest.raises(ValueError, match="release"):
        delivery.verify(release)


def test_reader_rejects_external_manifest_hard_link(tmp_path):
    descriptor, inputs, _ = edition(tmp_path)
    release = tmp_path / "release"
    delivery.publish(descriptor, inputs, "initial", release)
    os.link(release / "manifest.json", tmp_path / "external-manifest.json")
    with pytest.raises(ValueError, match="unaliased manifest"):
        delivery.verify(release)


@pytest.mark.parametrize("relationship", ["derives_from", "supersedes"])
@pytest.mark.parametrize("identity", ["", "bad/id", None, [], {}])
def test_relationship_requires_resolvable_artifact_identity(tmp_path, relationship, identity):
    descriptor, inputs, config = edition(tmp_path)
    release = tmp_path / "release"
    delivery.publish(descriptor, inputs, "initial", release)
    spec = config["stages"]["initial"]["artifacts"][0]
    spec[relationship] = [{"artifact_id": identity, "version": 1, "sha256": spec["sha256"]}]
    descriptor.write_bytes(delivery.encode(config))
    with pytest.raises(ValueError, match="relationship"):
        delivery.publish(descriptor, inputs, "initial", tmp_path / "denied")
    manifest = delivery.read_json(release / "manifest.json")
    manifest["artifacts"][0][relationship] = spec[relationship]
    (release / "manifest.json").write_bytes(delivery.encode(manifest))
    with pytest.raises(ValueError, match="relationship"):
        delivery.verify(release)


@pytest.mark.parametrize("event", ["", False, 0, [], {}])
def test_unknown_event_requires_explicit_null(tmp_path, event):
    descriptor, inputs, config = edition(tmp_path)
    spec = config["stages"]["initial"]["artifacts"][0]
    spec["event_at"] = event
    descriptor.write_bytes(delivery.encode(config))
    with pytest.raises(ValueError, match="Timestamp"):
        delivery.publish(descriptor, inputs, "initial", tmp_path / "denied")
    spec["event_at"] = None
    descriptor.write_bytes(delivery.encode(config))
    assert delivery.publish(descriptor, inputs, "initial", tmp_path / "accepted")


def test_configuration_distinguishes_absent_and_null():
    assert delivery.configuration_differences({"optional": None}, {}) == [
        {
            "field": "optional",
            "approved": None,
            "observed": None,
            "approved_present": True,
            "observed_present": False,
        }
    ]
    assert delivery.configuration_differences({}, {"optional": None}) == [
        {
            "field": "optional",
            "approved": None,
            "observed": None,
            "approved_present": False,
            "observed_present": True,
        }
    ]
    assert delivery.configuration_differences({"optional": None}, {"optional": None}) == []


def test_media_is_copied_and_hashed_without_whole_file_reads(tmp_path, monkeypatch):
    descriptor, inputs, config = edition(tmp_path)
    content = b"synthetic media " * 200000
    (inputs / "clip.mp4").write_bytes(content)
    spec = config["stages"]["initial"]["artifacts"][0]
    spec.update(
        input_path="clip.mp4",
        path="walkthrough/clip.mp4",
        media_type="video/mp4",
        bytes=len(content),
        sha256=delivery.digest(content),
        source_sha256=delivery.digest(content),
    )
    descriptor.write_bytes(delivery.encode(config))
    original = Path.read_bytes

    def reject_media_read(path):
        if path.suffix == ".mp4":
            raise AssertionError("Media must be streamed")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", reject_media_read)
    release = tmp_path / "release"
    delivery.publish(descriptor, inputs, "initial", release)
    assert delivery.verify(release)["artifacts"][0]["sha256"] == delivery.digest(content)
    assert delivery.file_digest(release / "walkthrough/clip.mp4") == (
        delivery.digest(content),
        len(content),
    )


@pytest.mark.parametrize("side", ["input", "destination"])
def test_normalized_roots_preserve_source_isolation(tmp_path, side):
    descriptor, inputs, _ = edition(tmp_path)
    (tmp_path / "intermediate").mkdir()
    destination = inputs / "release"
    if side == "input":
        inputs = tmp_path / "intermediate/../inputs"
    else:
        destination = tmp_path / "intermediate/../inputs/release"
    with pytest.raises(ValueError, match="outside input root"):
        delivery.publish(descriptor, inputs, "initial", destination)
    assert not (tmp_path / "inputs/release").exists()


@pytest.mark.parametrize(
    "path", ["RECORDS/OBSERVATION.JSON", "Records/other.json", "Manifest.JSON"]
)
def test_case_insensitive_paths_cannot_collide(tmp_path, path):
    descriptor, inputs, config = edition(tmp_path)
    spec = copy.deepcopy(config["stages"]["initial"]["artifacts"][0])
    spec.update(artifact_id="OTHER", path=path)
    config["stages"]["initial"]["artifacts"].append(spec)
    descriptor.write_bytes(delivery.encode(config))
    with pytest.raises(ValueError, match="[Cc]ollision|Duplicate"):
        delivery.publish(descriptor, inputs, "initial", tmp_path / "release")
    assert not (tmp_path / "release").exists()


@pytest.mark.parametrize("rights", ["read", {"read": True}, None, [["read"]]])
def test_population_requires_entitlement_list(rights):
    population = {
        "members": [
            {
                "subject_id": "S1",
                "relationship_kind": "EMPLOYEE",
                "accounts": [{"state": {"account_id": "A1", "subject_id": "S1", "rights": rights}}],
            }
        ]
    }
    with pytest.raises(ValueError, match="Entitlement list"):
        delivery.flatten_population(population)
