from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import textwrap
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Iterable
from xml.sax.saxutils import escape

import cairosvg
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image

try:
    from .validate_red_wash_visual_assets import (
        assert_safe_generation_output,
        validate_red_wash_visual_assets,
    )
except ImportError:  # Direct script execution.
    from validate_red_wash_visual_assets import (
        assert_safe_generation_output,
        validate_red_wash_visual_assets,
    )

REPO_ROOT = Path(
    os.environ.get('GITHUB_WORKSPACE', Path(__file__).resolve().parents[2])
).resolve()
OUT = Path(
    os.environ.get(
        'SABLE_HARBOR_ASSET_OUT',
        REPO_ROOT / '.brand-build' / 'sable-harbor-brand-assets-v0.1.0',
    )
).resolve()
LOGO_DIR = OUT / 'assets' / 'brand' / 'logos'
PREVIEW_DIR = OUT / 'qa-previews'
PACKAGE_DIR = OUT / 'packages'

OFF_WHITE = '#F4F1EA'
INK = '#101214'
MUTED = '#747A80'
DARK = '#101419'
WHITE = '#F7F5EF'

FONT_MEDIUM_PATH = Path(os.environ.get('SABLE_HARBOR_FONT_MEDIUM', '/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf'))
FONT_SEMIBOLD_PATH = Path(os.environ.get('SABLE_HARBOR_FONT_SEMIBOLD', '/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf'))
FONT_BOLD_PATH = Path(os.environ.get('SABLE_HARBOR_FONT_BOLD', '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'))


class OutlineFont:
    def __init__(self, path: Path):
        self.path = path
        self.font = TTFont(str(path))
        self.glyph_set = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font['hmtx']
        self.units_per_em = self.font['head'].unitsPerEm
        self._cache: dict[str, tuple[str, int]] = {}

    def glyph(self, ch: str) -> tuple[str, int]:
        if ch in self._cache:
            return self._cache[ch]
        glyph_name = self.cmap.get(ord(ch), '.notdef')
        pen = SVGPathPen(self.glyph_set)
        self.glyph_set[glyph_name].draw(pen)
        d = pen.getCommands()
        adv = self.hmtx[glyph_name][0]
        self._cache[ch] = (d, adv)
        return d, adv

    def measure(self, text: str, size: float, tracking: float = 0.0) -> float:
        total = 0.0
        chars = list(text)
        for idx, ch in enumerate(chars):
            if ch == ' ':
                adv = self.units_per_em * 0.48
            else:
                _, aw = self.glyph(ch)
                adv = aw
            total += adv / self.units_per_em * size
            if idx != len(chars) - 1:
                total += tracking
        return total

    def paths(
        self,
        text: str,
        x: float,
        baseline: float,
        size: float,
        fill: str,
        tracking: float = 0.0,
        anchor: str = 'start',
        opacity: float | None = None,
    ) -> str:
        width = self.measure(text, size, tracking)
        if anchor == 'middle':
            cursor = x - width / 2
        elif anchor == 'end':
            cursor = x - width
        else:
            cursor = x
        scale = size / self.units_per_em
        opacity_attr = '' if opacity is None else f' opacity="{opacity:.4f}"'
        parts = [f'<g fill="{fill}"{opacity_attr}>']
        for idx, ch in enumerate(text):
            if ch == ' ':
                adv = self.units_per_em * 0.48
            else:
                d, adv = self.glyph(ch)
                if d:
                    parts.append(
                        f'<path d="{d}" transform="translate({cursor:.3f},{baseline:.3f}) scale({scale:.8f},{-scale:.8f})"/>'
                    )
            cursor += adv / self.units_per_em * size
            if idx != len(text) - 1:
                cursor += tracking
        parts.append('</g>')
        return ''.join(parts)


for _font_path in (FONT_MEDIUM_PATH, FONT_SEMIBOLD_PATH, FONT_BOLD_PATH):
    if not _font_path.exists():
        raise FileNotFoundError(f'Required Inter Display font not found: {_font_path}')

FONT_MEDIUM = OutlineFont(FONT_MEDIUM_PATH)
FONT_SEMIBOLD = OutlineFont(FONT_SEMIBOLD_PATH)
FONT_BOLD = OutlineFont(FONT_BOLD_PATH)


@dataclass(frozen=True)
class Brand:
    slug: str
    display_name: str
    horizontal_lines: tuple[str, ...]
    mark: str
    accent: str
    classification: str
    endorsement: str | None
    canonical_status: str
    variants: tuple[str, ...]


CORE_VARIANTS = (
    'primary-horizontal',
    'stacked',
    'mark',
    'reverse-horizontal',
    'one-color-horizontal',
)
SUPPLEMENTAL_VARIANTS = (
    'primary-horizontal',
    'mark',
    'reverse-horizontal',
)

BRANDS: tuple[Brand, ...] = (
    Brand(
        'sable-harbor',
        'Sable Harbor',
        ('SABLE HARBOR',),
        'sable',
        '#C45124',
        'corporate master brand',
        None,
        'Corporate identity; artwork is a working production candidate and does not independently create canon.',
        CORE_VARIANTS,
    ),
    Brand(
        'foundry-field',
        'Foundry Field',
        ('FOUNDRY FIELD',),
        'foundry',
        '#C45124',
        'core business line',
        'A SABLE HARBOR BUSINESS LINE',
        'LOCKED business-line name and role in corporate lore v0.2.',
        CORE_VARIANTS,
    ),
    Brand(
        'willow',
        'Willow',
        ('WILLOW',),
        'willow',
        '#315F4D',
        'core business line',
        'A SABLE HARBOR BUSINESS LINE',
        'LOCKED business-line name and role in corporate lore v0.2.',
        CORE_VARIANTS,
    ),
    Brand(
        'atlas-meridian',
        'Atlas Meridian',
        ('ATLAS MERIDIAN',),
        'atlas',
        '#2E6F96',
        'core business line',
        'A SABLE HARBOR BUSINESS LINE',
        'LOCKED product/business-line name and controlled decision-support role in corporate lore v0.2.',
        CORE_VARIANTS,
    ),
    Brand(
        'pale-sun',
        'Pale Sun',
        ('PALE SUN',),
        'pale-sun',
        '#C38B1F',
        'core operating business line',
        'A SABLE HARBOR BUSINESS LINE',
        'LOCKED operating-business name and uranium thesis in corporate lore v0.2.',
        CORE_VARIANTS,
    ),
    Brand(
        'project-cradle',
        'Project Cradle',
        ('PROJECT CRADLE',),
        'cradle',
        '#C58A14',
        'core business line',
        'A SABLE HARBOR BUSINESS LINE',
        'LOCKED project/business-line name and rare-earth recovery role in corporate lore v0.2; narrative shorthand is “Cradle.”',
        CORE_VARIANTS,
    ),
    Brand(
        'american-resource-utility',
        'American Resource Utility',
        ('AMERICAN', 'RESOURCE', 'UTILITY'),
        'aru',
        '#C45124',
        'distinct operating company and core line',
        'A SABLE HARBOR BUSINESS LINE',
        'LOCKED name and operating role; detailed legal history remains OPEN in corporate lore v0.2.',
        CORE_VARIANTS,
    ),
    Brand(
        'advisory',
        'Advisory',
        ('ADVISORY',),
        'advisory',
        '#456C98',
        'core business line',
        'A SABLE HARBOR BUSINESS LINE',
        'LOCKED direction; exact organizational form remains OPEN in corporate lore v0.2.',
        CORE_VARIANTS,
    ),
    # Supplemental identity assets. These are intentionally separated from the seven-line 2026 narrative map.
    Brand(
        'foundry',
        'Foundry',
        ('FOUNDRY',),
        'foundry',
        '#C45124',
        'product substrate',
        'THE SABLE HARBOR PRODUCT SUBSTRATE',
        'LOCKED distinction: Foundry is the substrate; Foundry Field is the deployable operational product/service configuration.',
        SUPPLEMENTAL_VARIANTS,
    ),
    Brand(
        'red-wash-mine',
        'Red Wash Mine',
        ('RED WASH MINE',),
        'pale-sun',
        '#B94C2C',
        'operating asset',
        'A PALE SUN OPERATING ASSET',
        'LOCKED fictional mine name under Pale Sun; transaction and legal details remain OPEN.',
        SUPPLEMENTAL_VARIANTS,
    ),
    Brand(
        'blood-sweat-and-tears-railway',
        'Blood, Sweat & Tears Railway',
        ('BLOOD, SWEAT', '& TEARS RAILWAY'),
        'bst',
        '#B94C2C',
        'ARU operating component',
        'AN AMERICAN RESOURCE UTILITY OPERATING COMPONENT',
        'LOCKED name and relationship to ARU; exact legal and route details remain OPEN.',
        SUPPLEMENTAL_VARIANTS,
    ),
    Brand(
        'emberline',
        'Emberline',
        ('EMBERLINE',),
        'sable',
        '#C45124',
        'historical business line',
        'A HISTORICAL SABLE HARBOR LINE',
        'LOCKED historical status: active through 2025, then absorbed into enduring 2026 work.',
        SUPPLEMENTAL_VARIANTS,
    ),
    Brand(
        'red-wash-pale-sun',
        'Red Wash / Pale Sun',
        ('RED WASH', '/ PALE SUN'),
        'pale-sun',
        '#B94C2C',
        'endorsed operating lockup',
        'A SABLE HARBOR OPERATING BUSINESS',
        'Supplemental endorsed lockup joining the Pale Sun line to its Red Wash operating asset; does not replace either canonical name.',
        SUPPLEMENTAL_VARIANTS,
    ),
)


def svg_rect(x, y, w, h, fill, rx=0):
    rx_attr = f' rx="{rx}"' if rx else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"{rx_attr}/>'


def svg_polygon(points: Iterable[tuple[float, float]], fill: str):
    pts = ' '.join(f'{x:.3f},{y:.3f}' for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}"/>'


def svg_path(d: str, fill: str = 'none', stroke: str | None = None, stroke_width: float | None = None, linejoin='miter', linecap='square', fill_rule: str | None = None):
    attrs = [f'd="{d}"', f'fill="{fill}"']
    if stroke:
        attrs.append(f'stroke="{stroke}"')
    if stroke_width is not None:
        attrs.append(f'stroke-width="{stroke_width}"')
    if stroke:
        attrs.append(f'stroke-linejoin="{linejoin}"')
        attrs.append(f'stroke-linecap="{linecap}"')
    if fill_rule:
        attrs.append(f'fill-rule="{fill_rule}"')
    return '<path ' + ' '.join(attrs) + '/>'


def mark_sable(main: str, accent: str) -> str:
    e = [
        svg_rect(8, 8, 96, 20, main),
        svg_rect(8, 8, 20, 74, main),
        svg_polygon(((8, 62), (78, 62), (68, 82), (8, 82)), main),
        svg_rect(16, 92, 96, 20, main),
        svg_rect(92, 38, 20, 74, main),
        svg_polygon(((42, 38), (112, 38), (112, 58), (52, 58)), main),
        svg_rect(54, 54, 12, 12, accent),
    ]
    return ''.join(e)


def mark_foundry(main: str, accent: str) -> str:
    e = [
        svg_rect(10, 8, 100, 24, main),
        svg_rect(48, 32, 24, 23, main),
        svg_rect(10, 44, 36, 34, main),
        svg_rect(40, 54, 15, 14, main),
        svg_rect(74, 44, 36, 34, main),
        svg_rect(65, 54, 15, 14, main),
        svg_rect(10, 88, 60, 24, main),
        svg_rect(48, 75, 22, 13, main),
        svg_rect(54, 55, 12, 12, accent),
    ]
    return ''.join(e)


def mark_willow(main: str, accent: str) -> str:
    sw = 9.5
    e = [
        svg_path('M60 8 V112', stroke=main, stroke_width=sw),
        svg_path('M59 48 L39 28 H16', stroke=main, stroke_width=sw),
        svg_path('M59 59 H37 L19 43 H10', stroke=main, stroke_width=sw),
        svg_path('M59 70 L39 92 H16', stroke=main, stroke_width=sw),
        svg_path('M61 48 L81 28 H104', stroke=main, stroke_width=sw),
        svg_path('M61 59 H83 L101 43 H110', stroke=main, stroke_width=sw),
        svg_path('M61 70 L81 92 H104', stroke=main, stroke_width=sw),
        svg_rect(53, 53, 14, 14, accent),
    ]
    return ''.join(e)


def mark_advisory(main: str, accent: str) -> str:
    # Two open institutional brackets joined at an explicit decision point.
    e = [
        svg_rect(8, 8, 22, 104, main),
        svg_rect(8, 8, 42, 22, main),
        svg_rect(8, 49, 45, 22, main),
        svg_rect(8, 90, 42, 22, main),
        svg_polygon(((50, 49), (58, 57), (58, 63), (50, 71)), main),
        svg_rect(90, 8, 22, 104, main),
        svg_rect(70, 8, 42, 22, main),
        svg_rect(67, 49, 45, 22, main),
        svg_rect(70, 90, 42, 22, main),
        svg_polygon(((70, 49), (62, 57), (62, 63), (70, 71)), main),
        svg_rect(55, 64, 10, 48, main),
        svg_rect(53, 53, 14, 14, accent),
    ]
    return ''.join(e)


def mark_cradle(main: str, accent: str) -> str:
    e = [
        svg_rect(10, 10, 24, 100, main),
        svg_rect(86, 10, 24, 100, main),
        svg_polygon(((10, 10), (50, 10), (60, 20), (50, 34), (10, 34)), main),
        svg_polygon(((110, 10), (70, 10), (60, 20), (70, 34), (110, 34)), main),
        svg_rect(10, 86, 44, 24, main),
        svg_rect(66, 86, 44, 24, main),
        svg_rect(40, 40, 40, 16, main),
        svg_rect(40, 40, 14, 42, main),
        svg_rect(66, 40, 14, 42, main),
        svg_rect(54, 58, 12, 12, accent),
    ]
    return ''.join(e)


def mark_aru(main: str, accent: str) -> str:
    e = [
        svg_path('M12 20 H108 H42 L58 56', stroke=main, stroke_width=18),
        svg_path('M12 47 H44 L57 59', stroke=main, stroke_width=18),
        svg_path('M12 100 H108 H78 L62 64', stroke=main, stroke_width=18),
        svg_path('M12 73 H76 L63 61', stroke=main, stroke_width=18),
        svg_rect(53, 53, 14, 14, accent),
    ]
    return ''.join(e)


def mark_atlas(main: str, accent: str) -> str:
    e = [
        svg_path('M18 108 L58 14', stroke=main, stroke_width=18),
        svg_path('M102 108 L62 14', stroke=main, stroke_width=18),
        svg_path('M39 73 H54', stroke=main, stroke_width=16),
        svg_path('M66 73 H81', stroke=main, stroke_width=16),
        svg_path('M60 2 V118', stroke=accent, stroke_width=7),
        svg_rect(53, 58, 14, 14, accent),
    ]
    return ''.join(e)


def mark_pale_sun(main: str, accent: str) -> str:
    # Two non-converged enclosures, carried as distinct operating and material paths.
    e = [
        svg_rect(10, 10, 68, 20, main),
        svg_rect(10, 10, 20, 50, main),
        svg_rect(10, 40, 48, 20, main),
        svg_rect(42, 40, 20, 32, main),
        svg_rect(42, 48, 68, 20, accent),
        svg_rect(90, 48, 20, 62, accent),
        svg_rect(42, 90, 68, 20, accent),
        svg_rect(58, 70, 52, 20, accent),
    ]
    return ''.join(e)


def mark_bst(main: str, accent: str) -> str:
    e = [
        svg_path('M10 18 H110', stroke=main, stroke_width=14),
        svg_path('M10 48 H55 L76 20', stroke=main, stroke_width=14),
        svg_path('M10 78 H53 L76 102 H110', stroke=main, stroke_width=14),
        svg_path('M76 74 H110', stroke=main, stroke_width=14),
        svg_path('M48 47 L73 77', stroke=accent, stroke_width=12),
    ]
    return ''.join(e)


MARKS: dict[str, Callable[[str, str], str]] = {
    'sable': mark_sable,
    'foundry': mark_foundry,
    'willow': mark_willow,
    'advisory': mark_advisory,
    'cradle': mark_cradle,
    'aru': mark_aru,
    'atlas': mark_atlas,
    'pale-sun': mark_pale_sun,
    'bst': mark_bst,
}


def mark_group(mark_name: str, x: float, y: float, size: float, main: str, accent: str) -> str:
    scale = size / 120.0
    body = MARKS[mark_name](main, accent)
    return f'<g transform="translate({x:.3f},{y:.3f}) scale({scale:.8f})">{body}</g>'


def svg_document(width: int, height: int, body: str, title: str, desc: str, background: str | None = None) -> str:
    bg = '' if background is None else svg_rect(0, 0, width, height, background)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>'
        f'{bg}{body}</svg>'
    )


def fitted_font_size(lines: tuple[str, ...], max_width: float, max_size: float, min_size: float, tracking_ratio: float = 0.10) -> tuple[float, float]:
    size = max_size
    while size > min_size:
        tracking = size * tracking_ratio
        widest = max(FONT_MEDIUM.measure(line, size, tracking) for line in lines)
        if widest <= max_width:
            return size, tracking
        size -= 1
    return min_size, min_size * tracking_ratio


def render_horizontal(brand: Brand, reverse: bool = False, mono: bool = False) -> str:
    width, height = 1600, 500
    background = DARK if reverse else None
    main = WHITE if reverse else INK
    accent = main if mono else brand.accent
    secondary = '#B7BCC1' if reverse else MUTED

    mark_size = 280
    mark_x = 80
    mark_y = (height - mark_size) / 2
    body = [mark_group(brand.mark, mark_x, mark_y, mark_size, main, accent)]

    text_x = 430
    text_max_width = 1080
    n = len(brand.horizontal_lines)
    if n == 1:
        size_cap = 108
        line_gap = 24
    elif n == 2:
        size_cap = 84
        line_gap = 20
    else:
        size_cap = 74
        line_gap = 12
    size, tracking = fitted_font_size(brand.horizontal_lines, text_max_width, size_cap, 58)
    line_height = size * 1.08 + line_gap
    total_text_h = n * size + (n - 1) * (line_height - size)
    endorsement_h = 20 if brand.endorsement else 0
    group_total = total_text_h + (48 if brand.endorsement else 0)
    first_baseline = (height - group_total) / 2 + size * 0.78

    for i, line in enumerate(brand.horizontal_lines):
        baseline = first_baseline + i * line_height
        body.append(FONT_MEDIUM.paths(line, text_x, baseline, size, main, tracking))

    last_baseline = first_baseline + (n - 1) * line_height
    widest = max(FONT_MEDIUM.measure(line, size, tracking) for line in brand.horizontal_lines)
    rule_y = last_baseline + 26
    rule_width = min(widest, text_max_width)
    body.append(svg_rect(text_x, rule_y, rule_width, 4, accent))
    if brand.endorsement:
        end_size = 16
        end_track = 3.0
        body.append(FONT_SEMIBOLD.paths(brand.endorsement, text_x, rule_y + 42, end_size, secondary, end_track))

    variant = 'reverse horizontal' if reverse else ('one-color horizontal' if mono else 'primary horizontal')
    return svg_document(width, height, ''.join(body), f'{brand.display_name} — {variant}', f'Individual {variant} logo asset for {brand.display_name}.', background)


def render_stacked(brand: Brand) -> str:
    width, height = 1000, 1000
    mark_size = 390
    mark_x = (width - mark_size) / 2
    mark_y = 90
    body = [mark_group(brand.mark, mark_x, mark_y, mark_size, INK, brand.accent)]

    lines = brand.horizontal_lines
    n = len(lines)
    max_width = 820
    size_cap = 92 if n == 1 else (76 if n == 2 else 64)
    size, tracking = fitted_font_size(lines, max_width, size_cap, 50)
    line_height = size * 1.18
    first_baseline = 620 - (n - 1) * line_height / 2
    for i, line in enumerate(lines):
        body.append(FONT_MEDIUM.paths(line, width / 2, first_baseline + i * line_height, size, INK, tracking, anchor='middle'))
    last_baseline = first_baseline + (n - 1) * line_height
    if brand.endorsement:
        body.append(svg_rect(240, last_baseline + 36, 520, 4, brand.accent))
        body.append(FONT_SEMIBOLD.paths(brand.endorsement, width / 2, last_baseline + 84, 15, MUTED, 2.5, anchor='middle'))
    return svg_document(width, height, ''.join(body), f'{brand.display_name} — stacked', f'Individual stacked logo asset for {brand.display_name}.')


def render_mark(brand: Brand) -> str:
    width, height = 1000, 1000
    size = 680
    body = mark_group(brand.mark, (width - size) / 2, (height - size) / 2, size, INK, brand.accent)
    return svg_document(width, height, body, f'{brand.display_name} — mark', f'Individual mark-only logo asset for {brand.display_name}.')


def render_variant(brand: Brand, variant: str) -> str:
    if variant == 'primary-horizontal':
        return render_horizontal(brand, reverse=False, mono=False)
    if variant == 'reverse-horizontal':
        return render_horizontal(brand, reverse=True, mono=False)
    if variant == 'one-color-horizontal':
        return render_horizontal(brand, reverse=False, mono=True)
    if variant == 'stacked':
        return render_stacked(brand)
    if variant == 'mark':
        return render_mark(brand)
    raise ValueError(variant)


def output_dimensions(variant: str) -> tuple[int, int]:
    if 'horizontal' in variant:
        return (2400, 750)
    return (1600, 1600)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_deterministic_zip_member(
    archive: zipfile.ZipFile, source: Path, archive_name: str
) -> None:
    """Write a stable ZIP member without inheriting filesystem timestamps."""

    info = zipfile.ZipInfo(archive_name, date_time=(2026, 9, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(
        info,
        source.read_bytes(),
        compress_type=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    )


def make_contact_sheet(entries: list[dict], out_path: Path, title: str):
    thumbs = []
    for entry in entries:
        if entry['format'] != 'png' or entry['variant'] != 'primary-horizontal':
            continue
        p = OUT / entry['path']
        im = Image.open(p).convert('RGBA')
        canvas = Image.new('RGBA', (900, 300), OFF_WHITE)
        im.thumbnail((860, 260), Image.Resampling.LANCZOS)
        canvas.alpha_composite(im, ((900 - im.width) // 2, (300 - im.height) // 2))
        thumbs.append((entry['brand'], canvas.convert('RGB')))
    if not thumbs:
        return
    cols = 2
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new('RGB', (cols * 900, rows * 360 + 80), OFF_WHITE)
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(FONT_SEMIBOLD_PATH), 26)
    title_font = ImageFont.truetype(str(FONT_BOLD_PATH), 34)
    draw.text((40, 20), title, fill=INK, font=title_font)
    for idx, (name, im) in enumerate(thumbs):
        c, r = idx % cols, idx // cols
        x, y = c * 900, 80 + r * 360
        sheet.paste(im, (x, y))
        draw.text((x + 30, y + 310), name, fill=INK, font=font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, optimize=True)


def build_readme(manifest: dict) -> str:
    lines = [
        '# Sable Harbor Logo System — v0.1.0',
        '',
        'This directory contains individual, production-oriented generated logo assets for the Sable Harbor corporate identity and each business line in the August 31, 2026 narrative map.',
        '',
        '## Controlling naming source',
        '',
        'Business-line names and status are grounded in `docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md`. These artwork files do **not** independently create or change canon. Legal-entity, reporting-line, and exact organizational details that remain OPEN in canon remain open here.',
        '',
        '## File rule',
        '',
        '- One logo per file.',
        '- No contact sheets or composite logo boards are stored in the production logo directory.',
        '- Every generated production asset is supplied as self-contained SVG with outlined lettering and as a rendered PNG.',
        '- The four owner-approved Pale Sun/Red Wash raster sources listed in repository `assets/brand/red_wash_visual_manifest.json` are byte-exact overrides. The generator validates them in place and never regenerates, recompresses, or packages them as legacy v0.1 logo variants.',
        '- Reverse variants use a dark background; all other PNG variants preserve transparency.',
        '',
        '## Canonical 2026 business-line set',
        '',
        '| Identity | Classification | Variants |',
        '|---|---|---:|',
    ]
    for brand in BRANDS[:8]:
        lines.append(f'| {brand.display_name} | {brand.classification} | {len(brand.variants)} |')
    lines += [
        '',
        'The seven business lines are **Foundry Field, Willow, Atlas Meridian, Pale Sun, Project Cradle, American Resource Utility, and Advisory**. Sable Harbor is the corporate master brand.',
        '',
        '## Supplemental identities',
        '',
        '| Identity | Classification | Canon note |',
        '|---|---|---|',
    ]
    for brand in BRANDS[8:]:
        lines.append(f'| {brand.display_name} | {brand.classification} | {brand.canonical_status} |')
    lines += [
        '',
        '## Naming convention',
        '',
        '`<brand-slug>__<variant>.<format>`',
        '',
        'Examples:',
        '',
        '- `sable-harbor__primary-horizontal.svg`',
        '- `atlas-meridian__mark.png`',
        '- `american-resource-utility__reverse-horizontal.svg`',
        '',
        '## Intended use',
        '',
        '- **Primary horizontal:** README headings, wiki section headers, reports, and letterheads.',
        '- **Stacked:** covers, title pages, square placements, and presentation dividers.',
        '- **Mark:** favicons, avatars, small section identifiers, and document furniture.',
        '- **Reverse horizontal:** dark interfaces, dark presentation fields, signage, and video.',
        '- **One-color horizontal:** monochrome printing, stamps, engraving, and constrained reproduction.',
        '',
        '## Production constraints',
        '',
        '- Do not distort, rotate, bevel, shadow, or add gradients.',
        '- Do not combine two separate identities into one lockup unless an endorsed combined asset is provided here.',
        '- Do not substitute literal lighthouse, compass, shield, wave, mountain, mine-pick, or generic AI/circuit clip art.',
        '- Preserve clear space equal to at least one central accent square around the full lockup.',
        '- For identities without a later approved override, SVG files are the source of truth and PNG files are convenience renders.',
        '- The repository-level Pale Sun/Red Wash approved PNGs are controlling source artwork; legacy generated variants do not supersede them.',
        '',
        '## Package',
        '',
        'A ZIP archive containing the complete individual SVG and PNG set is generated under `assets/brand/packages/`.',
        '',
        '## Manifest and validation',
        '',
        '- `manifest.json` records every asset, dimensions, variant, classification, and SHA-256 digest.',
        '- Repository `assets/brand/red_wash_visual_manifest.json` separately controls the four approved Pale Sun/Red Wash raster sources.',
        '- `VALIDATION.md` records automated checks proving the one-logo-per-file rule and per-line variant coverage.',
        '',
        'All rights reserved unless a specific repository file states otherwise.',
        '',
    ]
    return '\n'.join(lines)


def build_validation(entries: list[dict], visual_assets: dict) -> str:
    core = BRANDS[:8]
    lines = [
        '# Logo Package Validation',
        '',
        '**Result:** PASS',
        '',
        'Automated validation completed against the generated package.',
        '',
        '## Required conditions',
        '',
        f'- Corporate master brand variants: **{len(core[0].variants)}**.',
        f'- Canonical business lines checked: **{len(core)-1}**.',
        '- Each canonical business line has at least three distinct variants: **PASS**.',
        '- Exactly one identity/lockup is rendered in each production file: **PASS**.',
        '- SVG text elements remaining: **0**; all lettering is outlined: **PASS**.',
        '- Every SVG has a matching PNG convenience render: **PASS**.',
        '- Production directory contains no composite sheets: **PASS**.',
        '',
        '## Approved Pale Sun / Red Wash raster sources',
        '',
        '- Repository manifest identity and approval state: **PASS**.',
        '- Exact path, byte count, dimensions, and SHA-256 for all four sources: **PASS**.',
        '- Generator output cleanup cannot contain or delete the controlled sources: **PASS**.',
        '',
        '| Controlled source | SHA-256 |',
        '|---|---|',
    ]
    for asset in visual_assets['assets']:
        lines.append(f"| `{asset['path']}` | `{asset['sha256']}` |")
    lines += [
        '',
        '## Coverage',
        '',
        '| Identity | SVG files | PNG files | Variant count |',
        '|---|---:|---:|---:|',
    ]
    for brand in BRANDS:
        svg_count = sum(1 for e in entries if e['brand_slug'] == brand.slug and e['format'] == 'svg')
        png_count = sum(1 for e in entries if e['brand_slug'] == brand.slug and e['format'] == 'png')
        lines.append(f'| {brand.display_name} | {svg_count} | {png_count} | {len(brand.variants)} |')
    lines += [
        '',
        '## Notes',
        '',
        'The QA contact sheet used during generation is intentionally excluded from `assets/brand/logos/` and from the GitHub production package. It is not a production logo asset.',
        '',
    ]
    return '\n'.join(lines)


def main():
    visual_assets_before = validate_red_wash_visual_assets(REPO_ROOT)
    assert_safe_generation_output(OUT, REPO_ROOT)
    if OUT.exists():
        shutil.rmtree(OUT)
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    for brand in BRANDS:
        for variant in brand.variants:
            base = f'{brand.slug}__{variant}'
            svg_path_out = LOGO_DIR / f'{base}.svg'
            png_path_out = LOGO_DIR / f'{base}.png'
            svg = render_variant(brand, variant)
            svg_path_out.write_text(svg, encoding='utf-8')
            ow, oh = output_dimensions(variant)
            cairosvg.svg2png(bytestring=svg.encode('utf-8'), write_to=str(png_path_out), output_width=ow, output_height=oh)
            for p, fmt in ((svg_path_out, 'svg'), (png_path_out, 'png')):
                if fmt == 'svg':
                    width, height = (1600, 500) if 'horizontal' in variant else (1000, 1000)
                else:
                    with Image.open(p) as im:
                        width, height = im.size
                entries.append({
                    'brand': brand.display_name,
                    'brand_slug': brand.slug,
                    'classification': brand.classification,
                    'canonical_status': brand.canonical_status,
                    'variant': variant,
                    'format': fmt,
                    'width': width,
                    'height': height,
                    'path': p.relative_to(OUT).as_posix(),
                    'sha256': sha256(p),
                })

    # Strict QA.
    expected = sum(len(b.variants) for b in BRANDS)
    assert len([e for e in entries if e['format'] == 'svg']) == expected
    assert len([e for e in entries if e['format'] == 'png']) == expected
    for brand in BRANDS[:8]:
        assert len(brand.variants) >= 3
        for variant in brand.variants:
            assert (LOGO_DIR / f'{brand.slug}__{variant}.svg').exists()
            assert (LOGO_DIR / f'{brand.slug}__{variant}.png').exists()
    for svg_file in LOGO_DIR.glob('*.svg'):
        text = svg_file.read_text(encoding='utf-8')
        assert '<text' not in text.lower(), svg_file
        assert text.count('<svg') == 1, svg_file
        assert text.count('<title') == 1, svg_file
    for png_file in LOGO_DIR.glob('*.png'):
        with Image.open(png_file) as im:
            assert im.width > 0 and im.height > 0
            assert im.mode in ('RGBA', 'RGB')

    manifest = {
        'package': 'Sable Harbor Logo System',
        'version': '0.1.0',
        'generated_utc': '2026-09-01T00:00:00Z',
        'controlling_canon': 'docs/canon/SABLE_HARBOR_CORPORATE_LORE_CANON_v0.2.md',
        'one_logo_per_file': True,
        'corporate_variant_count': len(BRANDS[0].variants),
        'canonical_business_lines': [b.display_name for b in BRANDS[1:8]],
        'supplemental_identities': [b.display_name for b in BRANDS[8:]],
        'asset_count': len(entries),
        'logo_count': expected,
        'formats': ['svg', 'png'],
        'assets': entries,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (OUT / 'README.md').write_text(build_readme(manifest), encoding='utf-8')
    (OUT / 'VALIDATION.md').write_text(
        build_validation(entries, visual_assets_before), encoding='utf-8'
    )

    make_contact_sheet(entries, PREVIEW_DIR / 'core-primary-horizontal-qa.png', 'SABLE HARBOR — CORE IDENTITY QA')
    make_contact_sheet(entries[16:], PREVIEW_DIR / 'all-primary-horizontal-qa.png', 'SABLE HARBOR — ALL PRIMARY LOCKUPS QA')

    # Convenience archive contains only production assets and documentation, not QA sheets.
    zip_path = PACKAGE_DIR / 'sable-harbor-logo-system-v0.1.0.zip'
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(LOGO_DIR.iterdir()):
            write_deterministic_zip_member(zf, p, f'logos/{p.name}')
        for p in (OUT / 'README.md', OUT / 'VALIDATION.md', OUT / 'manifest.json'):
            write_deterministic_zip_member(zf, p, p.name)

    visual_assets_after = validate_red_wash_visual_assets(REPO_ROOT)
    if visual_assets_after != visual_assets_before:
        raise RuntimeError('controlled Pale Sun/Red Wash visual assets changed during generation')

    print(json.dumps({
        'output': str(OUT),
        'logo_count': expected,
        'asset_files': len(entries),
        'svg_count': len(list(LOGO_DIR.glob('*.svg'))),
        'png_count': len(list(LOGO_DIR.glob('*.png'))),
        'zip': str(zip_path),
        'zip_bytes': zip_path.stat().st_size,
        'controlled_visual_assets': visual_assets_after,
    }, indent=2))


if __name__ == '__main__':
    main()
