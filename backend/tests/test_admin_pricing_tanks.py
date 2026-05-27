"""Smoke tests for POST /api/admin/pricing/tanks/run — Tier 2.5 bulk runner.

Scope: endpoint shape, auth gating, source-aware year default, and that the
engine actually produces a bracket-anchored RCN for a 500 BBL tank vs the
prior flat-$50k behaviour.
"""
from __future__ import annotations

import pytest

from app.api.admin_pricing_tanks import _default_year_for_source, _price_one_tank


# ── Unit: source-aware year default ───────────────────────────────────


class TestDefaultYearForSource:
    def test_fuelled_default(self):
        assert _default_year_for_source("fuelled") == 2015

    def test_ironplanet_default(self):
        assert _default_year_for_source("ironplanet") == 2018

    def test_kijiji_default(self):
        assert _default_year_for_source("kijiji") == 2010

    def test_case_insensitive(self):
        assert _default_year_for_source("IronPlanet") == 2018

    def test_unknown_source_falls_back_to_2015(self):
        assert _default_year_for_source("machinio") == 2015
        assert _default_year_for_source("govdeals") == 2015

    def test_none_falls_back_to_2015(self):
        assert _default_year_for_source(None) == 2015


# ── Unit: per-row pricing produces bracket-anchored RCN ───────────────


class TestPriceOneTank:
    def test_500_bbl_tank_uses_bracket_not_flat_50k(self):
        """A 500 BBL listing extracts to volume_bbl=500, engine uses the seed
        ladder. With the legacy flat $50k path, fmv_mid would not depend on
        volume at all — confirm it does now."""
        row_500 = {
            "id": "test-1", "title": "500 BBL Storage Tank",
            "category": "tanks", "source": "ironplanet",
        }
        row_100 = {
            "id": "test-2", "title": "100 BBL Production Tank",
            "category": "tanks", "source": "ironplanet",
        }
        priced_500 = _price_one_tank(row_500)
        priced_100 = _price_one_tank(row_100)
        assert priced_500["volume_bbl"] == pytest.approx(500)
        assert priced_100["volume_bbl"] == pytest.approx(100)
        # 500 BBL should price meaningfully higher than 100 BBL (seed mids $40k vs $12k newbuild).
        assert priced_500["fmv_mid"] > priced_100["fmv_mid"]

    def test_year_default_applied_when_missing(self):
        """No year on the listing → source-aware default applied (not a crash)."""
        row = {
            "id": "test-3", "title": "400 BBL Tank",
            "category": "tanks", "source": "kijiji",
        }
        priced = _price_one_tank(row)
        assert priced["year_used"] == 2010  # kijiji default
        assert priced["fmv_mid"] > 0

    def test_explicit_year_wins_over_default(self):
        row = {
            "id": "test-4", "title": "400 BBL Tank",
            "category": "tanks", "source": "kijiji", "year": 2022,
        }
        priced = _price_one_tank(row)
        assert priced["year_used"] == 2022

    def test_no_volume_still_produces_price(self):
        """Tank with no BBL token should still get a price (flat fallback)."""
        row = {
            "id": "test-5", "title": "Storage Tank",
            "category": "tanks", "source": "fuelled",
        }
        priced = _price_one_tank(row)
        assert priced["fmv_mid"] > 0
        assert priced["volume_bbl"] is None


# ── Endpoint: auth + happy path ───────────────────────────────────────


def _seed_tank_listings(monkeypatch):
    """Inject a small tank fixture into the in-memory test DB."""
    from tests import conftest
    conftest._db.listings.extend([
        {
            "id": "tnk-1", "title": "500 BBL Storage Tank",
            "category": "tanks", "make": None, "model": None, "year": None,
            "source": "ironplanet", "fair_value": None, "is_active": True,
            "condition": None, "location": None, "description": None,
            "horsepower": None, "hours": None, "weight_lbs": None,
        },
        {
            "id": "tnk-2", "title": "100 BBL Production Tank",
            "category": "tanks", "make": None, "model": None, "year": 2015,
            "source": "fuelled", "fair_value": None, "is_active": True,
            "condition": None, "location": None, "description": None,
            "horsepower": None, "hours": None, "weight_lbs": None,
        },
        {
            "id": "tnk-3", "title": "Compressor (not a tank — should be skipped)",
            "category": "compressors", "make": None, "model": None, "year": 2018,
            "source": "fuelled", "fair_value": None, "is_active": True,
            "condition": None, "location": None, "description": None,
            "horsepower": None, "hours": None, "weight_lbs": None,
        },
    ])


def test_tanks_run_endpoint_requires_admin_auth(client):
    """No bearer token → 401."""
    resp = client.post("/api/admin/pricing/tanks/run")
    assert resp.status_code == 401


def test_tanks_run_endpoint_rejects_non_admin(client, user_headers):
    """Analyst-role token → 403."""
    resp = client.post("/api/admin/pricing/tanks/run", headers=user_headers)
    assert resp.status_code == 403


def test_tanks_run_endpoint_smoke(client, admin_headers, monkeypatch):
    """Happy path: tank rows priced, non-tank rows ignored, run_id returned."""
    _seed_tank_listings(monkeypatch)
    resp = client.post("/api/admin/pricing/tanks/run", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "run_id" in body
    assert body["methodology"] == "nova_v2/tank/seed-rcn"
    # Both tank listings should price; the compressor should be skipped.
    assert body["total"] == 2
    assert body["succeeded"] == 2
    assert body["failed"] == 0
