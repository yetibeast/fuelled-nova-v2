"""Tests for /api/admin/supply-targets — Phase 1 of Mark's supply-targeting ask."""
from __future__ import annotations


class TestSupplyTargetsAuth:
    """Auth boundaries — same shape as other admin endpoints."""

    def test_requires_auth(self, client):
        resp = client.get("/api/admin/supply-targets")
        assert resp.status_code == 401

    def test_requires_admin(self, client, user_headers):
        resp = client.get("/api/admin/supply-targets", headers=user_headers)
        assert resp.status_code == 403

    def test_admin_gets_200(self, client, admin_headers):
        resp = client.get("/api/admin/supply-targets", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestSupplyTargetsListings:
    """Drilldown endpoint follows the same auth pattern."""

    def test_drilldown_requires_admin(self, client, user_headers):
        resp = client.get(
            "/api/admin/supply-targets/allsurplus/310/listings",
            headers=user_headers,
        )
        assert resp.status_code == 403

    def test_drilldown_admin_200(self, client, admin_headers):
        resp = client.get(
            "/api/admin/supply-targets/allsurplus/310/listings",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestSupplyTargetsParams:
    """Parameter validation — defaults and bounds."""

    def test_defaults_apply_when_no_params(self, client, admin_headers):
        # Should not 400 without any query params
        resp = client.get("/api/admin/supply-targets", headers=admin_headers)
        assert resp.status_code == 200

    def test_min_listings_must_be_positive(self, client, admin_headers):
        resp = client.get(
            "/api/admin/supply-targets?min_listings=0",
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_limit_caps_at_5000(self, client, admin_headers):
        resp = client.get(
            "/api/admin/supply-targets?limit=10000",
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_source_filter_accepted(self, client, admin_headers):
        resp = client.get(
            "/api/admin/supply-targets?source=allsurplus",
            headers=admin_headers,
        )
        assert resp.status_code == 200
