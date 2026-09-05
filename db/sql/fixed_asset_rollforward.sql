WITH depreciation AS (
    SELECT asset_id, SUM(amount) AS accumulated_depreciation
    FROM depreciation_record
    WHERE generation_run_id IN (:actual_run_id, :generation_run_id)
    GROUP BY asset_id
)
SELECT fa.entity_id,
       fa.asset_class,
       SUM(fa.cost) AS gross_cost,
       SUM(COALESCE(depreciation.accumulated_depreciation, 0))
           AS accumulated_depreciation,
       SUM(fa.cost - COALESCE(depreciation.accumulated_depreciation, 0))
           AS net_book_value
FROM fixed_asset fa
LEFT JOIN depreciation ON depreciation.asset_id = fa.id
WHERE fa.generation_run_id IN (:actual_run_id, :generation_run_id)
GROUP BY fa.entity_id, fa.asset_class
ORDER BY fa.entity_id, fa.asset_class;
