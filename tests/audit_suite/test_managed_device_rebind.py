"""A signed reboot rebind preserves every historical identity except st_dev."""

import copy

import pytest

from enterprise.audit_suite.managed_history_integrity import (
    CHECKPOINT_SCHEMA,
    DEVICE_REBIND_SCHEMA,
    IntegrityCatalogue,
)
from enterprise.audit_suite.store import DomainError, canonical

HASH = "a" * 64


def image(name, device):
    return {
        "path": f"/private/{name}.sqlite3",
        "sha256": HASH,
        "bytes": 100,
        "metadata": {
            "st_dev": device,
            "st_ino": 77 if name == "prefix" else 78,
            "st_mode": 0o100600,
            "st_uid": 1000,
            "st_gid": 1000,
            "st_nlink": 1,
            "st_size": 100,
            "st_mtime_ns": 101,
            "st_ctime_ns": 101,
        },
    }


def test_signed_device_rebind_preserves_history_and_refuses_other_metadata():
    frame = {
        "engagement_id": "ENG",
        "revision": 0,
        "command_id": "CMD",
        "request_sha256": HASH,
        "event_sha256": HASH,
        "previous_event_sha256": "",
        "actor": "operator",
        "recorded_at": 1,
        "command_kind": "start",
        "state_storage": "RAW_CANONICAL_JSON",
        "state_root_sha256": None,
        "state_sha256": HASH,
        "state_bytes": 1,
    }
    base = {
        "engagement_id": "ENG",
        "base_revision": 0,
        "frames": [frame],
        "images": {name: image(name, 58) for name in ("prefix", "tail")},
        "custody": {"files": {}, "custody": {}},
        "known_prefix_sha256": {},
        "node_inventory": {"sha256": HASH, "count": 1, "maximum_rowid": 1},
    }
    catalogue = IntegrityCatalogue(base, HASH)

    def signed(body):
        result = copy.deepcopy(body)
        result["signature"] = canonical(body)
        return result

    def verify(body, signature):
        assert canonical(body) == signature

    prior = signed(
        {
            "schema": CHECKPOINT_SCHEMA,
            "sequence": 1,
            "accepted_base_sha256": HASH,
            "previous_checkpoint_sha256": HASH,
            "engagement_id": "ENG",
            "kind": "AUTH_TRANSITION",
            "frames_before": 1,
            "added_frames": [],
            "images": base["images"],
            "custody": base["custody"],
            "authority_head": {"path": "/private/head.json", "sha256": HASH},
            "full_revocations": {},
            "node_inventory": base["node_inventory"],
        }
    )
    catalogue.apply_checkpoint(prior, "b" * 64, verify)
    candidate = {k: copy.deepcopy(v) for k, v in prior.items() if k != "signature"}
    candidate.update(
        schema=DEVICE_REBIND_SCHEMA,
        sequence=2,
        previous_checkpoint_sha256="b" * 64,
        kind="DEVICE_REBIND",
        images={name: image(name, 60) for name in ("prefix", "tail")},
        device_rebind={
            "reason": "POST_REBOOT_LINUX_DEVICE_RENUMBER",
            "boot_id": "12345678-1234-1234-1234-123456789abc",
            "backup_archive_sha256": HASH,
        },
    )
    for field, value in (("st_ino", 79), ("st_ctime_ns", 102)):
        changed = copy.deepcopy(candidate)
        changed["images"]["tail"]["metadata"][field] = value
        with pytest.raises(DomainError):
            catalogue.apply_checkpoint(signed(changed), "c" * 64, verify)
        assert catalogue.sequence == 1
    changed = copy.deepcopy(candidate)
    changed["node_inventory"]["count"] = 2
    with pytest.raises(DomainError):
        catalogue.apply_checkpoint(signed(changed), "c" * 64, verify)
    assert catalogue.sequence == 1
    catalogue.apply_checkpoint(signed(candidate), "c" * 64, verify)
    assert catalogue.sequence == 2
    assert catalogue.frames == [frame]
    assert catalogue.images["prefix"]["metadata"]["st_dev"] == 60
