SELECT
    v.code,
    v.name,
    COALESCE(SUM(vb.amount), 0) AS billed_spend
FROM vendor v
LEFT JOIN purchase_order po
    ON po.vendor_id = v.id
    AND po.generation_run_id = v.generation_run_id
LEFT JOIN vendor_bill vb
    ON vb.purchase_order_id = po.id
    AND vb.generation_run_id = po.generation_run_id
WHERE v.generation_run_id IN (:actual_run_id, :generation_run_id)
GROUP BY v.code, v.name
ORDER BY billed_spend DESC, v.code;
