#!/usr/bin/env python3
"""Render Sable Harbor's canon-derived organization charts as self-contained SVG."""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
import json

ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT / "docs" / "organization"
ASSETS = ORG / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

SNAPSHOT_DATE = "2026-08-31"
SNAPSHOT_DATE_DISPLAY = "August 31, 2026"
CANON_REVIEW_DATE = "2026-09-05"
CANON_REVIEW_DATE_DISPLAY = "September 5, 2026"
PACKAGE_VERSION = "0.4.0"
INDUSTRIAL_DATE = "2026-09-05"
INDUSTRIAL_PAGES = {"PALE_SUN_RED_WASH_ORGANIZATION.md", "ARU_BST_ORGANIZATION.md"}
CURRENT_CHARTS = {"enterprise-organization-2026.svg", "leadership-authority-2026.svg",
                  "pale-sun-red-wash-organization-2026.svg", "aru-bst-organization-2026.svg"}
ENTITY_SOURCE = json.loads((ROOT / "industrial/source/entities.json").read_text())
ENTITIES = {entity["entity_id"]: entity for entity in ENTITY_SOURCE["entities"]}


def officer(entity_id: str, title: str) -> str:
    return next(person.get("display_name", person["name"])
                for person in ENTITIES[entity_id]["officers"] if person["title"] == title)


C = {
    "bg": "#F4F0E6", "paper": "#FFFFFF", "ink": "#122532", "navy": "#17384A",
    "steel": "#557384", "blue": "#DDE9EE", "orange": "#D76835", "gold": "#C5973E",
    "green": "#4E7762", "red": "#994B48", "gray": "#68757D", "light": "#E7E9E7",
    "open": "#F2ECE4", "line": "#6C7D86",
}

STYLE = f"""
    text {{ font-family: Inter, 'IBM Plex Sans', Arial, sans-serif; fill: {C['ink']}; }}
    .title {{ font-size: 30px; font-weight: 800; letter-spacing: .4px; }}
    .subtitle {{ font-size: 14px; fill: {C['gray']}; }}
    .band {{ font-size: 13px; font-weight: 800; letter-spacing: 1.5px; fill: {C['gray']}; }}
    .name {{ font-size: 16px; font-weight: 800; fill: #fff; }}
    .role {{ font-size: 12px; font-weight: 700; }}
    .note {{ font-size: 10px; fill: {C['gray']}; }}
    .status {{ font-size: 9px; font-weight: 800; letter-spacing: .8px; }}
    .edge-label {{ font-size: 9px; font-weight: 700; fill: {C['gray']}; }}
    .footer {{ font-size: 9px; fill: {C['gray']}; }}
    .solid {{ stroke: {C['line']}; stroke-width: 2; fill: none; }}
    .dash {{ stroke: {C['line']}; stroke-width: 2; fill: none; stroke-dasharray: 8 6; }}
"""


def lines_text(x: float, y: float, lines: list[str] | tuple[str, ...], cls: str, step: int = 16,
               anchor: str = "start") -> str:
    spans = []
    for i, line in enumerate(lines):
        spans.append(f'<tspan x="{x}" dy="{0 if i == 0 else step}">{escape(line)}</tspan>')
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{"".join(spans)}</text>'


def card(x: int, y: int, w: int, h: int, name: str, role: str,
         note: str = "", *, header: str | None = None, accent: str | None = None,
         status: str = "", dashed: bool = False, fill: str | None = None) -> str:
    header = header or C["navy"]
    accent = accent or C["orange"]
    fill = fill or C["paper"]
    border = C["steel"]
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    out = [
        f'<g class="card">',
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}" stroke="{border}" stroke-width="1.5"{dash}/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="6" fill="{accent}"/>',
        f'<rect x="{x}" y="{y+6}" width="{w}" height="34" fill="{header}"/>',
        lines_text(x+12, y+29, [name], "name"),
    ]
    role_lines = role.split("\n")
    out.append(lines_text(x+12, y+59, role_lines, "role", 15))
    used = 59 + (len(role_lines)-1)*15
    if note:
        note_lines = note.split("\n")
        out.append(lines_text(x+12, y+used+20, note_lines, "note", 14))
    if status:
        out.append(f'<rect x="{x}" y="{y+h-24}" width="{w}" height="24" fill="{C["light"]}"/>')
        out.append(lines_text(x+12, y+h-8, [status], "status"))
    out.append('</g>')
    return "".join(out)


def unit_card(x: int, y: int, w: int, h: int, name: str, function: str,
              leader: str = "", *, accent: str | None = None, open_state: bool = False) -> str:
    status = "OPEN ELEMENT" if open_state else "LOCKED CANON"
    note = leader if leader else ""
    return card(x, y, w, h, name, function, note, accent=accent, status=status,
                dashed=open_state, fill=C["open"] if open_state else C["paper"])


def connector(x1: int, y1: int, x2: int, y2: int, *, dashed: bool = False,
              label: str = "", label_x: int | None = None, label_y: int | None = None) -> str:
    cls = "dash" if dashed else "solid"
    path = f'<path d="M {x1} {y1} L {x1} {(y1+y2)//2} L {x2} {(y1+y2)//2} L {x2} {y2}" class="{cls}"/>'
    if label:
        lx = label_x if label_x is not None else (x1+x2)//2
        ly = label_y if label_y is not None else (y1+y2)//2-6
        path += f'<text x="{lx}" y="{ly}" class="edge-label" text-anchor="middle">{escape(label)}</text>'
    return path


def line(x1: int, y1: int, x2: int, y2: int, *, dashed: bool = False) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{"dash" if dashed else "solid"}"/>'


def chart(filename: str, width: int, height: int, title: str, subtitle: str,
          desc: str, body: str) -> None:
    canonical_date = INDUSTRIAL_DATE if filename in CURRENT_CHARTS else SNAPSHOT_DATE
    relationship_label = ("LABELED OWNERSHIP / OPERATING AUTHORITY" if filename in CURRENT_CHARTS
                          else "LOCKED OPERATING RELATIONSHIP")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>
<style>{STYLE}</style>
<rect width="100%" height="100%" fill="{C['bg']}"/>
<rect x="0" y="0" width="14" height="{height}" fill="{C['orange']}"/>
<text x="48" y="52" class="title">{escape(title)}</text>
<text x="48" y="78" class="subtitle">{escape(subtitle)}</text>
{body}
<text x="48" y="{height-24}" class="footer">CANONICAL DATE: {canonical_date}  •  SOLID = {relationship_label}  •  DASHED = SEAM / OPEN STRUCTURE  •  NOT AN HR REPORTING TREE</text>
</svg>'''
    (ASSETS / filename).write_text(svg, encoding="utf-8")


def build_enterprise() -> None:
    b = []
    b.append(card(590, 112, 420, 112, "SABLE HARBOR", "Industrial-systems company",
                  "Principal corporate steward: Daniel Mercer", accent=C["orange"], status="LOCKED COMPANY IDENTITY"))
    b.append(lines_text(50, 282, ["ENTERPRISE AUTHORITIES"], "band"))
    auth = [
        (50, "Priya Raman", "Product + technical substrate", "Foundry architecture and product path"),
        (350, "Elena Torres", "Deployment reality", "Customer-operating translation"),
        (650, "Caleb Hargrove", "Field operations + qualification", "Test versus operating commitment"),
        (950, "Dr. Maya Okafor", "Independent challenge", "Scientific and model claims"),
        (1250, "Marcus Reed", "Senior technical authority", "Resolver without an empire"),
    ]
    for x, n, r, note in auth:
        b.append(card(x, 305, 260, 126, n, r, note, accent=C["gold"], status="LOCKED DOMAIN"))
    b.append(lines_text(50, 500, ["OPERATING LINES AND CAPABILITIES"], "band"))
    units = [
        (50, "FOUNDRY / FOUNDRY FIELD", "Represents operational reality", "Priya Raman — product/technical substrate", C["orange"], False),
        (350, "PROJECT WILLOW", "Tests consequential unknowns", "Gid Voss — Pittsburgh laboratory", C["green"], False),
        (650, "ATLAS MERIDIAN", "Investigates represented evidence", "Simone Vale — transition/repeatability", C["gold"], False),
        (950, "PALE SUN", "Owns and operates Red Wash", "Evan Vilander — President; Mari Varela — COO", C["red"], False),
        (1250, "PROJECT CRADLE", "Recovers value from process streams", "Kenji Arakawa — program lead", C["green"], False),
    ]
    for x, n, r, ldr, ac, op in units:
        b.append(unit_card(x, 525, 260, 142, n, r, ldr, accent=ac, open_state=op))
    b.append(unit_card(350, 735, 260, 142, "AMERICAN RESOURCE UTILITY", "Operates resource logistics", "Nora Ashcombe — President / COO", accent=C["steel"]))
    b.append(unit_card(650, 735, 260, 142, "ADVISORY", "Transfers the method", "Name, leader and home: OPEN", accent=C["gold"], open_state=True))
    b.append(unit_card(950, 735, 260, 142, "RED WASH MINE", "Wyoming uranium operating asset", "Pale Sun owns and operates", accent=C["red"]))
    # company to operating band; intentionally no person-to-person reporting connectors
    for x in [180, 480, 780, 1080, 1380]:
        b.append(connector(800, 224, x, 305, dashed=True))
    for x in [180, 480, 780, 1080, 1380]:
        b.append(connector(800, 224, x, 525))
    b.append(connector(800, 224, 480, 735))
    b.append(connector(800, 224, 780, 735, dashed=True))
    b.append(connector(1080, 667, 1080, 735, label="owns + operates", label_x=1160, label_y=712))
    chart("enterprise-organization-2026.svg", 1600, 940, "SABLE HARBOR — ENTERPRISE ORGANIZATION",
          "Functional map • industrial ownership/officers resolved September 5; see current legal tree",
          "Organization chart showing enterprise authorities and Sable Harbor operating lines with the September 5 industrial closeout applied.", "".join(b))


def build_leadership() -> None:
    b = [card(515, 110, 370, 108, "DANIEL MERCER", "Principal corporate steward", "Coherence, not omniscience", status="LOCKED ROLE")]
    b.append(lines_text(50, 270, ["COMPANY-WIDE DOMAIN AUTHORITIES"], "band"))
    people = [
        (50, "PRIYA RAMAN", "Product + technical substrate", "Foundry / Atlas substrate"),
        (330, "ELENA TORRES", "Deployment reality", "Customer-operating translation"),
        (610, "CALEB HARGROVE", "Field operations + qualification", "Experiment / operation boundary"),
        (890, "DR. MAYA OKAFOR", "Independent challenge", "Evidence-to-conclusion discipline"),
        (1170, "MARCUS REED", "Senior technical authority", "No management empire"),
    ]
    for x, n, r, note in people:
        b.append(card(x, 295, 240, 128, n, r, note, accent=C["gold"], status="LOCKED DOMAIN"))
        b.append(connector(700, 218, x+120, 295, dashed=True))
    b.append(lines_text(50, 490, ["PROGRAM AND OPERATING-LINE LEADERS"], "band"))
    leaders = [
        (50, "GID VOSS", "Project Willow", "Runs Pittsburgh laboratory", C["green"], False),
        (330, "RACHEL SLOANE", "Advanced-program seam", "Sacramento; not Gid's boss", C["steel"], False),
        (610, "SIMONE VALE", "Atlas transition", "Repeatability + product boundary", C["gold"], False),
        (890, "MARI VARELA", "Pale Sun COO / Red Wash CEO", "Evan Vilander: Pale Sun President", C["red"], False),
        (1170, "KENJI ARAKAWA", "Project Cradle", "Extractive metallurgy + program", C["green"], False),
    ]
    for x, n, r, note, ac, op in leaders:
        b.append(card(x, 515, 240, 128, n, r, note, accent=ac, status="LOCKED ROLE"))
    b.append(card(330, 710, 240, 128, "NORA ASHCOMBE", "ARU President / COO", "Seth Kettering: BS&T General Manager", accent=C["steel"], status="DERIVED SYNTHETIC CASE"))
    b.append(card(610, 710, 240, 128, "ADVISORY LEADER", "Identity + home unresolved", "Emerging practice", accent=C["gold"], status="OPEN", dashed=True, fill=C["open"]))
    b.append(card(890, 710, 240, 128, "JON BELL", "Board-associated", "Left executive team in 2023", accent=C["steel"], status="LOCKED STATUS"))
    chart("leadership-authority-2026.svg", 1460, 900, "SABLE HARBOR — LEADERSHIP & AUTHORITY",
          "Named leadership state • relationships shown are domain authority, not direct reports",
          "Leadership authority chart showing the locked role domains and open leadership positions in 2026.", "".join(b))


def build_foundry() -> None:
    b = [card(490, 110, 420, 118, "PRIYA RAMAN", "Product and technical substrate",
              "Primary product + architectural force behind Foundry", status="LOCKED DOMAIN")]
    b.append(lines_text(50, 280, ["CORE AUTHORITIES AND OPERATING COUNTERWEIGHTS"], "band"))
    roles = [
        (60, "MARCUS REED", "Senior technical authority", "Resolver; no large organizational empire", C["orange"], False),
        (390, "ELENA TORRES", "Deployment reality", "What will simplification destroy?", C["gold"], False),
        (720, "NADIA", "Foundry representation work", "Surname + formal title OPEN", C["steel"], True),
        (1050, "CALEB HARGROVE", "Field-operating translation", "Practical qualification boundary", C["green"], False),
    ]
    for x, n, r, note, ac, op in roles:
        b.append(card(x, 305, 280, 135, n, r, note, accent=ac, status="OPEN IDENTITY DETAIL" if op else "LOCKED DOMAIN", dashed=op, fill=C["open"] if op else C["paper"]))
        b.append(connector(700, 228, x+140, 305, dashed=True))
    b.append(lines_text(50, 520, ["FOUNDRY / FOUNDRY FIELD"], "band"))
    b.append(unit_card(490, 545, 420, 130, "COMMERCIAL PRODUCT + SUBSTRATE", "Relationship, meaning, integration and workflow",
                       "Observe → relate → reconcile → surface → act → record → learn", accent=C["orange"]))
    b.append(connector(700, 440, 700, 545))
    b.append(lines_text(50, 735, ["OPERATIONAL APPLICATION FAMILIES"], "band"))
    apps = [
        (60, "OPERATIONS", "Production, haulage, plan variance"),
        (390, "MAINTENANCE", "Work orders, identity, downtime"),
        (720, "RECONCILIATION", "Mine, plant, lab, inventory, finance"),
        (1050, "EXCEPTIONS", "Human attention where evidence differs"),
    ]
    for x, n, r in apps:
        b.append(card(x, 760, 280, 112, n, r, "Names provisional; behavior locked", accent=C["steel"], status="PROVISIONAL NAME"))
        b.append(connector(700, 675, x+140, 760))
    chart("foundry-field-organization-2026.svg", 1400, 930, "FOUNDRY / FOUNDRY FIELD — ORGANIZATION",
          "Product, technical authority, deployment counterweights and application families",
          "Foundry Field organization chart based on locked role domains and provisional application-family names.", "".join(b))


def build_willow() -> None:
    b = [card(505, 105, 390, 116, "GID VOSS", "Runs Project Willow from Pittsburgh",
              "Experimental and epistemic authority", accent=C["green"], status="LOCKED ROLE")]
    b.append(card(1040, 105, 300, 116, "RACHEL SLOANE", "Institutional seam — Sacramento",
                  "Budget, legal, security, product + executive translation", accent=C["steel"], status="NOT GID'S BOSS"))
    b.append(line(895, 163, 1040, 163, dashed=True))
    b.append(lines_text(50, 275, ["CORE LABORATORY TEAM"], "band"))
    core = [
        (50, "MARA AQUIL", "Embedded + field systems", "Reliability outside the laboratory"),
        (315, "THEO BELL", "Applied mathematics", "Proxy-signal discovery"),
        (580, "BENJI RAO", "Mechanical systems", "Prototypes + test rigs"),
        (845, "JUN PARK", "Human-computer interaction", "Operator-centered design"),
        (1110, "ELI", "RF + communications", "Surname OPEN"),
    ]
    for x, n, r, note in core:
        b.append(card(x, 300, 235, 125, n, r, note, accent=C["green"], status="LOCKED CORE" if n != "ELI" else "SURNAME OPEN"))
        b.append(connector(700, 221, x+118, 300))
    b.append(lines_text(50, 500, ["2025 JUNIOR RESEARCH-ENGINEERING HIRES"], "band"))
    b.append(card(365, 525, 300, 130, "OWEN KESSLER", "Junior research engineering", "Hound / Ranger; stacker", accent=C["gold"], status="LOCKED"))
    b.append(card(735, 525, 300, 130, "LAYLA HADDAD", "Research / evaluation rails", "Ranger; evidence discipline; stacker", accent=C["gold"], status="LOCKED"))
    b.append(connector(700, 221, 515, 525))
    b.append(connector(700, 221, 885, 525))
    b.append(lines_text(50, 735, ["FIELD-QUALIFICATION GATE"], "band"))
    b.append(card(505, 760, 390, 112, "CALEB HARGROVE", "Field operations + experimental qualification",
                  "A Willow prototype cannot enter production without an operating owner", accent=C["red"], status="LOCKED GUARDRAIL"))
    b.append(connector(700, 655, 700, 760, dashed=True, label="qualification gate", label_x=785, label_y=712))
    chart("willow-organization-2026.svg", 1400, 930, "PROJECT WILLOW — ORGANIZATION",
          "Pittsburgh laboratory, Sacramento institutional seam and operating qualification gate",
          "Project Willow organization chart showing Gid Voss, the locked core laboratory team, junior hires and qualification gate.", "".join(b))


def build_atlas() -> None:
    b = [card(505, 105, 390, 120, "SIMONE VALE", "Atlas transition + repeatability",
              "Leads or helps lead the product bridge", accent=C["gold"], status="LOCKED ROLE / TITLE OPEN")]
    b.append(lines_text(50, 285, ["CROSS-FUNCTIONAL PRODUCT BRIDGE"], "band"))
    inputs = [
        (50, "FOUNDRY", "Priya Raman", "Represented terrain + technical substrate", C["orange"]),
        (315, "WILLOW", "Gid Voss", "Experimental lineage", C["green"]),
        (580, "DEPLOYMENT", "Elena Torres", "Customer-operating reality", C["gold"]),
        (845, "INDEPENDENT CHALLENGE", "Dr. Maya Okafor", "Scientific + model claims", C["red"]),
        (1110, "INSTITUTIONAL SEAM", "Rachel Sloane", "Advanced-program governance", C["steel"]),
    ]
    for x, n, leader, role, ac in inputs:
        b.append(card(x, 310, 235, 132, n, role, leader, accent=ac, status="LOCKED INPUT"))
        b.append(connector(x+118, 442, 700, 570, dashed=True))
    b.append(unit_card(490, 570, 420, 142, "ATLAS MERIDIAN", "Disciplined investigation across represented evidence",
                       "Controlled commercialization; human decision ownership", accent=C["gold"]))
    b.append(connector(700, 225, 700, 570))
    b.append(lines_text(50, 780, ["RESEARCH AND EVALUATION LINEAGE"], "band"))
    b.append(card(270, 805, 260, 105, "HOUND", "Crude tool-using agent", "2025 research prototype", accent=C["steel"], status="HISTORICAL LINEAGE"))
    b.append(card(570, 805, 260, 105, "RANGER", "Intent, authority + stop conditions", "Owen Kessler + Layla Haddad", accent=C["green"], status="LOCKED LINEAGE"))
    b.append(card(870, 805, 260, 105, "COMMERCIAL OWNER", "Final ownership unresolved", "Bridge establishes repeatability first", accent=C["gold"], status="OPEN", dashed=True, fill=C["open"]))
    chart("atlas-meridian-bridge-2026.svg", 1400, 970, "ATLAS MERIDIAN — BRIDGE ORGANIZATION",
          "Cross-functional product bridge • not a standalone answer engine and not autonomous decision authority",
          "Atlas Meridian organization chart showing the transition leader, cross-functional inputs and research lineage.", "".join(b))


def build_pale_sun() -> None:
    ps, rw = ENTITIES["PS"], ENTITIES["RWH"]
    b = [card(500, 110, 440, 120, "INDUSTRIAL HOLDINGS", ENTITIES["SHIH"]["legal_name"],
              "100% owner of Pale Sun Inc.", status="LOCKED SYNTHETIC OWNERSHIP")]
    b.append(card(150, 315, 440, 145, officer("PS", "President").upper(), "Pale Sun President",
                  "Platform strategy, capital cases and downstream relationships\nAppointed November 3, 2025", accent=C["red"], status="DERIVED APPOINTMENT"))
    b.append(card(850, 315, 440, 145, officer("PS", "Chief Operating Officer").upper(), "Pale Sun COO / Red Wash CEO",
                  "Mining operations, protection and qualification of change\nOne platform FTE despite two officer titles", accent=C["red"], status="DERIVED APPOINTMENT"))
    b.append(connector(720, 230, 370, 315, label="PS officer authority"))
    b.append(connector(720, 230, 1070, 315, label="PS / RWH officer authority"))
    b.append(card(150, 545, 440, 135, ps["legal_name"], f"{ps['selected_fte']} FTE business layer — 2026 case",
                  "Separate platform company; 100% owner of RWH", accent=C["red"], status="LOCKED / SYNTHETIC CASE"))
    b.append(card(850, 545, 440, 135, rw["legal_name"], f"{rw['selected_fte']} FTE site — 2026 case",
                  "Wyoming underground uranium mine; acquired July 18, 2025", accent=C["red"], status="LOCKED / SYNTHETIC CASE"))
    b.append(connector(370, 460, 370, 545))
    b.append(connector(1070, 460, 1070, 545))
    b.append(line(590, 610, 850, 610))
    b.append(lines_text(720, 590, ["100% ownership"], "edge-label", anchor="middle"))
    b.append(card(160, 745, 310, 125, "COLE", "Red Wash site superintendent",
                  "Surname unestablished; temporary stop authority\nExisting single site general-management billet", accent=C["gold"], status="LOCKED ROLE"))
    b.append(card(565, 745, 310, 125, "WALT SUTTER", "External retired geologist",
                  "Source evidence; no employee or oracle status", accent=C["steel"], status="EXTERNAL"))
    b.append(card(970, 745, 310, 125, "QUALIFICATION INTERFACES", "Caleb / Foundry / Willow / Atlas",
                  "Participation does not transfer operating authority", accent=C["green"], status="QUALIFIED INTERFACE"))
    b.append(connector(1070, 680, 315, 745))
    b.append(connector(1070, 680, 720, 745, dashed=True))
    b.append(connector(1070, 680, 1125, 745, dashed=True))
    b.append(card(120, 975, 550, 135, "QUALIFIED EXTERNAL CARRIERS", "All Red Wash transport throughout 2025",
                  "Later ownership never backdates a transport relationship", accent=C["steel"], status="LOCKED TRANSPORT BOUNDARY"))
    b.append(card(770, 975, 550, 135, "ARU / BS&T INTERFACE", "131-FTE acquired industrial operator; January 7, 2026 close",
                  "No direct mine connection or authorized uranium custody", accent=C["steel"], status="OPEN GATES / NO CUSTODY", dashed=True, fill=C["open"]))
    chart("pale-sun-red-wash-organization-2026.svg", 1440, 1180, "PALE SUN / RED WASH — ORGANIZATION",
          "140 FTE selected case: 12 Pale Sun + 128 site • legal ownership and named authority, September 5 closeout",
          "Pale Sun legal ownership and named officer chart, 140-FTE split, site authority, external carrier boundary and gated ARU interface.", "".join(b))


def build_cradle() -> None:
    b = [card(505, 105, 390, 122, "KENJI ARAKAWA", "Project Cradle lead",
              "Extractive metallurgy + program ownership", accent=C["green"], status="LOCKED ROLE")]
    b.append(lines_text(50, 285, ["FOUNDING TEAM"], "band"))
    team = [
        (150, "TESSA QUINN", "Economic geology", "Chemistry cannot negotiate with geology"),
        (565, "LUIS ORTEGA", "Process engineering + operating reality", "Where does it go?"),
        (980, "MAEVE DONNELLY", "Data engineering + material genealogy", "Source → process → stream → destination"),
    ]
    for x, n, r, note in team:
        b.append(card(x, 310, 270, 132, n, r, note, accent=C["green"], status="LOCKED FOUNDING TEAM"))
        b.append(connector(700, 227, x+135, 310))
    b.append(unit_card(505, 535, 390, 140, "PROJECT CRADLE", "Rare-earth recovery from existing process streams",
                       "Owns/controls recovery intervention; generally not host mine", accent=C["green"]))
    for x in [285, 700, 1115]:
        b.append(connector(x, 442, 700, 535, dashed=True))
    b.append(lines_text(50, 745, ["COMMERCIAL AND OPERATING BOUNDARY"], "band"))
    b.append(card(170, 770, 330, 118, "HOST OPERATOR", "Owns and runs host mine / plant", "Customer identity and exact agreement OPEN", accent=C["steel"], status="SEPARATE OPERATOR", dashed=True, fill=C["open"]))
    b.append(card(535, 770, 330, 118, "RECOVERY INTERVENTION", "Bolt-on process or stream right", "Failure must not interrupt host process", accent=C["green"], status="LOCKED DOCTRINE"))
    b.append(card(900, 770, 330, 118, "COMMERCIAL STRUCTURE", "Equipment, access, recovery rights or royalty", "Exact structure OPEN", accent=C["gold"], status="OPEN", dashed=True, fill=C["open"]))
    b.append(line(500, 829, 535, 829, dashed=True))
    b.append(line(865, 829, 900, 829, dashed=True))
    chart("project-cradle-organization-2026.svg", 1400, 950, "PROJECT CRADLE — ORGANIZATION",
          "Founding team, recovery-system boundary and host-operator separation",
          "Project Cradle organization chart showing Kenji Arakawa and the locked founding team.", "".join(b))


def build_aru() -> None:
    aru, bst = ENTITIES["ARU"], ENTITIES["BST"]
    b = [card(500, 110, 440, 125, "INDUSTRIAL HOLDINGS", ENTITIES["SHIH"]["legal_name"],
              "100% ARU stock ownership from January 7, 2026", status="LOCKED SYNTHETIC OWNERSHIP")]
    b.append(card(500, 310, 440, 140, aru["legal_name"], f"{aru['consolidated_selected_fte']} FTE consolidated; {aru['selected_fte']} direct ARU employees",
                  officer("ARU", "President and Chief Operating Officer") + " — President / COO\nFred Tolman: external transition consultant; no authority", accent=C["steel"], status="DERIVED SYNTHETIC CASE"))
    b.append(connector(720, 235, 720, 310, label="100% equity"))
    b.append(card(60, 550, 500, 155, bst["legal_name"], f"{bst['selected_fte']} FTE railway; 100% ARU-owned legal subsidiary",
                  officer("BST", "General Manager") + " — General Manager\nAnika Soren: dispatch; Calvin Mott: MOW\nPaulina Dace: mechanical; Silas Wren: compliance", accent=C["red"], status="SEPARATE RAIL OPERATING AUTHORITY"))
    b.append(card(820, 550, 560, 155, "ARU NONRAIL OPERATIONS", "Gareth Pike — Industrial Operations",
                  "27 terminal: Derek Fenwick; 24 trucking: Marta Ellery\n12 warehouse: Inez Calderon; 10 corporate\nTessa Rourke: Controller; Owen Halberg: Safety / Environment", accent=C["steel"], status="73 DIRECT ARU EMPLOYEES"))
    b.append(connector(720, 450, 310, 550, label="100% legal ownership"))
    b.append(connector(720, 450, 1100, 550, label="operating responsibility"))
    b.append(card(80, 805, 400, 145, "WORKFORCE BOUNDARY", "58 + 27 + 24 + 12 + 10 = 131 FTE",
                  "14 named leaders occupy existing billets\nNo additional management overlay or Fred employee", accent=C["gold"], status="RECONCILED CENSUS"))
    b.append(card(520, 805, 400, 145, "OPERATING CONTINUITY", "Legacy customers, people and railway knowledge",
                  "Corporate capital and technical support do not\nrelease trains or override qualified operating stops", accent=C["green"], status="RETAINED AUTHORITY"))
    b.append(card(960, 805, 400, 145, "RED WASH INTERFACE", "Taylor: ordinary industrial terminal",
                  "External qualified carriers remain valid\nUranium custody requires separate documented gates", accent=C["red"], status="OPEN GATES / NO CUSTODY", dashed=True, fill=C["open"]))
    chart("aru-bst-organization-2026.svg", 1440, 1020, "ARU / BS&T — ORGANIZATION",
          "Named retained management • 131-FTE selected case • legal ownership does not grant uranium custody",
          "ARU and BS&T current legal ownership, Nora Ashcombe and Seth Kettering authority, 131-FTE workforce and gated Red Wash interface.", "".join(b))


def build_original_eight() -> None:
    b = []
    b.append(lines_text(50, 120, ["THREE FOUNDERS — 2016"], "band"))
    founders = [
        (160, "DANIEL MERCER", "Integrator + system-level wound", "2026: principal corporate steward"),
        (535, "PRIYA RAMAN", "Semantic / structural class", "2026: product + technical substrate"),
        (910, "JON BELL", "Commercial skeptic", "Left executive team 2023; board-associated"),
    ]
    for x, n, r, note in founders:
        b.append(card(x, 145, 330, 135, n, r, note, accent=C["orange"], status="FOUNDER"))
    b.append(lines_text(50, 355, ["FIVE EARLY EMPLOYEES — COALESCED THROUGH 2016–2017 WORK"], "band"))
    early = [
        (25, "ELENA TORRES", "Deployment counterweight", "Employed 2026"),
        (295, "MARCUS REED", "Resolver", "Employed 2026"),
        (565, "DR. MAYA OKAFOR", "Epistemic discipline", "Employed 2026"),
        (835, "CALEB HARGROVE", "Operating translator", "Employed 2026"),
        (1105, "RACHEL KIM", "Finance + operating legibility", "Departed voluntarily 2024"),
    ]
    for x, n, r, note in early:
        b.append(card(x, 380, 245, 130, n, r, note, accent=C["gold"], status="EARLY EMPLOYEE"))
    # formation spine, not direct reporting
    b.append(line(700, 280, 700, 335, dashed=True))
    b.append(line(148, 335, 1228, 335, dashed=True))
    for x in [148, 418, 688, 958, 1228]:
        b.append(line(x, 335, x, 380, dashed=True))
    b.append(lines_text(50, 590, ["BLACKRIDGE CONTINUITY"], "band"))
    b.append(card(500, 615, 400, 118, "DANIEL MERCER ONLY", "Direct exposure to Blackridge",
                  "The other seven were not retroactively inserted into Argent Ridge", accent=C["red"], status="LOCKED CONTINUITY"))
    b.append(lines_text(50, 805, ["2026 STATUS"], "band"))
    b.append(card(180, 830, 300, 100, "SIX STILL EMPLOYED", "Daniel · Priya · Elena · Marcus · Maya · Caleb", accent=C["green"], status="LOCKED"))
    b.append(card(550, 830, 300, 100, "FORMALLY ASSOCIATED", "Jon Bell — board-associated", accent=C["steel"], status="LOCKED STATUS"))
    b.append(card(920, 830, 300, 100, "DEPARTED", "Rachel Kim — 2024", accent=C["gold"], status="LOCKED STATUS"))
    chart("original-eight-formation-and-status.svg", 1400, 995, "THE ORIGINAL EIGHT — FORMATION & 2026 STATUS",
          "Three founders plus five early employees • not the Blackridge team",
          "Formation and status chart for Sable Harbor's Original Eight.", "".join(b))


PAGES = {
    "2026_OPERATING_TOPOLOGY.md": ("SABLE HARBOR — ENTERPRISE ORGANIZATION", "enterprise-organization-2026.svg", "SH-ORG-001",
        "August 31 functional operating-line baseline; later headquarters institutions remain controlled by the September 3 closeout."),
    "2026_LEADERSHIP_AND_AUTHORITY_MAP.md": ("SABLE HARBOR — LEADERSHIP & AUTHORITY", "leadership-authority-2026.svg", "SH-ORG-002",
        "Named leadership and domain-authority map. Edges and placement do not create direct-report relationships."),
    "FOUNDRY_FIELD_ORGANIZATION.md": ("FOUNDRY / FOUNDRY FIELD — ORGANIZATION", "foundry-field-organization-2026.svg", "SH-ORG-003",
        "Product, technical authority, deployment counterweights and application families."),
    "WILLOW_ORGANIZATION.md": ("PROJECT WILLOW — ORGANIZATION", "willow-organization-2026.svg", "SH-ORG-004",
        "Pittsburgh laboratory, Sacramento institutional seam and operating qualification gate."),
    "ATLAS_MERIDIAN_BRIDGE_ORGANIZATION.md": ("ATLAS MERIDIAN — BRIDGE ORGANIZATION", "atlas-meridian-bridge-2026.svg", "SH-ORG-005",
        "Cross-functional transition organization for repeatability and controlled commercialization."),
    "PALE_SUN_RED_WASH_ORGANIZATION.md": ("PALE SUN / RED WASH — ORGANIZATION", "pale-sun-red-wash-organization-2026.svg", "SH-ORG-006",
        "Operating-business and mine-authority organization, approved 140-FTE case split, and qualified interfaces."),
    "PROJECT_CRADLE_ORGANIZATION.md": ("PROJECT CRADLE — ORGANIZATION", "project-cradle-organization-2026.svg", "SH-ORG-007",
        "Founding team and the boundary among Cradle, its recovery intervention and the host operator."),
    "ARU_BST_ORGANIZATION.md": ("ARU / BS&T — ORGANIZATION", "aru-bst-organization-2026.svg", "SH-ORG-008",
        "Distinct acquired operator, named retained leadership, 131-FTE case and gated Red Wash interface."),
    "ORIGINAL_EIGHT.md": ("THE ORIGINAL EIGHT — FORMATION & STATUS", "original-eight-formation-and-status.svg", "SH-ORG-009",
        "Three founders plus five early employees, Blackridge continuity and 2026 status."),
}


def write_pages() -> None:
    for path, (title, image, chart_id, purpose) in PAGES.items():
        # These pages are substantive maintained sources, not disposable wrappers.
        # Fail if absent rather than quietly replace them with a generic template.
        if path in INDUSTRIAL_PAGES:
            if not (ORG / path).is_file():
                raise FileNotFoundError(f"Missing authored industrial page: {path}")
            continue
        source_lines = [
            "- [Industrial closeout](../canon/INDUSTRIAL_CLOSEOUT_2026-09-05.md)",
            "- [`SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md`](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md)",
            "- [`DECISION_REGISTER.md`](../canon/DECISION_REGISTER.md)",
            "- [`DECISION_REGISTER_ADDENDUM_2026-09-03.md`](../canon/DECISION_REGISTER_ADDENDUM_2026-09-03.md)",
            "- [`CHART_GOVERNANCE.md`](CHART_GOVERNANCE.md)",
        ]
        if path == "PALE_SUN_RED_WASH_ORGANIZATION.md":
            source_lines.extend([
                "- [`SH-PS-RW-DR-001` — `RW-017`–`RW-025`](../canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md)",
                "- [`RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md`](../canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md)",
                "- [`ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md`](../../red_wash/logistics/ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md)",
            ])
        elif path == "ARU_BST_ORGANIZATION.md":
            source_lines.extend([
                "- [`SH-PS-RW-DR-001` — `RW-017`–`RW-025`](../canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md)",
                "- [`ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md`](../../red_wash/logistics/ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md)",
            ])
        content = f"""# {title}

**Chart ID:** `{chart_id}`
**Canonical date:** {CANON_REVIEW_DATE_DISPLAY if image in CURRENT_CHARTS else SNAPSHOT_DATE_DISPLAY}
**Canon reviewed through:** {CANON_REVIEW_DATE_DISPLAY}
**Status:** Canon-derived visual organization chart
**Purpose:** {purpose}

![{title}](assets/{image})

## Interpretation

This chart renders only relationships that the corporate canon actually locks. Where
represented, Sable Harbor controls ARU, and BS&T is a wholly owned legal subsidiary
beneath ARU.
The industrial closeout expressly supplies current legal names, ownership and appointed
officers; other unprovided reporting lines remain unresolved. Where headcount appears, it is a
source-backed synthetic selected-case value, not an implied enterprise total or
reporting structure. Dashed structures identify an institutional seam,
historical/functional relationship, or deliberately OPEN detail.

## Controlling sources

{chr(10).join(source_lines)}

The SVG is a repository artifact generated by [`scripts/build_organization_charts.py`](../../scripts/build_organization_charts.py).
"""
        (ORG / path).write_text(content, encoding="utf-8")

    rows = []
    for path, (title, _image, chart_id, purpose) in PAGES.items():
        rows.append(f"| `{chart_id}` | [{title}]({path}) | {purpose} |")
    index = f"""# SABLE HARBOR — ORGANIZATION CHARTS

**Version:** {PACKAGE_VERSION}
**Canonical date represented:** {SNAPSHOT_DATE_DISPLAY}
**Canon reviewed through:** {CANON_REVIEW_DATE_DISPLAY}
**Status:** Canon-derived publication package

These are rendered organization charts for the repository and public wiki. The broader capability charts retain the August 31 snapshot. Enterprise, leadership, Pale Sun and ARU charts apply the September 5 industrial closeout. Current industrial legal identities, officers and selected workforce are resolved; unrelated unresolved positions remain OPEN.

The September 3 headquarters closeout controls the Board/CEO, Enterprise Support Services, J2, Internal Audit, and professional-practice architecture. The existing enterprise SVG is a narrower operating-line and authority baseline; omission from that image does not supersede or weaken the later headquarters decisions.

## Chart set

| ID | Chart | Scope |
|---|---|---|
{chr(10).join(rows)}

## Reading rule

The enterprise chart is a **functional organization chart**: it shows Sable Harbor's company-wide authorities, operating lines, known leaders and known ownership/component relationships. Named industrial officers and legal ownership are now resolved; the [current legal tree](LEGAL_AND_REPORTING_STRUCTURE_STATUS_R2.md) carries those explicit relationships. Other personal reporting lines are not inferred.

The unit charts go deeper wherever the canon supports real team structure. They consume the accepted structured case and distinguish derived synthetic details from historical originals. The 140-FTE Pale Sun/Red Wash value is an approved synthetic selected-case input: 12 FTE in the Pale Sun business layer and 128 FTE at the Red Wash site.

ARU discovery and diligence begin October 2025; ownership begins January 7, 2026. Its acquisition, network, workforce, leadership, legal and financial case are now explicitly sourced. All 2025 Red Wash transport remains with qualified external carriers, and ARU/BS&T uranium custody remains OPEN_GATED. The 131-FTE ARU case comprises 58 railway, 27 terminal, 24 trucking, 12 warehouse and 10 corporate; named management occupies those billets.

## Detailed narrative and controls

- [Pale Sun and Red Wash organization map](PALE_SUN_AND_RED_WASH.md) — workforce envelope, site authority, field-qualification gate, and limited transport-interface sequence.
- [Chart governance](CHART_GOVERNANCE.md) — relationship semantics and anti-invention rules.
- [Canon traceability matrix](CANON_TRACEABILITY_MATRIX.md) — source support and carried fact state.

## Historical artwork

[Archived v0.3 sources and SVGs](history/v0.3.0/HISTORY.md) preserve earlier bytes. Existing versioned briefing PNG/PDF/PPTX/ZIP exports are historical, with hashes in the archive manifest; their old OPEN labels do not control current industrial decisions.

## Source and regeneration

- Industrial closeout: [SH-IND-DR-001](../canon/INDUSTRIAL_CLOSEOUT_2026-09-05.md)
- Entity/authority source: [entities.json](../../industrial/source/entities.json)

- Controlling canon: [`SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md`](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md)
- Decision index: [`DECISION_REGISTER.md`](../canon/DECISION_REGISTER.md)
- September 3 decisions: [`DECISION_REGISTER_ADDENDUM_2026-09-03.md`](../canon/DECISION_REGISTER_ADDENDUM_2026-09-03.md)
- September 5 Red Wash decisions: [`SH-PS-RW-DR-001` — `RW-017`–`RW-025`](../canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md)
- Red Wash record: [`RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md`](../canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md)
- Limited logistics interface: [`ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md`](../../red_wash/logistics/ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md)
- Chart governance: [`CHART_GOVERNANCE.md`](CHART_GOVERNANCE.md)
- Deterministic renderer: [`scripts/build_organization_charts.py`](../../scripts/build_organization_charts.py)
"""
    (ORG / "README.md").write_text(index, encoding="utf-8")


def write_register() -> None:
    charts = []
    for path, (title, image, chart_id, purpose) in PAGES.items():
        charts.append({
            "id": chart_id,
            "title": title,
            "page": f"docs/organization/{path}",
            "asset": f"docs/organization/assets/{image}",
            "purpose": purpose,
            "canonicalDate": INDUSTRIAL_DATE if image in CURRENT_CHARTS else SNAPSHOT_DATE,
            "canonReviewedThrough": CANON_REVIEW_DATE,
            "relationshipSemantics": "functional authority and canon-locked operating relationships; not implicit HR reporting",
        })
    register = {
        "schemaVersion": PACKAGE_VERSION,
        "registerVersion": PACKAGE_VERSION,
        "canonicalDate": SNAPSHOT_DATE,
        "canonReviewedThrough": CANON_REVIEW_DATE,
        "status": "canon-derived-rendered-chart-package",
        "industrialEffectiveDate": INDUSTRIAL_DATE,
        "historicalArchive": "docs/organization/history/v0.3.0/manifest.json",
        "controllingSources": [
            "docs/canon/INDUSTRIAL_CLOSEOUT_2026-09-05.md",
            "industrial/source/entities.json",
            "docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.3.md",
            "docs/canon/DECISION_REGISTER.md",
            "docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-03.md",
            "docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md",
            "docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md",
            "red_wash/logistics/ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md",
        ],
        "prohibitedInferences": [
            "unstated direct-report relationship", "unstated executive title", "unstated legal-entity structure",
            "unstated headcount", "unstated ownership percentage", "OPEN detail presented as settled",
            "synthetic selected-case headcount presented as an external actual",
            "ARU or BS&T uranium custody before every applicable gate passes",
        ],
        "redWashBridgeDecisionSource": {
            "recordId": "SH-PS-RW-DR-001",
            "path": "docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-05_RED_WASH_R2.md",
            "decisionIds": [f"RW-{number:03d}" for number in range(17, 26)],
        },
        "charts": charts,
    }
    (ORG / "ORGANIZATION_MAP_REGISTER.json").write_text(json.dumps(register, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    build_enterprise(); build_leadership(); build_foundry(); build_willow(); build_atlas()
    build_pale_sun(); build_cradle(); build_aru(); build_original_eight()
    write_pages(); write_register()
    # Parse every SVG as XML to fail the build on malformed output.
    import xml.etree.ElementTree as ET
    for svg in ASSETS.glob("*.svg"):
        ET.parse(svg)
    print(f"Rendered {len(list(ASSETS.glob('*.svg')))} organization charts")


if __name__ == "__main__":
    main()
