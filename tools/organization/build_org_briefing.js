const pptxgen = require('pptxgenjs');
const fs = require('fs');
const path = require('path');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Sable Harbor';
pptx.company = 'Sable Harbor';
pptx.subject = 'Enterprise and business-line organization briefing';
pptx.title = 'Sable Harbor Organization Briefing — August 31, 2026';
pptx.lang = 'en-US';
pptx.theme = {
  headFontFace: 'Inter Display',
  bodyFontFace: 'Inter Display',
  lang: 'en-US'
};
pptx.defineSlideMaster({
  title: 'SABLE_MASTER',
  background: { color: 'F5F3EE' },
  objects: [
    { rect: { x: 0, y: 0, w: 13.333, h: 0.05, fill: { color: '101214' }, line: { color: '101214' } } },
    { rect: { x: 0, y: 7.43, w: 13.333, h: 0.07, fill: { color: 'C45124' }, line: { color: 'C45124' } } }
  ],
  slideNumber: { x: 12.55, y: 7.1, w: 0.35, h: 0.16, fontFace: 'Inter Display', fontSize: 8, color: '777A7D', align: 'right', margin: 0 }
});

const C = {
  bg: 'F5F3EE',
  white: 'FFFFFF',
  paper: 'FCFBF8',
  ink: '101214',
  muted: '6F7478',
  hair: 'D9D5CD',
  rust: 'C45124',
  willow: '315F4D',
  atlas: '2E6F96',
  pale: 'C38B1F',
  cradle: 'C58A14',
  advisory: '456C98',
  redwash: 'B94C2C',
  open: '8B8E91',
  softOpen: 'F0EFEC',
  softBlue: 'EAF0F4',
  softGreen: 'E8EFEB',
  softGold: 'F4EFE1',
  softRust: 'F3E9E4'
};

const FONT = 'Inter Display';
const REPO_ROOT = process.cwd();
const LOGO_DIR = path.join(REPO_ROOT, 'assets', 'brand', 'logos');
const OUT_DIR = path.join(REPO_ROOT, 'docs', 'organization', 'briefing');
fs.mkdirSync(OUT_DIR, { recursive: true });

function svgData(file) {
  const svg = fs.readFileSync(path.join(LOGO_DIR, file), 'utf8');
  return 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64');
}

const LOGOS = {
  sable: svgData('sable-harbor__mark.svg'),
  foundryField: svgData('foundry-field__mark.svg'),
  foundry: svgData('foundry__mark.svg'),
  willow: svgData('willow__mark.svg'),
  atlas: svgData('atlas-meridian__mark.svg'),
  pale: svgData('pale-sun__mark.svg'),
  cradle: svgData('project-cradle__mark.svg'),
  aru: svgData('american-resource-utility__mark.svg'),
  advisory: svgData('advisory__mark.svg'),
  redWash: svgData('red-wash-mine__mark.svg'),
  bst: svgData('blood-sweat-and-tears-railway__mark.svg')
};

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h,
    fontFace: FONT,
    fontSize: opts.fontSize || 12,
    color: opts.color || C.ink,
    bold: opts.bold || false,
    italic: opts.italic || false,
    align: opts.align || 'left',
    valign: opts.valign || 'mid',
    margin: opts.margin !== undefined ? opts.margin : 0,
    breakLine: false,
    fit: 'shrink',
    charSpacing: opts.charSpacing || 0,
    isTextBox: true,
    paraSpaceAfterPt: opts.paraSpaceAfterPt || 0,
    lineSpacingMultiple: 1,
    ...opts
  });
}

function addBrandHeader(slide, title, subtitle, accent, unitLogo, section = 'ORGANIZATION BRIEFING') {
  // Corporate furniture at left.
  slide.addImage({ data: LOGOS.sable, x: 0.45, y: 0.23, w: 0.38, h: 0.38 });
  addText(slide, 'SABLE HARBOR', 0.90, 0.20, 1.60, 0.23, { fontSize: 13.5, bold: true, charSpacing: 1.2 });
  addText(slide, section, 0.90, 0.44, 1.65, 0.16, { fontSize: 7.7, color: C.muted, charSpacing: 1.1 });
  slide.addShape(pptx.ShapeType.line, { x: 2.70, y: 0.20, w: 0, h: 0.43, line: { color: C.hair, width: 1.0 } });

  // Unit title.
  if (unitLogo) slide.addImage({ data: unitLogo, x: 2.98, y: 0.19, w: 0.43, h: 0.43 });
  addText(slide, title.toUpperCase(), 3.52, 0.15, 8.9, 0.33, { fontSize: 23, bold: true, charSpacing: 0.6 });
  addText(slide, subtitle, 3.52, 0.49, 8.9, 0.18, { fontSize: 9.4, color: C.muted });
  slide.addShape(pptx.ShapeType.line, { x: 3.52, y: 0.72, w: 8.92, h: 0, line: { color: accent, width: 2.4 } });
}

function addFooter(slide, sourceLabel = 'Canon date: August 31, 2026') {
  addText(slide, sourceLabel, 0.48, 7.12, 4.5, 0.15, { fontSize: 7.6, color: C.muted });
  addText(slide, 'Solid line = unit leadership or containment  •  Dashed line = cross-company interface  •  OPEN = unresolved by canon', 5.0, 7.08, 7.2, 0.18, { fontSize: 7.2, color: C.muted, align: 'right' });
}

function addMetaPanel(slide, meta, accent, x = 0.48, y = 0.92, w = 12.38, h = 0.82) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: 0.05,
    fill: { color: C.paper },
    line: { color: C.hair, width: 1.0 },
    shadow: { type: 'outer', color: '000000', opacity: 0.08, blur: 1, angle: 45, distance: 1 }
  });
  slide.addShape(pptx.ShapeType.rect, { x, y, w: 0.08, h, fill: { color: accent }, line: { color: accent } });

  const cols = [
    { label: 'HQ / OPERATING CENTER', value: meta.hq, x: x + 0.28, w: 2.55 },
    { label: 'BUSINESS', value: meta.business, x: x + 2.93, w: 5.62 },
    { label: 'CURRENT LEAD', value: meta.lead, x: x + 8.67, w: 1.75 },
    { label: 'STATUS', value: meta.status, x: x + 10.55, w: 1.56 }
  ];
  for (const c of cols) {
    addText(slide, c.label, c.x, y + 0.12, c.w, 0.15, { fontSize: 7.1, bold: true, color: accent, charSpacing: 0.8 });
    addText(slide, c.value, c.x, y + 0.31, c.w, 0.37, { fontSize: 10.3, color: C.ink, valign: 'top', margin: 0 });
  }
}

function addOrgBox(slide, cfg) {
  const {
    x, y, w, h, name, role, accent = C.rust, logo = null,
    dashed = false, open = false, fill = C.white, nameSize = 12.5, roleSize = 9.4,
    align = 'left'
  } = cfg;
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: 0.035,
    fill: { color: open ? C.softOpen : fill },
    line: { color: open ? C.open : C.ink, width: open ? 1.2 : 0.8, dash: dashed || open ? 'dash' : 'solid' },
    shadow: open ? undefined : { type: 'outer', color: '000000', opacity: 0.055, blur: 0.8, angle: 45, distance: 0.8 }
  });
  slide.addShape(pptx.ShapeType.rect, { x, y, w: 0.055, h, fill: { color: open ? C.open : accent }, line: { color: open ? C.open : accent } });
  if (logo) slide.addImage({ data: logo, x: x + 0.16, y: y + 0.18, w: Math.min(0.44, h - 0.36), h: Math.min(0.44, h - 0.36) });
  const tx = logo ? x + 0.72 : x + 0.20;
  const tw = logo ? w - 0.90 : w - 0.38;
  addText(slide, name, tx, y + 0.11, tw, Math.min(0.30, h * 0.38), { fontSize: nameSize, bold: true, color: open ? C.open : C.ink, align });
  addText(slide, role, tx, y + Math.min(0.43, h * 0.48), tw, h - Math.min(0.52, h * 0.56), { fontSize: roleSize, color: C.muted, valign: 'top', align });
}

function line(slide, x, y, w, h, opts = {}) {
  slide.addShape(pptx.ShapeType.line, {
    x, y, w, h,
    line: {
      color: opts.color || C.ink,
      width: opts.width || 1.0,
      dash: opts.dashed ? 'dash' : 'solid',
      transparency: opts.transparency || 0,
      beginArrowType: opts.beginArrowType,
      endArrowType: opts.arrow ? 'triangle' : opts.endArrowType
    }
  });
}

function orthoDown(slide, parent, child, midY = null, opts = {}) {
  const sx = parent.x + parent.w / 2;
  const sy = parent.y + parent.h;
  const ex = child.x + child.w / 2;
  const ey = child.y;
  const my = midY !== null ? midY : (sy + ey) / 2;
  line(slide, sx, sy, 0, my - sy, opts);
  line(slide, Math.min(sx, ex), my, Math.abs(ex - sx), 0, opts);
  line(slide, ex, my, 0, ey - my, { ...opts, arrow: true });
}

function straightDown(slide, parent, child, opts = {}) {
  const sx = parent.x + parent.w / 2;
  const sy = parent.y + parent.h;
  const ex = child.x + child.w / 2;
  const ey = child.y;
  line(slide, sx, sy, ex - sx, ey - sy, { ...opts, arrow: true });
}

function horizontalInterface(slide, from, to, opts = {}) {
  const sx = from.x + from.w;
  const sy = from.y + from.h / 2;
  const ex = to.x;
  const ey = to.y + to.h / 2;
  const mx = sx + (ex - sx) / 2;
  line(slide, sx, sy, mx - sx, 0, opts);
  line(slide, mx, Math.min(sy, ey), 0, Math.abs(ey - sy), opts);
  line(slide, mx, ey, ex - mx, 0, { ...opts, arrow: true });
}

function addNoteRail(slide, text, accent, x = 0.72, y = 6.58, w = 11.90, h = 0.34) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.025, fill: { color: C.paper }, line: { color: C.hair, width: 0.8 } });
  slide.addShape(pptx.ShapeType.rect, { x, y, w: 0.07, h, fill: { color: accent }, line: { color: accent } });
  addText(slide, text, x + 0.20, y + 0.03, w - 0.35, h - 0.05, { fontSize: 8.6, color: C.muted });
}

function addApplicationBox(slide, x, y, w, title, accent, logo = null) {
  slide.addShape(pptx.ShapeType.roundRect, { x, y, w, h: 0.60, rectRadius: 0.03, fill: { color: C.white }, line: { color: C.hair, width: 0.9 } });
  if (logo) slide.addImage({ data: logo, x: x + 0.12, y: y + 0.12, w: 0.34, h: 0.34 });
  addText(slide, title, x + (logo ? 0.55 : 0.18), y + 0.10, w - (logo ? 0.70 : 0.34), 0.38, { fontSize: 10.2, bold: true, color: C.ink });
  slide.addShape(pptx.ShapeType.rect, { x, y: y + 0.56, w, h: 0.04, fill: { color: accent }, line: { color: accent } });
}

// ---------- SLIDE 1: ENTERPRISE OVERVIEW ----------
{
  const slide = pptx.addSlide('SABLE_MASTER');
  addBrandHeader(slide, 'Enterprise Organization Overview', 'Portfolio structure, operating centers, business remit, and current unit leadership — August 31, 2026', C.rust, LOGOS.sable, 'CORPORATE ORGANIZATION BRIEFING');

  const corp = { x: 0.63, y: 1.02, w: 12.05, h: 1.02 };
  slide.addShape(pptx.ShapeType.roundRect, { x: corp.x, y: corp.y, w: corp.w, h: corp.h, rectRadius: 0.04, fill: { color: C.paper }, line: { color: C.ink, width: 0.9 }, shadow: { type: 'outer', color: '000000', opacity: 0.07, blur: 1, angle: 45, distance: 1 } });
  slide.addShape(pptx.ShapeType.rect, { x: corp.x, y: corp.y, w: 0.09, h: corp.h, fill: { color: C.rust }, line: { color: C.rust } });
  slide.addImage({ data: LOGOS.sable, x: 0.88, y: 1.23, w: 0.60, h: 0.60 });
  addText(slide, 'SABLE HARBOR', 1.65, 1.14, 2.05, 0.28, { fontSize: 20, bold: true, charSpacing: 0.7 });
  addText(slide, 'Industrial-systems company serving mining and natural resources through operational software, applied analytics, bounded experimentation, asset operations, logistics, and method transfer.', 1.65, 1.46, 5.37, 0.40, { fontSize: 9.8, color: C.muted, valign: 'top' });
  addText(slide, 'CORPORATE HQ', 7.22, 1.16, 1.25, 0.16, { fontSize: 7.0, bold: true, color: C.rust, charSpacing: 0.6 });
  addText(slide, 'Sacramento, California', 7.22, 1.37, 1.65, 0.22, { fontSize: 11.0, bold: true });
  addText(slide, 'PRINCIPAL STEWARD', 9.05, 1.16, 1.45, 0.16, { fontSize: 7.0, bold: true, color: C.rust, charSpacing: 0.6 });
  addText(slide, 'Daniel Mercer', 9.05, 1.37, 1.45, 0.22, { fontSize: 11.0, bold: true });
  addText(slide, 'GOVERNANCE ASSOCIATION', 10.72, 1.16, 1.70, 0.16, { fontSize: 7.0, bold: true, color: C.rust, charSpacing: 0.45 });
  addText(slide, 'Jon Bell\nBoard-associated; exact role open', 10.72, 1.34, 1.68, 0.40, { fontSize: 9.1, color: C.ink, valign: 'top' });

  // Portfolio spine.
  line(slide, 6.655, 2.04, 0, 0.25, { color: C.muted, width: 0.9 });
  line(slide, 1.72, 2.29, 9.90, 0, { color: C.muted, width: 0.8 });
  line(slide, 6.655, 2.29, 0, 2.10, { color: C.hair, width: 0.8 });
  line(slide, 2.70, 4.39, 7.93, 0, { color: C.hair, width: 0.8 });

  const units = [
    { x: 0.52, y: 2.48, w: 3.00, h: 1.52, logo: LOGOS.foundryField, accent: C.rust, name: 'FOUNDRY FIELD', hq: 'Sacramento, CA', lead: 'Priya Raman', business: 'Operational data-integration and workflow platform built on the Foundry substrate.', status: 'Mature commercial platform' },
    { x: 3.64, y: 2.48, w: 3.00, h: 1.52, logo: LOGOS.willow, accent: C.willow, name: 'WILLOW', hq: 'Pittsburgh, PA', lead: 'Gid Voss', business: 'Bounded industrial laboratory for consequential questions no other unit can own.', status: 'Active laboratory' },
    { x: 6.76, y: 2.48, w: 3.00, h: 1.52, logo: LOGOS.atlas, accent: C.atlas, name: 'ATLAS MERIDIAN', hq: 'Sacramento, CA · bridge home', lead: 'Simone Vale', business: 'Investigative decision-support system across represented industrial evidence.', status: 'Controlled 2026 bridge' },
    { x: 9.88, y: 2.48, w: 3.00, h: 1.52, logo: LOGOS.pale, accent: C.pale, name: 'PALE SUN / RED WASH', hq: 'Red Wash, Wyoming · operating center', lead: 'Mari Varela', business: 'Uranium operating business that owns and operates Red Wash Mine.', status: 'Active operating venture' },
    { x: 1.14, y: 4.58, w: 3.35, h: 1.52, logo: LOGOS.cradle, accent: C.cradle, name: 'PROJECT CRADLE', hq: 'OPEN · host-site dependent', lead: 'Kenji Arakawa', business: 'Rare-earth recovery through bolt-on interventions in existing process streams.', status: 'Active venture' },
    { x: 4.99, y: 4.58, w: 3.35, h: 1.52, logo: LOGOS.aru, accent: C.rust, name: 'AMERICAN RESOURCE UTILITY', hq: 'OPEN · legacy logistics network', lead: 'OPEN', business: 'Acquired resource-logistics operator; BS&T is its railway component.', status: 'Active · integration continuing' },
    { x: 8.84, y: 4.58, w: 3.35, h: 1.52, logo: LOGOS.advisory, accent: C.advisory, name: 'ADVISORY', hq: 'OPEN', lead: 'OPEN', business: 'Emerging operator-facing practice transferring Sable Harbor methods.', status: 'Emerging' }
  ];

  // Connectors to first and second row.
  for (let i = 0; i < 4; i++) {
    const u = units[i];
    line(slide, u.x + u.w / 2, 2.29, 0, u.y - 2.29, { color: C.muted, width: 0.8, arrow: true });
  }
  for (let i = 4; i < units.length; i++) {
    const u = units[i];
    line(slide, u.x + u.w / 2, 4.39, 0, u.y - 4.39, { color: C.muted, width: 0.8, arrow: true });
  }

  for (const u of units) {
    slide.addShape(pptx.ShapeType.roundRect, { x: u.x, y: u.y, w: u.w, h: u.h, rectRadius: 0.035, fill: { color: C.white }, line: { color: C.hair, width: 0.9 }, shadow: { type: 'outer', color: '000000', opacity: 0.055, blur: 0.8, angle: 45, distance: 0.8 } });
    slide.addShape(pptx.ShapeType.rect, { x: u.x, y: u.y, w: 0.07, h: u.h, fill: { color: u.accent }, line: { color: u.accent } });
    slide.addImage({ data: u.logo, x: u.x + 0.18, y: u.y + 0.17, w: 0.43, h: 0.43 });
    addText(slide, u.name, u.x + 0.72, u.y + 0.15, u.w - 0.90, 0.24, { fontSize: 12.8, bold: true });
    addText(slide, u.status.toUpperCase(), u.x + 0.72, u.y + 0.40, u.w - 0.90, 0.15, { fontSize: 6.7, bold: true, color: u.accent, charSpacing: 0.5 });
    slide.addShape(pptx.ShapeType.line, { x: u.x + 0.17, y: u.y + 0.67, w: u.w - 0.34, h: 0, line: { color: C.hair, width: 0.8 } });
    addText(slide, 'HQ', u.x + 0.19, u.y + 0.74, 0.42, 0.15, { fontSize: 7.1, bold: true, color: C.muted });
    addText(slide, u.hq, u.x + 0.61, u.y + 0.72, u.w - 0.79, 0.22, { fontSize: 8.6, bold: true });
    addText(slide, 'LEAD', u.x + 0.19, u.y + 0.98, 0.42, 0.15, { fontSize: 7.1, bold: true, color: C.muted });
    addText(slide, u.lead, u.x + 0.61, u.y + 0.96, u.w - 0.79, 0.22, { fontSize: 8.6, bold: true, color: u.lead === 'OPEN' ? C.open : C.ink });
    addText(slide, u.business, u.x + 0.19, u.y + 1.18, u.w - 0.38, 0.27, { fontSize: 7.65, color: C.muted, valign: 'top' });
  }

  addNoteRail(slide, 'HQ labels identify the best-supported operating or organizational center. Legal headquarters and detailed office allocations remain OPEN where noted.', C.rust, 0.72, 6.45, 11.90, 0.34);
  addFooter(slide);
}

// ---------- SLIDE 2: FOUNDRY FIELD ----------
{
  const slide = pptx.addSlide('SABLE_MASTER');
  addBrandHeader(slide, 'Foundry / Foundry Field', 'Functional leadership, product interfaces, and application families', C.rust, LOGOS.foundryField);
  addMetaPanel(slide, {
    hq: 'Sacramento, California\nOrganizational home',
    business: 'Foundry is the relationship-and-meaning substrate. Foundry Field is the deployable operational data-integration and workflow product.',
    lead: 'Priya Raman',
    status: 'Mature commercial platform'
  }, C.rust);

  const unit = { x: 4.60, y: 2.05, w: 4.12, h: 0.78 };
  addOrgBox(slide, { ...unit, name: 'FOUNDRY / FOUNDRY FIELD', role: 'Platform and commercial product', accent: C.rust, logo: LOGOS.foundryField, nameSize: 15.2, roleSize: 10.1 });
  const priya = { x: 4.90, y: 3.12, w: 3.52, h: 0.75 };
  addOrgBox(slide, { ...priya, name: 'PRIYA RAMAN', role: 'Product authority', accent: C.rust, nameSize: 14.0, roleSize: 10.1 });
  straightDown(slide, unit, priya, { color: C.ink, width: 1.2 });

  const roles = [
    { x: 0.72, y: 4.20, w: 2.60, h: 0.78, name: 'MARCUS REED', role: 'Senior technical authority', accent: C.ink },
    { x: 3.56, y: 4.20, w: 2.60, h: 0.78, name: 'ELENA TORRES', role: 'Deployment counterweight', accent: C.rust },
    { x: 6.40, y: 4.20, w: 2.60, h: 0.78, name: 'NADIA', role: 'Foundry engineer', accent: C.atlas },
    { x: 9.24, y: 4.20, w: 3.02, h: 0.78, name: 'CALEB HARGROVE', role: 'Qualification interface', accent: C.willow, dashed: true }
  ];
  for (let i = 0; i < roles.length; i++) {
    const r = roles[i];
    addOrgBox(slide, { ...r, nameSize: 12.0, roleSize: 9.2 });
    orthoDown(slide, priya, r, 4.02, { color: i === 3 ? C.willow : C.ink, width: 0.9, dashed: i === 3 });
  }

  addText(slide, 'OPERATIONAL APPLICATION FAMILIES', 0.72, 5.30, 3.05, 0.20, { fontSize: 8.4, bold: true, color: C.rust, charSpacing: 0.7 });
  slide.addShape(pptx.ShapeType.line, { x: 3.77, y: 5.42, w: 8.49, h: 0, line: { color: C.hair, width: 0.9 } });
  const appX = [0.72, 3.73, 6.74, 9.75];
  const apps = ['OPERATIONS', 'MAINTENANCE', 'RECONCILIATION', 'EXCEPTIONS'];
  for (let i = 0; i < 4; i++) addApplicationBox(slide, appX[i], 5.63, 2.51, apps[i], C.rust);

  addNoteRail(slide, 'Boundary preserved: Foundry is the reusable substrate; Foundry Field is the deployable customer-facing product and service configuration.', C.rust);
  addFooter(slide);
}

// ---------- SLIDE 3: WILLOW ----------
{
  const slide = pptx.addSlide('SABLE_MASTER');
  addBrandHeader(slide, 'Project Willow', 'Laboratory organization, institutional seam, and operating qualification gate', C.willow, LOGOS.willow);
  addMetaPanel(slide, {
    hq: 'Pittsburgh, Pennsylvania\nInstitutional seam: Sacramento',
    business: 'Bounded industrial laboratory pursuing consequential questions no existing product, delivery team, or operating unit can own.',
    lead: 'Gid Voss',
    status: 'Active laboratory'
  }, C.willow);

  const gate = { x: 0.62, y: 2.10, w: 3.04, h: 0.75 };
  const unit = { x: 4.07, y: 2.10, w: 5.16, h: 0.75 };
  const seam = { x: 9.66, y: 2.10, w: 3.04, h: 0.75 };
  addOrgBox(slide, { ...gate, name: 'CALEB HARGROVE', role: 'Qualification gate', accent: C.willow, dashed: true, nameSize: 12.3, roleSize: 9.2 });
  addOrgBox(slide, { ...unit, name: 'PROJECT WILLOW / WILLOW LABS', role: 'Bounded experimental program', accent: C.willow, logo: LOGOS.willow, nameSize: 15.0, roleSize: 10.0 });
  addOrgBox(slide, { ...seam, name: 'RACHEL SLOANE', role: 'Institutional seam · not Gid’s manager', accent: C.rust, dashed: true, nameSize: 12.0, roleSize: 8.9 });
  horizontalInterface(slide, gate, unit, { color: C.willow, width: 0.9, dashed: true });
  horizontalInterface(slide, unit, seam, { color: C.rust, width: 0.9, dashed: true });

  const gid = { x: 4.85, y: 3.15, w: 3.60, h: 0.75 };
  addOrgBox(slide, { ...gid, name: 'GID VOSS', role: 'Willow lead', accent: C.willow, nameSize: 14.2, roleSize: 10.0 });
  straightDown(slide, unit, gid, { color: C.ink, width: 1.2 });

  // Team in two rows of four.
  const team = [
    ['MARA AQUIL', 'Embedded & field systems'],
    ['THEO BELL', 'Applied mathematics'],
    ['BENJI RAO', 'Mechanical systems'],
    ['JUN PARK', 'Human-computer interaction'],
    ['ELI', 'RF & communications'],
    ['APPROX. TWO EARLY STAFF', 'Identities OPEN'],
    ['OWEN KESSLER', 'Research engineering'],
    ['LAYLA HADDAD', 'Evaluation & rules']
  ];
  const boxes = [];
  for (let i = 0; i < 8; i++) {
    const row = i < 4 ? 0 : 1;
    const col = i % 4;
    const b = { x: 0.55 + col * 3.18, y: 4.32 + row * 0.90, w: 2.88, h: 0.68 };
    boxes.push(b);
    addOrgBox(slide, { ...b, name: team[i][0], role: team[i][1], accent: i === 5 ? C.open : C.willow, open: i === 5, nameSize: i === 5 ? 9.8 : 11.1, roleSize: 8.4 });
    orthoDown(slide, gid, b, row === 0 ? 4.10 : 5.00, { color: C.ink, width: 0.8 });
  }

  addNoteRail(slide, 'Operating boundary: no Willow experiment enters production without an operating owner and qualification gate. Pittsburgh holds experimental authority; Sacramento provides institutional accountability.', C.willow);
  addFooter(slide);
}

// ---------- SLIDE 4: ATLAS MERIDIAN ----------
{
  const slide = pptx.addSlide('SABLE_MASTER');
  addBrandHeader(slide, 'Atlas Meridian', '2026 bridge organization for repeatability and controlled commercialization', C.atlas, LOGOS.atlas);
  addMetaPanel(slide, {
    hq: 'Sacramento, California\nBridge-program home',
    business: 'Disciplined investigative decision-support system operating across represented industrial evidence.',
    lead: 'Simone Vale',
    status: 'Controlled 2026 product bridge'
  }, C.atlas);

  const unit = { x: 4.49, y: 2.04, w: 4.36, h: 0.78 };
  const simone = { x: 4.86, y: 3.06, w: 3.62, h: 0.76 };
  addOrgBox(slide, { ...unit, name: 'ATLAS MERIDIAN', role: 'Investigative decision-support product', accent: C.atlas, logo: LOGOS.atlas, nameSize: 15.3, roleSize: 9.9 });
  addOrgBox(slide, { ...simone, name: 'SIMONE VALE', role: 'Transition / product lead', accent: C.atlas, nameSize: 14.2, roleSize: 9.9 });
  straightDown(slide, unit, simone, { color: C.ink, width: 1.2 });

  const interfaces = [
    { name: 'PRIYA RAMAN / FOUNDRY', role: 'Product & represented terrain', accent: C.rust },
    { name: 'GID VOSS / WILLOW', role: 'Research & investigation', accent: C.willow },
    { name: 'ELENA TORRES', role: 'Deployment & customer reality', accent: C.rust },
    { name: 'DR. MAYA OKAFOR', role: 'Independent challenge', accent: C.redwash },
    { name: 'RACHEL SLOANE', role: 'Institutional seam', accent: C.atlas },
    { name: 'COMMERCIAL INPUT', role: 'Owner OPEN', accent: C.open, open: true }
  ];
  const iboxes = [];
  for (let i = 0; i < 6; i++) {
    const b = { x: 0.48 + i * 2.14, y: 4.18, w: 1.94, h: 0.88 };
    iboxes.push(b);
    addOrgBox(slide, { ...b, name: interfaces[i].name, role: interfaces[i].role, accent: interfaces[i].accent, open: interfaces[i].open, nameSize: 9.4, roleSize: 8.0, align: 'center' });
    orthoDown(slide, simone, b, 4.00, { color: interfaces[i].accent, width: 0.8, dashed: true });
  }

  const gauntlet = { x: 4.47, y: 5.48, w: 4.40, h: 0.78 };
  addOrgBox(slide, { ...gauntlet, name: 'INVESTIGATION GAUNTLET', role: 'Repeatability and provenance gate', accent: C.atlas, nameSize: 13.6, roleSize: 9.2, align: 'center' });
  for (const b of iboxes) orthoDown(slide, b, gauntlet, 5.27, { color: C.atlas, width: 0.7, dashed: true });

  addNoteRail(slide, 'Product boundary: Atlas Meridian investigates and supports decisions; it does not autonomously own acquisition, capital, or operating decisions.', C.atlas);
  addFooter(slide);
}

// ---------- SLIDE 5: PALE SUN / RED WASH ----------
{
  const slide = pptx.addSlide('SABLE_MASTER');
  addBrandHeader(slide, 'Pale Sun / Red Wash', 'Operating organization, site authority, and qualified interfaces', C.pale, LOGOS.pale);
  addMetaPanel(slide, {
    hq: 'Red Wash Mine, Wyoming\nOperating center; legal HQ OPEN',
    business: 'Uranium operating business centered on ownership and operation of the Red Wash Mine.',
    lead: 'Marianne “Mari” Varela',
    status: 'Active operating venture'
  }, C.pale);

  const left = [
    { x: 0.55, y: 2.15, w: 2.65, h: 0.72, name: 'SABLE HARBOR', role: 'Parent organization', accent: C.rust, logo: LOGOS.sable },
    { x: 0.55, y: 3.05, w: 2.65, h: 0.72, name: 'CALEB HARGROVE', role: 'Qualification gate', accent: C.willow },
    { x: 0.55, y: 3.95, w: 2.65, h: 0.72, name: 'FOUNDRY', role: 'Representation', accent: C.rust, logo: LOGOS.foundry }
  ];
  const right = [
    { x: 10.13, y: 2.15, w: 2.65, h: 0.72, name: 'WILLOW', role: 'Bounded experiment', accent: C.willow, logo: LOGOS.willow },
    { x: 10.13, y: 3.05, w: 2.65, h: 0.72, name: 'ATLAS MERIDIAN', role: 'Decision support', accent: C.atlas, logo: LOGOS.atlas },
    { x: 10.13, y: 3.95, w: 2.65, h: 0.72, name: 'WALT SUTTER', role: 'Historical source', accent: C.open, dashed: true }
  ];
  for (const b of [...left, ...right]) addOrgBox(slide, { ...b, nameSize: 10.8, roleSize: 8.7 });

  const unit = { x: 4.33, y: 2.14, w: 4.66, h: 0.78 };
  const mari = { x: 4.63, y: 3.25, w: 4.06, h: 0.74 };
  const mine = { x: 4.63, y: 4.37, w: 4.06, h: 0.74 };
  const cole = { x: 4.88, y: 5.49, w: 3.56, h: 0.74 };
  addOrgBox(slide, { ...unit, name: 'PALE SUN', role: 'Uranium operating business', accent: C.pale, logo: LOGOS.pale, nameSize: 15.0, roleSize: 9.8, align: 'center' });
  addOrgBox(slide, { ...mari, name: 'MARIANNE “MARI” VARELA', role: 'Operating lead', accent: C.pale, nameSize: 13.1, roleSize: 9.8, align: 'center' });
  addOrgBox(slide, { ...mine, name: 'RED WASH MINE', role: 'Owned and operated mine', accent: C.redwash, logo: LOGOS.redWash, nameSize: 13.2, roleSize: 9.5, align: 'center' });
  addOrgBox(slide, { ...cole, name: 'COLE', role: 'Site superintendent', accent: C.willow, nameSize: 13.4, roleSize: 9.5, align: 'center' });
  straightDown(slide, unit, mari, { color: C.ink, width: 1.2 });
  straightDown(slide, mari, mine, { color: C.ink, width: 1.2 });
  straightDown(slide, mine, cole, { color: C.ink, width: 1.2 });

  for (const b of left) horizontalInterface(slide, b, unit, { color: b.accent, width: 0.8, dashed: b.name !== 'SABLE HARBOR' });
  for (const b of right) horizontalInterface(slide, unit, b, { color: b.accent, width: 0.8, dashed: true, beginArrowType: undefined });

  addNoteRail(slide, 'Operating rule: “Pale Sun first. Proving ground second.” Experiments and product work enter Red Wash only through qualification and operating ownership.', C.pale);
  addFooter(slide);
}

// ---------- SLIDE 6: PROJECT CRADLE ----------
{
  const slide = pptx.addSlide('SABLE_MASTER');
  addBrandHeader(slide, 'Project Cradle', 'Founding team and host-system recovery boundary', C.cradle, LOGOS.cradle);
  addMetaPanel(slide, {
    hq: 'OPEN\nHost-site dependent',
    business: 'Rare-earth recovery venture capturing value from streams existing mines and plants already create.',
    lead: 'Kenji Arakawa',
    status: 'Active venture'
  }, C.cradle);

  const unit = { x: 2.78, y: 2.04, w: 4.80, h: 0.78 };
  const kenji = { x: 3.36, y: 3.08, w: 3.64, h: 0.76 };
  addOrgBox(slide, { ...unit, name: 'PROJECT CRADLE', role: 'Rare-earth recovery program', accent: C.cradle, logo: LOGOS.cradle, nameSize: 15.0, roleSize: 10.0, align: 'center' });
  addOrgBox(slide, { ...kenji, name: 'KENJI ARAKAWA', role: 'Program lead', accent: C.cradle, nameSize: 14.0, roleSize: 9.8, align: 'center' });
  straightDown(slide, unit, kenji, { color: C.ink, width: 1.2 });

  const team = [
    { x: 0.63, y: 4.35, w: 2.42, h: 0.80, name: 'TESSA QUINN', role: 'Economic geology', accent: C.rust },
    { x: 3.25, y: 4.35, w: 2.42, h: 0.80, name: 'LUIS ORTEGA', role: 'Process engineering', accent: C.willow },
    { x: 5.87, y: 4.35, w: 2.42, h: 0.80, name: 'MAEVE DONNELLY', role: 'Data engineering', accent: C.atlas }
  ];
  for (const t of team) {
    addOrgBox(slide, { ...t, nameSize: 11.7, roleSize: 9.1, align: 'center' });
    orthoDown(slide, kenji, t, 4.12, { color: C.ink, width: 0.9 });
  }

  const host = { x: 9.72, y: 2.46, w: 2.86, h: 0.74 };
  const recovery = { x: 9.35, y: 4.17, w: 3.23, h: 0.82 };
  addOrgBox(slide, { ...host, name: 'HOST OPERATOR', role: 'Separate operator', accent: C.open, open: true, nameSize: 11.2, roleSize: 8.8, align: 'center' });
  addOrgBox(slide, { ...recovery, name: 'BOLT-ON RECOVERY STEP', role: 'Cradle-controlled intervention', accent: C.cradle, nameSize: 10.7, roleSize: 8.6, align: 'center' });
  orthoDown(slide, host, recovery, 3.70, { color: C.open, width: 0.9, dashed: true });
  // Route the program-to-recovery interface through the open right-side gutter.
  line(slide, unit.x + unit.w, unit.y + unit.h / 2, 1.20, 0, { color: C.cradle, width: 0.9, dashed: true });
  line(slide, unit.x + unit.w + 1.20, unit.y + unit.h / 2, 0, 2.13, { color: C.cradle, width: 0.9, dashed: true });
  line(slide, unit.x + unit.w + 1.20, recovery.y + recovery.h / 2, recovery.x - (unit.x + unit.w + 1.20), 0, { color: C.cradle, width: 0.9, dashed: true, arrow: true });

  addNoteRail(slide, 'Business boundary: Cradle generally avoids owning the host mine. The objective is the smallest recovery intervention that creates value without breaking the host system.', C.cradle);
  addFooter(slide);
}

// ---------- SLIDE 7: ARU / BS&T ----------
{
  const slide = pptx.addSlide('SABLE_MASTER');
  addBrandHeader(slide, 'American Resource Utility / BS&T', 'Acquired operating company, railway component, and integration interfaces', C.rust, LOGOS.aru);
  addMetaPanel(slide, {
    hq: 'OPEN\nLegacy logistics network',
    business: 'Acquired resource-logistics operator with legacy customers, dispatch practices, terminals, equipment, and operating knowledge.',
    lead: 'OPEN',
    status: 'Active · integration continuing'
  }, C.rust);

  const parent = { x: 0.58, y: 2.18, w: 2.68, h: 0.78 };
  const pale = { x: 0.58, y: 3.22, w: 2.68, h: 0.78 };
  const foundry = { x: 0.58, y: 4.26, w: 2.68, h: 0.78 };
  const advisory = { x: 10.08, y: 2.18, w: 2.68, h: 0.78 };
  const caleb = { x: 10.08, y: 3.22, w: 2.68, h: 0.78 };
  [parent, pale, foundry, advisory, caleb].forEach(()=>{});
  addOrgBox(slide, { ...parent, name: 'SABLE HARBOR', role: 'Parent organization', accent: C.rust, logo: LOGOS.sable, nameSize: 11.4, roleSize: 8.8 });
  addOrgBox(slide, { ...pale, name: 'PALE SUN', role: 'Operating / custody interface', accent: C.pale, logo: LOGOS.pale, nameSize: 11.4, roleSize: 8.6 });
  addOrgBox(slide, { ...foundry, name: 'FOUNDRY', role: 'Representation & workflow', accent: C.rust, logo: LOGOS.foundry, nameSize: 11.4, roleSize: 8.6 });
  addOrgBox(slide, { ...advisory, name: 'ADVISORY', role: 'Method-transfer interface', accent: C.advisory, logo: LOGOS.advisory, nameSize: 11.4, roleSize: 8.6, dashed: true });
  addOrgBox(slide, { ...caleb, name: 'CALEB HARGROVE', role: 'Field / operating authority', accent: C.willow, nameSize: 11.4, roleSize: 8.6, dashed: true });

  const aru = { x: 4.39, y: 2.13, w: 4.55, h: 0.82 };
  const leader = { x: 4.84, y: 3.39, w: 3.65, h: 0.76 };
  const bst = { x: 4.56, y: 4.79, w: 4.21, h: 0.82 };
  addOrgBox(slide, { ...aru, name: 'AMERICAN RESOURCE UTILITY', role: 'Distinct acquired operating company', accent: C.rust, logo: LOGOS.aru, nameSize: 14.5, roleSize: 9.7, align: 'center' });
  addOrgBox(slide, { ...leader, name: 'OPERATING LEADER — OPEN', role: 'Named role not yet locked', accent: C.open, open: true, nameSize: 12.5, roleSize: 8.9, align: 'center' });
  addOrgBox(slide, { ...bst, name: 'BLOOD, SWEAT & TEARS RAILWAY', role: 'ARU railway / short-line component', accent: C.redwash, logo: LOGOS.bst, nameSize: 12.6, roleSize: 9.2, align: 'center' });
  straightDown(slide, aru, leader, { color: C.ink, width: 1.2 });
  straightDown(slide, leader, bst, { color: C.ink, width: 1.2 });

  horizontalInterface(slide, parent, aru, { color: C.rust, width: 0.9 });
  horizontalInterface(slide, pale, aru, { color: C.pale, width: 0.8, dashed: true });
  horizontalInterface(slide, foundry, aru, { color: C.rust, width: 0.8, dashed: true });
  horizontalInterface(slide, aru, advisory, { color: C.advisory, width: 0.8, dashed: true });
  horizontalInterface(slide, aru, caleb, { color: C.willow, width: 0.8, dashed: true });

  addNoteRail(slide, 'Integration rule: ARU remains operationally distinct while Sable Harbor learns the legacy system. Exact routes, assets, workforce, headquarters, and final integration structure remain OPEN.', C.rust);
  addFooter(slide);
}

// ---------- SLIDE 8: ADVISORY ----------
{
  const slide = pptx.addSlide('SABLE_MASTER');
  addBrandHeader(slide, 'Advisory', 'Emerging method-transfer practice and organizational interfaces', C.advisory, LOGOS.advisory);
  addMetaPanel(slide, {
    hq: 'OPEN\nOrganizational home not locked',
    business: 'Operator-facing practice that transfers Sable Harbor’s operating and analytical method into systems the client can own.',
    lead: 'OPEN',
    status: 'Emerging'
  }, C.advisory);

  const unit = { x: 4.38, y: 2.03, w: 4.57, h: 0.82 };
  const lead = { x: 4.83, y: 3.24, w: 3.67, h: 0.78 };
  addOrgBox(slide, { ...unit, name: 'ADVISORY', role: 'Emerging method-transfer practice', accent: C.advisory, logo: LOGOS.advisory, nameSize: 15.6, roleSize: 9.8, align: 'center' });
  addOrgBox(slide, { ...lead, name: 'CURRENT LEADER / ORG HOME — OPEN', role: 'Final structure not yet institutionalized', accent: C.open, open: true, nameSize: 11.4, roleSize: 8.8, align: 'center' });
  straightDown(slide, unit, lead, { color: C.advisory, width: 1.1, dashed: true });

  const inputs = [
    { x: 0.72, y: 4.48, w: 2.95, h: 0.88, name: 'FOUNDRY FIELD', role: 'Product & representation methods', accent: C.rust, logo: LOGOS.foundryField },
    { x: 3.93, y: 4.48, w: 2.95, h: 0.88, name: 'PALE SUN / RED WASH', role: 'Operating methods', accent: C.pale, logo: LOGOS.pale },
    { x: 7.14, y: 4.48, w: 2.95, h: 0.88, name: 'ARU / BS&T', role: 'Logistics methods', accent: C.rust, logo: LOGOS.aru },
    { x: 10.35, y: 4.48, w: 2.27, h: 0.88, name: 'CLIENT OPERATORS', role: 'External owners', accent: C.advisory, dashed: true }
  ];
  for (const b of inputs) {
    addOrgBox(slide, { ...b, nameSize: 10.7, roleSize: 8.5, align: 'center' });
    orthoDown(slide, lead, b, 4.25, { color: b.accent, width: 0.8, dashed: true });
  }
  const engagements = { x: 4.50, y: 5.78, w: 4.33, h: 0.72 };
  addOrgBox(slide, { ...engagements, name: 'ADVISORY ENGAGEMENTS', role: 'Emerging client-owned capability transfer', accent: C.advisory, nameSize: 13.3, roleSize: 9.0, align: 'center' });
  for (const b of inputs) orthoDown(slide, b, engagements, 5.57, { color: C.advisory, width: 0.7, dashed: true });

  addNoteRail(slide, 'As of August 31, 2026, the exact practice name, leader, P&L, pricing, service catalog, and organizational home remain OPEN. The direction—method transfer rather than generic consulting—is locked.', C.advisory);
  addFooter(slide);
}

async function main() {
  const out = path.join(OUT_DIR, 'SABLE_HARBOR_Organization_Briefing_v1.0.pptx');
  await pptx.writeFile({ fileName: out });
  console.log(`Wrote ${out}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
