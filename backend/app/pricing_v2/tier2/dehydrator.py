"""Dehydrator family — TEG / mole sieve / generic.

RCN scales by gas throughput (MMSCFD). Depreciation follows
dedicated dehydrator curve (see rcn_engine/depreciation.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DehydratorVariant = Literal["teg", "mole_sieve", "generic"]

DEHYDRATOR_MATCH_TERMS = (
    "dehydrator", "dehy", "teg", "triethylene glycol", "mole sieve", "molecular sieve",
)


@dataclass(frozen=True)
class RcnBand:
    """Three-point RCN bracket (low/mid/high) — values in CAD."""
    low: int
    mid: int
    high: int


# ── PLACEHOLDER RCN BRACKETS ───────────────────────────────────────
# Source: pending — Curt to calibrate against
# seeds/rcn_price_reference_seed_v2.xlsx + seeds/hubspot/all-records.csv
# before Chunk 2 closes. Numbers below are anchored on rough domain
# intuition only.
_TEG_BRACKETS: dict[str, RcnBand] = {
    "small":  RcnBand(50_000,  100_000, 150_000),    # < 5 MMSCFD
    "medium": RcnBand(150_000, 275_000, 400_000),    # 5–25 MMSCFD
    "large":  RcnBand(400_000, 700_000, 1_000_000),  # > 25 MMSCFD
}

# Mole sieve carries ~1.5× premium on glycol units (molecular sieve
# beds + heavier regen package). Placeholder multiplier.
_MOLE_SIEVE_PREMIUM = 1.5


def classify_dehydrator(text: str) -> DehydratorVariant:
    t = text.lower()
    if "teg" in t or "triethylene" in t or "glycol" in t:
        return "teg"
    if "mole sieve" in t or "molecular sieve" in t:
        return "mole_sieve"
    return "generic"


def _bracket_for_mmscfd(mmscfd: float) -> str:
    if mmscfd < 5:
        return "small"
    if mmscfd < 25:
        return "medium"
    return "large"


def dehydrator_service_factor(service_description: str) -> float:
    """Sour gas service carries a premium on RCN — heavier metallurgy +
    NACE compliance + monitoring. Sweet gas is the baseline (1.00).
    Placeholder multipliers — Curt to calibrate."""
    t = service_description.lower()
    if "sour" in t or "h2s" in t or "h₂s" in t:
        return 1.15
    return 1.00


def dehydrator_rcn(*, variant: DehydratorVariant, mmscfd: float) -> RcnBand:
    """Return RCN bracket (low/mid/high CAD) for a dehydrator at given throughput.

    Variant determines a premium multiplier; mmscfd determines the size bracket.
    """
    band = _TEG_BRACKETS[_bracket_for_mmscfd(mmscfd)]
    if variant == "mole_sieve":
        m = _MOLE_SIEVE_PREMIUM
        return RcnBand(
            low=int(round(band.low * m)),
            mid=int(round(band.mid * m)),
            high=int(round(band.high * m)),
        )
    # teg + generic share the TEG bracket; generic absent a TEG/MS signal
    # defaults to the same base table.
    return band


def price_dehydrator(listing: dict) -> "Tier2Row":  # implemented in 2.3
    raise NotImplementedError
