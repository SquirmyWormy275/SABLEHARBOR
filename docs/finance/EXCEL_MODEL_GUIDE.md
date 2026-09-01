# Excel model guide

Run `shfin workbooks` or `make workbooks` after generating the standard SQLite database. The command produces the six named v0.1 workbooks under `workbooks/outputs/`.

Each sheet contains scenario, as-of date, seed, source-commit reference, and database-derived rows. Check sheets expose database controls and formulas. Workbooks use no external workbook links and are structurally reopened by the test suite.

Excel forbids `/` in sheet names and limits names to 31 characters. Required logical labels such as `ARU/BS&T` use `ARU-BS&T`; unusually long labels are shortened without changing their meaning. Generated `.xlsx` files are ignored by default and are release artifacts rather than systems of record.
