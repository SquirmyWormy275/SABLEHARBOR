"""Exact optional anchors in an already selected immutable workpaper version."""

from .store import DomainError

FIELDS = frozenset({"text", "objective", "procedures", "conclusion"})
MAX_EXCERPT = 4000


def normalize_anchor(anchor, reviewed_version):
    """Offsets are Unicode code points, inclusive start and exclusive end.

    The caller retains its existing workpaper version/digest alongside the anchor.
    This function never selects another version or searches for a similar passage.
    """
    if not isinstance(anchor, dict) or set(anchor) != {"field", "start", "end", "excerpt"}:
        raise DomainError("An anchor requires exactly field, start, end and excerpt")
    field, start, end, excerpt = (anchor[k] for k in ("field", "start", "end", "excerpt"))
    if not isinstance(field, str) or field not in FIELDS:
        raise DomainError("Choose an allowed workpaper text field")
    target = reviewed_version.get(field) if isinstance(reviewed_version, dict) else None
    if (
        not isinstance(target, str)
        or not isinstance(excerpt, str)
        or type(start) is not int
        or type(end) is not int
        or not 0 <= start < end <= len(target)
        or not 1 <= len(excerpt) <= MAX_EXCERPT
    ):
        raise DomainError("Anchor requires bounded exact Unicode code-point offsets and text")
    try:
        target.encode("utf-8", errors="strict")
        excerpt.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise DomainError("Anchor text must contain valid Unicode scalar values") from error
    if target[start:end] != excerpt:
        raise DomainError("Anchor excerpt differs from the selected workpaper version")
    return {**anchor, "offset_unit": "UNICODE_CODEPOINT"}
