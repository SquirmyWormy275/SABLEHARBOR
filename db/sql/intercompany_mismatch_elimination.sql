WITH reciprocal_lines AS (
    SELECT CASE WHEN owner.code < counterparty.code THEN owner.code ELSE counterparty.code END
               AS entity_a,
           CASE WHEN owner.code < counterparty.code THEN counterparty.code ELSE owner.code END
               AS entity_b,
           fp.code AS period,
           a.code AS account_code,
           jl.debit,
           jl.credit
    FROM journal_line jl
    JOIN journal_entry je ON je.id = jl.entry_id
    JOIN accounting_book book ON book.id = je.book_id
    JOIN legal_entity owner ON owner.id = book.entity_id
    JOIN legal_entity counterparty ON counterparty.id = jl.counterparty_entity_id
    JOIN fiscal_period fp ON fp.id = je.period_id
    JOIN account a ON a.id = jl.account_id
    WHERE je.state = 'POSTED'
      AND je.source_type <> 'consolidation_elimination'
      AND je.generation_run_id IN (:actual_run_id, :generation_run_id)
), paired AS (
    SELECT entity_a,
           entity_b,
           period,
           SUM(CASE WHEN account_code = '1100' THEN debit - credit ELSE 0 END)
               AS receivable,
           SUM(CASE WHEN account_code IN ('2000', '2100') THEN credit - debit ELSE 0 END)
               AS payable,
           SUM(CASE WHEN account_code = '4090' THEN credit - debit ELSE 0 END)
               AS intercompany_revenue,
           SUM(CASE WHEN account_code = '6400' THEN debit - credit ELSE 0 END)
               AS intercompany_expense
    FROM reciprocal_lines
    GROUP BY entity_a, entity_b, period
)
SELECT entity_a,
       entity_b,
       period,
       receivable,
       payable,
       receivable - payable AS balance_sheet_mismatch,
       intercompany_revenue,
       intercompany_expense,
       intercompany_revenue - intercompany_expense AS income_statement_mismatch,
       ABS(receivable - payable) + ABS(intercompany_revenue - intercompany_expense)
           AS total_mismatch
FROM paired
ORDER BY period, entity_a, entity_b;
