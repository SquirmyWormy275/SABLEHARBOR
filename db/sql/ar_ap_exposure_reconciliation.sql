WITH report_date AS (
    SELECT MAX(entry_date) AS as_of_date
    FROM journal_entry
    WHERE generation_run_id IN (:actual_run_id, :generation_run_id)
), ar_documents AS (
    SELECT i.id,
           i.total AS original_amount,
           i.due_date,
           COALESCE(SUM(cr.amount), 0) AS settled_amount,
           i.total - COALESCE(SUM(cr.amount), 0) AS open_amount
    FROM invoice i
    LEFT JOIN cash_receipt cr
      ON cr.invoice_id = i.id
     AND cr.generation_run_id IN (:actual_run_id, :generation_run_id)
    WHERE i.generation_run_id IN (:actual_run_id, :generation_run_id)
    GROUP BY i.id, i.total, i.due_date
), ap_documents AS (
    SELECT vb.id,
           vb.amount AS original_amount,
           COALESCE(SUM(vp.amount), 0) AS settled_amount,
           vb.amount - COALESCE(SUM(vp.amount), 0) AS open_amount
    FROM vendor_bill vb
    LEFT JOIN vendor_payment vp
      ON vp.vendor_bill_id = vb.id
     AND vp.generation_run_id IN (:actual_run_id, :generation_run_id)
    WHERE vb.generation_run_id IN (:actual_run_id, :generation_run_id)
    GROUP BY vb.id, vb.amount
), gl AS (
    SELECT a.code,
           SUM(CASE WHEN a.code = '1100' THEN jl.debit - jl.credit
                    ELSE jl.credit - jl.debit END) AS open_amount
    FROM journal_line jl
    JOIN journal_entry je ON je.id = jl.entry_id
    JOIN account a ON a.id = jl.account_id
    WHERE a.code IN ('1100', '2100')
      AND je.state = 'POSTED'
      AND je.generation_run_id IN (:actual_run_id, :generation_run_id)
    GROUP BY a.code
), ar_document_journals AS (
    SELECT journal_entry_id
    FROM invoice
    WHERE generation_run_id IN (:actual_run_id, :generation_run_id)
      AND journal_entry_id IS NOT NULL
    UNION
    SELECT journal_entry_id
    FROM cash_receipt
    WHERE generation_run_id IN (:actual_run_id, :generation_run_id)
), ap_document_journals AS (
    SELECT journal_entry_id
    FROM vendor_bill
    WHERE generation_run_id IN (:actual_run_id, :generation_run_id)
    UNION
    SELECT journal_entry_id
    FROM vendor_payment
    WHERE generation_run_id IN (:actual_run_id, :generation_run_id)
), non_document_gl AS (
    SELECT a.code,
           SUM(CASE WHEN a.code = '1100' THEN jl.debit - jl.credit
                    ELSE jl.credit - jl.debit END) AS open_amount
    FROM journal_line jl
    JOIN journal_entry je ON je.id = jl.entry_id
    JOIN account a ON a.id = jl.account_id
    WHERE a.code IN ('1100', '2100')
      AND je.state = 'POSTED'
      AND je.generation_run_id IN (:actual_run_id, :generation_run_id)
      AND ((a.code = '1100' AND NOT EXISTS (
             SELECT 1 FROM ar_document_journals document
             WHERE document.journal_entry_id = je.id
           ))
        OR (a.code = '2100' AND NOT EXISTS (
             SELECT 1 FROM ap_document_journals document
             WHERE document.journal_entry_id = je.id
           )))
    GROUP BY a.code
), ar AS (
    SELECT COALESCE(SUM(original_amount), 0) AS original_amount,
           COALESCE(SUM(settled_amount), 0) AS settled_amount,
           COALESCE(SUM(open_amount), 0) AS document_open_amount,
           COALESCE(SUM(CASE WHEN due_date >= report_date.as_of_date
                             THEN open_amount ELSE 0 END), 0) AS not_due_amount,
           COALESCE(SUM(CASE WHEN due_date < report_date.as_of_date
                             THEN open_amount ELSE 0 END), 0) AS past_due_amount,
           report_date.as_of_date
    FROM ar_documents CROSS JOIN report_date
    GROUP BY report_date.as_of_date
), ap AS (
    SELECT COALESCE(SUM(original_amount), 0) AS original_amount,
           COALESCE(SUM(settled_amount), 0) AS settled_amount,
           COALESCE(SUM(open_amount), 0) AS document_open_amount,
           report_date.as_of_date
    FROM ap_documents CROSS JOIN report_date
    GROUP BY report_date.as_of_date
)
SELECT 'AR' AS ledger,
       ar.as_of_date,
       ar.original_amount,
       ar.settled_amount,
       ar.document_open_amount,
       ar.not_due_amount,
       ar.past_due_amount,
       0 AS due_date_unavailable_amount,
       COALESCE(non_document_gl.open_amount, 0) AS non_document_source_event_amount,
       COALESCE(gl.open_amount, 0) AS gl_open_amount,
       COALESCE(gl.open_amount, 0) AS open_amount,
       COALESCE(gl.open_amount, 0)
         - ar.document_open_amount
         - COALESCE(non_document_gl.open_amount, 0)
           AS reconciliation_difference
FROM ar LEFT JOIN gl ON gl.code = '1100'
LEFT JOIN non_document_gl ON non_document_gl.code = '1100'
UNION ALL
SELECT 'AP' AS ledger,
       ap.as_of_date,
       ap.original_amount,
       ap.settled_amount,
       ap.document_open_amount,
       0 AS not_due_amount,
       0 AS past_due_amount,
       ap.document_open_amount AS due_date_unavailable_amount,
       COALESCE(non_document_gl.open_amount, 0) AS non_document_source_event_amount,
       COALESCE(gl.open_amount, 0) AS gl_open_amount,
       COALESCE(gl.open_amount, 0) AS open_amount,
       COALESCE(gl.open_amount, 0)
         - ap.document_open_amount
         - COALESCE(non_document_gl.open_amount, 0)
           AS reconciliation_difference
FROM ap LEFT JOIN gl ON gl.code = '2100'
LEFT JOIN non_document_gl ON non_document_gl.code = '2100'
ORDER BY ledger;
