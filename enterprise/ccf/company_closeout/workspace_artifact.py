"""Bounded non-authoritative workspace excerpts; no model, institutional write or promotion."""
import json
import os
import stat
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from .information_policy import decide

MARKING = 'SYNTHETIC_NON_AUTHORITATIVE_WORKSPACE_ARTIFACT'
NOTICE = 'Working excerpt only. Not an institutional judgment, approved policy, or promoted source.'
MAX_SOURCE = 65536


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compose(records, source_id, subject, now, *, source_bytes, source_path, action='export'):
    """Trusted authenticated context required. Caller-supplied source prose is never an instruction."""
    require(action in {'export', 'memory'}, 'Institutional write or promotion forbidden')
    require(decide(records, source_id, subject, action, now) == 'ALLOW', 'Not authorized')
    row = records[source_id]
    require(isinstance(source_bytes, bytes) and 0 < len(source_bytes) <= MAX_SOURCE, 'Bounded source bytes required')
    require(sha256(source_bytes).hexdigest() == row['source_sha256'], 'Source bytes differ')
    require(isinstance(source_path, str) and source_path and not Path(source_path).is_absolute()
            and '..' not in Path(source_path).parts, 'Repository-relative source path required')
    excerpt = source_bytes.decode('utf-8')[:2000]
    # Every route emits the same non-removable wrapper; no raw/plaintext export option.
    return {
        'format': 'SH-WORKSPACE-ARTIFACT-1', 'marking': MARKING, 'notice': NOTICE,
        'institutional_authority': False, 'promotion_allowed': False,
        'artifact_kind': 'DETERMINISTIC_SOURCE_EXCERPT_NOT_MODEL_OUTPUT',
        'owner_id': subject['id'], 'tenant': subject['tenant'], 'purpose': subject['purpose'],
        'effective_at': now, 'observed_at': datetime.now(UTC).isoformat(),
        'source': {'record_id': source_id, 'repository_path': source_path,
                   'version': row['source_version'], 'sha256': row['source_sha256'],
                   'available_at': row['available_at'], 'effective_at': row['effective_at']},
        'excerpt': excerpt, 'excerpt_sha256': sha256(excerpt.encode()).hexdigest(),
        'transformation': 'First 2000 Unicode characters of the exact UTF-8 source; no summarization or inference',
        'access': 'Owner-specific working copy; every mediated read/export rechecks current source permissions',
        'canonical_source_modified': False, 'model_invoked': False,
    }


def publish(path, artifact):
    """Actually write a new private artifact. Destination is a trusted operator workspace."""
    _marking(artifact)
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Aliased workspace')
    require(path.parent.is_dir() and not path.parent.stat().st_mode & 0o077, 'Private workspace required')
    raw = json.dumps(artifact, indent=2, ensure_ascii=False, allow_nan=False).encode() + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    return {'artifact_sha256': sha256(raw).hexdigest(), 'bytes': len(raw), 'marking': MARKING,
            'canonical_source_modified': False, 'model_invoked': False}


def _marking(artifact):
    require(artifact.get('format') == 'SH-WORKSPACE-ARTIFACT-1' and artifact.get('marking') == MARKING
            and artifact.get('notice') == NOTICE and artifact.get('institutional_authority') is False
            and artifact.get('promotion_allowed') is False and artifact.get('canonical_source_modified') is False
            and artifact.get('model_invoked') is False, 'Required non-authoritative marking')


def read(path, records, subject, now, *, expected_sha256, action='read'):
    """Rechecks source entitlement and personal ownership before any artifact enters context."""
    require(action in {'read', 'export', 'memory'}, 'No institutional write or promotion')
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Aliased artifact')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        state = os.fstat(fd)
        require(stat.S_ISREG(state.st_mode) and state.st_nlink == 1 and state.st_uid == os.getuid()
                and not state.st_mode & 0o077 and state.st_size <= MAX_SOURCE, 'Private bounded artifact required')
        raw = os.read(fd, MAX_SOURCE + 1)
        require(len(raw) == state.st_size and os.fstat(fd).st_ctime_ns == state.st_ctime_ns, 'Artifact changed')
    finally:
        os.close(fd)
    require(sha256(raw).hexdigest() == expected_sha256, 'Artifact integrity')
    artifact = json.loads(raw)
    _marking(artifact)
    require(artifact['owner_id'] == subject.get('id') and artifact['tenant'] == subject.get('tenant')
            and artifact['purpose'] == subject.get('purpose'), 'Personal workspace isolation')
    source_id = artifact['source']['record_id']
    require(decide(records, source_id, subject, action, now) == 'ALLOW', 'Current source access denied')
    source = records[source_id]
    require(artifact['source']['version'] == source['source_version']
            and artifact['source']['sha256'] == source['source_sha256'], 'Stale source derivative')
    require(sha256(artifact['excerpt'].encode()).hexdigest() == artifact['excerpt_sha256'], 'Excerpt integrity')
    return artifact
