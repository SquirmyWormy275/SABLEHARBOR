SELECT df.facility_number, df.commitment,
       COALESCE((SELECT SUM(dd.principal) FROM debt_draw dd
                 WHERE dd.facility_id = df.id
                   AND dd.generation_run_id IN (:actual_run_id, :generation_run_id)), 0) AS drawn,
       COALESCE((SELECT SUM(dr.principal) FROM debt_repayment dr
                 JOIN debt_draw dd ON dd.id = dr.debt_draw_id
                 WHERE dd.facility_id = df.id
                   AND dr.generation_run_id IN (:actual_run_id, :generation_run_id)), 0) AS repaid,
       COALESCE((SELECT SUM(dd.principal) FROM debt_draw dd
                 WHERE dd.facility_id = df.id
                   AND dd.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
       - COALESCE((SELECT SUM(dr.principal) FROM debt_repayment dr
                   JOIN debt_draw dd ON dd.id = dr.debt_draw_id
                   WHERE dd.facility_id = df.id
                     AND dr.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
           AS principal_outstanding,
       COALESCE((SELECT SUM(ia.amount) FROM interest_accrual ia
                 JOIN debt_draw dd ON dd.id = ia.debt_draw_id
                 WHERE dd.facility_id = df.id
                   AND ia.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
           AS accrued_interest,
       df.commitment
       - COALESCE((SELECT SUM(dd.principal) FROM debt_draw dd
                   WHERE dd.facility_id = df.id
                     AND dd.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
       + COALESCE((SELECT SUM(dr.principal) FROM debt_repayment dr
                   JOIN debt_draw dd ON dd.id = dr.debt_draw_id
                   WHERE dd.facility_id = df.id
                     AND dr.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
           AS availability,
       'PROVISIONAL_NO_LOCKED_THRESHOLD' AS covenant_status
FROM debt_facility df
WHERE df.generation_run_id IN (:actual_run_id, :generation_run_id)
UNION ALL
SELECT 'ACQUISITION_OPENING_CONTROL' AS facility_number, 0 AS commitment, 0 AS drawn, 0 AS repaid,
       COALESCE((SELECT SUM(jl.credit - jl.debit)
                 FROM journal_line jl
                 JOIN journal_entry je ON je.id = jl.entry_id
                 JOIN account a ON a.id = jl.account_id
                 WHERE a.code IN ('2500', '2510')
                   AND je.state = 'POSTED'
                   AND je.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
       - COALESCE((SELECT SUM(dd.principal) FROM debt_draw dd
                   WHERE dd.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
       + COALESCE((SELECT SUM(dr.principal) FROM debt_repayment dr
                   WHERE dr.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
       - COALESCE((SELECT SUM(ia.amount) FROM interest_accrual ia
                   WHERE ia.generation_run_id IN (:actual_run_id, :generation_run_id)), 0)
           AS principal_outstanding,
       0 AS accrued_interest, 0 AS availability,
       'PROVISIONAL_ACQUISITION_OPENING_BALANCE' AS covenant_status
ORDER BY facility_number;
