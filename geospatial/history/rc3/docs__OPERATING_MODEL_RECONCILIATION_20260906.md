# Operating-model reconciliation - rc3

The previous rc2 package was recovered from local commits after current main and active branches were inspected. It contained a mine-connector proposal and an unresolved acquisition date that had been overtaken by later approved decisions.

## Changes

- Retain approved Sweetwater anchor and Taylor name.
- Remove BST-SEG-002 and its Red Wash railway node from current layers and route membership. Preserve their prior state in `history/sable-harbor-rc2-superseded-mine-spur.zip` and `history/superseded_mine_connector.geojson`.
- Keep BST-SEG-001 as proposed, without inventing a validity start date for unknown physical track.
- Date the pre-Sable-Harbor acquisition scenario 2026-01-06, against closing 2026-01-07; do not infer the earlier ARU acquisition of BS&T.
- Record approved Taylor logistics separately from geometry. Truck last-mile route remains unlocated; the rejected railway line is not relabeled as a road.
- Preserve the unmerged ARU baseline snapshot at e385d29c4cd6fc49438e956027c8165102608e1b with its source state.
- Add a regression test preventing the superseded spur from returning to the current network.
- Remove an accidentally committed SQLite building journal.

The supplied NAILEX authority report was inspected for its provenance principles. Its audit-standard assertions are outside the geographic execution scope and were not adopted as GIS or legal authority.

## Material unresolved decision

Current main lore describes the original Evalon shop outside Pittsburgh. The handover selects Hazelwood inside Pittsburgh. Recommended resolution: Hazelwood is the later Willow/Evalon-lineage campus; the original leased shop remains a separate historical, unlocated asset. An occupancy/relocation date must be established before a dated historical map can show the later campus.

## Publication state

The recovered package records an earlier automatic-approval rejection of public GitHub publication. This execution preserves that boundary; it prepares local, committed, reviewable work without retrying the rejected public push.
