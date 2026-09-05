"""Import all ORM domains so metadata and migrations see the complete schema."""

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from sable_harbor.accounting.models import Base
from sable_harbor.commercial import models as commercial
from sable_harbor.logistics import models as logistics
from sable_harbor.mining import models as mining
from sable_harbor.operations import models as operations
from sable_harbor.provenance import models as provenance
from sable_harbor.recovery import models as recovery
from sable_harbor.research import models as research


def _enforce_same_run_relationships() -> None:
    """Mirror generated parent ownership in every generated child relationship."""
    owned = {
        table.name: table
        for table in Base.metadata.tables.values()
        if "generation_run_id" in table.c and "id" in table.c
    }
    for table in owned.values():
        if not any(
            isinstance(constraint, UniqueConstraint)
            and tuple(column.name for column in constraint.columns) == ("id", "generation_run_id")
            for constraint in table.constraints
        ):
            table.append_constraint(
                UniqueConstraint(
                    "id",
                    "generation_run_id",
                    name=f"uq_{table.name}_id_generation_run_id",
                )
            )

    for child in owned.values():
        links = tuple(
            foreign_key
            for foreign_key in child.foreign_keys
            if foreign_key.column.table.name in owned
            and foreign_key.parent.name != "generation_run_id"
        )
        for foreign_key in links:
            parent = foreign_key.column.table
            name = f"fk_{child.name}_{foreign_key.parent.name}_same_run"
            if any(constraint.name == name for constraint in child.constraints):
                continue
            child.append_constraint(
                ForeignKeyConstraint(
                    [foreign_key.parent.name, "generation_run_id"],
                    [
                        f"{parent.name}.{foreign_key.column.name}",
                        f"{parent.name}.generation_run_id",
                    ],
                    name=name,
                )
            )


_enforce_same_run_relationships()

__all__ = [
    "commercial",
    "logistics",
    "mining",
    "operations",
    "provenance",
    "recovery",
    "research",
]
