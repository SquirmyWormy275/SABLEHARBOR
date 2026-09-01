# Validation and reconciliation

Automated gates verify deterministic IDs, assumption schema, migrations, balanced/nonzero journals, posted immutability, reversals, period close, idempotence, actual/forecast periods, scenario results, canon states, causal subledger/GL flows, all named queries, workbooks, release checksums, and public safety.

Domain equations tested include:

- contract → invoice → deferred revenue → recognition → receipt;
- payroll/procurement/assets/debt source records → journal IDs;
- Red Wash feed tons × 2,000 × grade × recovery = produced pounds;
- opening/produced quantity − shipped quantity = closing quantity;
- waybill tons × route miles = ton-miles, with fuel and crew direct costs;
- Cradle feed × grade × recovery = recovered units and host share;
- Willow gates and Atlas authority constraints;
- aggregate trial-balance debits = credits;
- workbook database controls and release SHA-256 digests.

Local PostgreSQL was unavailable due Docker socket permissions; the configured CI job performs PostgreSQL 16 migration, standard generation, and validation.
