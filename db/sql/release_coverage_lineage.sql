SELECT source_type,COUNT(DISTINCT source_id) AS source_records,COUNT(*) AS journal_entries FROM journal_entry GROUP BY source_type ORDER BY source_type;
