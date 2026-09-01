SELECT waybill_number,ton_miles,revenue,fuel_cost+crew_cost AS direct_cost,revenue-fuel_cost-crew_cost AS contribution_margin FROM waybill ORDER BY movement_date;
