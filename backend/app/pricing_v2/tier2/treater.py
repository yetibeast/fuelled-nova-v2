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

from .column_spec import TIER2_COLUMNS, Tier2Row
from .reasoning import ReasoningTrail

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


# ── Parsing helpers ────────────────────────────────────────────────

# Inches: integer or decimal followed by an inch-mark (") — e.g. 96",
# 96.5", or `60-inch` style. Keep the regex tight: a bare number
# without a unit hint is too ambiguous (could be year, MAWP, etc.).
_DIAMETER_RE = re.compile(r"(\d{1,3})(?:\.\d+)?\s*\"")
_DIAMETER_INCH_RE = re.compile(r"(\d{1,3})(?:\.\d+)?\s*-?\s*inch", re.IGNORECASE)


def _parse_diameter_in(text: str, default: float = 60.0) -> tuple[float, bool]:
    """Extract contactor diameter in inches from free text.

    Returns (diameter_in, was_parsed). `was_parsed` lets callers know
    whether we actually pulled a size signal (affects confidence
    specificity).
    """
    text = text or ""
    m = _DIAMETER_RE.search(text)
    if m:
        try:
            return float(m.group(1)), True
        except ValueError:
            pass
    m = _DIAMETER_INCH_RE.search(text)
    if m:
        try:
            return float(m.group(1)), True
        except ValueError:
            pass
    return default, False


# ── Output band derivation ─────────────────────────────────────────

# Price target band widths around the FMV mid. Same convention as
# dehydrator: asymmetric floor/ceiling.
_PRICE_FLOOR_RATIO = 0.80
_PRICE_CEILING_RATIO = 1.20


def _price_targets(fmv_mid: float) -> tuple[int, int, int]:
    low = int(round(fmv_mid * _PRICE_FLOOR_RATIO))
    high = int(round(fmv_mid * _PRICE_CEILING_RATIO))
    mid = int(round(fmv_mid))
    return low, mid, high


# ── End-to-end pricing ─────────────────────────────────────────────

def price_treater(listing: dict) -> Tier2Row:
    """End-to-end pricing for a treater listing.

    Pulls together: variant classification → diameter parse → RCN
    bracket → age factor → condition factor → service factor (sour or
    electrostatic-bypass) → combined factor → confidence → reasoning
    trail → spec-compliant row assembly.
    """
    description = str(listing.get("description") or listing.get("listing_name") or "")
    listing_name = str(listing.get("listing_name") or "")
    full_text = f"{listing_name} {description}".strip()

    # 1. Variant + diameter
    variant = classify_treater(full_text)
    diameter_in, dia_parsed = _parse_diameter_in(full_text)

    # 2. RCN bracket
    rcn = treater_rcn(variant=variant, diameter_in=diameter_in)

    # 3. Age (year is required to compute age; absent year, assume 10y)
    current_year = datetime.now().year
    raw_year = listing.get("year")
    has_year = raw_year is not None
    age_years: int = (current_year - int(raw_year)) if has_year else 10
    age_years = max(0, age_years)
    age_f = float(get_age_factor(age_years, "treater"))

    # 4. Condition
    raw_condition = listing.get("condition")
    has_condition = bool(raw_condition)
    condition_tier = (
        normalize_condition(raw_condition) if has_condition else normalize_condition(None)
    )
    cond_f = float(get_condition_factor(condition_tier))

    # 5. Service factor (sweet/sour parsed from description; electrostatic bypasses sour)
    service_f = float(treater_service_factor(full_text, variant=variant))

    # 6. Combined factor — service is a RCN-side modifier; multiply
    # through with age × condition for a single combined view that the
    # spec contract expects.
    combined = age_f * cond_f * service_f

    # 7. FMV mid (RCN × combined)
    fmv_mid = rcn.mid * combined

    # 8. Confidence (no comps in standalone run)
    conf = calculate_confidence(
        rcn_confidence=0.50,  # fallback-bracket source → mid-range
        comparable_count=0,
        comparable_cv=None,
        has_year=has_year,
        has_condition=has_condition,
        has_hours=False,
        has_size_param=dia_parsed,
        data_age_days=0,
    )
    conf_class = classify_confidence(conf.composite)

    # 9. Methodology path
    methodology_path = f"treater/{variant}/diameter-scaled"

    # 10. Reasoning trail
    trail = ReasoningTrail()
    trail.add("Variant", f"{variant} (matched on description text)")
    trail.add(
        "Diameter",
        f"{diameter_in}\" ({'parsed from text' if dia_parsed else 'default — no size in description'})",
    )
    trail.add(
        "RCN bracket",
        f"low ${rcn.low:,} / mid ${rcn.mid:,} / high ${rcn.high:,} CAD "
        f"(2026 newbuild RCN; anchor: 96\" sour heater-treater = $750k CAD mid per Curt domain call, "
        f"validated against HubSpot 96\" sour 11-16yr sold $80-150k range)",
    )
    trail.add("Age", f"{age_years}yr -> factor {age_f:.3f} (treater curve)")
    trail.add(
        "Condition",
        f"{raw_condition!r} -> {condition_tier} -> factor {cond_f:.3f}",
    )
    trail.add(
        "Service",
        f"factor {service_f:.2f} "
        f"({'electrostatic bypasses sour' if variant == 'electrostatic' else 'sweet=1.00, sour=1.15'})",
    )
    trail.add("Combined", f"age × condition × service = {combined:.4f}")
    trail.add("FMV mid", f"RCN mid × combined = ${fmv_mid:,.0f}")
    trail.add("Confidence", f"composite {conf.composite:.2f} -> {conf_class}")

    # 11. Price targets
    pt_low, pt_mid, pt_high = _price_targets(fmv_mid)

    # 12. Row assembly
    data: dict = {
        # Identity
        "Listing ID": str(listing.get("listing_id") or ""),
        "Record ID": str(listing.get("record_id") or ""),
        "Listing Name": listing_name,
        "Category": str(listing.get("category") or "treater"),
        "Family": "treater",
        "Supplier Company": str(listing.get("supplier_company") or ""),
        "URL": str(listing.get("url") or ""),
        # Inputs
        "Size / Basis": (
            f"{diameter_in}\" diameter" if dia_parsed else f"{diameter_in}\" diameter (assumed)"
        ),
        "Age Assumed (yr)": age_years,
        "Condition Assumed": condition_tier,
        # RCN
        "RCN New Low": rcn.low,
        "RCN New Mid": rcn.mid,
        "RCN New High": rcn.high,
        "RCN Source": "fallback/treater",
        # Methodology
        "Methodology Path": methodology_path,
        "Depreciation Curve": "treater",
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
        # Confidence breakdown
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
