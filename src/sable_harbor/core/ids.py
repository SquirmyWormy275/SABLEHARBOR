from uuid import UUID, uuid5

NAMESPACE = UUID("f52095cc-ea4e-5d9d-a2f6-5c64dcc3e25b")


def stable_id(kind: str, natural_key: str) -> str:
    """Return a deterministic public identity for a modeled object."""
    return str(uuid5(NAMESPACE, f"{kind}:{natural_key}"))
