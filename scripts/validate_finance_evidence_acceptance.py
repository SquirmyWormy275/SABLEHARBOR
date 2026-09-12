#!/usr/bin/env python3
"""Verify exact owner-accepted finance artifacts without regenerating them."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/documents"))
from reader_library import evidence_acceptance
status = evidence_acceptance(ROOT, ROOT / "docs/finance/evidence/SH-FIN-HUMAN-001", "DRAFT")
assert status == "OWNER_ACCEPTED_EXACT_PACKET"
print("PASS: accepted Foundry Field packet and review artifacts match exact hashes")
