"""Dehydrator family — TEG / mole sieve / generic.

RCN scales by gas throughput (MMSCFD). Depreciation follows
dedicated dehydrator curve (see rcn_engine/depreciation.py).
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


# ── RCN BRACKETS ──────────────────────────────────────────────────
# Anchored 2026-05-26 against `seeds/rcn_price_reference_seed_v2.xlsx`
# Static Equipment sheet — two dehydrator references:
#   dehy:glycol:small:std  →  5–25 MMCF/D @ 10 ref →  $60k / $100k / $150k
#   dehy:glycol:large:std  → 25–100 MMCF/D @ 50 ref → $150k / $280k / $420k
# Cross-checked against HubSpot corpus: 50 MMSCFD unused unit asks
# $300k with RV $570k (matches seed's large bracket). Sub-5 MMSCFD
# skid packages not in the seed; values scaled down from seed-small
# using HubSpot's two 2-MMSCFD listings (~$12k ask → ~$25–30k implied
# RCN at typical depreciation). Open to Curt tightening the tiny
# bracket once more data lands.
_TEG_BRACKETS: dict[str, RcnBand] = {
    "small":  RcnBand( 20_000,  40_000,  60_000),   # < 5 MMSCFD  (sub-seed extrapolation)
    "medium": RcnBand( 60_000, 100_000, 150_000),   # 5–25 MMSCFD (RCN seed dehy:glycol:small:std)
    "large":  RcnBand(150_000, 280_000, 420_000),   # > 25 MMSCFD (RCN seed dehy:glycol:large:std)
}

# Mole sieve premium over glycol (molecular sieve beds + heavier regen
# package). HubSpot corpus has 0 explicit mole-sieve listings to
# calibrate against; 1.5× retained as agent's domain-intuition default
# pending a corpus point.
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


# ── Parsing helpers ────────────────────────────────────────────────

_MMSCFD_RE = re.compile(r"(\d+(?:\.\d+)?)\s*mmscfd", re.IGNORECASE)


def _parse_mmscfd(text: str, default: float = 5.0) -> tuple[float, bool]:
    """Extract MMSCFD throughput from free text.

    Returns (mmscfd, was_parsed). `was_parsed` lets callers know whether
    we actually pulled a size signal (affects confidence specificity).
    """
    m = _MMSCFD_RE.search(text or "")
    if m:
        try:
            return float(m.group(1)), True
        except ValueError:
            pass
    return default, False


# ── Output band derivation ─────────────────────────────────────────

# Price target band widths around the FMV mid. Asymmetric: floor sits
# tighter to mid (walk-away discipline), ceiling allows asking-anchor.
_PRICE_FLOOR_RATIO = 0.80
_PRICE_CEILING_RATIO = 1.20


def _price_targets(fmv_mid: float) -> tuple[int, int, int]:
    low = int(round(fmv_mid * _PRICE_FLOOR_RATIO))
    high = int(round(fmv_mid * _PRICE_CEILING_RATIO))
    mid = int(round(fmv_mid))
    return low, mid, high


# ── End-to-end pricing ─────────────────────────────────────────────

def price_dehydrator(listing: dict) -> Tier2Row:
    """End-to-end pricing for a dehydrator listing.

    Pulls together: variant classification → RCN bracket → age factor
    → condition factor → service factor → combined factor → confidence
    → reasoning trail → spec-compliant row assembly.
    """
    description = str(listing.get("description") or listing.get("listing_name") or "")
    listing_name = str(listing.get("listing_name") or "")
    full_text = f"{listing_name} {description}".strip()

    # 1. Variant + throughput
    variant = classify_dehydrator(full_text)
    mmscfd, mmscfd_parsed = _parse_mmscfd(full_text)

    # 2. RCN bracket
    rcn = dehydrator_rcn(variant=variant, mmscfd=mmscfd)

    # 3. Age (year is required to compute age; absent year, assume 10y)
    current_year = datetime.now().year
    raw_year = listing.get("year")
    has_year = raw_year is not None
    age_years: int = (current_year - int(raw_year)) if has_year else 10
    age_years = max(0, age_years)
    age_f = float(get_age_factor(age_years, "dehydrator"))

    # 4. Condition
    raw_condition = listing.get("condition")
    has_condition = bool(raw_condition)
    condition_tier = normalize_condition(raw_condition) if has_condition else normalize_condition(None)
    cond_f = float(get_condition_factor(condition_tier))

    # 5. Service factor (sweet/sour parsed from description)
    service_f = float(dehydrator_service_factor(full_text))

    # 6. Combined factor — service is a RCN-side modifier; here we
    # multiply through with age × condition for a single combined view
    # that the spec contract expects.
    combined = age_f * cond_f * service_f

    # 7. RCN: apply service premium directly into the bracket so the
    # downstream FMV (RCN × combined-of-age-and-condition) doesn't
    # double-count. The spec captures Factor Service separately for
    # transparency, but combined drives the math.
    fmv_mid = rcn.mid * combined

    # 8. Confidence (no comps in standalone run)
    conf = calculate_confidence(
        rcn_confidence=0.50,  # fallback-bracket source → mid-range
        comparable_count=0,
        comparable_cv=None,
        has_year=has_year,
        has_condition=has_condition,
        has_hours=False,
        has_size_param=mmscfd_parsed,
        data_age_days=0,
    )
    conf_class = classify_confidence(conf.composite)

    # 9. Methodology path
    methodology_path = f"dehydrator/{variant}/MMSCFD-scaled"

    # 10. Reasoning trail
    trail = ReasoningTrail()
    trail.add("Variant", f"{variant} (matched on description text)")
    trail.add(
        "Throughput",
        f"{mmscfd} MMSCFD ({'parsed from text' if mmscfd_parsed else 'default — no size in description'})",
    )
    trail.add(
        "RCN bracket",
        f"low ${rcn.low:,} / mid ${rcn.mid:,} / high ${rcn.high:,} CAD (seed-anchored: rcn_price_reference_seed_v2.xlsx dehy:glycol entries; mole-sieve premium 1.5× remains a domain-intuition default)",
    )
    trail.add(
        "Age",
        f"{age_years}yr -> factor {age_f:.3f} (dehydrator curve)",
    )
    trail.add(
        "Condition",
        f"{raw_condition!r} -> {condition_tier} -> factor {cond_f:.3f}",
    )
    trail.add(
        "Service",
        f"factor {service_f:.2f} (sweet=1.00, sour=1.15)",
    )
    trail.add(
        "Combined",
        f"age × condition × service = {combined:.4f}",
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
        "Category": str(listing.get("category") or "dehydrator"),
        "Family": "dehydrator",
        "Supplier Company": str(listing.get("supplier_company") or ""),
        "URL": str(listing.get("url") or ""),
        # Inputs
        "Size / Basis": f"{mmscfd} MMSCFD" if mmscfd_parsed else f"{mmscfd} MMSCFD (assumed)",
        "Age Assumed (yr)": age_years,
        "Condition Assumed": condition_tier,
        # RCN
        "RCN New Low": rcn.low,
        "RCN New Mid": rcn.mid,
        "RCN New High": rcn.high,
        # Granular source so Mark can tell which family's bracket fired
        # without parsing methodology_path. Same pattern propagates to
        # other Tier 2 families (treater/heater/knockouts) in their
        # respective Chunks.
        "RCN Source": "fallback/dehydrator",
        # Methodology
        "Methodology Path": methodology_path,
        "Depreciation Curve": "dehydrator",
        "Factor Service": service_f,
        "Factor Age": age_f,
        "Factor Condition": cond_f,
        "Factor Combined": combined,
        # Weights (constants from confidence module)
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
