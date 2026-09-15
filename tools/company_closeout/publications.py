"""Dated company publication successor using the preserved approved renderer.

The predecessor module's exact bytes are pinned by immutable finance evidence.
This entry point extends only its document population and retains the renderer,
artwork, PDF normalization and existing publication manifest schema.
"""

from tools.documents import build_controlled_publications as predecessor

COMPANY_DOCS = [
    ("docs/canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md", "docs/governance/publications/SH-COMPANY-DIRECTIONS-20260915_v1.2.0.pdf", "corporate"),
    ("docs/internal/company-closeout/INSPECTION_GUIDE.md", "docs/finance/publications/SH-COMPANY-INSPECTION-20260915_v1.0.0.pdf", "corporate"),
    ("docs/finance/evidence/company-closeout/SOVEREIGNTY_METHOD.md", "docs/finance/publications/SH-COMPANY-SOVEREIGNTY-20260915_v1.0.0.pdf", "corporate"),
    ("docs/finance/evidence/company-closeout/ADOPTED_PARENT_TAX.md", "docs/finance/publications/SH-COMPANY-PARENT-TAX-20260915_v1.0.0.pdf", "corporate"),
]


def main():
    previous = predecessor.DOCS
    try:
        predecessor.DOCS = [*previous, *COMPANY_DOCS]
        predecessor.main()
    finally:
        predecessor.DOCS = previous


if __name__ == "__main__":
    main()
