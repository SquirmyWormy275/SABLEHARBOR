# PostgreSQL Compatibility Report

The PostgreSQL v16 DDL contains 303 parser-recognized statements and passes local PostgreSQL AST
parsing. Pull-request CI provisions PostgreSQL 16 and executes the complete DDL with
`ON_ERROR_STOP=1`. GitHub Actions run `33585301219` passed that deployment on Python 3.11, 3.12,
and 3.13 jobs. Local Docker execution was unavailable because this user cannot access the Docker
daemon; the hosted PostgreSQL 16 service supplied the clean execution environment instead.
