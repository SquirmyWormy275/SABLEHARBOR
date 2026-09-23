"""Dated company publication successor using the preserved approved renderer.

The predecessor module's exact bytes are pinned by immutable finance evidence.
This entry point extends only its document population and retains the renderer,
artwork, PDF normalization and existing publication manifest schema.
"""

from tools.documents import build_controlled_publications as predecessor
from tools.company_closeout.headquarters_publication import (
    SOURCE as HQ_SOURCE, PUBLICATION as HQ_PUBLICATION, render_with_artwork, bind_artwork,
)

COMPANY_DOCS = [
    (HQ_SOURCE, HQ_PUBLICATION, "corporate"),
    ("docs/internal/company-closeout/INSPECTION_GUIDE_v1.2.0.md", "docs/finance/publications/SH-COMPANY-INSPECTION-20260922_v1.2.0.pdf", "corporate"),
    ("docs/canon/J2_PERSONNEL_COMPLETION_2026-09-22.md", "docs/governance/publications/SH-J2-PERSONNEL-20260922_v1.0.0.pdf", "corporate"),
    ("docs/canon/ARU_ADMINISTRATIVE_COMPLETION_2026-09-22.md", "docs/legal/publications/SH-ARU-ADMIN-20260922_v1.0.0.pdf", "corporate"),
    ("docs/canon/ADVISORY_LEGAL_IMPLEMENTATION_2026-09-22.md", "docs/legal/publications/SH-ADVISORY-LEGAL-20260922_v1.0.0.pdf", "corporate"),
    ("docs/j2/alexandria/COMPANY_INFORMATION_POLICY_IMPLEMENTATION_2026-09-22.md", "docs/governance/publications/SH-INFORMATION-POLICY-20260922_v1.0.0.pdf", "corporate"),
    ("docs/internal/company-closeout/INSPECTION_GUIDE_v1.1.0.md", "docs/finance/publications/SH-COMPANY-INSPECTION-20260922_v1.1.0.pdf", "corporate"),
    ("docs/canon/ARU_SECURED_FINANCING_SUCCESSOR_2026-09-22.md", "docs/finance/publications/SH-ARU-SECURED-20260922_v1.0.0.pdf", "corporate"),
    ("docs/canon/CAPITAL_DESIGNATION_RIGHTS_2026-09-22.md", "docs/governance/publications/SH-CAP-RIGHTS-20260922_v1.0.0.pdf", "corporate"),
    ("docs/canon/CRADLE_HOST_TERMS_2026-09-22.md", "docs/legal/host-successor/publications/SH-HOST-B-ADOPTION-20260922_v1.0.0.pdf", "corporate"),
    ("docs/legal/host-successor/KGM_B_2026-09-22.md", "docs/legal/host-successor/publications/SH-HOST-KGM-B-20260922_v1.0.0.pdf", "corporate"),
    ("docs/legal/host-successor/DEMOTTE_B_2026-09-22.md", "docs/legal/host-successor/publications/SH-HOST-DEMOTTE-B-20260922_v1.0.0.pdf", "corporate"),
    ("docs/canon/COMPANY_CLOSEOUT_DIRECTIONS_2026-09-15.md", "docs/governance/publications/SH-COMPANY-DIRECTIONS-20260915_v1.2.0.pdf", "corporate"),
    ("docs/internal/company-closeout/INSPECTION_GUIDE.md", "docs/finance/publications/SH-COMPANY-INSPECTION-20260915_v1.0.0.pdf", "corporate"),
    ("docs/finance/evidence/company-closeout/SOVEREIGNTY_METHOD.md", "docs/finance/publications/SH-COMPANY-SOVEREIGNTY-20260915_v1.0.0.pdf", "corporate"),
    ("docs/finance/evidence/company-closeout/ADOPTED_PARENT_TAX.md", "docs/finance/publications/SH-COMPANY-PARENT-TAX-20260915_v2.0.0.pdf", "corporate"),
]


def main():
    previous = predecessor.DOCS
    original_render = predecessor.render_pdf
    try:
        predecessor.DOCS = [*previous, *COMPANY_DOCS]
        predecessor.render_pdf = render_with_artwork(original_render)
        predecessor.main()
        bind_artwork()
    finally:
        predecessor.DOCS = previous
        predecessor.render_pdf = original_render


if __name__ == "__main__":
    main()
