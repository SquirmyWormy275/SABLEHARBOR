"""Narrow exclusions for explicitly rejected identities in the review register."""
import json

REJECTED = {
    'P057': 'Leah Moravec', 'P058': 'Owen Rourke',
    'P059': 'Dr. Nadia Serrano', 'P060': 'Richard Halden',
}


def current_text(root, rel, text):
    source_path = 'docs/organization/source/chartbook.json'
    review_path = 'docs/organization/UNRESOLVED_AND_EXCLUDED.md'
    if rel not in (source_path, review_path):
        return text
    data = json.loads((root / source_path).read_text())
    displayed = {n['id'] for n in data['nodes']}
    rejected = []
    for row in data['register_only']:
        if row['id'] in REJECTED:
            if (row['name'] != REJECTED[row['id']] or row['id'] in displayed
                    or row['status'] != 'superseded_never_accepted'
                    or row['reason'] != 'excluded_superseded'):
                raise ValueError(f"Rejected identity promoted or altered: {row['id']}")
            rejected.append(row)
    if rel == source_path:
        data['register_only'] = [r for r in data['register_only'] if r not in rejected]
        return json.dumps(data, ensure_ascii=False)
    excluded_lines = {
        '| ' + ' | '.join(str(r[k]) for k in ('id', 'name', 'status', 'reason')) + ' |'
        for r in rejected
    }
    return '\n'.join(line for line in text.splitlines() if line not in excluded_lines)
