"""Portable publication boundaries and independent source calculations."""

import copy

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
