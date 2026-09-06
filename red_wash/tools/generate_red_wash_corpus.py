"""Compatibility entry point for the canonical Red Wash package builder.

All generation logic lives in :mod:`build_red_wash_package`. Keeping this thin
wrapper preserves older operator commands without maintaining a second schema.
"""

from __future__ import annotations

from build_red_wash_package import main

if __name__ == "__main__":
    raise SystemExit(main())
