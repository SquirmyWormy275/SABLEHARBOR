# Blackridge SQL Query Guide

Open `data/public/databases/blackridge_public_v0.1.0.sqlite3` with SQLite 3 and run queries from
`queries/blackridge_query_cookbook_v0.1.0.sql`. The entity-search FTS table supports canonical ID,
display-name, and source-system searches. High-volume facts should be queried in SQL or consumed
from the generated domain CSV extracts.

