-- PostgreSQL-compatible Blackridge schema v0.1.0.
CREATE TABLE "account" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "action_item" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "actual_shift" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "application_system" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "artifact_manifest" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "assay_result" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "asset" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "asset_class" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "asset_hierarchy" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "asset_model" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "assumption" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "backlog_snapshot" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "bench" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "blend_option" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "budget_version" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "building" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "calendar_date" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "canon_reference" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "capital_authorization" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "capital_project" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "cash_receipt" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "close_task" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "commitment" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "communication_message" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "component_installation_history" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "concentrate_lot" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE conservation_balance (
        id INTEGER PRIMARY KEY, period TEXT NOT NULL, domain TEXT NOT NULL,
        opening_milli INTEGER NOT NULL, inflow_milli INTEGER NOT NULL,
        outflow_milli INTEGER NOT NULL, closing_milli INTEGER NOT NULL,
        tolerance_milli INTEGER NOT NULL DEFAULT 0, UNIQUE(period, domain));
CREATE TABLE "construction_in_progress" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "contract" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "contractor" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "control" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "control_execution" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "cost_center" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "crew" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "currency" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "customer" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "data_quality_rule" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "dataset_version" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "decision" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "decision_record" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "department" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "depreciation_run" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "discounted_cash_flow" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "dispatch_plan" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "document" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "document_version" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "downtime_event" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "dump_event" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "employee" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "environmental_permit" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "equipment_assignment" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE event_ledger (
        id INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, domain TEXT NOT NULL,
        entity_id TEXT NOT NULL, event_at TEXT NOT NULL, available_at TEXT NOT NULL,
        state_from TEXT, state_to TEXT NOT NULL, quantity_milli INTEGER NOT NULL DEFAULT 0,
        source_system TEXT NOT NULL);
CREATE TABLE "evidence_artifact" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE exclusive_assignment (
        id INTEGER PRIMARY KEY, resource_type TEXT NOT NULL, resource_id TEXT NOT NULL,
        assignment_id TEXT NOT NULL UNIQUE, starts_at TEXT NOT NULL, ends_at TEXT NOT NULL,
        location_id TEXT NOT NULL, CHECK(starts_at < ends_at));
CREATE TABLE "facility" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "failure_mode" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "feed_campaign" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "final_settlement" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE financial_statement (
        id INTEGER PRIMARY KEY, period TEXT NOT NULL, statement TEXT NOT NULL,
        line_code TEXT NOT NULL, amount_minor INTEGER NOT NULL,
        UNIQUE(period, statement, line_code));
CREATE TABLE "financial_statement_value" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "fiscal_period" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "fixed_asset" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "forecast_version" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "fuel_consumption" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "generation_run" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "geological_domain" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "goods_receipt" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "governance_action" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "haul_cycle" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE haul_cycle_detail (
        haul_cycle_id INTEGER PRIMARY KEY REFERENCES haul_cycle(id),
        truck_id TEXT NOT NULL, operator_id TEXT NOT NULL,
        origin_location TEXT NOT NULL, destination_location TEXT NOT NULL,
        load_at TEXT NOT NULL, dump_at TEXT NOT NULL, CHECK(load_at < dump_at));
CREATE TABLE "hse_incident" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "identifier_map" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "impairment_calculation" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "impairment_scenario" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "interface" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "inventory_balance" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "inventory_reservation" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "inventory_transaction" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "item_master" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "journal" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "journal_line" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE journal_line_detail (
        id INTEGER PRIMARY KEY, journal_id TEXT NOT NULL, period TEXT NOT NULL,
        account_code TEXT NOT NULL, debit_minor INTEGER NOT NULL, credit_minor INTEGER NOT NULL,
        source_ref TEXT NOT NULL, CHECK (debit_minor >= 0 AND credit_minor >= 0));
CREATE TABLE "kpi_definition" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "kpi_observation" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "labor_booking" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "laboratory_sample" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "ledger" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "legal_entity" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "lineage_edge" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "load_event" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "location" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "maintenance_notification" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "meeting" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "meeting_attendee" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "meter_reading" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "mine_plan_version" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "mining_block" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "offtake_contract" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "oil_sample" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "operating_area" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "operating_shift" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "operating_unit" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "operator_assignment" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "ore_block_estimate" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "organization" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "payment" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "payroll_entry" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "payroll_run" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "person" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "phase" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE phase4_valuation (
        valuation_date TEXT PRIMARY KEY, case_name TEXT NOT NULL, cash_flow_minor INTEGER NOT NULL,
        discount_bps INTEGER NOT NULL, npv_minor INTEGER NOT NULL, irr_bps INTEGER NOT NULL,
        carrying_minor INTEGER NOT NULL, recoverable_minor INTEGER NOT NULL,
        impairment_minor INTEGER NOT NULL);
CREATE TABLE "physical_progress" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "pit" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "plant_hourly" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "plant_unit" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "position" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "position_assignment" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "process_mass_balance" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "production_actual" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "purchase_order" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "purchase_order_line" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE purchase_order_line_link (
        line_id INTEGER PRIMARY KEY REFERENCES purchase_order_line(id),
        purchase_order_id INTEGER NOT NULL REFERENCES purchase_order(id));
CREATE TABLE "purchase_requisition" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "qualification" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "recovery_calculation" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "reorder_policy" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "repairable_pool_status" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "report_definition" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "room" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "scheduled_shift" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "security_zone" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "sensor_reading" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "serialized_component" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "shadow_artifact" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "shipment_lot" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "snapshot_cutoff" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "source_system" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "stockout_event" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "stockpile" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "stockpile_movement" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "storage_location" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE subledger_reconciliation (
        period TEXT NOT NULL, subledger TEXT NOT NULL, subledger_minor INTEGER NOT NULL,
        control_minor INTEGER NOT NULL, difference_minor INTEGER NOT NULL,
        PRIMARY KEY(period, subledger), CHECK(difference_minor = subledger_minor-control_minor));
CREATE TABLE "supplier_invoice" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "supplier_invoice_line" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "tracker_snapshot" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "training_completion" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "trial_balance" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "unit_of_measure" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "validation_result" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "vendor" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "warehouse" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "wbs_element" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE TABLE "work_order" (
            id INTEGER PRIMARY KEY, canonical_id TEXT NOT NULL UNIQUE,
            immutable_uuid TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            status TEXT NOT NULL, event_at TEXT, recorded_at TEXT,
            available_at TEXT, amount_minor INTEGER NOT NULL DEFAULT 0,
            quantity_milli INTEGER NOT NULL DEFAULT 0, source_system TEXT NOT NULL,
            provenance TEXT NOT NULL);
CREATE INDEX "ix_account_available" ON "account"(available_at);
CREATE INDEX "ix_action_item_available" ON "action_item"(available_at);
CREATE INDEX "ix_actual_shift_available" ON "actual_shift"(available_at);
CREATE INDEX "ix_application_system_available" ON "application_system"(available_at);
CREATE INDEX "ix_artifact_manifest_available" ON "artifact_manifest"(available_at);
CREATE INDEX "ix_assay_result_available" ON "assay_result"(available_at);
CREATE INDEX "ix_asset_available" ON "asset"(available_at);
CREATE INDEX "ix_asset_class_available" ON "asset_class"(available_at);
CREATE INDEX "ix_asset_hierarchy_available" ON "asset_hierarchy"(available_at);
CREATE INDEX "ix_asset_model_available" ON "asset_model"(available_at);
CREATE INDEX ix_assignment_resource_time ON exclusive_assignment(resource_type,resource_id,starts_at,ends_at);
CREATE INDEX "ix_assumption_available" ON "assumption"(available_at);
CREATE INDEX "ix_backlog_snapshot_available" ON "backlog_snapshot"(available_at);
CREATE INDEX "ix_bench_available" ON "bench"(available_at);
CREATE INDEX "ix_blend_option_available" ON "blend_option"(available_at);
CREATE INDEX "ix_budget_version_available" ON "budget_version"(available_at);
CREATE INDEX "ix_building_available" ON "building"(available_at);
CREATE INDEX "ix_calendar_date_available" ON "calendar_date"(available_at);
CREATE INDEX "ix_canon_reference_available" ON "canon_reference"(available_at);
CREATE INDEX "ix_capital_authorization_available" ON "capital_authorization"(available_at);
CREATE INDEX "ix_capital_project_available" ON "capital_project"(available_at);
CREATE INDEX "ix_cash_receipt_available" ON "cash_receipt"(available_at);
CREATE INDEX "ix_close_task_available" ON "close_task"(available_at);
CREATE INDEX "ix_commitment_available" ON "commitment"(available_at);
CREATE INDEX "ix_communication_message_available" ON "communication_message"(available_at);
CREATE INDEX "ix_component_installation_history_available" ON "component_installation_history"(available_at);
CREATE INDEX "ix_concentrate_lot_available" ON "concentrate_lot"(available_at);
CREATE INDEX "ix_construction_in_progress_available" ON "construction_in_progress"(available_at);
CREATE INDEX "ix_contract_available" ON "contract"(available_at);
CREATE INDEX "ix_contractor_available" ON "contractor"(available_at);
CREATE INDEX "ix_control_available" ON "control"(available_at);
CREATE INDEX "ix_control_execution_available" ON "control_execution"(available_at);
CREATE INDEX "ix_cost_center_available" ON "cost_center"(available_at);
CREATE INDEX "ix_crew_available" ON "crew"(available_at);
CREATE INDEX "ix_currency_available" ON "currency"(available_at);
CREATE INDEX "ix_customer_available" ON "customer"(available_at);
CREATE INDEX "ix_data_quality_rule_available" ON "data_quality_rule"(available_at);
CREATE INDEX "ix_dataset_version_available" ON "dataset_version"(available_at);
CREATE INDEX "ix_decision_available" ON "decision"(available_at);
CREATE INDEX "ix_decision_record_available" ON "decision_record"(available_at);
CREATE INDEX "ix_department_available" ON "department"(available_at);
CREATE INDEX "ix_depreciation_run_available" ON "depreciation_run"(available_at);
CREATE INDEX "ix_discounted_cash_flow_available" ON "discounted_cash_flow"(available_at);
CREATE INDEX "ix_dispatch_plan_available" ON "dispatch_plan"(available_at);
CREATE INDEX "ix_document_available" ON "document"(available_at);
CREATE INDEX "ix_document_version_available" ON "document_version"(available_at);
CREATE INDEX "ix_downtime_event_available" ON "downtime_event"(available_at);
CREATE INDEX "ix_dump_event_available" ON "dump_event"(available_at);
CREATE INDEX "ix_employee_available" ON "employee"(available_at);
CREATE INDEX "ix_environmental_permit_available" ON "environmental_permit"(available_at);
CREATE INDEX "ix_equipment_assignment_available" ON "equipment_assignment"(available_at);
CREATE INDEX "ix_evidence_artifact_available" ON "evidence_artifact"(available_at);
CREATE INDEX "ix_facility_available" ON "facility"(available_at);
CREATE INDEX "ix_failure_mode_available" ON "failure_mode"(available_at);
CREATE INDEX "ix_feed_campaign_available" ON "feed_campaign"(available_at);
CREATE INDEX "ix_final_settlement_available" ON "final_settlement"(available_at);
CREATE INDEX "ix_financial_statement_value_available" ON "financial_statement_value"(available_at);
CREATE INDEX "ix_fiscal_period_available" ON "fiscal_period"(available_at);
CREATE INDEX "ix_fixed_asset_available" ON "fixed_asset"(available_at);
CREATE INDEX "ix_forecast_version_available" ON "forecast_version"(available_at);
CREATE INDEX "ix_fuel_consumption_available" ON "fuel_consumption"(available_at);
CREATE INDEX "ix_generation_run_available" ON "generation_run"(available_at);
CREATE INDEX "ix_geological_domain_available" ON "geological_domain"(available_at);
CREATE INDEX "ix_goods_receipt_available" ON "goods_receipt"(available_at);
CREATE INDEX "ix_governance_action_available" ON "governance_action"(available_at);
CREATE INDEX "ix_haul_cycle_available" ON "haul_cycle"(available_at);
CREATE INDEX "ix_hse_incident_available" ON "hse_incident"(available_at);
CREATE INDEX "ix_identifier_map_available" ON "identifier_map"(available_at);
CREATE INDEX "ix_impairment_calculation_available" ON "impairment_calculation"(available_at);
CREATE INDEX "ix_impairment_scenario_available" ON "impairment_scenario"(available_at);
CREATE INDEX "ix_interface_available" ON "interface"(available_at);
CREATE INDEX "ix_inventory_balance_available" ON "inventory_balance"(available_at);
CREATE INDEX "ix_inventory_reservation_available" ON "inventory_reservation"(available_at);
CREATE INDEX "ix_inventory_transaction_available" ON "inventory_transaction"(available_at);
CREATE INDEX "ix_item_master_available" ON "item_master"(available_at);
CREATE INDEX "ix_journal_available" ON "journal"(available_at);
CREATE INDEX "ix_journal_line_available" ON "journal_line"(available_at);
CREATE INDEX "ix_kpi_definition_available" ON "kpi_definition"(available_at);
CREATE INDEX "ix_kpi_observation_available" ON "kpi_observation"(available_at);
CREATE INDEX "ix_labor_booking_available" ON "labor_booking"(available_at);
CREATE INDEX "ix_laboratory_sample_available" ON "laboratory_sample"(available_at);
CREATE INDEX "ix_ledger_available" ON "ledger"(available_at);
CREATE INDEX "ix_legal_entity_available" ON "legal_entity"(available_at);
CREATE INDEX "ix_lineage_edge_available" ON "lineage_edge"(available_at);
CREATE INDEX "ix_load_event_available" ON "load_event"(available_at);
CREATE INDEX "ix_location_available" ON "location"(available_at);
CREATE INDEX "ix_maintenance_notification_available" ON "maintenance_notification"(available_at);
CREATE INDEX "ix_meeting_attendee_available" ON "meeting_attendee"(available_at);
CREATE INDEX "ix_meeting_available" ON "meeting"(available_at);
CREATE INDEX "ix_meter_reading_available" ON "meter_reading"(available_at);
CREATE INDEX "ix_mine_plan_version_available" ON "mine_plan_version"(available_at);
CREATE INDEX "ix_mining_block_available" ON "mining_block"(available_at);
CREATE INDEX "ix_offtake_contract_available" ON "offtake_contract"(available_at);
CREATE INDEX "ix_oil_sample_available" ON "oil_sample"(available_at);
CREATE INDEX "ix_operating_area_available" ON "operating_area"(available_at);
CREATE INDEX "ix_operating_shift_available" ON "operating_shift"(available_at);
CREATE INDEX "ix_operating_unit_available" ON "operating_unit"(available_at);
CREATE INDEX "ix_operator_assignment_available" ON "operator_assignment"(available_at);
CREATE INDEX "ix_ore_block_estimate_available" ON "ore_block_estimate"(available_at);
CREATE INDEX "ix_organization_available" ON "organization"(available_at);
CREATE INDEX "ix_payment_available" ON "payment"(available_at);
CREATE INDEX "ix_payroll_entry_available" ON "payroll_entry"(available_at);
CREATE INDEX "ix_payroll_run_available" ON "payroll_run"(available_at);
CREATE INDEX "ix_person_available" ON "person"(available_at);
CREATE INDEX "ix_phase_available" ON "phase"(available_at);
CREATE INDEX "ix_physical_progress_available" ON "physical_progress"(available_at);
CREATE INDEX "ix_pit_available" ON "pit"(available_at);
CREATE INDEX "ix_plant_hourly_available" ON "plant_hourly"(available_at);
CREATE INDEX "ix_plant_unit_available" ON "plant_unit"(available_at);
CREATE INDEX "ix_position_assignment_available" ON "position_assignment"(available_at);
CREATE INDEX "ix_position_available" ON "position"(available_at);
CREATE INDEX "ix_process_mass_balance_available" ON "process_mass_balance"(available_at);
CREATE INDEX "ix_production_actual_available" ON "production_actual"(available_at);
CREATE INDEX "ix_purchase_order_available" ON "purchase_order"(available_at);
CREATE INDEX "ix_purchase_order_line_available" ON "purchase_order_line"(available_at);
CREATE INDEX "ix_purchase_requisition_available" ON "purchase_requisition"(available_at);
CREATE INDEX "ix_qualification_available" ON "qualification"(available_at);
CREATE INDEX "ix_recovery_calculation_available" ON "recovery_calculation"(available_at);
CREATE INDEX "ix_reorder_policy_available" ON "reorder_policy"(available_at);
CREATE INDEX "ix_repairable_pool_status_available" ON "repairable_pool_status"(available_at);
CREATE INDEX "ix_report_definition_available" ON "report_definition"(available_at);
CREATE INDEX "ix_room_available" ON "room"(available_at);
CREATE INDEX "ix_scheduled_shift_available" ON "scheduled_shift"(available_at);
CREATE INDEX "ix_security_zone_available" ON "security_zone"(available_at);
CREATE INDEX "ix_sensor_reading_available" ON "sensor_reading"(available_at);
CREATE INDEX "ix_serialized_component_available" ON "serialized_component"(available_at);
CREATE INDEX "ix_shadow_artifact_available" ON "shadow_artifact"(available_at);
CREATE INDEX "ix_shipment_lot_available" ON "shipment_lot"(available_at);
CREATE INDEX "ix_snapshot_cutoff_available" ON "snapshot_cutoff"(available_at);
CREATE INDEX "ix_source_system_available" ON "source_system"(available_at);
CREATE INDEX "ix_stockout_event_available" ON "stockout_event"(available_at);
CREATE INDEX "ix_stockpile_available" ON "stockpile"(available_at);
CREATE INDEX "ix_stockpile_movement_available" ON "stockpile_movement"(available_at);
CREATE INDEX "ix_storage_location_available" ON "storage_location"(available_at);
CREATE INDEX "ix_supplier_invoice_available" ON "supplier_invoice"(available_at);
CREATE INDEX "ix_supplier_invoice_line_available" ON "supplier_invoice_line"(available_at);
CREATE INDEX "ix_tracker_snapshot_available" ON "tracker_snapshot"(available_at);
CREATE INDEX "ix_training_completion_available" ON "training_completion"(available_at);
CREATE INDEX "ix_trial_balance_available" ON "trial_balance"(available_at);
CREATE INDEX "ix_unit_of_measure_available" ON "unit_of_measure"(available_at);
CREATE INDEX "ix_validation_result_available" ON "validation_result"(available_at);
CREATE INDEX "ix_vendor_available" ON "vendor"(available_at);
CREATE INDEX "ix_warehouse_available" ON "warehouse"(available_at);
CREATE INDEX "ix_wbs_element_available" ON "wbs_element"(available_at);
CREATE INDEX "ix_work_order_available" ON "work_order"(available_at);
CREATE TABLE entity_search_fts (
    canonical_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    source_system TEXT NOT NULL,
    search_document TSVECTOR GENERATED ALWAYS AS
      (to_tsvector('english', coalesce(canonical_id,'') || ' ' || coalesce(display_name,'') || ' ' || coalesce(source_system,''))) STORED
);
CREATE INDEX ix_entity_search_fts_document ON entity_search_fts USING GIN(search_document);
CREATE VIEW vw_master_entity_search AS SELECT canonical_id, immutable_uuid, name display_name, status, source_system FROM asset UNION ALL SELECT canonical_id,immutable_uuid,name,status,source_system FROM person UNION ALL SELECT canonical_id,immutable_uuid,name,status,source_system FROM vendor;
CREATE VIEW vw_phase4_impairment AS SELECT * FROM phase4_valuation;
CREATE VIEW vw_trial_balance_monthly AS SELECT period, account_code, SUM(debit_minor) debit_minor, SUM(credit_minor) credit_minor FROM journal_line_detail GROUP BY period,account_code;
