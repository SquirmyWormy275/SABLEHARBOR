SELECT batch_number,production_cost,pounds_u3o8,CASE WHEN pounds_u3o8=0 THEN NULL ELSE production_cost/pounds_u3o8 END AS cost_per_lb FROM mine_production_batch ORDER BY production_date;
