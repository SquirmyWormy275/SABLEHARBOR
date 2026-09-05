# Physical Conservation Report

Status: **PASS**

For each month of 2015, the database validates `opening + inflow - outflow = closing` for material,
contained copper, contained gold, and fuel with zero configured residual. Resource-overlap queries
also pass for exactly 27 haul trucks, 54 operators across two daily shifts, and 1,600 serialized
components. The corruption suite proves a one-unit closing-balance mutation fails validation.

