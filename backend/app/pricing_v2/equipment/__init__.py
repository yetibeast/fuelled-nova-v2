"""Equipment intelligence pipeline — parsing, alias resolution, identity management."""

from app.pricing_v2.equipment.parsing import CompoundParseResult, parse_compound_description
from app.pricing_v2.equipment.aliases import normalize_manufacturer, normalize_model

__all__ = [
    "CompoundParseResult",
    "parse_compound_description",
    "normalize_manufacturer",
    "normalize_model",
]
