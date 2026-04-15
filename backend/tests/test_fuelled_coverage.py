"""Tests for GET /api/admin/fuelled/coverage endpoint."""
from __future__ import annotations


class TestFuelledCoverage:
    """Coverage stats endpoint tests."""

    def test_requires_auth(self, client):
        """401 without token."""
        resp = client.get("/api/admin/fuelled/coverage")
        assert resp.status_code == 401

    def test_returns_coverage_stats(self, client, admin_headers):
        """All expected fields are present in the response."""
        resp = client.get("/api/admin/fuelled/coverage", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = {
            "total", "asking_price_count", "asking_price_pct",
            "valued_count", "valued_pct", "ai_only_count",
            "unpriced", "by_tier", "by_category", "completeness_avg",
        }
        assert expected_keys.issubset(data.keys())

    def test_percentages_are_valid(self, client, admin_headers):
        """Percentages are 0-100 and valued_pct >= asking_price_pct."""
        resp = client.get("/api/admin/fuelled/coverage", headers=admin_headers)
        data = resp.json()
        assert 0 <= data["asking_price_pct"] <= 100
        assert 0 <= data["valued_pct"] <= 100
        assert data["valued_pct"] >= data["asking_price_pct"]

    def test_counts_match_seeds(self, client, admin_headers):
        """Counts align with the 6 seeded fuelled listings."""
        resp = client.get("/api/admin/fuelled/coverage", headers=admin_headers)
        data = resp.json()
        # 6 total seeded fuelled listings
        assert data["total"] == 6
        # 1 has asking_price (fu-t1-priced = 450000)
        assert data["asking_price_count"] == 1
        # 5 have no asking_price and no fair_value
        assert data["unpriced"] == 5

    def test_analyst_can_view(self, client, user_headers):
        """Non-admin users (analysts) can access this read-only endpoint."""
        resp = client.get("/api/admin/fuelled/coverage", headers=user_headers)
        assert resp.status_code == 200
