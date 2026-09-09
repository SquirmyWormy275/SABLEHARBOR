"""Testable reference boundaries; these functions are not a deployed IAM system."""

from datetime import date


def source_access(*, principal_tenant, source_tenant, plane, source_right, purpose_right):
    """No tenant, source or purpose grant is implied by a portal relationship."""
    return bool(
        principal_tenant
        and principal_tenant == source_tenant
        and plane == "client"
        and source_right is True
        and purpose_right is True
    )


def advisory_application(
    *, serving_j2, service_end=None, application_date=None, initiated_by_person=False
):
    if serving_j2:
        return "DENIED_SERVING_J2"
    if service_end is None:
        return "ORDINARY_NON_J2_HIRING"
    if not initiated_by_person or not application_date:
        return "DENIED_POST_SERVICE_INITIATIVE_NOT_ESTABLISHED"
    if date.fromisoformat(application_date) < date.fromisoformat(service_end):
        return "DENIED_APPLICATION_PRECEDES_COMPLETED_SERVICE"
    return "PERMITTED_POST_SERVICE_APPLICATION"


def carry_eligibility(
    *,
    profession,
    serving_j2=False,
    full_orientation_tour=False,
    qualifying_fellowship=False,
    judgment_years=0,
    operating_line_years=0,
    contact_leadership_years=0,
    substantive_contact_leadership=False,
):
    """Eligibility confers no allocation, vested right, expense or legal instrument."""
    if serving_j2:
        return "INELIGIBLE_SERVING_J2"
    if profession == "orientation":
        qualifies = full_orientation_tour and qualifying_fellowship
    elif profession == "judgment":
        qualifies = judgment_years >= 5 and operating_line_years >= 2
    elif profession == "contact":
        qualifies = contact_leadership_years >= 4 and substantive_contact_leadership
    elif profession in {"education", "j2-hq"}:
        return "OPEN_GATE_NOT_INFERRED"
    else:
        return "INELIGIBLE_NONQUALIFYING_SERVICE"
    return "ELIGIBLE_NO_ALLOCATION" if qualifies else "INELIGIBLE_SERVICE_GATE"


def orientation_role(*, former_orientation, has_line_authority):
    return not (former_orientation and has_line_authority)
