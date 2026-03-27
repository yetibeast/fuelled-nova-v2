"""Tests for confidence scoring — 5-dimension weighted composite.

Confidence determines automation level (automated / HITL review / manual).
"""
import pytest

from app.pricing_v2.rcn_engine.confidence import (
    ConfidenceBreakdown,
    calculate_confidence,
    classify_confidence,
    MIN_CONFIDENCE,
    MAX_CONFIDENCE,
    W_RCN_SOURCE,
    W_DATA_VOLUME,
    W_DATA_FRESHNESS,
    W_SPECIFICITY,
    W_VARIANCE,
)


# ── Confidence calculation ────────────────────────────────────────────


class TestCalculateConfidence:
    """Weighted composite from 5 dimensions."""

    def test_weights_sum_to_one(self):
        total = W_RCN_SOURCE + W_DATA_VOLUME + W_DATA_FRESHNESS + W_SPECIFICITY + W_VARIANCE
        assert total == pytest.approx(1.0)

    def test_high_confidence_scenario(self):
        result = calculate_confidence(
            rcn_confidence=0.9,
            comparable_count=50,
            comparable_cv=0.3,
            has_year=True, has_condition=True,
            has_hours=True, has_size_param=True,
            data_age_days=15,
        )
        assert result.composite >= 0.85
        assert result.data_volume_score == pytest.approx(1.0)
        assert result.data_freshness_score == pytest.approx(1.0)
        assert result.variance_score == pytest.approx(1.0)

    def test_low_confidence_scenario(self):
        result = calculate_confidence(
            rcn_confidence=0.3,
            comparable_count=0,
            comparable_cv=None,
            has_year=False, has_condition=False,
            has_hours=False, has_size_param=False,
            data_age_days=400,
        )
        assert result.composite < 0.35
        assert result.data_volume_score == pytest.approx(0.1)

    def test_composite_never_below_minimum(self):
        result = calculate_confidence(
            rcn_confidence=0.0, comparable_count=0,
            comparable_cv=None, has_year=False,
            has_condition=False, has_hours=False,
            has_size_param=False, data_age_days=9999,
        )
        assert result.composite >= MIN_CONFIDENCE

    def test_composite_never_above_maximum(self):
        result = calculate_confidence(
            rcn_confidence=2.0, comparable_count=1000,
            comparable_cv=0.01, has_year=True,
            has_condition=True, has_hours=True,
            has_size_param=True, data_age_days=0,
        )
        assert result.composite <= MAX_CONFIDENCE

    # ── Data volume dimension ─────────────────────────────────

    @pytest.mark.parametrize("count,expected", [
        (0, 0.1),
        (1, 0.2),
        (5, 0.4),
        (20, 0.7),
        (50, 1.0),
        (100, 1.0),
    ])
    def test_data_volume_tiers(self, count, expected):
        result = calculate_confidence(
            rcn_confidence=0.5, comparable_count=count,
            comparable_cv=None, has_year=False,
            has_condition=False, has_hours=False,
            has_size_param=False, data_age_days=30,
        )
        assert result.data_volume_score == pytest.approx(expected, abs=0.01)

    # ── Data freshness dimension ──────────────────────────────

    @pytest.mark.parametrize("days,expected", [
        (15, 1.0),
        (30, 1.0),
        (60, 0.8),
        (120, 0.6),
        (300, 0.4),
        (500, 0.2),
    ])
    def test_data_freshness_tiers(self, days, expected):
        result = calculate_confidence(
            rcn_confidence=0.5, comparable_count=10,
            comparable_cv=0.5, has_year=True,
            has_condition=True, has_hours=True,
            has_size_param=True, data_age_days=days,
        )
        assert result.data_freshness_score == pytest.approx(expected)

    # ── Specificity dimension ─────────────────────────────────

    def test_specificity_increases_with_more_data(self):
        none = calculate_confidence(
            rcn_confidence=0.5, comparable_count=10,
            comparable_cv=0.5, has_year=False,
            has_condition=False, has_hours=False,
            has_size_param=False, data_age_days=30,
        )
        all_specs = calculate_confidence(
            rcn_confidence=0.5, comparable_count=10,
            comparable_cv=0.5, has_year=True,
            has_condition=True, has_hours=True,
            has_size_param=True, data_age_days=30,
        )
        assert all_specs.specificity_score > none.specificity_score
        assert none.specificity_score == pytest.approx(0.3)

    # ── Variance dimension ────────────────────────────────────

    @pytest.mark.parametrize("cv,expected", [
        (0.3, 1.0),
        (0.5, 1.0),
        (0.8, 0.7),
        (1.2, 0.5),
        (1.8, 0.3),
        (2.5, 0.15),
    ])
    def test_variance_tiers(self, cv, expected):
        result = calculate_confidence(
            rcn_confidence=0.5, comparable_count=10,
            comparable_cv=cv, has_year=True,
            has_condition=True, has_hours=True,
            has_size_param=True, data_age_days=30,
        )
        assert result.variance_score == pytest.approx(expected)

    def test_variance_with_low_comps_defaults(self):
        result = calculate_confidence(
            rcn_confidence=0.5, comparable_count=3,
            comparable_cv=0.1, has_year=True,
            has_condition=True, has_hours=True,
            has_size_param=True, data_age_days=30,
        )
        assert result.variance_score == pytest.approx(0.3)


# ── Classification ────────────────────────────────────────────────────


class TestClassifyConfidence:
    """Maps composite score to automation level."""

    @pytest.mark.parametrize("score,expected", [
        (0.90, "automated"),
        (0.75, "automated"),
        (0.60, "hitl_review"),
        (0.40, "hitl_review"),
        (0.30, "manual"),
        (0.10, "manual"),
    ])
    def test_classification_tiers(self, score, expected):
        assert classify_confidence(score) == expected

    def test_boundary_at_automated_threshold(self):
        assert classify_confidence(0.75) == "automated"
        assert classify_confidence(0.749) == "hitl_review"

    def test_boundary_at_hitl_threshold(self):
        assert classify_confidence(0.40) == "hitl_review"
        assert classify_confidence(0.399) == "manual"
