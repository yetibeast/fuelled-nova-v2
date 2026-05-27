"""RCN v2 engine — ported from fuelled-nova V1.

Public API:
    calculate_rcn(category, specs) -> RCNResult
    compute_base_rcn(category_key, specs) -> (scaled_rcn, quality, has_size)
    normalize_category(category) -> str
"""

from .calculator import RCNResult, calculate_rcn
from .rcn_tables import (
    RCNInput,
    compute_base_rcn,
    normalize_category,
)

__all__ = [
    "RCNInput",
    "RCNResult",
    "calculate_rcn",
    "compute_base_rcn",
    "normalize_category",
]
