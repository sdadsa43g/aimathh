"""Physics layer: units, constants, dimensional analysis, domain plugins."""

from aimathh.physics.units import get_registry, parse_quantity, convert, UnitError
from aimathh.physics.constants import get_constant, list_constants, CODATA_VERSION
from aimathh.physics.dimensional import check_equation, DimensionalReport
from aimathh.physics.domains import DomainPlugin, get_domain_registry, DomainRegistry

__all__ = [
    "get_registry",
    "parse_quantity",
    "convert",
    "UnitError",
    "get_constant",
    "list_constants",
    "CODATA_VERSION",
    "check_equation",
    "DimensionalReport",
    "DomainPlugin",
    "get_domain_registry",
    "DomainRegistry",
]
