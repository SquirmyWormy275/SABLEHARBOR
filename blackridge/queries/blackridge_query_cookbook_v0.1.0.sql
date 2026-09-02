-- Blackridge query cookbook v0.1.0
-- Seventy-five documented, executable public-safe analytical queries.

-- Q01: Find every record linked to haul truck BRG-HT-017.
SELECT * FROM haul_cycle_detail WHERE truck_id='BRG-HT-017' ORDER BY load_at LIMIT 25;

-- Q02: Trace a serialized component through hosts and time.
SELECT * FROM exclusive_assignment WHERE resource_type='COMPONENT' AND resource_id='BRG-CMP-00004' ORDER BY starts_at;

-- Q03: Trace material movement from mine toward concentrate.
SELECT event_id,entity_id,event_at,state_from,state_to,quantity_milli FROM event_ledger WHERE domain IN ('mine','plant') ORDER BY event_at LIMIT 25;

-- Q04: Trace concentrate lots toward invoices and cash.
SELECT c.canonical_id concentrate_id,s.canonical_id shipment_id,f.canonical_id settlement_id,r.canonical_id cash_id FROM concentrate_lot c LEFT JOIN shipment_lot s ON s.id=c.id LEFT JOIN final_settlement f ON f.id=c.id LEFT JOIN cash_receipt r ON r.id=c.id LIMIT 25;

-- Q05: Reconcile AP subledger to its control balance.
SELECT period,subledger_minor,control_minor,difference_minor FROM subledger_reconciliation WHERE subledger='AP' ORDER BY period;

-- Q06: Reconcile inventory subledger to its control balance.
SELECT period,subledger_minor,control_minor,difference_minor FROM subledger_reconciliation WHERE subledger='INVENTORY' ORDER BY period;

-- Q07: Compare physical and system inventory representations.
SELECT canonical_id,quantity_milli,amount_minor,status,available_at FROM inventory_balance ORDER BY canonical_id LIMIT 25;

-- Q08: List employees and qualifications available on a date.
SELECT e.canonical_id employee_id,q.name qualification FROM employee e JOIN qualification q ON q.id=e.id WHERE e.available_at<='2015-05-18T23:59:59+00:00' LIMIT 25;

-- Q09: Find assets sharing a facility dependency.
SELECT a.canonical_id asset_id,f.canonical_id facility_id FROM asset a JOIN facility f ON f.id=((a.id-1)%275)+1 WHERE f.id=1 LIMIT 25;

-- Q10: Reconstruct Phase 4 commitments at the June approval cutoff.
SELECT canonical_id,name,amount_minor,available_at FROM commitment WHERE available_at<='2015-06-26T23:59:59+00:00' ORDER BY available_at;

-- Q11: Show source-system definitions of availability.
SELECT source_system,status,COUNT(*) records FROM asset GROUP BY source_system,status ORDER BY source_system;

-- Q12: Compare tracker status definitions and snapshots.
SELECT canonical_id tracker,name,status,available_at FROM tracker_snapshot ORDER BY id;

-- Q13: Find artifacts available by May 18.
SELECT canonical_id,name,available_at FROM document WHERE available_at<='2015-05-18T23:59:59+00:00' ORDER BY available_at LIMIT 25;

-- Q14: Find records not yet available on June 26.
SELECT event_id,domain,event_at,available_at FROM event_ledger WHERE event_at<='2015-06-26T23:59:59+00:00' AND available_at>'2015-06-26T23:59:59+00:00' ORDER BY event_at LIMIT 25;

-- Q15: Trace the October reconstruction window.
SELECT event_id,domain,entity_id,event_at,available_at FROM event_ledger WHERE event_at BETWEEN '2015-10-06T00:00:00+00:00' AND '2015-10-19T23:59:59+00:00' ORDER BY event_at LIMIT 25;

-- Q16: Review current and historical asset criticality evidence.
SELECT a.canonical_id,a.name,a.status,c.name asset_class,c.available_at FROM asset a JOIN asset_class c ON c.id=((a.id-1)%12)+1 LIMIT 25;

-- Q17: Identify stale declared critical-equipment entries.
SELECT canonical_id,name,status,available_at FROM asset WHERE available_at<'2015-06-01T00:00:00+00:00' ORDER BY available_at LIMIT 25;

-- Q18: Show inventory physically present but not available.
SELECT canonical_id,name,status,quantity_milli FROM inventory_balance WHERE quantity_milli>0 AND status<>'AVAILABLE' LIMIT 25;

-- Q19: Produce monthly trial balances.
SELECT * FROM vw_trial_balance_monthly ORDER BY period,account_code;

-- Q20: Produce monthly primary financial statements.
SELECT period,statement,line_code,amount_minor FROM financial_statement ORDER BY period,statement,line_code;

-- Q21: Run budget-versus-actual source comparison.
SELECT b.canonical_id budget,a.amount_minor actual_minor,b.amount_minor budget_minor,a.amount_minor-b.amount_minor variance_minor FROM budget_version b JOIN account a ON a.id=b.id ORDER BY b.id;

-- Q22: Run Phase 4 impairment and sensitivity inputs.
SELECT valuation_date,case_name,npv_minor,irr_bps,carrying_minor,recoverable_minor,impairment_minor FROM phase4_valuation;

-- Q23: Show causal precursors without oracle truth fields.
SELECT domain,state_from,state_to,COUNT(*) events,SUM(quantity_milli) quantity_milli FROM event_ledger WHERE event_at<'2015-10-06T00:00:00+00:00' GROUP BY domain,state_from,state_to ORDER BY domain;

-- Q24: Prove physical material metal and fuel conservation.
SELECT period,domain,opening_milli,inflow_milli,outflow_milli,closing_milli,opening_milli+inflow_milli-outflow_milli-closing_milli residual FROM conservation_balance ORDER BY period,domain;

-- Q25: Prove truck operator and component exclusivity candidates.
SELECT resource_type,resource_id,COUNT(*) assignments,MIN(starts_at),MAX(ends_at) FROM exclusive_assignment GROUP BY resource_type,resource_id ORDER BY resource_type,resource_id LIMIT 25;

-- Q26: Profile person population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "person";

-- Q27: Profile facility population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "facility";

-- Q28: Profile asset population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "asset";

-- Q29: Profile serialized_component population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "serialized_component";

-- Q30: Profile item_master population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "item_master";

-- Q31: Profile vendor population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "vendor";

-- Q32: Profile contract population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "contract";

-- Q33: Profile purchase_order population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "purchase_order";

-- Q34: Profile purchase_order_line population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "purchase_order_line";

-- Q35: Profile goods_receipt population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "goods_receipt";

-- Q36: Profile supplier_invoice_line population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "supplier_invoice_line";

-- Q37: Profile work_order population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "work_order";

-- Q38: Profile labor_booking population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "labor_booking";

-- Q39: Profile inventory_transaction population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "inventory_transaction";

-- Q40: Profile haul_cycle population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "haul_cycle";

-- Q41: Profile plant_hourly population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "plant_hourly";

-- Q42: Profile journal_line population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "journal_line";

-- Q43: Profile document population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "document";

-- Q44: Profile governance_action population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "governance_action";

-- Q45: Profile source_system population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "source_system";

-- Q46: Profile identifier_map population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "identifier_map";

-- Q47: Profile unit_of_measure population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "unit_of_measure";

-- Q48: Profile department population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "department";

-- Q49: Profile cost_center population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "cost_center";

-- Q50: Profile warehouse population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "warehouse";

-- Q51: Profile stockpile population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "stockpile";

-- Q52: Profile pit population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "pit";

-- Q53: Profile phase population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "phase";

-- Q54: Profile bench population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "bench";

-- Q55: Profile mining_block population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "mining_block";

-- Q56: Profile ore_block_estimate population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "ore_block_estimate";

-- Q57: Profile asset_hierarchy population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "asset_hierarchy";

-- Q58: Profile component_installation_history population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "component_installation_history";

-- Q59: Profile downtime_event population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "downtime_event";

-- Q60: Profile backlog_snapshot population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "backlog_snapshot";

-- Q61: Profile operating_shift population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "operating_shift";

-- Q62: Profile dispatch_plan population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "dispatch_plan";

-- Q63: Profile fuel_consumption population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "fuel_consumption";

-- Q64: Profile laboratory_sample population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "laboratory_sample";

-- Q65: Profile assay_result population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "assay_result";

-- Q66: Profile recovery_calculation population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "recovery_calculation";

-- Q67: Profile offtake_contract population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "offtake_contract";

-- Q68: Profile shipment_lot population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "shipment_lot";

-- Q69: Profile capital_project population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "capital_project";

-- Q70: Profile wbs_element population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "wbs_element";

-- Q71: Profile journal population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "journal";

-- Q72: Profile meeting population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "meeting";

-- Q73: Profile action_item population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "action_item";

-- Q74: Profile application_system population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "application_system";

-- Q75: Profile shadow_artifact population and availability range.
SELECT COUNT(*) records,MIN(available_at) first_available,MAX(available_at) last_available FROM "shadow_artifact";
