WITH approved_time AS (
    SELECT pt.engagement_id,
           SUM(te.hours * te.bill_rate) AS approved_value
    FROM project_task pt
    JOIN time_entry te ON te.task_id = pt.id
    WHERE pt.generation_run_id IN (:actual_run_id, :generation_run_id)
      AND te.generation_run_id IN (:actual_run_id, :generation_run_id)
      AND te.status = 'APPROVED'
    GROUP BY pt.engagement_id
), billed AS (
    SELECT engagement_id, SUM(billed_amount) AS billed_amount
    FROM engagement_invoice_link
    WHERE generation_run_id IN (:actual_run_id, :generation_run_id)
    GROUP BY engagement_id
), costs AS (
    SELECT engagement_id, SUM(amount) AS cost_amount
    FROM project_cost
    WHERE generation_run_id IN (:actual_run_id, :generation_run_id)
    GROUP BY engagement_id
)
SELECT e.engagement_code AS engagement,
       COALESCE(b.billed_amount, 0) AS revenue,
       COALESCE(c.cost_amount, 0) AS cost,
       COALESCE(t.approved_value, 0) - COALESCE(b.billed_amount, 0) AS wip
FROM engagement e
LEFT JOIN approved_time t ON t.engagement_id = e.id
LEFT JOIN billed b ON b.engagement_id = e.id
LEFT JOIN costs c ON c.engagement_id = e.id
WHERE e.generation_run_id IN (:actual_run_id, :generation_run_id)
ORDER BY e.engagement_code;
