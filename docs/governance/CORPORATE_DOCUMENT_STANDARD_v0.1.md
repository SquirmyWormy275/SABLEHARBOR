# SABLE HARBOR — CORPORATE DOCUMENT STANDARD v0.1

**Standard ID:** `SH-GOV-DOC-001`  
**Version:** 0.1.0  
**Approval date:** September 2, 2026  
**Status:** APPROVED DESIGN STANDARD

## 1. Purpose

Sable Harbor corporate records must exist as credible institutional documents, not merely repository text or machine data. This standard defines the required publication model for governance, policy, control, finance, legal, HR, operating, assurance, and other substantive corporate artifacts.

## 2. Three-representation rule

Where applicable, every substantive controlled document has three coordinated representations:

1. **Canonical Markdown** — authoritative human-readable source text maintained in the repository.
2. **Controlled corporate publication** — a rendered office/PDF form using the approved Sable Harbor document system and letterhead/report templates.
3. **Structured representation** — JSON, YAML, CSV, SQL/database, or another machine-readable record when the document contains data or relationships that must be queried or validated programmatically.

A representation must not silently diverge from the others. Generated publications and structured derivatives trace back to the canonical source version.

## 3. Approved corporate letterhead

The approved U.S. Letter corporate correspondence template is:

`assets/brand/collateral/letterhead/sable-harbor-letterhead-us-letter.svg`

The approved design uses:

- the canonical Sable Harbor primary-horizontal logo and geometric mark;
- warm off-white paper field `#F4F1EA`;
- near-black primary typography `#101214`;
- Sable Harbor rust accent `#C45124`;
- restrained gray metadata `#747A80`;
- corporate correspondence label and date/reference block at upper right;
- a single top accent rule beneath the header;
- recipient and subject fields aligned to the left document grid;
- a restrained footer rule, contact line, and Sable Harbor identifier;
- no decorative lighthouse, shield, compass, wave, faux seal, unrelated iconography, gradients, shadows, or invented brand marks.

The design approved on September 2, 2026 is the visual baseline. Future revisions require explicit brand/document-standard versioning.

## 4. Source-of-truth rule

The canonical logo files under `assets/brand/logos/` remain the authoritative identity assets. Corporate stationery must use those assets or exact embedded geometry derived from them. A generated or AI-created substitute logo is prohibited.

## 5. Controlled-document metadata

Substantive controlled documents should carry, where appropriate:

- document title;
- stable document/control ID;
- owner;
- approver or approving body;
- version;
- status;
- approval date;
- effective date;
- next review date or review trigger;
- classification/distribution designation;
- superseded version reference;
- source repository path or manifest reference.

Not every field must appear visually on every correspondence page, but the controlled record must retain them.

## 6. Publication classes

### Corporate correspondence
Use the approved letterhead for formal letters, notices, certifications, transmittals, representations, and signed correspondence.

### Policies, standards, charters, and handbooks
Use a controlled cover/title treatment plus approved Sable Harbor document furniture. Multi-page publications should not repeat the full correspondence header on every page; subsequent pages use restrained headers/footers with title, ID, version, classification, and page numbering.

### Board and committee records
Board resolutions, committee charters, written consents, minutes, reserved-matters schedules, and delegation instruments use the corporate document system and retain approval/signature metadata.

### Business-line documents
Business-line identities may use their approved business-line logo variants, but parent-company controlled documents remain traceable to Sable Harbor governance and must not imply a separate legal entity unless canon establishes one.

### Subsidiary documents
True subsidiaries such as ARU, BS&T, and the dedicated Red Wash operating entity may maintain subsidiary stationery while retaining parent-control metadata and document lineage where applicable.

## 7. Generation and archival rules

- PDFs are generated from approved source/template inputs; they are not manually edited after rendering.
- Generated PDF/PNG/DOCX artifacts should carry manifest entries and checksums when used as retained evidence or archival releases.
- The repository should retain canonical sources and controlled templates; deterministic generated artifacts may be retained where evidentiary value justifies it.
- Historical documents are rendered according to the document system that existed at their historical effective date where the history matters. Current branding is not retroactively imposed on all past records.
- Placeholder addresses, email addresses, phone numbers, domains, legal suffixes, and officer titles must not be converted into fictional facts without canon approval.

## 8. Retrofit rule

Existing Sable Harbor substantive documents should be classified and progressively retrofitted into the controlled publication system without rewriting their substantive history.

Priority order:

1. board/governance instruments and committee charters;
2. enterprise policies and standards;
3. employee handbook and training materials;
4. legal/contractual and compliance forms;
5. financial reporting and approval packages;
6. security, technology, and operational procedures;
7. business-line and subsidiary controlled documents;
8. historical evidence packages where presentation materially improves realism or usability.

## 9. Quality gates

A controlled publication is not release-ready unless:

1. the logo/identity is an approved asset;
2. document version and source match;
3. placeholders are either deliberately retained or replaced only with canon-supported facts;
4. pagination, margins, typography, and tables render correctly;
5. no text is clipped or obscured;
6. the publication identifies its controlled-document state;
7. structured derivatives, if present, reconcile to the source;
8. generated artifacts are reviewable and reproducible.

## 10. Standing rule

From approval of this standard forward, new substantive Sable Harbor governance and control documentation should be created with the canonical-source / controlled-publication / structured-record model in mind from the start rather than retrofitted later.
