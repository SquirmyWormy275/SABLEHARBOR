# Blackridge Case Snapshot Guide

Run `python -m blackridge snapshot --cutoff YYYY-MM-DD`. Seven mandated cutoffs have been generated.
Rows are copied only when `available_at` is on or before the cutoff; journals and statements are
limited by fiscal period. The December snapshot alone contains year-end Phase 4 valuation results.

