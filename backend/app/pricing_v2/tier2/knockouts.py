"""Knockout family — FWKO / Flare KO / Gas KO / Ambiguous.

Three knockout types ride different RCN brackets and depreciation
curves because they're different equipment despite shared
nomenclature:

  FWKO     — free-water knockout, production vessel, water/solids service
  Flare KO — flare-stack knockout drum, vapor service
  Gas KO   — inlet/discharge gas scrubber, lighter package

Bare "knockout" with no sub-family signal is held as **Ambiguous**:
priced with widened bands and forced into manual review rather than
silently guessing.

Calibration locked 2026-05-27 by Curt. RCN brackets are CAD newbuild
(2026 spec). Sour service applies a 1.15× premium on RCN. See per-
family bracket tables below for anchor reasoning.
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

KnockoutSubFamily = Literal["fwko", "flare", "gas", "ambiguous"]


# ── Disambiguator ─────────────────────────────────────────────────
# Ordered first-match-wins, case-insensitive. Patterns locked
# 2026-05-27 by Curt.

_FWKO_PATTERNS = (
    re.compile(r"\bfwko\b", re.IGNORECASE),
    re.compile(r"free water knock", re.IGNORECASE),
    re.compile(r"free-water", re.IGNORECASE),
)

_FLARE_PATTERNS = (
    re.compile(r"flare\s*knockout", re.IGNORECASE),
    re.compile(r"flare\s*ko\b", re.IGNORECASE),
    re.compile(r"flare\s*drum", re.IGNORECASE),
    re.compile(r"flare\s*knock-?out", re.IGNORECASE),
)

_GAS_PATTERNS = (
    re.compile(r"gas\s*knockout", re.IGNORECASE),
    re.compile(r"gas\s*ko\b", re.IGNORECASE),
    re.compile(r"inlet\s*scrubber", re.IGNORECASE),
    re.compile(r"inlet\s*ko\b", re.IGNORECASE),
)

_AMBIGUOUS_PATTERNS = (
    re.compile(r"knockout\s*drum", re.IGNORECASE),
    re.compile(r"ko\s*drum", re.IGNORECASE),
    re.compile(r"slug\s*catcher", re.IGNORECASE),
)

_FWKO_CATEGORY_FALLBACK = re.compile(r"3-?phase", re.IGNORECASE)
_FWKO_CATEGORIES = {"separator", "vessel"}


def classify_knockout(text: str, category: str | None = None) -> KnockoutSubFamily:
    """4-way knockout disambiguation. First match wins.

    Order:
      1. FWKO — explicit "FWKO" / "free water knock" / "free-water"
      2. FWKO via category fallback — category∈{Separator,Vessel} + "3-phase"
      3. Flare KO — "flare knockout" / "flare KO" / "flare drum" / "flare knock-out"
      4. Gas KO — "gas knockout" / "gas KO" / "inlet scrubber" / "inlet KO"
      5. Ambiguous — bare "knockout drum" / "KO drum" / "slug catcher"
      6. Ambiguous — anything else with no signal
    """
    t = text or ""
    # 1. Explicit FWKO tokens
    for pat in _FWKO_PATTERNS:
        if pat.search(t):
            return "fwko"
    # 2. FWKO via category fallback: 3-phase in a Separator/Vessel listing
    if category and category.strip().lower() in _FWKO_CATEGORIES:
        if _FWKO_CATEGORY_FALLBACK.search(t):
            return "fwko"
    # 3. Flare KO
    for pat in _FLARE_PATTERNS:
        if pat.search(t):
            return "flare"
    # 4. Gas KO
    for pat in _GAS_PATTERNS:
        if pat.search(t):
            return "gas"
    # 5. Ambiguous catch-all
    for pat in _AMBIGUOUS_PATTERNS:
        if pat.search(t):
            return "ambiguous"
    return "ambiguous"


# ── RCN brackets ──────────────────────────────────────────────────


@dataclass(frozen=True)
class RcnBand:
    """Three-point RCN bracket (low/mid/high) — values in CAD."""
    low: int
    mid: int
    high: int


# FWKO — sized by shell diameter (production vessel). Anchor: 48"
# Medium sits at $200k mid CAD newbuild sweet base. Sour adds 1.15×.
_FWKO_BRACKETS: dict[str, RcnBand] = {
    "small":  RcnBand( 50_000,  80_000, 120_000),  # < 36"
    "medium": RcnBand(140_000, 200_000, 280_000),  # 36-60"
    "large":  RcnBand(300_000, 400_000, 520_000),  # 60-96"
    "xl":     RcnBand(550_000, 700_000, 900_000),  # ≥ 96"
}

# Flare KO — vapor service drum. Lighter package than FWKO at same
# diameter; 27% bump over original calibration per Curt's "should be
# a bit more" feedback 2026-05-27.
_FLARE_KO_BRACKETS: dict[str, RcnBand] = {
    "tiny":   RcnBand( 12_000,  18_000,  25_000),  # < 36"
    "small":  RcnBand( 30_000,  45_000,  60_000),  # 36-60"
    "medium": RcnBand( 70_000, 100_000, 140_000),  # 60-96"
    "large":  RcnBand(140_000, 200_000, 270_000),  # ≥ 96"
}

# Gas KO — inlet/discharge scrubber. DATA-THIN: only 1 corpus row
# at locked time. Brackets are domain-intuition placeholders pending
# corpus growth. price_knockout() surfaces "validation pending" in
# the reasoning trail for any gas-KO row.
_GAS_KO_BRACKETS: dict[str, RcnBand] = {
    "small":  RcnBand(20_000, 30_000,  45_000),  # < 24"
    "medium": RcnBand(40_000, 55_000,  75_000),  # 24-36"
    "large":  RcnBand(65_000, 85_000, 110_000),  # ≥ 36"
}


def _fwko_bracket(diameter_in: float) -> str:
    if diameter_in < 36:
        return "small"
    if diameter_in < 60:
        return "medium"
    if diameter_in < 96:
        return "large"
    return "xl"


def _flare_ko_bracket(diameter_in: float) -> str:
    if diameter_in < 36:
        return "tiny"
    if diameter_in < 60:
        return "small"
    if diameter_in < 96:
        return "medium"
    return "large"


def _gas_ko_bracket(diameter_in: float) -> str:
    if diameter_in < 24:
        return "small"
    if diameter_in < 36:
        return "medium"
    return "large"


def fwko_rcn(*, diameter_in: float) -> RcnBand:
    return _FWKO_BRACKETS[_fwko_bracket(diameter_in)]


def flare_ko_rcn(*, diameter_in: float) -> RcnBand:
    return _FLARE_KO_BRACKETS[_flare_ko_bracket(diameter_in)]


def gas_ko_rcn(*, diameter_in: float) -> RcnBand:
    return _GAS_KO_BRACKETS[_gas_ko_bracket(diameter_in)]


# ── Service factor ─────────────────────────────────────────────────


def knockout_service_factor(service_description: str) -> float:
    """Sour service carries +15% RCN premium (same as Tier 1 + dehy)."""
    t = service_description.lower()
    if "sour" in t or "h2s" in t or "h₂s" in t or "nace" in t:
        return 1.15
    return 1.00


# ── Parsing helpers ────────────────────────────────────────────────

# Match e.g. "48 inch", "48-inch", "48in", "48\"", "48 in"
_DIAMETER_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:-?\s*inch\b|-?\s*in\b|\")",
    re.IGNORECASE,
)


def _parse_diameter(text: str, default: float = 36.0) -> tuple[float, bool]:
    """Extract shell diameter (inches) from free text.

    Returns (diameter_in, was_parsed). When no diameter is present, falls
    back to 36" — a defensible mid-range for an unknown knockout — and
    lowers specificity score downstream.
    """
    m = _DIAMETER_RE.search(text or "")
    if m:
        try:
            return float(m.group(1)), True
        except ValueError:
            pass
    return default, False


# ── Output band derivation ─────────────────────────────────────────

# Standard ±20% band (same as dehy)
_PRICE_FLOOR_RATIO = 0.80
_PRICE_CEILING_RATIO = 1.20

# Ambiguous gets ±25% (widened ≥50% spread, per locked spec)
_AMBIGUOUS_FLOOR_RATIO = 0.75
_AMBIGUOUS_CEILING_RATIO = 1.25


def _price_targets(fmv_mid: float, *, ambiguous: bool) -> tuple[int, int, int]:
    floor = _AMBIGUOUS_FLOOR_RATIO if ambiguous else _PRICE_FLOOR_RATIO
    ceil_ = _AMBIGUOUS_CEILING_RATIO if ambiguous else _PRICE_CEILING_RATIO
    low = int(round(fmv_mid * floor))
    high = int(round(fmv_mid * ceil_))
    mid = int(round(fmv_mid))
    return low, mid, high


# ── Per-sub-family RCN dispatch ────────────────────────────────────


def _rcn_for_subfamily(
    sub: KnockoutSubFamily, diameter_in: float
) -> tuple[RcnBand, str, str, str]:
    """Return (band, methodology_path, depreciation_curve, rcn_source).

    Ambiguous + Gas KO both ride the separator curve.
    """
    if sub == "fwko":
        return (
            fwko_rcn(diameter_in=diameter_in),
            "knockout/fwko/diameter-scaled",
            "knockout_fwko",
            "fallback/knockout-fwko",
        )
    if sub == "flare":
        return (
            flare_ko_rcn(diameter_in=diameter_in),
            "knockout/flare/diameter-scaled",
            "knockout_flare",
            "fallback/knockout-flare",
        )
    if sub == "gas":
        return (
            gas_ko_rcn(diameter_in=diameter_in),
            "knockout/gas/diameter-scaled",
            "separator",  # rides separator until corpus grows
            "fallback/knockout-gas",
        )
    # ambiguous: use FWKO band as a defensible midpoint between the
    # three real sub-families, but flag for review and widen the band.
    return (
        fwko_rcn(diameter_in=diameter_in),
        "knockout/ambiguous/manual-review",
        "separator",
        "fallback/knockout-ambiguous",
    )


_FAMILY_LABEL: dict[KnockoutSubFamily, str] = {
    "fwko": "knockout-fwko",
    "flare": "knockout-flare",
    "gas": "knockout-gas",
    "ambiguous": "knockout-ambiguous",
}


# ── End-to-end pricing ─────────────────────────────────────────────


def price_knockout(listing: dict) -> Tier2Row:
    """End-to-end pricing for a knockout listing.

    Dispatches: classify → RCN bracket → age × condition × service →
    confidence → reasoning trail → spec-compliant row. Ambiguous rows
    are flagged for review with widened price bands.
    """
    description = str(listing.get("description") or listing.get("listing_name") or "")
    listing_name = str(listing.get("listing_name") or "")
    category_in = listing.get("category")
    full_text = f"{listing_name} {description}".strip()

    # 1. Sub-family classification
    sub = classify_knockout(full_text, category=category_in)

    # 2. Size parse
    diameter_in, diameter_parsed = _parse_diameter(full_text)

    # 3. RCN bracket + curve + methodology
    rcn, methodology_path, curve_name, rcn_source = _rcn_for_subfamily(
        sub, diameter_in
    )

    # 4. Age (default 10y if year missing)
    current_year = datetime.now().year
    raw_year = listing.get("year")
    has_year = raw_year is not None
    age_years: int = (current_year - int(raw_year)) if has_year else 10
    age_years = max(0, age_years)
    age_f = float(get_age_factor(age_years, curve_name))

    # 5. Condition
    raw_condition = listing.get("condition")
    has_condition = bool(raw_condition)
    condition_tier = normalize_condition(raw_condition) if has_condition else normalize_condition(None)
    cond_f = float(get_condition_factor(condition_tier))

    # 6. Service factor
    service_f = float(knockout_service_factor(full_text))

    # 7. Combined
    combined = age_f * cond_f * service_f
    fmv_mid = rcn.mid * combined

    # 8. Confidence
    # Ambiguous gets a lower RCN-source score — we can't tell which
    # bracket actually applies.
    rcn_confidence = 0.30 if sub == "ambiguous" else (
        0.40 if sub == "gas" else 0.50  # gas is data-thin
    )
    conf = calculate_confidence(
        rcn_confidence=rcn_confidence,
        comparable_count=0,
        comparable_cv=None,
        has_year=has_year,
        has_condition=has_condition,
        has_hours=False,
        has_size_param=diameter_parsed,
        data_age_days=0,
    )
    conf_class = classify_confidence(conf.composite)

    # 9. Reasoning trail
    trail = ReasoningTrail()
    trail.add("Sub-family", f"{sub} (disambiguator first-match-wins on description text)")
    trail.add(
        "Diameter",
        f"{diameter_in}\" ({'parsed from text' if diameter_parsed else 'default — no size in description'})",
    )
    trail.add(
        "RCN bracket",
        f"low ${rcn.low:,} / mid ${rcn.mid:,} / high ${rcn.high:,} CAD "
        f"(2026 newbuild RCN sweet base; sour ×1.15)",
    )
    trail.add("Age", f"{age_years}yr -> factor {age_f:.3f} ({curve_name} curve)")
    trail.add("Condition", f"{raw_condition!r} -> {condition_tier} -> factor {cond_f:.3f}")
    trail.add("Service", f"factor {service_f:.2f} (sweet=1.00, sour=1.15)")
    trail.add("Combined", f"age × condition × service = {combined:.4f}")
    trail.add("FMV mid", f"RCN mid × combined = ${fmv_mid:,.0f}")
    if sub == "gas":
        trail.add(
            "Gas KO note",
            "data-thin family (1 corpus row at calibration time) — "
            "validation pending; bracket is domain-intuition placeholder",
        )
    if sub == "ambiguous":
        trail.add(
            "Ambiguous note",
            "no sub-family signal in description — priced with widened "
            "band (±25%) and flagged for manual disambiguation",
        )
    trail.add("Confidence", f"composite {conf.composite:.2f} -> {conf_class}")

    # 10. Price targets (widened for ambiguous)
    pt_low, pt_mid, pt_high = _price_targets(fmv_mid, ambiguous=(sub == "ambiguous"))

    # 11. Review flag handling
    review_flag = sub == "ambiguous"
    review_reason = (
        "ambiguous knockout sub-family — manual disambiguation required"
        if review_flag
        else ""
    )

    # 12. Size/basis string
    if diameter_parsed:
        size_basis = f"{diameter_in}\" diameter"
    else:
        size_basis = f"{diameter_in}\" diameter (assumed)"

    # 13. Row assembly
    data: dict = {
        # Identity
        "Listing ID": str(listing.get("listing_id") or ""),
        "Record ID": str(listing.get("record_id") or ""),
        "Listing Name": listing_name,
        "Category": str(category_in or "knockout"),
        "Family": _FAMILY_LABEL[sub],
        "Supplier Company": str(listing.get("supplier_company") or ""),
        "URL": str(listing.get("url") or ""),
        # Inputs
        "Size / Basis": size_basis,
        "Age Assumed (yr)": age_years,
        "Condition Assumed": condition_tier,
        # RCN
        "RCN New Low": rcn.low,
        "RCN New Mid": rcn.mid,
        "RCN New High": rcn.high,
        "RCN Source": rcn_source,
        # Methodology
        "Methodology Path": methodology_path,
        "Depreciation Curve": curve_name,
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
        "Review Flag": review_flag,
        "Review Reason": review_reason,
        "Hold From Publication": False,
        # Provenance
        "Sold Anchor Used": False,
        "Sold Anchor Count": 0,
    }
    return Tier2Row(data=data)
