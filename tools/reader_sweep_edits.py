"""Apply reviewed prose edits to the October 8 reader sources; temporary tool."""
from pathlib import Path
import re

ROOT = Path.cwd()
changed = set()
def put(path, text):
    p = ROOT / path
    text = text.strip() + '\n'
    if p.read_text() != text:
        p.write_text(text)
        changed.add(path)

def sub(path, old, new, count=1):
    p = ROOT / path
    text = p.read_text()
    assert text.count(old) == count, (path, old, text.count(old))
    put(path, text.replace(old, new))

sub('docs/wiki/Start-Here.md', 'practise accounting', 'practice accounting')
sub('docs/wiki/Home.md',
    "Sable Harbor develops industrial software, operates resource businesses, and provides professional services. This Wiki introduces its businesses and corporate functions: who works there, what they do, how the finances work, and where operations take place. Each article explains the subject first. Supporting records are available at the end when you need to inspect them.",
    "Welcome to Sable Harbor. This fictional company develops industrial software, operates resource businesses and provides professional services. Meet its people, explore their workplaces and follow the records behind their work—from a customer invoice to an acquisition or a mine's operating plan.\n\nYou can browse the company out of curiosity or use its records for accounting, audit and business exercises. Start with whatever interests you; you do not need to read the archive in order.")
sub('docs/wiki/Home.md',
    "Choose a business or department below, or open [All files](Files.md) to find a particular document, dataset, map or program. The file directory takes you from this page to any original in three clicks: directory, collection, file. Articles link the documents that explain their work; the [records guide](Records-and-Decisions.md) brings the decision history together.",
    "Choose a business or department below. Each guide introduces its work and points to useful records when you are ready to look closer. Looking for a particular document, dataset, map or program? [All files](Files.md) takes you there in three clicks: directory, collection, original.")
sub('docs/wiki/Home.md',
    "For practical work, try the [acquisition exercise](../reader/exercises/ACQUISITION.md), [invoice exercise](../reader/exercises/INVOICE.md), or [contract review exercise](../reader/exercises/CONTRACTS.md). You can read the instructions in the Wiki and download the linked Excel, PDF, or SQLite files as needed.",
    "For a first exercise, try [tracing an invoice](../reader/exercises/INVOICE.md). It connects contract terms, dated movements and journal entries. The [acquisition](../reader/exercises/ACQUISITION.md) and [contract review](../reader/exercises/CONTRACTS.md) exercises offer other ways in. Read the instructions here and download the linked records as you go.")
sub('docs/wiki/Home.md', 'introduces the delivered audit workspace', 'introduces the audit workspace')
sub('docs/wiki/Home.md', '[Selected V08 visitor map]', '[Sacramento visitor map]')
sub('docs/wiki/Home.md', '## Places, records, and history', '## Places, records, and history\n\nTake a look around the workplaces, follow a transaction or read how the company developed.')
sub('docs/wiki/Home.md', '[Approved identity assets]', '[Logos and brand artwork]')
sub('docs/wiki/Home.md', 'Current logos and the original artwork that must be preserved.', 'The company’s logos and original artwork.')
sub('docs/wiki/Home.md',
    'For terminology, use the [glossary](Glossary.md). For accepted resolutions and further work, see [decisions and remaining work](Open-Questions.md).',
    'Unfamiliar term? Try the [glossary](Glossary.md). The detailed approval history lives in [Records and decisions](Records-and-Decisions.md), with [decisions and remaining work](Open-Questions.md) explaining what has been completed and what comes next. Supporting records stay available without interrupting the company guides.')

put('docs/wiki/businesses/README.md', '''# Current businesses

[Wiki home](../Home.md) · [All files](../Files.md) · [Departments](../departments/README.md)

Sable Harbor's businesses connect software, field work, industrial operations and professional services. Choose one to meet its people and see how its work becomes a product, a customer engagement or an operating record.

| Business | What you can explore |
|---|---|
| [Foundry Field](Foundry-Field.md) | Production tracking, maintenance, reconciliations and the software used to handle operating exceptions. |
| [Atlas Meridian](Atlas-Meridian.md) | Investigations, operating data, evidence review and the management of client work. |
| [Willow](Willow.md) | Industrial prototypes, sensors, software and experimental processes. |
| [Pale Sun and Red Wash](Pale-Sun-Red-Wash.md) | A Wyoming uranium mine, its acquisition, production, processing and transport. |
| [Project Cradle](Cradle.md) | Recovery of rare-earth materials from industrial byproducts and mine water. |
| [American Resource Utility and BS&T](American-Resource-Utility.md) | Rail, truck, terminal and warehouse services for industrial customers. |
| [Sable Harbor Advisory](Advisory.md) | Client investigations, intelligence teams and improvements to business operations. |

Each guide links the relevant accounts, contracts, people and places. For accounting work, use the [legal ownership chart](../../organization/charts/industrial-ownership.md) as well: a business line is not necessarily a separate legal entity.

The [history and external relationships](../subjects/README.md) directory covers earlier programs, host businesses and separate cases. The [department directory](../departments/README.md) introduces the people who support and review current operations.
''')
put('docs/wiki/departments/README.md', '''# Departments, institutions and shared capabilities

[Wiki home](../Home.md) · [All files](../Files.md) · [Audit practice](../Audit.md)

Who can explain the accounts, approve a contract or help a team recover from an interruption? Start with the function that matches your question. Each guide describes its work, responsibilities and useful records.

## Leadership and governance

| Function | Where to begin |
|---|---|
| [Board and committees](board.md) | Company governance and oversight. |
| [Office of the CEO](executive.md) | Executive direction and management responsibilities. |
| [Corporate Secretary](corporate-secretary.md) | Formal company records and governance coordination. |

## Shared services and operating support

| Function | Where to begin |
|---|---|
| [Enterprise Support Services](ess.md) | How shared services are administered across the company. |
| [Finance](finance.md) | Accounts, financial models and reporting responsibilities. |
| [People & Culture](people-culture.md) | People, employment and workforce records. |
| [Enterprise Technology Services](technology.md) | Systems, infrastructure and recovery responsibilities. |
| [Facilities and workplace services](facilities.md) | Offices, operating sites and workplace support. |
| [Enterprise security capability](security.md) | Security responsibilities and their interfaces with other teams. |
| [Procurement and vendor support](procurement.md) | Suppliers, purchasing and third-party relationships. |
| [Safety and environmental governance](safety-environment.md) | Safety, environmental responsibilities and operating constraints. |
| [Quality and technical standards](quality-standards.md) | Quality expectations and technical review. |

## Legal, risk and independent review

| Function | Where to begin |
|---|---|
| [Office of the General Counsel](legal.md) | Legal advice, contracts and professional responsibilities. |
| [Risk & Compliance](risk-compliance.md) | Risk assessment and compliance coordination. |
| [Internal Audit](internal-audit.md) | Independent review and reporting to the Board Audit & Compliance Committee. |

## J2 and institutional knowledge

Start with [J2 — Judgment & Junction](j2.md) for the overall institution, then explore its work through [Headquarters](j2-headquarters.md), [Contact](contact.md), [Judgment](judgment.md), [Orientation](orientation.md), [Education](education.md) and the [Junction Advisory Group](jag.md).

[Alexandria](alexandria.md) explains the institutional environment for records and knowledge.

These groups are reading categories, not reporting lines. The Board governs, the CEO directs and businesses operate. ESS administers shared services without taking over professional officers' substantive authority. Internal Audit reports functionally to the Board Audit & Compliance Committee; J2 remains outside ESS.

[Organization charts](../../organization/README.md) · [ESS and independence](../../governance/ENTERPRISE_SUPPORT_SERVICES_AND_INDEPENDENCE.md) · [Business directory](../businesses/README.md) · [History and related subjects](../subjects/README.md) · [Continuity responsibilities](../subjects/Continuity.md)
''')
put('enterprise/README.md', '''# Enterprise operating and financial models

Explore how Sable Harbor earns money, supports its businesses and checks its work. This part of the archive connects financial models with operations, technology, services and controls.

| What would you like to investigate? | Start here |
|---|---|
| How do the seven businesses work financially? | The [business finance model](business/README.md) combines their economics and produces reconciled evidence packages. Its 2027–2031 figures are conditional forecasts; historical and industrial records keep their original scope. |
| How do transactions and day-to-day operations fit together? | The [operating model](operations/README.md) and its linked workbooks and records. |
| Which services and infrastructure does the company depend on? | The [services guide](services/README.md) covers sourcing, six workload classes, capacity and recovery requirements, and a separate five-year technology comparison. |
| How are hosting, recovery and facilities planned? | The [technology estate](runtime/README.md) brings together the September 11 design, land record, conditional finance and recovery plans. |
| How can I examine a control or follow an exception? | The [common control framework](ccf/README.md) includes finance, identity and recovery exercises, with evidence, original results and follow-up work. |

For a first practical task, use the [audit guide](../docs/wiki/Audit.md) or [finance exercises](../docs/finance/READER_EXERCISES.md). They explain what to open and what to produce before you need the build tools.

Planning is not deployment. A selected supplier, capacity assumption or recovery design does not establish a signed contract or an operating service. The [runtime release record](../docs/releases/RUNTIME_ESTATE_RELEASES.md) explains that edition's scope; earlier business and operations releases remain reproducible from their own sources.

[Company guide](../docs/wiki/Home.md) · [All files](../docs/wiki/Files.md) · [Records and decisions](../docs/wiki/Records-and-Decisions.md)
''')

p = 'geospatial/README.md'
s = (ROOT/p).read_text()
start = s.index('[R02 facility drill-down atlas]')
end = s.index('## Current source authority')
s = s[:start] + '''## Explore the places

Start with the [Sacramento visitor map](facilities/visitor/v08/artifacts/visitor-map-v08.png), browse the [individual maps and floor plans](maps/facilities/ARTIFACT_INDEX.md), or download the [facility atlas PDF](maps/SABLE_HARBOR_Facility_Atlas_v0.2.0.pdf). The [interactive atlas](maps/index.html) runs locally from a downloaded checkout, not inside GitHub.

| Edition | What it contains |
|---|---|
| [Facility atlas v0.2.0 / R02](../docs/releases/FACILITY_ATLAS_RELEASES.md) | Published September 11, 2026. It preserves the approved four-building, ten-floor Sacramento baseline and connects site, building and floor plans with the runtime locations. |
| [Geographic evidence v1.5.0](../docs/releases/GEOGRAPHIC_EVIDENCE_1_5_0_RECEIPT.md) | Published September 29, 2026. The complete declared synthetic geographic edition, including its preserved earlier package and supplement. |
| [Geographic framework v0.1.0-rc4](maps/SABLE_HARBOR_Geographic_Framework_Atlas_v0.1.0-rc4.pdf) | The earlier eleven-sheet context atlas. Its [GeoPackage](master/sable_harbor_master_v0.1.gpkg), [QGIS project](qgis/sable_harbor_master.qgz) and [closeout matrix](docs/PROGRAM_CLOSEOUT_MATRIX.md) retain that edition's dates and limitations. |

A published plan is not a completed building, a survey or a property conveyance. Use the [locations guide](../docs/wiki/Locations.md) to distinguish offices, operating sites, shared accommodation and proposed facilities. The 1898/1954 rail alignments remain unlocated; later illustrative history does not establish their real positions.

<details>
<summary>Atlas inventory and earlier editions</summary>

The original facility subpackage contains 58 sheets across 16 sites. The [runtime bridge](facilities/RUNTIME_BRIDGE.json) reuses twelve existing plates and adds three location packages, one proposed building and one floor. The combined inventory is 19 locations, 18 buildings, 25 floors and 70 facility/runtime plates in 210 SVG/PNG/PDF assets, plus eleven preserved rc4 context records: 81 maps. The [facility release record](../docs/releases/FACILITY_ATLAS_RELEASES.md) provides the checks and publication history.

The rc4 framework was reconciled to September 7 company decisions. Its original open-work statements describe that edition, not the later v1.5.0 delivery. Engineering, survey and real-world rights limitations remain in force.

</details>

''' + s[end:]
put(p,s)
sub(p, 'The enterprise Geo package is a combined view.', 'The geographic package brings several source sets together.')
sub(p, 'Contracts and operation remain unestablished.', 'Those selections alone do not establish signed contracts or operating services.')
sub(p, 'state the actual limits. A valid framework is not a surveyed estate, a completed 50-section program, or a claim of actual land/rail rights.', 'describe the earlier framework’s limits. For the later delivered scope, use the [v1.5.0 receipt](../docs/releases/GEOGRAPHIC_EVIDENCE_1_5_0_RECEIPT.md). Neither edition establishes surveyed boundaries or real land and rail rights.')

p = 'docs/finance/README.md'
s = (ROOT/p).read_text()
start = s.index('The platform is a Python/SQLAlchemy')
s = s[start:]
s = s.replace('It currently implements deterministic identities, explicit canon/model\nstates,', 'It implements deterministic identities, explicit record and model\nstates,')
s = s.replace('The current Alembic target is', 'The v0.1 acceptance target is')
s = s.replace('Read `KNOWN_LIMITATIONS.md` before interpreting any output. Quantitative values and proposed legal\nimplementation details are not locked canon. The relationship shapes Sable Harbor → controlled ARU\n→ wholly owned BS&T and Sable Harbor → dedicated Red Wash operator are locked and are not optional\nentity scenarios.', 'Read [the v0.1 limitations](KNOWN_LIMITATIONS.md) before interpreting this edition. Its generated values and proposed implementation details do not replace later company decisions. For the current industrial legal structure, use the [industrial case](../../industrial/README.md) and its linked legal records rather than treating this earlier snapshot as a current ownership chart.')
put(p, '''# Sable Harbor finance platform

Follow the money from a business question to the workbook and the records behind it. You can use the accounting exercises without running the financial platform.

## Start with a question

| Work | Open first |
|---|---|
| Trace an invoice or investigate a balance | [Finance exercises](READER_EXERCISES.md) and the [invoice exercise](../reader/exercises/INVOICE.md). |
| Inspect supporting accounting records | [Accounting evidence packages](evidence/coverage/README.md), with reconciliations and CSV/SQLite extracts. |
| Compare the seven businesses | The [business finance model](../../enterprise/business/README.md) and [release guide](../releases/BUSINESS_FINANCE_RELEASES.md). Its 2027–2031 figures are conditional forecasts. |
| Work through an industrial acquisition | The [Pale Sun, Red Wash, ARU and BS&T case](../../industrial/README.md) and [finance bridge](INDUSTRIAL_FINANCE_BRIDGE_v1.0.md). |

Keep each exercise's period, scenario and source edition together. The [business model design](BUSINESS_DRIVEN_SUCCESSOR_2026-09-09.md) explains which later assumptions replace the earlier platform forecast and which historical records remain unchanged.

## Reproduce the original v0.1 platform

The instructions below describe the original, reproducible enterprise v0.1 edition—not the whole company's current financial or legal position.

''' + s)

p = 'industrial/README.md'
sub(p, 'Start with the [participant guide](CASE_GUIDE.md), [legal structure](corporate/LEGAL_STRUCTURE_AND_FORMATION.md), and [implementation decisions](IMPLEMENTATION_DECISIONS.md).', 'Follow the [case guide](CASE_GUIDE.md) to explore their work together, or open the [legal structure](corporate/LEGAL_STRUCTURE_AND_FORMATION.md) to understand the companies involved.')
sub(p, '## Build and verify', '''## Explore the case

Start with a practical question: how was an acquisition funded, how does mine production become inventory and sales, or what can the transport business actually carry? The [case guide](CASE_GUIDE.md) points to the transaction, operating and financial records for each part of the story.

The [Red Wash guide](../red_wash/README.md) goes deeper into the mine. The [operations guide](operations/README.md) connects transport, facilities and customer work. Use the [release index](../docs/releases/INDUSTRIAL_CASE_RELEASES.md) for complete downloads.

## Build and verify''')
s = (ROOT/p).read_text()
s += '\nFor model design choices and their rationale, see [implementation decisions](IMPLEMENTATION_DECISIONS.md).\n'
put(p,s)

p = 'red_wash/README.md'
s = (ROOT/p).read_text()
meta_start = s.index('**Record:**')
meta_end = s.index('Red Wash Mining, LLC')
meta = s[meta_start:meta_end].strip()
s = s[:meta_start] + s[meta_end:]
s = s.replace('The controlling industrial structure, acquisitions, integrated financing and Taylor\nservice case are in the [industrial package](../industrial/README.md). This directory\nsupplies its detailed mine, diligence, operating and commercial evidence.', 'Start with the [casebook](RED_WASH_CASEBOOK.md) to explore the mine, then follow its production, processing, contracts and accounts. The [industrial case](../industrial/README.md) connects the acquisition and financing with the Taylor transport service.')
s = s.replace('| Selected transaction and standalone baseline | [Canon 1.1](../docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md) |\n| Reconciled decisions | [Decision addendum 1.1](../docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md) |\n', '')
s += '''
<details>
<summary>Edition details and decision history</summary>

''' + meta + '''

The [transaction and standalone baseline](../docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md) and [decision addendum](../docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md) record the choices behind this edition. [Records and decisions](../docs/wiki/Records-and-Decisions.md) connects them to the wider company history.

</details>
'''
put(p,s)

p = 'docs/business-lines/README.md'
sub(p, 'Seven current operating worlds have one source-linked dossier each. The structured [register](../structured/business-lines/register.json) separates reporting lines from legal entities. A dossier is a current navigation and implementation record; its linked controlling source resolves conflicts.', 'These seven dossiers bring together each business’s work, responsibilities and supporting records. For a first introduction, try the [Wiki business guides](../wiki/businesses/README.md). Use the dossiers when you need to follow the detail.\n\nThe legal-book codes below identify the records used for accounting; they do not turn every business line into a separate company. The [business register](../structured/business-lines/register.json) distinguishes reporting lines from legal entities.')
sub(p, '[executable finance successor]', '[business finance model]')
sub(p, 'under the [unit export contract]', 'using the [unit evidence specification]')

p = 'docs/reader/exercises/README.md'
sub(p, '# Three exercises using the existing records', '# Three exercises using the existing records\n\nNew to the company? Start with the invoice exercise, then try an acquisition or a contract review.')
sub(p, "The linked documents and workbook already exist on accepted main. No exercise requires the new designs held in PR #145 or proposed billing details in PR #138. The Foundry Field packet's [acceptance record](../../finance/evidence/SH-FIN-HUMAN-001/ACCEPTANCE.json) controls its current status even though its frozen PDF retains earlier draft wording.", "The exercises use the linked documents and workbook as supplied; no new design or additional software is required. The Foundry Field packet is accepted for this exercise. Its [edition record](../../finance/evidence/SH-FIN-HUMAN-001/ACCEPTANCE.json) explains why the preserved PDF still carries earlier draft wording.")
sub(p, 'If you want to extend a case, consult', 'To extend a case, consult')

p = 'docs/wiki/README.md'
sub(p, "The [live GitHub Wiki](https://github.com/SquirmyWormy275/SABLEHARBOR/wiki) is published. Its first 56-page edition was accepted in September 2026. [PR #155](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/155) added fuller business, department, and history articles, along with 198 complete supporting records. Earlier reports that the Wiki was unavailable describe the situation before publication.", "Read the [live GitHub Wiki](https://github.com/SquirmyWormy275/SABLEHARBOR/wiki) for the published company guides. Changes are reviewed in this repository before they are published there. The manifest described below lets maintainers check that the two agree.")
sub(p, "Business and department pages introduce their subjects, suggest what to read, and identify unanswered questions. The exporter adds their selected source documents to the in-depth reading sections.", "Business and department pages introduce their subjects and suggest what to explore next. The exporter keeps selected source documents in a closed supporting-records section at the end, so readers can choose when to open the detail.")
s = (ROOT/p).read_text() + '''
<details>
<summary>Earlier Wiki editions</summary>

The first 56-page edition was accepted in September 2026. [PR #155](https://github.com/SquirmyWormy275/SABLEHARBOR/pull/155) added fuller business, department and history articles, along with 198 complete supporting records. Older reports that the Wiki was unavailable describe the period before publication.

</details>
'''
put(p,s)

for p in sorted((ROOT/'docs/wiki/businesses').glob('*.md')):
    if p.name == 'README.md':
        continue
    rel = str(p.relative_to(ROOT))
    s = p.read_text()
    old = '[Wiki home](../Home.md) · [All files](../Files.md) · [Business directory](README.md) · [Department directory](../departments/README.md) · [Business dossiers](../../business-lines/README.md) · [Company charts](../../organization/README.md)'
    assert old in s, rel
    s = s.replace(old, '[Wiki home](../Home.md) · [Businesses](README.md) · [All files](../Files.md)')
    s += '\n[Departments](../departments/README.md) · [Business dossiers](../../business-lines/README.md) · [Company charts](../../organization/README.md)\n'
    s = s.replace('[Current business dossier]', '[Business dossier]').replace('[Letterhead dossier PDF]', '[Dossier PDF]')
    s = s.replace('[finance successor guide]', '[finance model guide]').replace('[Finance successor guide]', '[Finance model guide]')
    s = s.replace('The matching CSV and SQLite extracts provide the same scoped evidence; SQL is optional.', 'The matching CSV and SQLite extracts contain the same records; SQL is optional.')
    s = re.sub(r'alt="Approved ([^"]+) logo"', r'alt="\1 logo"', s)
    s = s.replace('existing organization chart', 'organization chart')
    put(rel,s)

edits = {
 'History.md': [('Read the evidence', 'Read more'), ('reusable Foundry substrate', 'reusable Foundry software'), ('[controlling Klein decision]', '[Klein’s name and history]'), ('[Cradle closeout]', '[Cradle’s development]'), ('[headquarters closeout]', '[Headquarters and management]'), ('[dated canon library]', '[history library]')],
 'Research-History.md': [('The bounded laboratory created', 'The laboratory created'), ('[approved logo]', '[logo]'), ('[approved identity]', '[brand history]'), ('[Willow/Klein closeout]', '[Willow/Klein history]'), ('The closeout supplies the specific 2018 instrumentation incident and the Sar-e-Sang governance history where earlier lore left detail open.', 'The Willow/Klein history describes the 2018 instrumentation incident and the Sar-e-Sang governance history in more detail.'), ('[Existing research-history chart]', '[Research-history chart]')],
 'Project-History.md': [('Controlling reading', 'Read more'), ('[Cradle closeout, section 4]', '[Cradle history, section 4]')],
 'External-Hosts.md': [('Cradle adds bounded recovery to Stream 17.', 'Cradle adds a defined recovery operation to Stream 17.'), ('[Closeout section 3]', '[Stream 17 agreement and history]'), ('[Closeout section 5]', '[Demotte agreement and history]'), ('[approved logo]', '[logo]'), ('[Existing external-host chart]', '[External-host chart]'), ('modelled geometry', 'modeled geometry')],
 'People.md': [('Who are the six approved J2 leaders?', 'Who are the six J2 leaders?'), (' These are the existing approved files.', ''), ('[Original Eight chart and qualifications]', '[Original Eight chart and biographies]')],
 'External-Counterparties.md': [('[approved logo]', '[logo]'), ('[R2 transaction source]', '[Red Wash transaction history]'), ('[Willow/Klein closeout]', '[Willow/Klein history]')],
 'Continuity.md': [('Existing route', 'Start here'), ('[Native CCF procedures]', '[Control-testing procedures]'), ('[accepted assurance workbench scope]', '[Assessment workbench]')],
}
for name, pairs in edits.items():
    p = 'docs/wiki/subjects/' + name
    for old,new in pairs:
        n = (ROOT/p).read_text().count(old)
        assert n > 0, (p,old)
        sub(p,old,new,n)

print('\n'.join(sorted(changed)))
print(f'{len(changed)} files edited')
