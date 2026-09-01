SELECT segment_code,function_code,COUNT(*) AS workers,SUM(annual_cost) AS annual_loaded_cost FROM worker GROUP BY segment_code,function_code ORDER BY segment_code,function_code;
