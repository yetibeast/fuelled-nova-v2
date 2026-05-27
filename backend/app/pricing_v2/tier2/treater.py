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

from dataclasses import dataclass
from typing import Literal

TreaterVariant = Literal["heater_treater", "electrostatic", "generic"]


@dataclass(frozen=True)
class RcnBand:
    """Three-point RCN bracket (low/mid/high) — values in CAD."""
    low: int
    mid: int
    high: int


# ── RCN BRACKETS — 2026 NEWBUILD CAD ─────────────────────────────
# Anchored 2026-05-26 by Curt against HubSpot 96" sour sold corpus:
#   96" sour heater-treater newbuild RCN = $750k CAD mid
#   → Large bracket × 1.15× sour = $598k–$1.09M sour mid ≈ matches the
#   $80-150k sold range at 11-16yr with the (replaced, flatter)
#   treater depreciation curve below.
#
# Brackets sized by contactor diameter (inches). RCN here is NEWBUILD
# at 2026 spec; the depreciation curve does the heavy lifting to land
# FMV against the heavily-aged Fuelled inventory.
_TREATER_BRACKETS: dict[str, RcnBand] = {
    "small":  RcnBand(    50_000,    100_000,    150_000),  # < 60"
    "medium": RcnBand(   200_000,    350_000,    500_000),  # 60–84"
    "large":  RcnBand(   520_000,    750_000,    950_000),  # 84–108"  (96" sour anchor)
    "mega":   RcnBand( 1_400_000,  1_800_000,  2_500_000),  # ≥ 108"   (electrostatic / 120"+)
}


def _bracket_for_diameter(diameter_in: float) -> str:
    if diameter_in < 60:
        return "small"
    if diameter_in < 84:
        return "medium"
    if diameter_in < 108:
        return "large"
    return "mega"


def treater_service_factor(service_description: str, *, variant: TreaterVariant) -> float:
    """Sour gas service carries a premium on RCN — heavier metallurgy +
    NACE compliance + monitoring. Sweet gas is the baseline (1.00).

    Electrostatic units bypass the sour multiplier entirely:
    electrostatic internals break emulsions and aren't sour-rated the
    same way as heater-treaters (typically lower-pressure separator
    metallurgy).
    """
    if variant == "electrostatic":
        return 1.00
    t = service_description.lower()
    if "sour" in t or "h2s" in t or "h₂s" in t:
        return 1.15
    return 1.00


def treater_rcn(*, variant: TreaterVariant, diameter_in: float) -> RcnBand:
    """Return RCN bracket (low/mid/high CAD) for a treater of given diameter.

    Electrostatic variant routes to the Mega bracket regardless of
    diameter — Fuelled corpus electrostatic units sit at 120"+ scale,
    and forcing Mega prevents under-pricing if the diameter parser
    misses on a low/missing value.
    """
    if variant == "electrostatic":
        return _TREATER_BRACKETS["mega"]
    return _TREATER_BRACKETS[_bracket_for_diameter(diameter_in)]

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
