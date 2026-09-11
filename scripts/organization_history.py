"""Narrow exclusions for rejected identities in current and verified historical registers."""
import hashlib
import json

REJECTED = {
    'P057': 'Leah Moravec', 'P058': 'Owen Rourke',
    'P059': 'Dr. Nadia Serrano', 'P060': 'Richard Halden',
}
ARCHIVED_SOURCE = 'docs/organization/history/v1.0.0/chartbook.json'
ARCHIVED_SOURCE_SHA256 = '3439249c509ff9c37e4035e88a158b364268fb62be1f9e570649473790f1d77e'


def current_text(root, rel, text):
    source_path = 'docs/organization/source/chartbook.json'
    review_path = 'docs/organization/UNRESOLVED_AND_EXCLUDED.md'
    if rel == ARCHIVED_SOURCE:
        # The exact prior display register is provenance, not a second live
        # personnel source. Only its already-rejected review rows are excluded;
        # all other text is still scanned. No wildcard history exemption exists.
        payload = (root / rel).read_bytes()
        if hashlib.sha256(payload).hexdigest() != ARCHIVED_SOURCE_SHA256:
            raise ValueError(f'Archive checksum drift: {rel}')
        data = json.loads(payload)
    elif rel in (source_path, review_path):
        data = json.loads((root / source_path).read_text())
    else:
        return text
    displayed = {n['id'] for n in data['nodes']}
    rejected = []
    for row in data['register_only']:
        if row['id'] in REJECTED:
            if (row['name'] != REJECTED[row['id']] or row['id'] in displayed
                    or row['status'] != 'superseded_never_accepted'
                    or row['reason'] != 'excluded_superseded'):
                raise ValueError(f"Rejected identity promoted or altered: {row['id']}")
            rejected.append(row)
    if rel in (source_path, ARCHIVED_SOURCE):
        data['register_only'] = [r for r in data['register_only'] if r not in rejected]
        return json.dumps(data, ensure_ascii=False)
    excluded_lines = {
        '| ' + ' | '.join(str(r[k]) for k in ('id', 'name', 'status', 'reason')) + ' |'
        for r in rejected
    }
    return '\n'.join(line for line in text.splitlines() if line not in excluded_lines)
