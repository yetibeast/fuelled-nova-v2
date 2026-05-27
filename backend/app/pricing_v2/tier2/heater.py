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
from datetime import datetime
from typing import Literal

from ..rcn_engine.condition import (
    get_condition_factor,
    normalize_condition,
)
from ..rcn_engine.confidence import (
    W_DATA_FRESHNESS,
    W_DATA_VOLUME,
    W_RCN_SOURCE,
    W_SPECIFICITY,
    W_VARIANCE,
    calculate_confidence,
    classify_confidence,
)
from ..rcn_engine.depreciation import get_age_factor

from .column_spec import Tier2Row
from .reasoning import ReasoningTrail


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
# Dual-rating pattern: "2500/600#" / "2500#/600#" / "1500/1500 ANSI"
# Suffix (#, ANSI, RTJ, RF) may attach to either half or to the whole.
# We also accept a bare dual pair like "1500/1500" — corpus shows
# this format when followed by service/equipment context. Bare-form
# values must each be in the typical ANSI-class range to qualify
# (filters out year ranges, model numbers, etc.).
_DUAL_PAIR_RE = re.compile(
    r"(\d{3,5})\s*#?\s*/\s*(\d{3,5})\s*(?:#|ANSI|RTJ|RF)?",
    re.IGNORECASE,
)
# Plausible ANSI-class buckets. Listings outside this set are very
# likely model/year noise (e.g. "2018/2020") and get filtered out.
_PLAUSIBLE_ANSI_VALUES: frozenset[int] = frozenset(
    {150, 300, 600, 900, 1500, 2500, 3000, 5000, 10000}
)
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

    # Dual pairs first ("2500/600#" / "1500/1500"): catches both halves.
    # Bare dual pairs only count when BOTH halves are plausible ANSI
    # classes — otherwise model numbers like "JGK/4" or year ranges
    # would poison the parse.
    for m in _DUAL_PAIR_RE.finditer(t):
        try:
            left = int(m.group(1))
            right = int(m.group(2))
        except ValueError:
            continue
        suffix_present = bool(re.search(
            r"#|ANSI|RTJ|RF",
            m.group(0),
            re.IGNORECASE,
        ))
        if suffix_present or (
            left in _PLAUSIBLE_ANSI_VALUES and right in _PLAUSIBLE_ANSI_VALUES
        ):
            ratings.append(left)
            ratings.append(right)

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


# ── Output band derivation ─────────────────────────────────────────

# Price target band widths around the FMV mid. Same shape as dehy:
# floor sits tighter to mid (walk-away discipline), ceiling allows
# asking-anchor.
_PRICE_FLOOR_RATIO = 0.80
_PRICE_CEILING_RATIO = 1.20


def _price_targets(fmv_mid: float) -> tuple[int, int, int]:
    low = int(round(fmv_mid * _PRICE_FLOOR_RATIO))
    high = int(round(fmv_mid * _PRICE_CEILING_RATIO))
    mid = int(round(fmv_mid))
    return low, mid, high


def _pressure_label(ansi: int | None) -> str:
    if ansi is None:
        return "unknown"
    if ansi < 600:
        return f"{ansi} (< 600#)"
    if ansi < 1500:
        return f"{ansi} (600-1499#)"
    if ansi < 2500:
        return f"{ansi} (1500-2499#)"
    return f"{ansi} (≥2500#)"


# ── End-to-end pricing ─────────────────────────────────────────────

def price_heater(listing: dict) -> Tier2Row:
    """End-to-end pricing for a line-heater listing.

    Pulls together: variant classification → BTU + ANSI parse → RCN
    bracket → pressure adder → service factor → code-stamp adder →
    age + condition → combined factor → confidence → reasoning trail
    → spec-compliant row assembly.
    """
    description = str(listing.get("description") or listing.get("listing_name") or "")
    listing_name = str(listing.get("listing_name") or "")
    full_text = f"{listing_name} {description}".strip()

    # 1. Variant + size + pressure parse
    variant = classify_heater(full_text)
    mmbtu, mmbtu_parsed = parse_mmbtu(full_text)
    ansi = parse_ansi_class(full_text)

    # 2. Sweet-base RCN bracket from MMBTU
    rcn_base = heater_rcn(mmbtu=mmbtu)

    # 3. RCN multipliers (applied to base bracket)
    pressure_mult = heater_pressure_adder(ansi)
    service_f = float(heater_service_factor(full_text))
    code_stamp_mult = heater_code_stamp_adder(full_text)
    # Combined RCN-side premium — applied to the bracket so downstream
    # FMV math doesn't double-count. Mirrors dehy's "service folded
    # into RCN" pattern.
    rcn_premium = pressure_mult * service_f * code_stamp_mult
    rcn = RcnBand(
        low=int(round(rcn_base.low * rcn_premium)),
        mid=int(round(rcn_base.mid * rcn_premium)),
        high=int(round(rcn_base.high * rcn_premium)),
    )

    # 4. Age (year required; absent year, assume 10y)
    current_year = datetime.now().year
    raw_year = listing.get("year")
    has_year = raw_year is not None
    age_years: int = (current_year - int(raw_year)) if has_year else 10
    age_years = max(0, age_years)
    age_f = float(get_age_factor(age_years, "heater"))

    # 5. Condition
    raw_condition = listing.get("condition")
    has_condition = bool(raw_condition)
    condition_tier = (
        normalize_condition(raw_condition) if has_condition else normalize_condition(None)
    )
    cond_f = float(get_condition_factor(condition_tier))

    # 6. Combined factor (age × condition; service+pressure+codestamp
    # already folded into the RCN bracket above).
    combined = age_f * cond_f

    # 7. FMV mid
    fmv_mid = rcn.mid * combined

    # 8. Confidence (no comps in standalone run)
    conf = calculate_confidence(
        rcn_confidence=0.50,  # fallback-bracket source → mid-range
        comparable_count=0,
        comparable_cv=None,
        has_year=has_year,
        has_condition=has_condition,
        has_hours=False,
        has_size_param=mmbtu_parsed,
        data_age_days=0,
    )
    conf_class = classify_confidence(conf.composite)

    # 9. Methodology path — captures the load-bearing decisions
    bracket_name = _bracket_for_mmbtu(mmbtu)
    methodology_path = f"heater/{variant}/{bracket_name}-MMBTU"

    # 10. Reasoning trail
    trail = ReasoningTrail()
    trail.add(
        "Variant",
        f"{variant} (matched on description text)",
    )
    trail.add(
        "Heat duty",
        f"{mmbtu} MMBTU "
        f"({'parsed from text' if mmbtu_parsed else 'default — no size in description'}); "
        f"bracket={bracket_name}",
    )
    trail.add(
        "Pressure class",
        f"{_pressure_label(ansi)} -> adder ×{pressure_mult:.2f}",
    )
    trail.add(
        "Sweet-base RCN bracket",
        f"low ${rcn_base.low:,} / mid ${rcn_base.mid:,} / high ${rcn_base.high:,} CAD "
        f"(2026 newbuild RCN; anchor: 2.0 MMBTU sour 1500# = $250k mid per Curt domain deep-dive)",
    )
    trail.add(
        "Service",
        f"factor ×{service_f:.2f} (sweet=1.00, sour=1.15)",
    )
    trail.add(
        "Code stamp / ABSA",
        f"adder ×{code_stamp_mult:.2f} "
        f"({'+20% B149.3/ABSA-registered premium' if code_stamp_mult > 1.0 else 'none detected'})",
    )
    trail.add(
        "Adjusted RCN bracket",
        f"low ${rcn.low:,} / mid ${rcn.mid:,} / high ${rcn.high:,} CAD "
        f"(sweet-base × {rcn_premium:.3f})",
    )
    trail.add(
        "Age",
        f"{age_years}yr -> factor {age_f:.3f} (heater curve)",
    )
    trail.add(
        "Condition",
        f"{raw_condition!r} -> {condition_tier} -> factor {cond_f:.3f}",
    )
    trail.add(
        "Combined",
        f"age × condition = {combined:.4f}",
    )
    trail.add("FMV mid", f"RCN mid × combined = ${fmv_mid:,.0f}")
    trail.add(
        "Confidence",
        f"composite {conf.composite:.2f} -> {conf_class}",
    )

    # 11. Price targets
    pt_low, pt_mid, pt_high = _price_targets(fmv_mid)

    # 12. Row assembly
    data: dict = {
        # Identity
        "Listing ID": str(listing.get("listing_id") or ""),
        "Record ID": str(listing.get("record_id") or ""),
        "Listing Name": listing_name,
        "Category": str(listing.get("category") or "heater"),
        "Family": "heater",
        "Supplier Company": str(listing.get("supplier_company") or ""),
        "URL": str(listing.get("url") or ""),
        # Inputs
        "Size / Basis": (
            f"{mmbtu} MMBTU"
            + (f" @ {ansi}#" if ansi is not None else "")
            + ("" if mmbtu_parsed else " (size assumed)")
        ),
        "Age Assumed (yr)": age_years,
        "Condition Assumed": condition_tier,
        # RCN (post-premium)
        "RCN New Low": rcn.low,
        "RCN New Mid": rcn.mid,
        "RCN New High": rcn.high,
        "RCN Source": "fallback/heater",
        # Methodology
        "Methodology Path": methodology_path,
        "Depreciation Curve": "heater",
        "Factor Service": service_f,
        "Factor Age": age_f,
        "Factor Condition": cond_f,
        "Factor Combined": combined,
        # Weights
        "Weight RCN Source": W_RCN_SOURCE,
        "Weight Data Volume": W_DATA_VOLUME,
        "Weight Freshness": W_DATA_FRESHNESS,
        "Weight Specificity": W_SPECIFICITY,
        "Weight Variance": W_VARIANCE,
        # Confidence
        "Conf RCN Source": conf.rcn_source_score,
        "Conf Data Volume": conf.data_volume_score,
        "Conf Freshness": conf.data_freshness_score,
        "Conf Specificity": conf.specificity_score,
        "Conf Variance": conf.variance_score,
        "Conf Composite": conf.composite,
        "Conf Class": conf_class,
        # Price targets
        "Price Target LOW": pt_low,
        "Price Target MID": pt_mid,
        "Price Target HIGH": pt_high,
        # Comparables
        "Comparables Count": 0,
        "Comparables Summary": "no comps (standalone run)",
        # Reasoning
        "Reasoning Trail": trail.render(),
        "Review Flag": False,
        "Review Reason": "",
        "Hold From Publication": False,
        # Provenance
        "Sold Anchor Used": False,
        "Sold Anchor Count": 0,
    }
    return Tier2Row(data=data)
