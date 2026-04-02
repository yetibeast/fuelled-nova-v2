"""Tests for scraper management endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

import pytest


class TestListScrapers:
    """GET /api/admin/scrapers"""

    def test_returns_empty_list_initially(self, client, admin_headers):
        resp = client.get("/api/admin/scrapers", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_returns_created_targets(self, client, admin_headers):
        client.post("/api/admin/scrapers", json={"name": "test_src", "url": "https://example.com"}, headers=admin_headers)
        resp = client.get("/api/admin/scrapers", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "test_src"
        assert data[0]["status"] == "active"
        assert data[0]["scraper_type"] == "scrapekit"

    def test_requires_admin(self, client, user_headers):
        resp = client.get("/api/admin/scrapers", headers=user_headers)
        assert resp.status_code == 403

    def test_requires_auth(self, client):
        resp = client.get("/api/admin/scrapers")
        assert resp.status_code == 401


class TestCreateScraper:
    """POST /api/admin/scrapers"""

    def test_creates_target(self, client, admin_headers):
        resp = client.post("/api/admin/scrapers", json={
            "name": "newsource",
            "url": "https://newsource.com",
            "scraper_type": "standalone",
            "schedule_cron": "0 */6 * * *",
        }, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "newsource"
        assert data["scraper_type"] == "standalone"
        assert data["schedule_cron"] == "0 */6 * * *"
        assert "id" in data

    def test_defaults_to_scrapekit(self, client, admin_headers):
        resp = client.post("/api/admin/scrapers", json={
            "name": "default_type",
            "url": "https://example.com",
        }, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["scraper_type"] == "scrapekit"

    def test_name_required(self, client, admin_headers):
        resp = client.post("/api/admin/scrapers", json={"url": "https://example.com"}, headers=admin_headers)
        assert resp.status_code == 400

    def test_requires_admin(self, client, user_headers):
        resp = client.post("/api/admin/scrapers", json={"name": "x"}, headers=user_headers)
        assert resp.status_code == 403


class TestUpdateScraper:
    """PUT /api/admin/scrapers/{target_id}"""

    def test_updates_schedule(self, client, admin_headers):
        create = client.post("/api/admin/scrapers", json={"name": "upd_test"}, headers=admin_headers)
        tid = create.json()["id"]
        resp = client.put(f"/api/admin/scrapers/{tid}", json={"schedule_cron": "0 0 * * *"}, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

    def test_rejects_empty_update(self, client, admin_headers):
        create = client.post("/api/admin/scrapers", json={"name": "upd_test2"}, headers=admin_headers)
        tid = create.json()["id"]
        resp = client.put(f"/api/admin/scrapers/{tid}", json={"invalid_field": "x"}, headers=admin_headers)
        assert resp.status_code == 400

    def test_404_for_missing_target(self, client, admin_headers):
        fake_id = str(uuid.uuid4())
        resp = client.put(f"/api/admin/scrapers/{fake_id}", json={"name": "x"}, headers=admin_headers)
        assert resp.status_code == 404


class TestDeleteScraper:
    """DELETE /api/admin/scrapers/{target_id}"""

    def test_deletes_target(self, client, admin_headers):
        create = client.post("/api/admin/scrapers", json={"name": "del_test"}, headers=admin_headers)
        tid = create.json()["id"]
        resp = client.delete(f"/api/admin/scrapers/{tid}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify gone
        listing = client.get("/api/admin/scrapers", headers=admin_headers)
        names = [s["name"] for s in listing.json()]
        assert "del_test" not in names

    def test_404_for_missing(self, client, admin_headers):
        resp = client.delete(f"/api/admin/scrapers/{uuid.uuid4()}", headers=admin_headers)
        assert resp.status_code == 404


class TestTriggerRun:
    """POST /api/admin/scrapers/{target_id}/run"""

    def test_sets_run_requested(self, client, admin_headers):
        create = client.post("/api/admin/scrapers", json={"name": "run_test"}, headers=admin_headers)
        tid = create.json()["id"]
        resp = client.post(f"/api/admin/scrapers/{tid}/run", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "run_requested"
        assert data["name"] == "run_test"

    def test_404_for_missing(self, client, admin_headers):
        resp = client.post(f"/api/admin/scrapers/{uuid.uuid4()}/run", headers=admin_headers)
        assert resp.status_code == 404


class TestPauseResume:
    """POST /api/admin/scrapers/{target_id}/pause and /resume"""

    def test_pause_sets_paused(self, client, admin_headers):
        create = client.post("/api/admin/scrapers", json={"name": "pause_test"}, headers=admin_headers)
        tid = create.json()["id"]
        resp = client.post(f"/api/admin/scrapers/{tid}/pause", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_resume_sets_active(self, client, admin_headers):
        create = client.post("/api/admin/scrapers", json={"name": "resume_test"}, headers=admin_headers)
        tid = create.json()["id"]
        # Pause first
        client.post(f"/api/admin/scrapers/{tid}/pause", headers=admin_headers)
        # Resume
        resp = client.post(f"/api/admin/scrapers/{tid}/resume", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_pause_404(self, client, admin_headers):
        resp = client.post(f"/api/admin/scrapers/{uuid.uuid4()}/pause", headers=admin_headers)
        assert resp.status_code == 404

    def test_resume_404(self, client, admin_headers):
        resp = client.post(f"/api/admin/scrapers/{uuid.uuid4()}/resume", headers=admin_headers)
        assert resp.status_code == 404


class TestRecentRuns:
    """GET /api/admin/scrapers/runs/recent"""

    def test_returns_empty_initially(self, client, admin_headers):
        resp = client.get("/api/admin/scrapers/runs/recent", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_requires_admin(self, client, user_headers):
        resp = client.get("/api/admin/scrapers/runs/recent", headers=user_headers)
        assert resp.status_code == 403


class TestTargetRuns:
    """GET /api/admin/scrapers/{target_id}/runs"""

    def test_returns_empty(self, client, admin_headers):
        create = client.post("/api/admin/scrapers", json={"name": "runs_test"}, headers=admin_headers)
        tid = create.json()["id"]
        resp = client.get(f"/api/admin/scrapers/{tid}/runs", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestHarvest:
    """POST /api/admin/scrapers/harvest"""

    def test_trigger_harvest(self, client, admin_headers):
        # Create the harvester target first
        client.post("/api/admin/scrapers", json={
            "name": "sold_price_harvester",
            "scraper_type": "harvester",
            "schedule_cron": "0 2 * * *",
        }, headers=admin_headers)
        resp = client.post("/api/admin/scrapers/harvest", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "harvest_requested"

    def test_requires_admin(self, client, user_headers):
        resp = client.post("/api/admin/scrapers/harvest", headers=user_headers)
        assert resp.status_code == 403


class TestHarvestStats:
    """GET /api/admin/scrapers/harvest/stats"""

    def test_returns_stats(self, client, admin_headers):
        resp = client.get("/api/admin/scrapers/harvest/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_closed_auctions" in data
        assert "harvested" in data
        assert "remaining" in data
        assert "sources" in data

    def test_requires_admin(self, client, user_headers):
        resp = client.get("/api/admin/scrapers/harvest/stats", headers=user_headers)
        assert resp.status_code == 403


class TestAuthGuards:
    """All scraper endpoints require admin auth."""

    def test_no_token_all_endpoints(self, client):
        endpoints = [
            ("GET", "/api/admin/scrapers", None),
            ("POST", "/api/admin/scrapers", {"name": "x"}),
            ("GET", "/api/admin/scrapers/runs/recent", None),
            ("POST", "/api/admin/scrapers/harvest", None),
            ("GET", "/api/admin/scrapers/harvest/stats", None),
        ]
        for method, path, body in endpoints:
            kwargs = {"json": body} if body else {}
            resp = getattr(client, method.lower())(path, **kwargs)
            assert resp.status_code == 401, f"{method} {path} should require auth"

    def test_expired_token(self, client, expired_token):
        headers = {"Authorization": f"Bearer {expired_token}"}
        resp = client.get("/api/admin/scrapers", headers=headers)
        assert resp.status_code == 401
