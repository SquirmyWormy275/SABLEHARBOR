# Complete retained company records

These are the actual retained synthetic company records, included directly in Git. An ordinary clone contains **all 5,714 source versions across 922 source systems** from the recovered source-only company snapshot. Open the JSON, text and binary files directly; no local launcher, external drive, credentials or generator is needed.

The [data availability record](../DATA_AVAILABILITY.md) explains publication and recovery. The narrower [November client submissions](../demo-2026-11/client-records/README.md) provide a ready-to-use exercise with correspondence and walkthroughs. This directory supplies the broader company source history behind that kind of work.

| History | Native source branch | Source versions | Systems | Complete source provenance |
| --- | --- | ---: | ---: | --- |
| [History 01](history-01/) | HARBOR-OPERATIONS-A | 2,793 | 447 | [provenance.jsonl](history-01/provenance.jsonl) |
| [History 02](history-02/) | HARBOR-OPERATIONS-B | 2,921 | 475 | [provenance.jsonl](history-02/provenance.jsonl) |

The histories are separate alternatives. Preserve the branch, system, record and version when joining records; do not add the two histories together as one company population. The [manifest](manifest.json) lists every file and preserves each original identity, source version, business-event time, availability time, import time, origin, source hash and delivery hash. Its systems register also retains every source owner. Each provenance line joins on the same five identity fields and retains the complete source provenance, ingestion command identifier and input digest. In particular, qualification, completeness, authority, control mappings and source relationships remain available.

For audit-software testing, [the CLEAN/MESSY intake guide](../CLEAN_MESSY_INTAKE.md)
maps History 01 to CLEAN and History 02 to MESSY and explains how to import one
verified history at a time while retaining native identities and dates.

Of the 5,714 files, **5,709 retain their exact original bytes**. Five are explicitly marked derivatives: only absolute workstation `source_root` or `runtime_root` values were replaced with consistent `local-source:` locators. Their original hashes and changed JSON field paths remain in the manifest. No source facts, record versions or historical errors were removed. The file extensions reflect the retained source media types: 5,696 JSON files, 12 small binary source objects and six text files.

These are fictional company records and local reference exercises. Their own provenance and scope limitations remain authoritative; possession of a record does not establish real employment, deployment, compliance, or audit sufficiency. Source chronology is retained, including records with future fictional dates. This snapshot is complete for the two populated source tables (`systems` and `versions`), not a claim that every possible company fact was ever authored. Evaluator packages and live workspace authentication are separate from company evidence.

From the repository root, verify the complete delivered population with standard Python:

```sh
python tools/audit_suite/company_record_delivery.py verify --root docs/audit-suite/company-records
```

Verification checks every member, source/delivery relationship, provenance digest, system membership and count. It reports 5,714 versions, 922 systems, 5,709 originals and five derivatives. It does not need the original private database. The manifest is a checksum inventory, not an independent signature; retain the Git commit when citing this edition.
