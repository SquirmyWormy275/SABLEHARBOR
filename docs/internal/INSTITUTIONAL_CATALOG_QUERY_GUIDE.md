# ALEXANDRIA INSTITUTIONAL CATALOG — QUERY GUIDE

**Document ID:** `SH-ALX-CATALOG-GUIDE-001` | **Version:** 1.0.0 | **Effective:** September 2, 2026 | **State:** CONTROLLED
**Owner:** Orientation | **Related:** Pinakes, Alexandria, controlled-document system | **Cross-reference:** `institutional_catalog.json`; `institutional_catalog.sqlite3`; `../CONTROLLED_DOCUMENT_INDEX.md`

## Purpose and authority

The institutional catalog makes Sable Harbor doctrine discoverable without becoming another source of truth. Canonical Markdown governs content. The controlled-publication manifest binds each source to its publication checksum. The JSON catalog and SQLite database are generated views of those records and can always be rebuilt.

The database contains `institutional_object`, `relationship`, `institutional_search`, and `current_institutional_object`. Each object has a stable document ID, title, category, owner, version, state, canonical source, controlled publication, and both checksums. Relationships expose related doctrines and cross-references. Full-text search supports discovery across titles and source content.

## Representative queries

```sql
-- Every Judgment doctrine
SELECT id, title, source_path FROM institutional_object WHERE search_text LIKE '%judgment%';

-- Governance policies and committee charters
SELECT id, title FROM institutional_object WHERE category IN ('governance policy','committee charter');

-- Doctrine owned by Orientation
SELECT id, title FROM institutional_object WHERE owner LIKE 'Orientation%';

-- Anything related to Daedalus, JAG, or finance
SELECT id, title FROM institutional_object WHERE search_text LIKE '%daedalus%';
SELECT id, title FROM institutional_object WHERE search_text LIKE '%jag%';
SELECT id, title FROM institutional_object WHERE search_text LIKE '%finance%';

-- Superseded institutional objects
SELECT id, title, status FROM institutional_object WHERE upper(status) LIKE 'SUPERSEDED%';

-- Full-text discovery
SELECT id, title FROM institutional_search WHERE institutional_search MATCH 'temporal integrity';
```

## Employee navigation contract

Pinakes is the human front door. Search results must take the employee to the canonical source, controlled publication, structured record, and available lineage. Access controls may restrict evidence, but they should preserve the visible question and the existence of relevant restricted material where lawful. A broken source, publication, checksum, relationship, or search record is a controlled-document defect.
