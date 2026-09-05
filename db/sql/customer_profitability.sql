WITH invoice_totals AS (
    SELECT
        contract_id,
        generation_run_id,
        SUM(total) AS billings
    FROM invoice
    WHERE generation_run_id IN (:actual_run_id, :generation_run_id)
    GROUP BY contract_id, generation_run_id
),
recognition_totals AS (
    SELECT
        po.contract_id,
        rr.generation_run_id,
        SUM(rr.amount) AS recognized_revenue
    FROM revenue_recognition rr
    JOIN performance_obligation po
        ON po.id = rr.performance_obligation_id
        AND po.generation_run_id = rr.generation_run_id
    WHERE rr.generation_run_id IN (:actual_run_id, :generation_run_id)
    GROUP BY po.contract_id, rr.generation_run_id
)
SELECT
    c.customer_id,
    COALESCE(SUM(i.billings), 0) AS billings,
    COALESCE(SUM(r.recognized_revenue), 0) AS recognized_revenue
FROM customer_contract c
LEFT JOIN invoice_totals i
    ON i.contract_id = c.id
    AND i.generation_run_id = c.generation_run_id
LEFT JOIN recognition_totals r
    ON r.contract_id = c.id
    AND r.generation_run_id = c.generation_run_id
WHERE c.generation_run_id IN (:actual_run_id, :generation_run_id)
GROUP BY c.customer_id
ORDER BY c.customer_id;
