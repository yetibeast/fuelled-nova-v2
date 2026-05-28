"""Meter Run family — Tier 2.5.

Pipe-size × ANSI bracket pricing with meter-type adders. Static
utility equipment; ages via the treater curve (no dedicated meter
curve — see scoping report `docs/tier2-calibration/
tanks-meter-runs-scoping-2026-05-27.md`).

Brackets are 2026 newbuild CAD (sweet base; sour ×1.15). Calibration
anchors:

- HubSpot sold meter runs (n=175 sold w/ pipe parsed): median ask
  for 2-4" 600 ANSI plain meter runs falls in the $750–$6,250 range.
  Newbuild × treater(15yr)=0.35 × GOOD=0.75 ≈ 0.26× → 4" 600 mid
  $28k × 0.26 = $7.3k FMV; 2" 600 mid $10k × 0.26 = $2.6k FMV.
  Both centre defensibly on the median-ask zone.
- LACT / custody-transfer / large metering skids are deferred to
  Tier 3 manual pricing (sample range: $230k-$1.4M RCN per PDF
  evidence; ~10-20 listings in the corpus). The classifier flags
  these and emits a Review-Required row with $0 price targets.

Mirrors the structure of `dehydrator.py`.
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


MeterType = Literal["orifice", "turbine", "coriolis", "ultrasonic", "vortex"]


METER_RUN_MATCH_TERMS = (
    "meter run",
    "meter skid",
    "metering skid",
    "flow meter",
    "flow run",
)

_LACT_MATCH_TERMS = (
    "lact",
    "custody transfer",
    "custody-transfer",
)


@dataclass(frozen=True)
class RcnBand:
    """Three-point RCN bracket (low/mid/high) — values in CAD."""
    low: int
    mid: int
    high: int


@dataclass(frozen=True)
class MeterRunInputs:
    pipe_size_in: int
    ansi_class: int
    is_sour: bool
    pipe_parsed: bool
    ansi_parsed: bool


# ── RCN bracket grid — 2026 NEWBUILD CAD ──────────────────────────
# Pipe size (row) × ANSI class (column). Sweet base; sour applies a
# 1.15× multiplier on top. Sourced from scoping report (2026-05-27).
#
# ANSI columns:
#   col 0: <300        (atmospheric / 150# class)
#   col 1: 300 ≤ ansi ≤ 600
#   col 2: 600 < ansi ≤ 1500
#   col 3: ansi > 1500 (heavy-pressure)
_PIPE_BRACKETS: dict[int, tuple[RcnBand, RcnBand, RcnBand, RcnBand]] = {
    2: (
        RcnBand( 4_000,  7_000, 10_000),
        RcnBand( 6_000, 10_000, 14_000),
        RcnBand( 9_000, 14_000, 19_000),
        RcnBand(14_000, 20_000, 28_000),
    ),
    3: (
        RcnBand( 7_000, 12_000, 17_000),
        RcnBand(11_000, 17_000, 24_000),
        RcnBand(15_000, 23_000, 32_000),
        RcnBand(22_000, 32_000, 44_000),
    ),
    4: (
        RcnBand(12_000, 19_000, 27_000),
        RcnBand(18_000, 28_000, 39_000),
        RcnBand(25_000, 38_000, 52_000),
        RcnBand(36_000, 52_000, 72_000),
    ),
    6: (
        RcnBand(22_000, 35_000,  50_000),
        RcnBand(33_000, 50_000,  70_000),
        RcnBand(45_000, 68_000,  92_000),
        RcnBand(65_000, 95_000, 130_000),
    ),
    8: (
        RcnBand( 40_000,  60_000,  85_000),
        RcnBand( 58_000,  88_000, 122_000),
        RcnBand( 80_000, 120_000, 165_000),
        RcnBand(115_000, 170_000, 235_000),
    ),
}


# Meter-type multipliers (multiplicative on top of pipe×ANSI base).
# Orifice is the baseline; populated when no other meter-type signal
# in the listing text. Scoping report flags meter-type coverage at
# only 12% in HubSpot — the bracket is dominated by pipe×ANSI, the
# adder is a refinement when populated.
_METER_TYPE_FACTORS: dict[MeterType, float] = {
    "orifice": 1.00,
    "turbine": 1.15,
    "ultrasonic": 1.25,
    "vortex": 1.20,
    "coriolis": 1.40,
}


_SOUR_PREMIUM = 1.15


# ── Classifier ─────────────────────────────────────────────────────

def classify_meter_run(text: str) -> bool:
    """True if listing text identifies a meter run / metering skid.

    LACT / custody-transfer listings also classify as meter-run (they
    are routed via the sub-flag in `price_meter_run`, not excluded
    here).
    """
    t = (text or "").lower()
    if any(term in t for term in METER_RUN_MATCH_TERMS):
        return True
    if any(term in t for term in _LACT_MATCH_TERMS):
        return True
    return False


def is_lact_or_custody(text: str) -> bool:
    """True if the listing is LACT / custody-transfer / large meter skid.

    These route to Tier 3 manual pricing — too large a $-range to fit
    the generic meter-run bracket (RCN $230k-$1.4M per PDF evidence).
    """
    t = (text or "").lower()
    return any(term in t for term in _LACT_MATCH_TERMS)


def detect_meter_type(text: str) -> MeterType:
    """Detect meter type from listing text. Defaults to orifice (baseline)."""
    t = (text or "").lower()
    # Order matters: 'coriolis' before 'micro motion' adjacency hint
    if "coriolis" in t or "micro motion" in t or "mass flow" in t:
        return "coriolis"
    if "ultrasonic" in t:
        return "ultrasonic"
    if "vortex" in t:
        return "vortex"
    if "turbine" in t:
        return "turbine"
    return "orifice"


# ── Pipe + ANSI parsing ───────────────────────────────────────────

# Pipe size: 1-2 digit inch followed by quote (straight or smart).
_PIPE_RE = re.compile(r'(\d{1,2})\s*[\"”“]')

# ANSI / pressure class: one of the standard ratings.
_ANSI_RE = re.compile(r'(?:ansi[\s-]*)?\b(150|300|600|900|1500|2500)\b', re.IGNORECASE)

# Sour indicators in listing text.
_SOUR_RE = re.compile(r'\bsour\b|\bh2s\b|\bnace\b|h₂s', re.IGNORECASE)


def parse_meter_run_inputs(text: str) -> MeterRunInputs:
    """Extract pipe size, ANSI class, and sour flag from listing text."""
    src = text or ""

    pipe_match = _PIPE_RE.search(src)
    pipe_parsed = pipe_match is not None
    pipe_size_in = int(pipe_match.group(1)) if pipe_match else 4  # default mid-size

    ansi_match = _ANSI_RE.search(src)
    ansi_parsed = ansi_match is not None
    ansi_class = int(ansi_match.group(1)) if ansi_match else 600  # default 600#

    is_sour = bool(_SOUR_RE.search(src))

    return MeterRunInputs(
        pipe_size_in=pipe_size_in,
        ansi_class=ansi_class,
        is_sour=is_sour,
        pipe_parsed=pipe_parsed,
        ansi_parsed=ansi_parsed,
    )


def _pipe_bucket(pipe_size_in: int) -> int:
    """Map any pipe size to the nearest bracket row (2, 3, 4, 6, or 8)."""
    if pipe_size_in < 3:
        return 2
    if pipe_size_in < 4:
        return 3
    if pipe_size_in < 5:
        return 4
    if pipe_size_in < 8:
        return 6
    return 8


def _ansi_bucket(ansi_class: int) -> int:
    """Map ANSI/pressure class to the column index (0..3) in _PIPE_BRACKETS."""
    if ansi_class < 300:
        return 0
    if ansi_class <= 600:
        return 1
    if ansi_class <= 1500:
        return 2
    return 3


# ── Service factor ────────────────────────────────────────────────

def meter_run_service_factor(service_description: str) -> float:
    """Sour service applies a 1.15× premium (NACE-rated materials)."""
    t = (service_description or "").lower()
    if "sour" in t or "h2s" in t or "h₂s" in t or "nace" in t:
        return 1.15
    return 1.00


# ── RCN bracket lookup ────────────────────────────────────────────

def meter_run_rcn(
    *,
    pipe_size_in: int,
    ansi_class: int,
    meter_type: MeterType,
    is_sour: bool,
) -> RcnBand:
    """Return the RCN bracket (low/mid/high CAD) for a meter run.

    Lookup: pipe bucket × ANSI bucket → base band. Apply meter-type
    multiplier, then sour premium.
    """
    pipe_row = _pipe_bucket(pipe_size_in)
    ansi_col = _ansi_bucket(ansi_class)
    base = _PIPE_BRACKETS[pipe_row][ansi_col]

    mult = _METER_TYPE_FACTORS.get(meter_type, 1.00)
    if is_sour:
        mult *= _SOUR_PREMIUM

    if mult == 1.00:
        return base
    return RcnBand(
        low=int(round(base.low * mult)),
        mid=int(round(base.mid * mult)),
        high=int(round(base.high * mult)),
    )


# ── Output band derivation ────────────────────────────────────────

_PRICE_FLOOR_RATIO = 0.80
_PRICE_CEILING_RATIO = 1.20


def _price_targets(fmv_mid: float) -> tuple[int, int, int]:
    low = int(round(fmv_mid * _PRICE_FLOOR_RATIO))
    high = int(round(fmv_mid * _PRICE_CEILING_RATIO))
    mid = int(round(fmv_mid))
    return low, mid, high


# ── End-to-end pricing ────────────────────────────────────────────

def _build_lact_row(
    listing: dict,
    inputs: MeterRunInputs,
    listing_name: str,
) -> Tier2Row:
    """Build a Review-Required row for LACT / custody-transfer listings.

    Curt's call (2026-05-27): defer to Tier 3 manual pricing — package
    complexity and $-range ($230k-$1.4M per PDF evidence) make a
    generic bracket misleading. Family stays `meter-run`; price
    targets are 0; reviewer must reprice manually.
    """
    trail = ReasoningTrail()
    trail.add(
        "Routing",
        "LACT / custody-transfer detected — Tier 3 manual pricing required.",
    )
    trail.add(
        "Inputs parsed",
        f"pipe={inputs.pipe_size_in}\" ansi={inputs.ansi_class}# sour={inputs.is_sour}",
    )
    trail.add(
        "Decision",
        "No auto-price emitted; reviewer must source comparable LACT skids manually.",
    )

    data: dict = {
        # Identity
        "Listing ID": str(listing.get("listing_id") or ""),
        "Record ID": str(listing.get("record_id") or ""),
        "Listing Name": listing_name,
        "Category": str(listing.get("category") or "meter run"),
        "Family": "meter-run",
        "Supplier Company": str(listing.get("supplier_company") or ""),
        "URL": str(listing.get("url") or ""),
        # Inputs
        "Size / Basis": f"{inputs.pipe_size_in}\" / {inputs.ansi_class}# ANSI (LACT)",
        "Age Assumed (yr)": 0,
        "Condition Assumed": normalize_condition(listing.get("condition")),
        # RCN — left at 0/0/0; no bracket fired
        "RCN New Low": 0,
        "RCN New Mid": 0,
        "RCN New High": 0,
        "RCN Source": "deferred/lact_custody_transfer",
        # Methodology
        "Methodology Path": "meter-run/lact_custody_transfer/manual",
        "Depreciation Curve": "treater",
        "Factor Service": 1.0,
        "Factor Age": 1.0,
        "Factor Condition": 1.0,
        "Factor Combined": 1.0,
        # Weights
        "Weight RCN Source": W_RCN_SOURCE,
        "Weight Data Volume": W_DATA_VOLUME,
        "Weight Freshness": W_DATA_FRESHNESS,
        "Weight Specificity": W_SPECIFICITY,
        "Weight Variance": W_VARIANCE,
        # Confidence — pinned low; manual review will replace.
        "Conf RCN Source": 0.1,
        "Conf Data Volume": 0.1,
        "Conf Freshness": 0.1,
        "Conf Specificity": 0.1,
        "Conf Variance": 0.1,
        "Conf Composite": 0.1,
        "Conf Class": "manual",
        # Price targets — zero; nothing to publish.
        "Price Target LOW": 0,
        "Price Target MID": 0,
        "Price Target HIGH": 0,
        # Comparables
        "Comparables Count": 0,
        "Comparables Summary": "no comps (LACT deferred to Tier 3)",
        # Reasoning
        "Reasoning Trail": trail.render(),
        "Review Flag": True,
        "Review Reason": (
            "LACT / custody-transfer — deferred to Tier 3, manual pricing required"
        ),
        "Hold From Publication": True,
        # Provenance
        "Sold Anchor Used": False,
        "Sold Anchor Count": 0,
    }
    return Tier2Row(data=data)


def price_meter_run(listing: dict) -> Tier2Row:
    """End-to-end pricing for a meter-run listing.

    Pulls together: classifier → pipe/ANSI/meter-type parsing →
    RCN bracket → age factor → condition factor → service factor →
    combined factor → confidence → reasoning trail → spec-compliant
    row.

    LACT / custody-transfer listings bypass the bracket math and
    emit a Review-Required row (Tier 3 manual pricing). See
    `_build_lact_row` for the deferred path.
    """
    description = str(listing.get("description") or listing.get("listing_name") or "")
    listing_name = str(listing.get("listing_name") or "")
    full_text = f"{listing_name} {description}".strip()

    inputs = parse_meter_run_inputs(full_text)

    if is_lact_or_custody(full_text):
        return _build_lact_row(listing, inputs, listing_name)

    # 1. Meter type
    meter_type = detect_meter_type(full_text)

    # 2. RCN bracket
    rcn = meter_run_rcn(
        pipe_size_in=inputs.pipe_size_in,
        ansi_class=inputs.ansi_class,
        meter_type=meter_type,
        is_sour=inputs.is_sour,
    )

    # 3. Age (default 10y when year absent)
    current_year = datetime.now().year
    raw_year = listing.get("year")
    has_year = raw_year is not None
    age_years: int = (current_year - int(raw_year)) if has_year else 10
    age_years = max(0, age_years)
    # Curve key 'treater' — meter runs are aliased to treater in
    # CATEGORY_CURVE_MAP. Passing 'meter_run' here works (it routes
    # through the alias) and keeps the spec column truthful.
    age_f = float(get_age_factor(age_years, "meter_run"))

    # 4. Condition
    raw_condition = listing.get("condition")
    has_condition = bool(raw_condition)
    condition_tier = (
        normalize_condition(raw_condition) if has_condition else normalize_condition(None)
    )
    cond_f = float(get_condition_factor(condition_tier))

    # 5. Service factor (sour/sweet)
    # `meter_run_rcn` already applies the sour premium to the bracket;
    # `Factor Service` is emitted separately for transparency, but
    # the RCN value should NOT be re-multiplied by it in fmv_mid.
    service_f = float(meter_run_service_factor(full_text))

    # 6. Combined factor — age × condition (service is folded into RCN).
    combined = age_f * cond_f

    # 7. FMV mid
    fmv_mid = rcn.mid * combined

    # 8. Confidence
    conf = calculate_confidence(
        rcn_confidence=0.50,
        comparable_count=0,
        comparable_cv=None,
        has_year=has_year,
        has_condition=has_condition,
        has_hours=False,
        has_size_param=inputs.pipe_parsed,
        data_age_days=0,
    )
    conf_class = classify_confidence(conf.composite)

    # 9. Methodology path
    sour_tag = "sour" if inputs.is_sour else "sweet"
    methodology_path = (
        f"meter-run/{inputs.pipe_size_in}in-{inputs.ansi_class}ansi/"
        f"{meter_type}/{sour_tag}"
    )

    # 10. Reasoning trail
    trail = ReasoningTrail()
    trail.add(
        "Pipe size",
        f"{inputs.pipe_size_in}\""
        + ("" if inputs.pipe_parsed else " (default — not parsed from text)"),
    )
    trail.add(
        "ANSI class",
        f"{inputs.ansi_class}#"
        + ("" if inputs.ansi_parsed else " (default 600# — not parsed)"),
    )
    trail.add("Meter type", f"{meter_type} (mult {_METER_TYPE_FACTORS[meter_type]:.2f})")
    trail.add(
        "Service",
        f"{sour_tag} (factor {service_f:.2f}, sour premium folded into RCN)",
    )
    trail.add(
        "RCN bracket",
        f"low ${rcn.low:,} / mid ${rcn.mid:,} / high ${rcn.high:,} CAD "
        f"(2026 newbuild; pipe×ANSI grid from tier2.5 scoping 2026-05-27)",
    )
    trail.add("Age", f"{age_years}yr -> factor {age_f:.3f} (treater curve)")
    trail.add(
        "Condition",
        f"{raw_condition!r} -> {condition_tier} -> factor {cond_f:.3f}",
    )
    trail.add("Combined", f"age × condition = {combined:.4f}")
    trail.add("FMV mid", f"RCN mid × combined = ${fmv_mid:,.0f}")
    trail.add("Confidence", f"composite {conf.composite:.2f} -> {conf_class}")

    # 11. Price targets
    pt_low, pt_mid, pt_high = _price_targets(fmv_mid)

    data: dict = {
        # Identity
        "Listing ID": str(listing.get("listing_id") or ""),
        "Record ID": str(listing.get("record_id") or ""),
        "Listing Name": listing_name,
        "Category": str(listing.get("category") or "meter run"),
        "Family": "meter-run",
        "Supplier Company": str(listing.get("supplier_company") or ""),
        "URL": str(listing.get("url") or ""),
        # Inputs
        "Size / Basis": (
            f"{inputs.pipe_size_in}\" / {inputs.ansi_class}# ANSI / {meter_type}"
        ),
        "Age Assumed (yr)": age_years,
        "Condition Assumed": condition_tier,
        # RCN
        "RCN New Low": rcn.low,
        "RCN New Mid": rcn.mid,
        "RCN New High": rcn.high,
        "RCN Source": "fallback/meter-run",
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
