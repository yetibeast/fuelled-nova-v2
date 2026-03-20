"""Multi-factor continuous confidence scoring.

Produces a weighted composite score in [0.10, 1.00] from five dimensions:
RCN source quality, data volume, data freshness, specificity, and variance.

Source: V1 rcn_v2/confidence.py — weights and thresholds preserved exactly.
"""
from __future__ import annotations

from dataclasses import dataclass

# ── POLICY CONSTANTS ──────────────────────────────────────────────────
AUTOMATED_CONFIDENCE_THRESHOLD = 0.75
HITL_REVIEW_THRESHOLD = 0.40
MIN_CONFIDENCE = 0.10
MAX_CONFIDENCE = 1.00

# Composite weights (must sum to 1.0)
W_RCN_SOURCE = 0.25
W_DATA_VOLUME = 0.25
W_DATA_FRESHNESS = 0.10
W_SPECIFICITY = 0.25
W_VARIANCE = 0.15


@dataclass(frozen=True)
class ConfidenceBreakdown:
    rcn_source_score: float
    data_volume_score: float
    data_freshness_score: float
    specificity_score: float
    variance_score: float
    composite: float


def calculate_confidence(
    *,
    rcn_confidence: float,
    comparable_count: int,
    comparable_cv: float | None,
    has_year: bool,
    has_condition: bool,
    has_hours: bool,
    has_size_param: bool,
    data_age_days: int = 0,
) -> ConfidenceBreakdown:
    """Calculate weighted confidence score in [0.10, 1.00]."""
    rcn_source_score = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, float(rcn_confidence)))

    if comparable_count >= 50:
        data_volume_score = 1.0
    elif comparable_count >= 20:
        data_volume_score = 0.7 + (0.3 * (comparable_count - 20) / 30)
    elif comparable_count >= 5:
        data_volume_score = 0.4 + (0.3 * (comparable_count - 5) / 15)
    elif comparable_count >= 1:
        data_volume_score = 0.2 + (0.2 * (comparable_count - 1) / 4)
    else:
        data_volume_score = 0.1

    if data_age_days <= 30:
        data_freshness_score = 1.0
    elif data_age_days <= 90:
        data_freshness_score = 0.8
    elif data_age_days <= 180:
        data_freshness_score = 0.6
    elif data_age_days <= 365:
        data_freshness_score = 0.4
    else:
        data_freshness_score = 0.2

    specificity_score = 0.3
    if has_year:
        specificity_score += 0.25
    if has_condition:
        specificity_score += 0.15
    if has_hours:
        specificity_score += 0.15
    if has_size_param:
        specificity_score += 0.15
    specificity_score = min(1.0, specificity_score)

    if comparable_cv is None or comparable_count < 5:
        variance_score = 0.3
    elif comparable_cv <= 0.5:
        variance_score = 1.0
    elif comparable_cv <= 1.0:
        variance_score = 0.7
    elif comparable_cv <= 1.5:
        variance_score = 0.5
    elif comparable_cv <= 2.0:
        variance_score = 0.3
    else:
        variance_score = 0.15

    composite = (
        (W_RCN_SOURCE * rcn_source_score)
        + (W_DATA_VOLUME * data_volume_score)
        + (W_DATA_FRESHNESS * data_freshness_score)
        + (W_SPECIFICITY * specificity_score)
        + (W_VARIANCE * variance_score)
    )
    composite = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, composite))

    return ConfidenceBreakdown(
        rcn_source_score=round(rcn_source_score, 3),
        data_volume_score=round(data_volume_score, 3),
        data_freshness_score=round(data_freshness_score, 3),
        specificity_score=round(specificity_score, 3),
        variance_score=round(variance_score, 3),
        composite=round(composite, 3),
    )


def classify_confidence(score: float) -> str:
    """Classify automation mode from confidence score."""
    if score >= AUTOMATED_CONFIDENCE_THRESHOLD:
        return "automated"
    if score >= HITL_REVIEW_THRESHOLD:
        return "hitl_review"
    return "manual"
