"""C1 — Cost / LLM Spend Tracking tests."""
import json
import os
import tempfile
from unittest.mock import patch

import pytest


class TestCostHistory:
    """GET /api/admin/ai/cost-history"""

    def test_returns_30_day_structure(self, client, admin_headers):
        resp = client.get("/api/admin/ai/cost-history", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "daily" in data
        assert "monthly_total" in data
        assert "avg_daily" in data
        assert "projected_monthly" in data

    def test_daily_has_30_entries(self, client, admin_headers):
        resp = client.get("/api/admin/ai/cost-history", headers=admin_headers)
        data = resp.json()
        assert len(data["daily"]) == 30

    def test_daily_entry_shape(self, client, admin_headers):
        resp = client.get("/api/admin/ai/cost-history", headers=admin_headers)
        entry = resp.json()["daily"][0]
        assert "date" in entry
        assert "queries" in entry
        assert "cost" in entry
        # date format YYYY-MM-DD
        assert len(entry["date"]) == 10
        assert entry["date"][4] == "-"

    def test_cost_math(self, client, admin_headers):
        resp = client.get("/api/admin/ai/cost-history", headers=admin_headers)
        for entry in resp.json()["daily"]:
            expected_cost = round(entry["queries"] * 1.50, 2)
            assert entry["cost"] == expected_cost

    def test_requires_auth(self, client):
        resp = client.get("/api/admin/ai/cost-history")
        assert resp.status_code in (401, 403, 422)


class TestModelBreakdown:
    """GET /api/admin/ai/model-breakdown"""

    def test_returns_array(self, client, admin_headers):
        resp = client.get("/api/admin/ai/model-breakdown", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_entry_shape(self, client, admin_headers):
        resp = client.get("/api/admin/ai/model-breakdown", headers=admin_headers)
        data = resp.json()
        if data:  # may be empty if no log entries
            entry = data[0]
            assert "model" in entry
            assert "queries" in entry
            assert "cost" in entry
            assert "pct" in entry

    def test_requires_auth(self, client):
        resp = client.get("/api/admin/ai/model-breakdown")
        assert resp.status_code in (401, 403, 422)
