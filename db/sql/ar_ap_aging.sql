WITH ar AS (
    SELECT COALESCE(SUM(i.total), 0) AS original_amount,
           COALESCE((SELECT SUM(cr.amount) FROM cash_receipt cr
                     WHERE cr.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
               AS settled_amount
    FROM invoice i
    WHERE i.generation_run_id IN (:actual_run_id, :generation_run_id)
), ar_gl AS (
    SELECT COALESCE(SUM(jl.debit - jl.credit), 0) AS open_amount
    FROM journal_line jl
    JOIN journal_entry je ON je.id = jl.entry_id
    JOIN account a ON a.id = jl.account_id
    WHERE a.code = '1100'
      AND je.state = 'POSTED'
      AND je.generation_run_id IN (:actual_run_id, :generation_run_id)
), ap AS (
    SELECT COALESCE(SUM(vb.amount), 0) AS original_amount,
           COALESCE((SELECT SUM(vp.amount) FROM vendor_payment vp
                     WHERE vp.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
               AS settled_amount
    FROM vendor_bill vb
    WHERE vb.generation_run_id IN (:actual_run_id, :generation_run_id)
), ap_gl AS (
    SELECT COALESCE(SUM(jl.credit - jl.debit), 0) AS open_amount
    FROM journal_line jl
    JOIN journal_entry je ON je.id = jl.entry_id
    JOIN account a ON a.id = jl.account_id
    WHERE a.code = '2100'
      AND je.state = 'POSTED'
      AND je.generation_run_id IN (:actual_run_id, :generation_run_id)
)
SELECT 'AR' AS ledger, original_amount, settled_amount, ar_gl.open_amount,
       ar_gl.open_amount - (original_amount - settled_amount) AS source_event_subledger_amount,
       0 AS unallocated_subledger_amount,
       ar_gl.open_amount AS current_bucket,
       0 AS days_31_60, 0 AS days_61_90, 0 AS days_over_90
FROM ar CROSS JOIN ar_gl
UNION ALL
SELECT 'AP' AS ledger, original_amount, settled_amount, ap_gl.open_amount,
       ap_gl.open_amount - (original_amount - settled_amount) AS source_event_subledger_amount,
       0 AS unallocated_subledger_amount,
       ap_gl.open_amount AS current_bucket,
       0 AS days_31_60, 0 AS days_61_90, 0 AS days_over_90
FROM ap CROSS JOIN ap_gl
ORDER BY ledger;
