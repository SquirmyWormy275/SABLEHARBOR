WITH selected_values AS (
  SELECT metric_code, entity_code, period_code, SUM(amount) AS selected_amount
  FROM scenario_value
  WHERE generation_run_id IN (:calibration_run_id, :selected_generation_run_id)
  GROUP BY metric_code, entity_code, period_code
), comparison_values AS (
  SELECT metric_code, entity_code, period_code, SUM(amount) AS comparison_amount
  FROM scenario_value
  WHERE generation_run_id IN (:calibration_run_id, :comparison_generation_run_id)
  GROUP BY metric_code, entity_code, period_code
), comparison_keys AS (
  SELECT metric_code, entity_code, period_code FROM selected_values
  UNION
  SELECT metric_code, entity_code, period_code FROM comparison_values
)
SELECT
  comparison_keys.metric_code,
  comparison_keys.entity_code,
  comparison_keys.period_code,
  selected_values.selected_amount,
  comparison_values.comparison_amount,
  COALESCE(comparison_values.comparison_amount, 0)
    - COALESCE(selected_values.selected_amount, 0) AS comparison_variance
FROM comparison_keys
LEFT JOIN selected_values
  ON selected_values.metric_code = comparison_keys.metric_code
 AND selected_values.entity_code = comparison_keys.entity_code
 AND selected_values.period_code = comparison_keys.period_code
LEFT JOIN comparison_values
  ON comparison_values.metric_code = comparison_keys.metric_code
 AND comparison_values.entity_code = comparison_keys.entity_code
 AND comparison_values.period_code = comparison_keys.period_code
ORDER BY comparison_keys.metric_code, comparison_keys.entity_code, comparison_keys.period_code;
