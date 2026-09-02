# PostgreSQL Compatibility Report

The PostgreSQL v16 DDL contains 303 parser-recognized statements and passes local PostgreSQL AST
parsing. Pull-request CI provisions PostgreSQL 16 and executes the complete DDL with
`ON_ERROR_STOP=1`. Local Docker execution was unavailable because this user cannot access the
Docker daemon; the hosted CI service provides the independent execution environment instead.
