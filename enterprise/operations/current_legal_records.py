"""Ordinary execution detail for existing current SOWs and workforce instruments."""

from decimal import Decimal as D

SOURCE = "enterprise/operations/source/current_legal_completion_2026_08.json"


def extend(source, tables):
    from industrial.planning.enterprise import load_anchor

    from .completed_period import read, stamp
    from .retention_payroll import awards_by_name

    detail = read(SOURCE)
    contract = {r["customer_id"]: r for r in tables["current_contracts"] if r["unit"] == "advisory"}
    people = {r["person_id"]: r for r in tables["people"]}
    customers = {r["customer_id"]: r for r in tables["current_customers"]}
    executions = []
    for party in detail["advisory"]:
        row = contract[party["customer_id"]]
        customers[party["customer_id"]]["name"] = party["legal_name"]
        executions.append(
            stamp(
                source,
                execution_id=row["contract_id"] + "-EXEC",
                contract_id=row["contract_id"],
                legal_entity="SHI",
                fee_usd=row["monthly_fee_usd"],
                shi_signatory_person_id=row["accountable_person_id"],
                shi_signatory_name=people[row["accountable_person_id"]]["name"],
                authority_ref=row["contract_id"] + "-AUTH",
                invoice_id=row["contract_id"] + "-INV-202608",
                delivery_evidence_id=row["contract_id"] + "-PERFORM-202608-EVIDENCE",
                **party,
                **detail["advisory_execution"],
            )
        )
    awards = awards_by_name()
    employees = {r["name"]: r for r in tables["people"]}
    bonus = {
        r["employee_name"]: r
        for r in tables["retention_payroll_ytd"]
        if r["payment_kind"] == "RETENTION"
    }
    retention = []
    for name, half in awards.items():
        person, payment = employees[name], bonus[name]
        retention.append(
            stamp(
                source,
                execution_id="SH-RETENTION-EXEC-" + person["person_id"],
                person_id=person["person_id"],
                employee_name=name,
                legal_entity=person["legal_employer"],
                accepted_total_award_usd=str(half * 2),
                first_gross_installment_usd=str(half),
                second_gross_installment_usd=str(half),
                employee_signature_name=name,
                employer_record_signatory_name=people["P033"]["name"],
                payroll_workpaper_event_id=payment["event_id"],
                source_payment_id="RETENTION-PAYMENT",
                payment_ref=payment["payment_ref"],
                employee_net_usd=payment["employee_net_usd"],
                employee_withholding_usd=payment["employee_withholding_usd"],
                signature_state="NEWLY_AUTHORED_SYNTHETIC_ACCEPTANCE_EXISTING_INSTRUMENT",
                **detail["retention"],
            )
        )
    deliveries = []
    descriptions = {
        1: "Nora controls ARU; Fred transfers records without directing employees.",
        2: "Tessa reviews remembered commitments against the customer contract register.",
        3: "Property index preserves leased equipment and customer-property ownership.",
        4: "Qualified mechanical inspection controls release; owner pressure does not.",
        5: "Controller owns claims and disputed AR; allowance is not customer forgiveness.",
        6: "Expansion lessons inform current review without creating capital commitments.",
        7: "Ordinary industrial freight does not authorize finished-uranium carriage.",
        8: "Nora receives unresolved security terms and instrument-specific release questions.",
    }

    for row in load_anchor():
        if (
            row["entity"] == "ARU_GROUP"
            and int(row["year"]) == 2026
            and 1 <= int(row["month"]) <= 8
            and row["source_id"] == "TOLMAN-CONSULTING"
            and row["account"] == "1000"
        ):
            month = int(row["month"])
            deliveries.append(
                stamp(
                    source,
                    delivery_id=f"SH-TOLMAN-DELIVERY-2026{month:02}",
                    event_period=f"2026-{month:02}",
                    legal_entity="ARU",
                    delivered_on=row["effective_period_end"],
                    accepted_on=row["effective_period_end"],
                    paid_on=row["effective_period_end"],
                    source_journal_id=row["journal_id"],
                    source_id=row["source_id"],
                    amount_usd=str(-D(row["signed_usd"])),
                    evidence_summary=descriptions[month],
                    acceptance_state_of_service="NEWLY_AUTHORED_SYNTHETIC_ACCEPTED_COMPLETED_MONTH",
                    **detail["consultancy"],
                )
            )
            deliveries[-1]["effective_period"] = f"2026-{month:02}"
    tables.update(
        advisory_execution=executions,
        retention_execution=retention,
        consultancy_delivery=deliveries,
    )


def validate(tables):
    from .completed_period import SOURCE as PERIOD_SOURCE
    from .completed_period import read

    rebuilt = dict(tables)
    # A copy of customer rows prevents the source check from repairing the caller's names.
    rebuilt["current_customers"] = [dict(r) for r in tables["current_customers"]]
    extend(read(PERIOD_SOURCE), rebuilt)
    metadata = {
        "available_at",
        "recorded_at",
        "repository_source_commit",
        "repository_source_available_at",
        "publication_state",
        "publishable_source_snapshot",
        "declared_available_at",
        "declared_available_precision",
        "declared_recorded_at",
        "authored_day",
    }
    for name in ("advisory_execution", "retention_execution", "consultancy_delivery"):
        actual = [{k: v for k, v in r.items() if k not in metadata} for r in tables[name]]
        expected = [{k: v for k, v in r.items() if k not in metadata} for r in rebuilt[name]]
        if actual != expected:
            raise ValueError(
                "Current legal execution differs from accepted scope/source population"
            )
    original = {r["customer_id"]: r["name"] for r in tables["current_customers"]}
    if any(original[r["customer_id"]] != r["name"] for r in rebuilt["current_customers"]):
        raise ValueError("Current legal party name does not reconcile")
    return {
        "advisory_sows": len(tables["advisory_execution"]),
        "retention_instruments": len(tables["retention_execution"]),
        "consultancy_completed_months": len(tables["consultancy_delivery"]),
    }
