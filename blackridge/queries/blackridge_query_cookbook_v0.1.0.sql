-- Blackridge query cookbook v0.1.0
-- Every numbered query is executable against the public SQLite database.

-- Q01: Inspect account records with contemporaneous availability.
SELECT * FROM "account" ORDER BY 1 LIMIT 25;

-- Q02: Inspect action_item records with contemporaneous availability.
SELECT * FROM "action_item" ORDER BY 1 LIMIT 25;

-- Q03: Inspect actual_shift records with contemporaneous availability.
SELECT * FROM "actual_shift" ORDER BY 1 LIMIT 25;

-- Q04: Inspect application_system records with contemporaneous availability.
SELECT * FROM "application_system" ORDER BY 1 LIMIT 25;

-- Q05: Inspect artifact_manifest records with contemporaneous availability.
SELECT * FROM "artifact_manifest" ORDER BY 1 LIMIT 25;

-- Q06: Inspect assay_result records with contemporaneous availability.
SELECT * FROM "assay_result" ORDER BY 1 LIMIT 25;

-- Q07: Inspect asset records with contemporaneous availability.
SELECT * FROM "asset" ORDER BY 1 LIMIT 25;

-- Q08: Inspect asset_class records with contemporaneous availability.
SELECT * FROM "asset_class" ORDER BY 1 LIMIT 25;

-- Q09: Inspect asset_hierarchy records with contemporaneous availability.
SELECT * FROM "asset_hierarchy" ORDER BY 1 LIMIT 25;

-- Q10: Inspect asset_model records with contemporaneous availability.
SELECT * FROM "asset_model" ORDER BY 1 LIMIT 25;

-- Q11: Inspect assumption records with contemporaneous availability.
SELECT * FROM "assumption" ORDER BY 1 LIMIT 25;

-- Q12: Inspect backlog_snapshot records with contemporaneous availability.
SELECT * FROM "backlog_snapshot" ORDER BY 1 LIMIT 25;

-- Q13: Inspect bench records with contemporaneous availability.
SELECT * FROM "bench" ORDER BY 1 LIMIT 25;

-- Q14: Inspect blend_option records with contemporaneous availability.
SELECT * FROM "blend_option" ORDER BY 1 LIMIT 25;

-- Q15: Inspect budget_version records with contemporaneous availability.
SELECT * FROM "budget_version" ORDER BY 1 LIMIT 25;

-- Q16: Inspect building records with contemporaneous availability.
SELECT * FROM "building" ORDER BY 1 LIMIT 25;

-- Q17: Inspect calendar_date records with contemporaneous availability.
SELECT * FROM "calendar_date" ORDER BY 1 LIMIT 25;

-- Q18: Inspect canon_reference records with contemporaneous availability.
SELECT * FROM "canon_reference" ORDER BY 1 LIMIT 25;

-- Q19: Inspect capital_authorization records with contemporaneous availability.
SELECT * FROM "capital_authorization" ORDER BY 1 LIMIT 25;

-- Q20: Inspect capital_project records with contemporaneous availability.
SELECT * FROM "capital_project" ORDER BY 1 LIMIT 25;

-- Q21: Inspect cash_receipt records with contemporaneous availability.
SELECT * FROM "cash_receipt" ORDER BY 1 LIMIT 25;

-- Q22: Inspect close_task records with contemporaneous availability.
SELECT * FROM "close_task" ORDER BY 1 LIMIT 25;

-- Q23: Inspect commitment records with contemporaneous availability.
SELECT * FROM "commitment" ORDER BY 1 LIMIT 25;

-- Q24: Inspect communication_message records with contemporaneous availability.
SELECT * FROM "communication_message" ORDER BY 1 LIMIT 25;

-- Q25: Inspect component_installation_history records with contemporaneous availability.
SELECT * FROM "component_installation_history" ORDER BY 1 LIMIT 25;

-- Q26: Inspect concentrate_lot records with contemporaneous availability.
SELECT * FROM "concentrate_lot" ORDER BY 1 LIMIT 25;

-- Q27: Inspect construction_in_progress records with contemporaneous availability.
SELECT * FROM "construction_in_progress" ORDER BY 1 LIMIT 25;

-- Q28: Inspect contract records with contemporaneous availability.
SELECT * FROM "contract" ORDER BY 1 LIMIT 25;

-- Q29: Inspect contractor records with contemporaneous availability.
SELECT * FROM "contractor" ORDER BY 1 LIMIT 25;

-- Q30: Inspect control records with contemporaneous availability.
SELECT * FROM "control" ORDER BY 1 LIMIT 25;

-- Q31: Inspect control_execution records with contemporaneous availability.
SELECT * FROM "control_execution" ORDER BY 1 LIMIT 25;

-- Q32: Inspect cost_center records with contemporaneous availability.
SELECT * FROM "cost_center" ORDER BY 1 LIMIT 25;

-- Q33: Inspect crew records with contemporaneous availability.
SELECT * FROM "crew" ORDER BY 1 LIMIT 25;

-- Q34: Inspect currency records with contemporaneous availability.
SELECT * FROM "currency" ORDER BY 1 LIMIT 25;

-- Q35: Inspect customer records with contemporaneous availability.
SELECT * FROM "customer" ORDER BY 1 LIMIT 25;

-- Q36: Inspect data_quality_rule records with contemporaneous availability.
SELECT * FROM "data_quality_rule" ORDER BY 1 LIMIT 25;

-- Q37: Inspect dataset_version records with contemporaneous availability.
SELECT * FROM "dataset_version" ORDER BY 1 LIMIT 25;

-- Q38: Inspect decision records with contemporaneous availability.
SELECT * FROM "decision" ORDER BY 1 LIMIT 25;

-- Q39: Inspect decision_record records with contemporaneous availability.
SELECT * FROM "decision_record" ORDER BY 1 LIMIT 25;

-- Q40: Inspect department records with contemporaneous availability.
SELECT * FROM "department" ORDER BY 1 LIMIT 25;

-- Q41: Inspect depreciation_run records with contemporaneous availability.
SELECT * FROM "depreciation_run" ORDER BY 1 LIMIT 25;

-- Q42: Inspect discounted_cash_flow records with contemporaneous availability.
SELECT * FROM "discounted_cash_flow" ORDER BY 1 LIMIT 25;

-- Q43: Inspect dispatch_plan records with contemporaneous availability.
SELECT * FROM "dispatch_plan" ORDER BY 1 LIMIT 25;

-- Q44: Inspect document records with contemporaneous availability.
SELECT * FROM "document" ORDER BY 1 LIMIT 25;

-- Q45: Inspect document_version records with contemporaneous availability.
SELECT * FROM "document_version" ORDER BY 1 LIMIT 25;

-- Q46: Inspect downtime_event records with contemporaneous availability.
SELECT * FROM "downtime_event" ORDER BY 1 LIMIT 25;

-- Q47: Inspect dump_event records with contemporaneous availability.
SELECT * FROM "dump_event" ORDER BY 1 LIMIT 25;

-- Q48: Inspect employee records with contemporaneous availability.
SELECT * FROM "employee" ORDER BY 1 LIMIT 25;

-- Q49: Inspect entity_search_fts records with contemporaneous availability.
SELECT * FROM "entity_search_fts" ORDER BY 1 LIMIT 25;

-- Q50: Inspect entity_search_fts_config records with contemporaneous availability.
SELECT * FROM "entity_search_fts_config" ORDER BY 1 LIMIT 25;

-- Q51: Inspect entity_search_fts_content records with contemporaneous availability.
SELECT * FROM "entity_search_fts_content" ORDER BY 1 LIMIT 25;

-- Q52: Inspect entity_search_fts_data records with contemporaneous availability.
SELECT * FROM "entity_search_fts_data" ORDER BY 1 LIMIT 25;

-- Q53: Inspect entity_search_fts_docsize records with contemporaneous availability.
SELECT * FROM "entity_search_fts_docsize" ORDER BY 1 LIMIT 25;

-- Q54: Inspect entity_search_fts_idx records with contemporaneous availability.
SELECT * FROM "entity_search_fts_idx" ORDER BY 1 LIMIT 25;

-- Q55: Inspect environmental_permit records with contemporaneous availability.
SELECT * FROM "environmental_permit" ORDER BY 1 LIMIT 25;

-- Q56: Inspect equipment_assignment records with contemporaneous availability.
SELECT * FROM "equipment_assignment" ORDER BY 1 LIMIT 25;

-- Q57: Inspect event_ledger records with contemporaneous availability.
SELECT * FROM "event_ledger" ORDER BY 1 LIMIT 25;

-- Q58: Inspect evidence_artifact records with contemporaneous availability.
SELECT * FROM "evidence_artifact" ORDER BY 1 LIMIT 25;

-- Q59: Inspect facility records with contemporaneous availability.
SELECT * FROM "facility" ORDER BY 1 LIMIT 25;

-- Q60: Inspect failure_mode records with contemporaneous availability.
SELECT * FROM "failure_mode" ORDER BY 1 LIMIT 25;

-- Q61: Inspect feed_campaign records with contemporaneous availability.
SELECT * FROM "feed_campaign" ORDER BY 1 LIMIT 25;

-- Q62: Inspect final_settlement records with contemporaneous availability.
SELECT * FROM "final_settlement" ORDER BY 1 LIMIT 25;

-- Q63: Inspect financial_statement records with contemporaneous availability.
SELECT * FROM "financial_statement" ORDER BY 1 LIMIT 25;

-- Q64: Inspect financial_statement_value records with contemporaneous availability.
SELECT * FROM "financial_statement_value" ORDER BY 1 LIMIT 25;

-- Q65: Inspect fiscal_period records with contemporaneous availability.
SELECT * FROM "fiscal_period" ORDER BY 1 LIMIT 25;

-- Q66: Inspect fixed_asset records with contemporaneous availability.
SELECT * FROM "fixed_asset" ORDER BY 1 LIMIT 25;

-- Q67: Inspect forecast_version records with contemporaneous availability.
SELECT * FROM "forecast_version" ORDER BY 1 LIMIT 25;

-- Q68: Inspect fuel_consumption records with contemporaneous availability.
SELECT * FROM "fuel_consumption" ORDER BY 1 LIMIT 25;

-- Q69: Inspect generation_run records with contemporaneous availability.
SELECT * FROM "generation_run" ORDER BY 1 LIMIT 25;

-- Q70: Inspect geological_domain records with contemporaneous availability.
SELECT * FROM "geological_domain" ORDER BY 1 LIMIT 25;

-- Q71: Inspect goods_receipt records with contemporaneous availability.
SELECT * FROM "goods_receipt" ORDER BY 1 LIMIT 25;

-- Q72: Inspect governance_action records with contemporaneous availability.
SELECT * FROM "governance_action" ORDER BY 1 LIMIT 25;

-- Q73: Inspect haul_cycle records with contemporaneous availability.
SELECT * FROM "haul_cycle" ORDER BY 1 LIMIT 25;

-- Q74: Inspect hse_incident records with contemporaneous availability.
SELECT * FROM "hse_incident" ORDER BY 1 LIMIT 25;

-- Q75: Inspect identifier_map records with contemporaneous availability.
SELECT * FROM "identifier_map" ORDER BY 1 LIMIT 25;
