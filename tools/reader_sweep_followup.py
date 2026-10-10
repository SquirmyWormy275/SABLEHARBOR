"""Apply the final reviewed reader corrections; remove before integration."""
from pathlib import Path

changed = set()
def put(name, text):
    path = Path(name)
    text = text.strip() + '\n'
    if path.read_text() != text:
        path.write_text(text)
        changed.add(name)

def sub(name, old, new):
    text = Path(name).read_text()
    assert text.count(old) == 1, (name, old)
    put(name, text.replace(old, new))

put('docs/j2/README.md', '''# J2 — Judgment & Junction

J2 helps Sable Harbor understand what is happening, investigate difficult questions and learn from its work. Contact gathers evidence, Judgment investigates, Orientation briefs leaders, the Junction Advisory Group works alongside operating teams, and Education helps people develop their skills. It is not a legal entity or customer-facing business line.

## Current leadership

Meet the ten people covered by the current leadership records. Joining years describe when they joined Sable Harbor, not when they took up their present offices.

| Person | Role | Joined Sable Harbor |
|---|---|---:|
| Jonathan Goldstryker | Head of J2 | 2020 |
| Amanda Chenahot | Deputy Head of J2 | 2021 |
| Miriam Solano | Chief of Staff | 2019 |
| Mara Hammer | Head of Contact | 2021 |
| Owen Faraday | Deputy Head of Contact | 2020 |
| Anika Trish | Head of Judgment | 2021 |
| Nadia Ivers | Deputy Head of Judgment | 2021 |
| Grant Kohrs | Head of Orientation | 2020 |
| Leila Soren | Deputy Head of Orientation | 2019 |
| Brett Calder | Head of Education | 2021 |

The [personnel profiles](../../enterprise/operations/source/j2_personnel_completion_2026_09_22.json) describe their professional experience and internal reviews. The [company edition guide](../internal/company-closeout/INSPECTION_GUIDE_v1.2.0.md) explains how to inspect the personnel and appointment records together.

The [September 10 people chart](../organization/charts/people-j2.md) and [roster](../structured/j2_leadership_2026-09-10.json) preserve the earlier six-person edition. The four additional names above identify people already in their posts; they do not represent new hires or additional positions.

<a id="controlled-package"></a>

## Explore J2

| Your question | Start here |
|---|---|
| How does J2 work, and what authority does it have? | The [charter](J2_CHARTER.md), [headquarters guide](J2_HEADQUARTERS.md) and [operating model](J2_OPERATING_MODEL.md). |
| How is evidence gathered and investigated? | [Contact](CONTACT.md), [collection management](CONTACT_COLLECTION_MANAGEMENT.md), [Judgment](JUDGMENT.md) and the [Judgment Officer profession](JUDGMENT_OFFICER_PROFESSION.md). |
| How do people make sense of a problem and act on it? | [Orientation](ORIENTATION.md), the [Orientation Officer profession](ORIENTATION_OFFICER_PROFESSION.md), [JAG](JUNCTION_ADVISORY_GROUP.md) and [Education](EDUCATION.md). |
| How do questions and information move through the company? | [EIB and edge reporting](EIB_AND_ENTERPRISE_QUESTIONS.md), [information access](INFORMATION_ACCESS_DOCTRINE.md) and [Alexandria](alexandria/README.md). |
| Where are the formatted documents? | The [publication library](publications/). |

<details>
<summary>Supporting records and decision history</summary>

The [September 10 leadership record](../canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) established the original six names. The [September 22 personnel record](../canon/J2_PERSONNEL_COMPLETION_2026-09-22.md), accepted with company edition 1.2.0, supplies the four remaining names and ten professional profiles. Earlier statements that those names or the current appointment histories are unresolved describe the period before that completion. Exact hire days and a biography for every staff position are not part of this record.

For the broader design, see [corporate history](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.1.md), [governance](../governance/), the [source coverage review](../internal/COVERAGE_AUDIT_PHASE2.md), the [Pinakes register](structured/pinakes_portals.json) and [Daedalus policy](structured/daedalus_policy.json). Original J2 artwork remains in the [brand library](../../assets/brand/).

</details>
''')

sub('docs/wiki/departments/j2-headquarters.md',
    'The establishment provides 28 headquarters billets. The roster identifies recorded occupants; appointment histories are available through the dated personnel and leadership records.',
    'Jonathan Goldstryker leads J2, Amanda Chenahot is Deputy Head, and Miriam Solano is Chief of Staff. Miriam joined Sable Harbor in 2019. The headquarters establishment provides 28 billets; the [leadership guide](../../j2/README.md#current-leadership) introduces the current leaders and links their professional profiles and appointment records.')
sub('docs/wiki/departments/j2-headquarters.md',
    '- [Controlled headquarters publication]',
    '- [Personnel profiles](../../../docs/canon/J2_PERSONNEL_COMPLETION_2026-09-22.md) — The completed ten-person leadership record, including the Chief of Staff and three deputies.\n- [Headquarters publication]')
sub('docs/wiki/departments/j2-headquarters.md', '**Reviewed:** October 7, 2026.', '**Reviewed:** October 9, 2026.')
sub('docs/wiki/departments/j2.md',
    'The establishment contains 237 billets. The [people charts](../../organization/charts/people-j2.md) show recorded leaders and roles; the [Alexandria guide](alexandria.md) explains the records environment used to connect evidence and decisions.',
    'The establishment contains 237 billets. Meet the ten people in the [current leadership guide](../../j2/README.md#current-leadership), then explore the arms below. The [Alexandria guide](alexandria.md) explains how people find records and connect what the company has learned.')
sub('docs/wiki/departments/j2.md',
    '- [Approved leadership](../../../docs/canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) — Six current leaders and company joining years.',
    '- [Current personnel profiles](../../../docs/canon/J2_PERSONNEL_COMPLETION_2026-09-22.md) — Ten leaders, their joining years, professional histories and internal reviews.\n- [September 10 leadership record](../../../docs/canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) — The earlier six-person edition.')
sub('docs/wiki/departments/j2.md',
    '- [Current leadership chart](../../../docs/organization/charts/people-j2.md) — Approved leader cards.',
    '- [Leadership chart](../../../docs/organization/charts/people-j2.md) — The preserved September 10 cards; use the current personnel guide for all ten profiles.')
sub('docs/wiki/departments/j2.md', '**Reviewed:** October 7, 2026.', '**Reviewed:** October 9, 2026.')
sub('docs/wiki/subjects/People.md',
    '| Who are the six J2 leaders? | [J2 people chart](../../organization/charts/people-j2.md), [dated appointments](../../canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) |',
    '| Who are the ten people in the current J2 leadership record? | [Current leadership and profiles](../../j2/README.md#current-leadership). The [people chart](../../organization/charts/people-j2.md) and [September 10 record](../../canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) preserve the earlier six-person edition. |')

p = 'docs/advisory/README.md'
s = Path(p).read_text()
start = s.index('**Status:**')
end = s.index('## Integrated firm manual')
meta = s[start:s.index('\n\nSable Harbor Advisory')]
s = s[:start] + '''Sable Harbor Advisory helps clients investigate business problems, build intelligence teams and improve operations. Its three practices draw on the same group of professionals: the question determines who joins the team.

Atlas Meridian provides the software for investigations, client work and relationships. Advisory serves external clients; J2 serves Sable Harbor internally. The two remain institutionally separate, and Advisory may not solicit serving J2 personnel.

''' + s[end:]
s = s.replace('The consolidated executive operating artifact is [`SABLE_HARBOR_ADVISORY_FIRM_MANUAL_2026-09-09.md`](SABLE_HARBOR_ADVISORY_FIRM_MANUAL_2026-09-09.md). Detailed controlled standards below govern where more specific.', 'Start with the [firm manual](SABLE_HARBOR_ADVISORY_FIRM_MANUAL_2026-09-09.md) for an overview of the business. The standards below explain particular responsibilities and procedures in more detail.')
s = s.replace('## Controlled operating documents', '<a id="controlled-operating-documents"></a>\n\n## How the practice works')
s = s.replace('## Controlled templates', '<a id="controlled-templates"></a>\n\n## Templates for client work')
for code, name in [('001', 'Matter acceptance form'), ('002', 'Matter charter'), ('003', 'Outcome schedule'), ('004', 'Transfer certificate'), ('005', 'Independent review memorandum'), ('006', 'Client proposal')]:
    old = '[`SH-ADV-TPL-' + code + '`]'
    assert old in s
    s = s.replace(old, '[' + name + ']')
s = s.replace('## Controlling principles', '<details>\n<summary>Professional principles</summary>\n\n## Controlling principles')
s = s.replace('## Current implementation state', '</details>\n\n## Current implementation state')
s = s.replace('The operating/business-line name **Sable Harbor Advisory** is the accepted institutional name. Advisory remains a business line of the existing controlling Sable Harbor contracting entity unless a later approved transaction creates a separate entity. The individual President is an appointment decision, not an unresolved operating-model dependency.', 'Sable Harbor Advisory operates as a business line of the existing Sable Harbor contracting entity, not a separately incorporated firm. The [business guide](../wiki/businesses/Advisory.md) connects its people, accounts and legal records.')
s = s.replace('Qualified counsel, tax, insurance, privacy, security and trademark work are execution requirements before real external commercialization; the repository does not pretend those professional sign-offs have occurred merely because the operating design is complete.', 'This is a fictional operating design. Real external commercialization would require the relevant legal, tax, insurance, privacy, security and trademark work; the design is not evidence that those professional sign-offs have occurred.')
s += '\n<details>\n<summary>Design records and earlier editions</summary>\n\n' + meta + '\n\nThese records preserve the choices behind the operating design. [Records and decisions](../wiki/Records-and-Decisions.md) connects them to the wider company history.\n\n</details>\n'
put(p,s)

put('docs/j2/alexandria/README.md', '''# Alexandria Foundation

Alexandria helps people find what Sable Harbor knows, see where it came from and understand how it changed. Its promise is simple: **Sable Harbor does not lose what it learns.** It is an internal environment for records and institutional knowledge, not a customer-facing business.

## Find your way around

| What would you like to understand? | Start here |
|---|---|
| How records connect across the company | The [charter](ALEXANDRIA_CHARTER.md) and [institutional memory guide](INSTITUTIONAL_MEMORY_AND_CONNECTION.md). |
| How people find and use information | [Pinakes](PINAKES_PORTAL_AND_UX.md), the human portal and catalog, and [information access and disclosure](INFORMATION_ACCESS_AND_DISCLOSURE.md). |
| How questions, messages and knowledge move | The [Semaphore traffic system](SEMAPHORE_TRAFFIC_SYSTEM.md) and [Canon institutional knowledge](CANON_INSTITUTIONAL_KNOWLEDGE.md). |
| What people knew at a particular time | [Search and historical reconstruction](SEARCH_AND_HISTORICAL_RECONSTRUCTION.md), [branching history](VISUALIZATION_AND_BRANCHING_HISTORY.md), [temporal integrity](TEMPORAL_INTEGRITY.md) and [source history](PROVENANCE_AND_LINEAGE.md). |
| What an AI assistant may do | [Daedalus](DAEDALUS_OPERATING_DOCTRINE.md), [human authorship and AI authority](AI_AUTHORITY_AND_HUMAN_AUTHORSHIP.md), and the [personal workspace](DAEDALUS_PERSONAL_INSTANCE_AND_WORKSPACE.md). |

Pinakes is the catalog. Daedalus accompanies the user: it is not a portal and cannot alter the authoritative environment. Original records and their history remain available when someone needs to check an answer.

## Query the records

The generated [institutional catalog](../../internal/institutional_catalog.json) and [SQLite database](../../internal/institutional_catalog.sqlite3) make the documented objects and relationships searchable. Follow the [query guide](../../internal/INSTITUTIONAL_CATALOG_QUERY_GUIDE.md) to use them. They are indexes of the source Markdown, not a separate authority for company facts.

[Alexandria company guide](../../wiki/departments/alexandria.md) · [J2](../README.md) · [Records and decisions](../../wiki/Records-and-Decisions.md)
''')

p = 'docs/governance/board-records/README.md'
s = Path(p).read_text()
start = s.index('**Record class:**')
end = s.index('## Records')
meta = s[start:s.index('\n\nThis directory')]
s = s[:start] + '''These minutes and written consents trace Sable Harbor's financing, Board appointments and governance from 2021 to 2026. Start with the event that interests you, then follow its exhibits for the documents considered by the Board.

The records are part of the fictional company's history. Their dates matter: a later committee structure or responsibility should not be read back into an earlier year.

''' + s[end:]
s = s.replace('and controlled-document package now represented in PR #16.', 'and the accompanying company documents.')
s = s.replace('They index approved artifacts without adding doctrine.', 'They list the documents covered by the consent.')
s = s.replace('## Structured record\n\nThe machine-readable register is [`../structured/board_approval_records.json`](../structured/board_approval_records.json).', '## Structured record\n\nThe [Board record register](../structured/board_approval_records.json) provides the same record identities and dates for queries and data work.')
s = s.replace('## Guardrails', '<details>\n<summary>Scope and design history</summary>\n\n' + meta + '\n\n## Guardrails')
s += '''

These records ratify and sequence the decisions used to build this part of the company history; they do not create new governance powers. The [records guide](../../wiki/Records-and-Decisions.md) brings the broader approval and supersession history together.

</details>
'''
put(p,s)
assert len(changed) == 7, changed
print('\n'.join(sorted(changed)))
