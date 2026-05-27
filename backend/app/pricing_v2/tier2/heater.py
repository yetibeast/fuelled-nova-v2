"""Heater family — line heaters sized by BTU/hr × ANSI pressure class.

Scope: indirect-fired glycol-bath wellsite/battery line heaters. Heater
treaters live in the `treater` family. Frac/steam/heat-exchangers are
out of Tier 2 scope.

RCN scales by BTU/hr heat duty; pressure class is the load-bearing
second axis. Sour service and B149.3/ABSA code-stamp add multiplicative
premiums on RCN.

Anchor (Curt 2026-05-26 deep-dive): 2.0 MMBTU sour 1500# newbuild RCN
= $250k CAD mid. See `docs/tier2-calibration/heater-calibration-2026-05-26.md`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


HeaterVariant = Literal["line_heater", "generic"]

HEATER_MATCH_TERMS = (
    "line heater",
    "indirect heater",
    "glycol heater",
    "water bath",
    "bath heater",
    "inline heater",
    "crude heater",
    "wellsite heater",
)


@dataclass(frozen=True)
class RcnBand:
    """Three-point RCN bracket (low/mid/high) — values in CAD."""
    low: int
    mid: int
    high: int


def classify_heater(text: str) -> HeaterVariant:
    """Return heater variant from a listing's free text.

    `line_heater` matches the canonical wellsite/battery class. `generic`
    is the fallback for heater-family listings that didn't surface a
    canonical line-heater keyword. Upstream router is responsible for
    rejecting treaters/frac/steam/heat-exchangers before we get here.
    """
    t = text.lower()
    if any(term in t for term in (
        "line heater",
        "indirect heater",
        "glycol heater",
        "water bath",
        "bath heater",
        "inline heater",
        "crude heater",
        "wellsite heater",
    )):
        return "line_heater"
    return "generic"


# ── Parsing helpers ────────────────────────────────────────────────

_MMBTU_RE = re.compile(r"(\d+(?:\.\d+)?)\s*mmbtu", re.IGNORECASE)

# ANSI class words like "1500#" / "1500 ANSI" / "1500 RF" / "1500 RTJ".
# We also accept dual ratings ("2500/600#") — take the higher.
_ANSI_CLASS_RE = re.compile(
    r"(\d{3,5})\s*(?:#|ANSI|RTJ|RF|/(?:\d{3,5})\s*(?:#|ANSI|RTJ|RF))",
    re.IGNORECASE,
)
# Dual-rating pattern to also catch the second half: "2500/600#"
_DUAL_PAIR_RE = re.compile(r"(\d{3,5})\s*/\s*(\d{3,5})\s*#", re.IGNORECASE)
# PSI rating fallback when no ANSI class present
_PSI_RE = re.compile(r"(\d{2,5})\s*psi", re.IGNORECASE)


def parse_mmbtu(text: str, default: float = 1.5) -> tuple[float, bool]:
    """Extract BTU/hr heat duty in MMBTU from free text.

    Returns (mmbtu, was_parsed). Default 1.5 keeps the Medium bracket
    as the unknown-size fallback so missing-size doesn't auto-cheap.
    """
    m = _MMBTU_RE.search(text or "")
    if m:
        try:
            return float(m.group(1)), True
        except ValueError:
            pass
    return default, False


def parse_ansi_class(text: str) -> int | None:
    """Extract the highest pressure rating (in PSI or ANSI class).

    Logic:
    1. Find every `NNNN#` / `NNNN ANSI` / `NNNN RTJ` / `NNNN RF`
       occurrence, take the max.
    2. Also catch `NNNN/MMM#` dual ratings and take the higher half.
    3. If none found, fall back to `NNNN PSI`.
    4. Return None if no signal at all.
    """
    t = text or ""
    ratings: list[int] = []

    # Dual pairs first ("2500/600#"): catches both halves
    for m in _DUAL_PAIR_RE.finditer(t):
        try:
            ratings.append(int(m.group(1)))
            ratings.append(int(m.group(2)))
        except ValueError:
            pass

    # ANSI-class singletons
    for m in re.finditer(
        r"(\d{3,5})\s*(?:#|ANSI(?!\w)|RTJ|RF(?!\w))",
        t,
        re.IGNORECASE,
    ):
        try:
            ratings.append(int(m.group(1)))
        except ValueError:
            pass

    # PSI fallback if nothing else
    if not ratings:
        for m in _PSI_RE.finditer(t):
            try:
                ratings.append(int(m.group(1)))
            except ValueError:
                pass

    if not ratings:
        return None
    return max(ratings)


# ── RCN BRACKETS — 2026 NEWBUILD CAD ──────────────────────────────
# Locked 2026-05-26 by Curt after deep-dive calibration. Anchor:
# 2.0 MMBTU sour 1500# newbuild RCN = $250k CAD mid.
#
# Derivation: medium-mid × pressure(1500=×1.20) × sour(×1.15)
#   = $180k × 1.20 × 1.15 = $248.4k → $250k anchor matches.
#
# Bracket spans + sweet-base values per Curt:
#   Small      ≤ 1.0 MMBTU:  $45k /  $70k / $100k
#   Medium  1.0-2.0 MMBTU:  $110k / $180k / $250k
#   Large   2.0-3.5 MMBTU:  $220k / $320k / $430k
#   Industrial 3.5-7.5 MMBTU: $430k / $600k / $850k
#
# Validation against HubSpot sold corpus (10 sold rows):
#   8 of 10 land within ±35% of predicted FMV using these brackets +
#   the dedicated heater curve below; the 2 misses both go UNDER
#   (B149.3 / ABSA-registered units), which the +20% code-stamp
#   adder closes.
#
# Industrial bracket (>3.5 MMBTU) is weakly anchored — only 1 sold
# Aquatube unit in corpus. Flagged for Curt before scaling above
# 7.5 MMBTU.
_BTU_BRACKETS: dict[str, RcnBand] = {
    "small":      RcnBand( 45_000,  70_000, 100_000),  # ≤ 1.0 MMBTU
    "medium":     RcnBand(110_000, 180_000, 250_000),  # 1.0-2.0 MMBTU
    "large":      RcnBand(220_000, 320_000, 430_000),  # 2.0-3.5 MMBTU
    "industrial": RcnBand(430_000, 600_000, 850_000),  # 3.5-7.5 MMBTU
}


def _bracket_for_mmbtu(mmbtu: float) -> str:
    if mmbtu <= 1.0:
        return "small"
    if mmbtu <= 2.0:
        return "medium"
    if mmbtu <= 3.5:
        return "large"
    return "industrial"


def heater_rcn(*, mmbtu: float) -> RcnBand:
    """Return RCN bracket (low/mid/high CAD) at given BTU heat duty.

    Sweet-base values only — pressure / service / code-stamp adders
    are applied multiplicatively in `price_heater`.
    """
    return _BTU_BRACKETS[_bracket_for_mmbtu(mmbtu)]


# ── Multiplicative adders ───────────────────────────────────────────

def heater_pressure_adder(ansi: int | None) -> float:
    """Pressure-class multiplier on RCN.

    Buckets per Curt 2026-05-26 deep-dive:
        < 600 PSI  → 1.00 (baseline)
        < 1500 PSI → 1.10 (900/1500 wall, B149.3 considerations)
        < 2500 PSI → 1.20 (RTJ flanges, heavier metallurgy)
        ≥ 2500 PSI → 1.30 (forged body / special service)
    """
    if ansi is None:
        return 1.00
    if ansi < 600:
        return 1.00
    if ansi < 1500:
        return 1.10
    if ansi < 2500:
        return 1.20
    return 1.30


def heater_service_factor(service_description: str) -> float:
    """Sweet/sour service factor. Sour carries +15% on RCN for
    NACE-rated metallurgy / monitoring (same factor as dehy/treater)."""
    t = service_description.lower()
    if "sour" in t or "h2s" in t or "h₂s" in t:
        return 1.15
    return 1.00


_CODE_STAMP_TERMS = (
    "b149.3",
    "csa b149",
    "absa",
    "code stamp",
    "code-stamp",
    "code-stamped",
    "code stamped",
)


def heater_code_stamp_adder(text: str) -> float:
    """+20% RCN adder for B149.3 / ABSA-registered / code-stamped units.

    Deep-dive showed un-adjusted model under-predicted 1.25 MMBTU sour
    1500# B149.3 by 38%. Without this adder the calibration fails on
    the registered-class corpus.
    """
    t = (text or "").lower()
    if any(term in t for term in _CODE_STAMP_TERMS):
        return 1.20
    return 1.00


# Stub — implemented in the end-to-end step below.
def price_heater(listing: dict):  # noqa: D401
    raise NotImplementedError("price_heater implemented in step 4")
