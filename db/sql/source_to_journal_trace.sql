SELECT source_type,source_id,id AS journal_id,entry_date,state FROM journal_entry WHERE generation_run_id IN (:actual_run_id,:generation_run_id) ORDER BY source_type,source_id,entry_date;
