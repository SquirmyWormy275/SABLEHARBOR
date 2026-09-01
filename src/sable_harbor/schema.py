"""Import all ORM domains so metadata and migrations see the complete schema."""

from sable_harbor.commercial import models as commercial
from sable_harbor.logistics import models as logistics
from sable_harbor.mining import models as mining
from sable_harbor.operations import models as operations
from sable_harbor.recovery import models as recovery
from sable_harbor.research import models as research

__all__ = ["commercial", "logistics", "mining", "operations", "recovery", "research"]
