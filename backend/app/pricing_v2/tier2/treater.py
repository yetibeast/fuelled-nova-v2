"""Treater family — heater-treater (sweet/sour) and electrostatic.

RCN scales by contactor diameter (inches). Depreciation follows a
flatter mid-life curve than dehydrators — see `treater` curve in
rcn_engine/depreciation.py.

Calibration locked 2026-05-26:
  96" sour heater-treater newbuild RCN = $750k CAD mid
  electrostatic 120"+ → Mega bracket and bypasses sour multiplier
  (electrostatic internals break emulsions; not sour-rated the same way)
"""
from __future__ import annotations

from typing import Literal

TreaterVariant = Literal["heater_treater", "electrostatic", "generic"]

TREATER_MATCH_TERMS = (
    "treater",
    "heater treater",
    "heater-treater",
    "electrostatic",
)


def classify_treater(text: str) -> TreaterVariant:
    t = text.lower()
    if "electrostatic" in t:
        return "electrostatic"
    if "heater treater" in t or "heater-treater" in t:
        return "heater_treater"
    return "generic"
