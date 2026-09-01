#!/usr/bin/env python3
"""Render Sable Harbor's canon-derived organization charts as self-contained SVG."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from xml.sax.saxutils import escape
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT / "docs" / "organization"
ASSETS = ORG / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

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
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>
<style>{STYLE}</style>
<rect width="100%" height="100%" fill="{C['bg']}"/>
<rect x="0" y="0" width="14" height="{height}" fill="{C['orange']}"/>
<text x="48" y="52" class="title">{escape(title)}</text>
<text x="48" y="78" class="subtitle">{escape(subtitle)}</text>
{body}
<text x="48" y="{height-24}" class="footer">CANONICAL DATE: 2026-08-31  •  SOLID = LOCKED OPERATING RELATIONSHIP  •  DASHED = SEAM / OPEN STRUCTURE  •  NOT AN HR REPORTING TREE</text>
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
        (950, "PALE SUN", "Owns and operates Red Wash", "Mari Varela — operating thesis", C["red"], False),
        (1250, "PROJECT CRADLE", "Recovers value from process streams", "Kenji Arakawa — program lead", C["green"], False),
    ]
    for x, n, r, ldr, ac, op in units:
        b.append(unit_card(x, 525, 260, 142, n, r, ldr, accent=ac, open_state=op))
    b.append(unit_card(350, 735, 260, 142, "AMERICAN RESOURCE UTILITY", "Operates resource logistics", "Operating leadership: OPEN", accent=C["steel"], open_state=True))
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
          "Operating ownership and authority map • exact HR reporting lines and legal entities remain open",
          "Organization chart showing enterprise authorities and Sable Harbor operating lines as of August 31, 2026.", "".join(b))


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
        (890, "MARI VARELA", "Pale Sun", "Red Wash operating thesis", C["red"], False),
        (1170, "KENJI ARAKAWA", "Project Cradle", "Extractive metallurgy + program", C["green"], False),
    ]
    for x, n, r, note, ac, op in leaders:
        b.append(card(x, 515, 240, 128, n, r, note, accent=ac, status="LOCKED ROLE"))
    b.append(card(330, 710, 240, 128, "ARU OPERATING LEADER", "Identity unresolved", "ARU remains operationally distinct", accent=C["steel"], status="OPEN", dashed=True, fill=C["open"]))
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
    b = [card(505, 105, 390, 122, "MARIANNE “MARI” VARELA", "Leads Pale Sun's operating thesis",
              "Protects Red Wash from becoming a science fair", accent=C["red"], status="LOCKED ROLE")]
    b.append(unit_card(505, 300, 390, 130, "PALE SUN", "Uranium operating business",
                       "Operation first; proving ground second", accent=C["red"]))
    b.append(connector(700, 227, 700, 300))
    b.append(unit_card(505, 505, 390, 130, "RED WASH MINE", "Underground Wyoming uranium mine",
                       "Owned and operated by Pale Sun", accent=C["red"]))
    b.append(connector(700, 430, 700, 505, label="owns + operates", label_x=790, label_y=475))
    b.append(card(160, 505, 270, 130, "COLE", "Red Wash site superintendent", "Surname OPEN; defined temporary stop authority", accent=C["gold"], status="LOCKED ROLE"))
    b.append(connector(565, 570, 430, 570))
    b.append(card(970, 505, 270, 130, "WALT SUTTER", "Retired geologist — external source", "Useful source; not employee and not oracle", accent=C["steel"], status="EXTERNAL"))
    b.append(line(895, 570, 970, 570, dashed=True))
    b.append(lines_text(50, 720, ["OPERATING INTERFACES — ACCESS THROUGH QUALIFICATION GATES"], "band"))
    interfaces = [
        (100, "CALEB HARGROVE", "Field qualification + operating boundary", C["green"]),
        (410, "FOUNDRY", "Representation + workflow", C["orange"]),
        (720, "WILLOW", "Qualified experiments only", C["green"]),
        (1030, "ATLAS MERIDIAN", "Decision support only", C["gold"]),
    ]
    for x, n, r, ac in interfaces:
        b.append(card(x, 745, 270, 112, n, r, "Pale Sun operating accountability controls consequence", accent=ac, status="LOCKED INTERFACE"))
        b.append(connector(700, 635, x+135, 745, dashed=True))
    chart("pale-sun-red-wash-organization-2026.svg", 1400, 920, "PALE SUN / RED WASH — ORGANIZATION",
          "Operating business and mine authority • Pale Sun first, proving ground second",
          "Pale Sun organization chart showing Mari Varela, Red Wash, Cole, Walt Sutter and qualified interfaces.", "".join(b))


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
    b = [unit_card(500, 105, 400, 128, "AMERICAN RESOURCE UTILITY", "Acquired resource-logistics operator",
                   "Remains operationally distinct during integration", accent=C["steel"])]
    b.append(card(500, 310, 400, 118, "ARU OPERATING LEADERSHIP", "Identity and exact title unresolved",
                  "Legacy operating accountability remains real", accent=C["steel"], status="OPEN", dashed=True, fill=C["open"]))
    b.append(connector(700, 233, 700, 310))
    b.append(lines_text(50, 500, ["LOCKED OPERATING COMPONENT AND ESTATE"], "band"))
    b.append(unit_card(190, 525, 360, 135, "BLOOD, SWEAT & TEARS RAILWAY", "ARU railway / short-line component",
                       "Exact legal name, routes and asset count OPEN", accent=C["red"]))
    b.append(unit_card(850, 525, 360, 135, "LEGACY LOGISTICS OPERATIONS", "Customers, dispatch, terminals, equipment + know-how",
                       "Detailed structure and footprint OPEN", accent=C["steel"], open_state=True))
    b.append(connector(700, 428, 370, 525))
    b.append(connector(700, 428, 1030, 525, dashed=True))
    b.append(lines_text(50, 735, ["SABLE HARBOR INTERFACES"], "band"))
    b.append(card(210, 760, 300, 112, "PALE SUN", "Logistics + custody constraint", "Acquisition rationale", accent=C["red"], status="LOCKED INTERFACE"))
    b.append(card(550, 760, 300, 112, "FOUNDRY", "Representation + workflow", "May not overstate source certainty", accent=C["orange"], status="LOCKED INTERFACE"))
    b.append(card(890, 760, 300, 112, "CALEB / OPERATIONS", "Immediate operating consequence", "Technical and capital authority remain distinct", accent=C["green"], status="LOCKED RULE"))
    chart("aru-bst-organization-2026.svg", 1400, 930, "ARU / BS&T — ORGANIZATION",
          "Distinct acquired operator • detailed leadership, footprint and legal structure remain open",
          "American Resource Utility organization chart showing its open operating leadership and BS&T railway component.", "".join(b))


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
        "Functional enterprise organization: company-wide authorities, operating lines and known ownership/component relationships."),
    "2026_LEADERSHIP_AND_AUTHORITY_MAP.md": ("SABLE HARBOR — LEADERSHIP & AUTHORITY", "leadership-authority-2026.svg", "SH-ORG-002",
        "Named leadership and domain-authority map. Edges and placement do not create direct-report relationships."),
    "FOUNDRY_FIELD_ORGANIZATION.md": ("FOUNDRY / FOUNDRY FIELD — ORGANIZATION", "foundry-field-organization-2026.svg", "SH-ORG-003",
        "Product, technical authority, deployment counterweights and application families."),
    "WILLOW_ORGANIZATION.md": ("PROJECT WILLOW — ORGANIZATION", "willow-organization-2026.svg", "SH-ORG-004",
        "Pittsburgh laboratory, Sacramento institutional seam and operating qualification gate."),
    "ATLAS_MERIDIAN_BRIDGE_ORGANIZATION.md": ("ATLAS MERIDIAN — BRIDGE ORGANIZATION", "atlas-meridian-bridge-2026.svg", "SH-ORG-005",
        "Cross-functional transition organization for repeatability and controlled commercialization."),
    "PALE_SUN_RED_WASH_ORGANIZATION.md": ("PALE SUN / RED WASH — ORGANIZATION", "pale-sun-red-wash-organization-2026.svg", "SH-ORG-006",
        "Operating-business and mine-authority organization, including qualified interfaces."),
    "PROJECT_CRADLE_ORGANIZATION.md": ("PROJECT CRADLE — ORGANIZATION", "project-cradle-organization-2026.svg", "SH-ORG-007",
        "Founding team and the boundary among Cradle, its recovery intervention and the host operator."),
    "ARU_BST_ORGANIZATION.md": ("ARU / BS&T — ORGANIZATION", "aru-bst-organization-2026.svg", "SH-ORG-008",
        "Distinct acquired operator, known railway component and open operating structure."),
    "ORIGINAL_EIGHT.md": ("THE ORIGINAL EIGHT — FORMATION & STATUS", "original-eight-formation-and-status.svg", "SH-ORG-009",
        "Three founders plus five early employees, Blackridge continuity and 2026 status."),
}


def write_pages() -> None:
    for path, (title, image, chart_id, purpose) in PAGES.items():
        content = f"""# {title}

**Chart ID:** `{chart_id}`  
**Canonical date:** August 31, 2026  
**Status:** Canon-derived visual organization chart  
**Purpose:** {purpose}

![{title}](assets/{image})

## Interpretation

This chart renders relationships that the corporate canon actually locks. It does **not** invent final legal entities, executive titles, headcount, or person-to-person reporting lines. Dashed structures identify an institutional seam, historical/functional relationship, or deliberately OPEN detail.

## Controlling sources

- [`SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md`](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- [`DECISION_REGISTER.md`](../canon/DECISION_REGISTER.md)
- [`CHART_GOVERNANCE.md`](CHART_GOVERNANCE.md)

The SVG is a repository artifact generated by [`scripts/build_organization_charts.py`](../../scripts/build_organization_charts.py).
"""
        (ORG / path).write_text(content, encoding="utf-8")

    rows = []
    for path, (title, _image, chart_id, purpose) in PAGES.items():
        rows.append(f"| `{chart_id}` | [{title}]({path}) | {purpose} |")
    index = f"""# SABLE HARBOR — ORGANIZATION CHARTS

**Version:** 0.2.0  
**Canonical date represented:** August 31, 2026  
**Status:** Canon-derived publication package

These are rendered organization charts for the repository README and public wiki. The charts preserve every locked organizational relationship currently available and display genuinely unresolved positions as OPEN rather than fabricating a polished hierarchy.

## Chart set

| ID | Chart | Scope |
|---|---|---|
{chr(10).join(rows)}

## Reading rule

The enterprise chart is a **functional organization chart**: it shows Sable Harbor's company-wide authorities, operating lines, known leaders and known ownership/component relationships. It is not a conventional HR reporting tree because the canon deliberately leaves exact executive titles and reporting lines open.

The unit charts go deeper wherever the canon supports real team structure. They do not fill remaining gaps with plausible-sounding executives, mine departments, subsidiaries, or headcount.

## Source and regeneration

- Controlling canon: [`SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md`](../canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md)
- Decision index: [`DECISION_REGISTER.md`](../canon/DECISION_REGISTER.md)
- Chart governance: [`CHART_GOVERNANCE.md`](CHART_GOVERNANCE.md)
- Deterministic renderer: [`scripts/build_organization_charts.py`](../../scripts/build_organization_charts.py)
"""
    (ORG / "README.md").write_text(index, encoding="utf-8")


def update_root_readme() -> None:
    readme_path = ROOT / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    section = """## Organization at a glance

This is the canon-derived August 31, 2026 **functional enterprise organization chart**. It shows company-wide authorities, operating lines, named leaders and known ownership/component relationships. Exact HR reporting lines and final legal entities remain deliberately open.

[![Sable Harbor enterprise organization chart](docs/organization/assets/enterprise-organization-2026.svg)](docs/organization/README.md)

The full package contains dedicated charts for [leadership and authority](docs/organization/2026_LEADERSHIP_AND_AUTHORITY_MAP.md), [Foundry Field](docs/organization/FOUNDRY_FIELD_ORGANIZATION.md), [Project Willow](docs/organization/WILLOW_ORGANIZATION.md), [Atlas Meridian](docs/organization/ATLAS_MERIDIAN_BRIDGE_ORGANIZATION.md), [Pale Sun and Red Wash](docs/organization/PALE_SUN_RED_WASH_ORGANIZATION.md), [Project Cradle](docs/organization/PROJECT_CRADLE_ORGANIZATION.md), [ARU and BS&T](docs/organization/ARU_BST_ORGANIZATION.md), and [the Original Eight](docs/organization/ORIGINAL_EIGHT.md).

### Official organization briefing

The briefing-grade publication package uses the approved production logo system and includes one rendered 16:9 image per chart, an editable PowerPoint deck, a PDF, a packaged ZIP, a source builder, and a validation manifest.

- [Organization briefing index](docs/organization/briefing/README.md)
- [Editable PowerPoint](docs/organization/briefing/SABLE_HARBOR_Organization_Briefing_v1.0.pptx)
- [Briefing PDF](docs/organization/briefing/SABLE_HARBOR_Organization_Briefing_v1.0.pdf)
- [Complete briefing package](docs/organization/briefing/SABLE_HARBOR_Organization_Briefing_v1.0.zip)

"""
    pattern = re.compile(r"## Organization at a glance\n.*?(?=## Blackridge status\n)", re.S)
    if not pattern.search(text):
        raise RuntimeError("README organization section not found")
    readme_path.write_text(pattern.sub(section, text), encoding="utf-8")


def write_register() -> None:
    charts = []
    for path, (title, image, chart_id, purpose) in PAGES.items():
        charts.append({
            "id": chart_id,
            "title": title,
            "page": f"docs/organization/{path}",
            "asset": f"docs/organization/assets/{image}",
            "purpose": purpose,
            "canonicalDate": "2026-08-31",
            "relationshipSemantics": "functional authority and canon-locked operating relationships; not implicit HR reporting",
        })
    register = {
        "schemaVersion": "0.2.0",
        "registerVersion": "0.2.0",
        "canonicalDate": "2026-08-31",
        "status": "canon-derived-rendered-chart-package",
        "controllingSources": [
            "docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md",
            "docs/canon/DECISION_REGISTER.md",
        ],
        "prohibitedInferences": [
            "unstated direct-report relationship", "final executive title", "final legal-entity structure",
            "unstated headcount", "unstated ownership percentage", "OPEN detail presented as settled",
        ],
        "charts": charts,
    }
    (ORG / "ORGANIZATION_MAP_REGISTER.json").write_text(json.dumps(register, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    build_enterprise(); build_leadership(); build_foundry(); build_willow(); build_atlas()
    build_pale_sun(); build_cradle(); build_aru(); build_original_eight()
    write_pages(); write_register(); update_root_readme()
    # Parse every SVG as XML to fail the build on malformed output.
    import xml.etree.ElementTree as ET
    for svg in ASSETS.glob("*.svg"):
        ET.parse(svg)
    print(f"Rendered {len(list(ASSETS.glob('*.svg')))} organization charts")


if __name__ == "__main__":
    main()
