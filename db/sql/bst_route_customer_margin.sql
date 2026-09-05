SELECT
    waybill_number,
    ton_miles,
    revenue,
    fuel_cost + crew_cost AS direct_cost,
    revenue - fuel_cost - crew_cost AS contribution_margin
FROM waybill w
JOIN legal_entity le ON le.id = w.entity_id
WHERE w.generation_run_id IN (:actual_run_id, :generation_run_id)
  AND le.code = 'BST'
ORDER BY w.movement_date, w.waybill_number;
