"""Competitive stale-inventory acquisition tests."""


class TestCompetitiveSummary:
    def test_stale_count_excludes_fuelled_rows(self, client, user_headers):
        resp = client.get("/api/competitive/summary", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["stale_count"] == 2


class TestCompetitiveStaleTargets:
    def test_requires_auth(self, client):
        resp = client.get("/api/competitive/stale-targets")
        assert resp.status_code == 401

    def test_returns_competitor_only_ranked_targets(self, client, user_headers):
        resp = client.get("/api/competitive/stale-targets", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        ids = {row["source_listing_id"] for row in data}
        assert "cmp-stale-dealer" in ids
        assert "cmp-stale-auction" in ids
        assert "fu-stale-ignored" not in ids
        assert all(row["source"].lower() != "fuelled" for row in data)
        assert all("acquisition_score" in row for row in data)

    def test_promotable_only_filters_auction_rows(self, client, user_headers):
        resp = client.get("/api/competitive/stale-targets?promotable_only=true", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        ids = {row["source_listing_id"] for row in data}
        assert "cmp-stale-dealer" in ids
        assert "cmp-stale-auction" not in ids


class TestCompetitiveAcquisitionQueue:
    def test_summary_requires_admin(self, client, user_headers):
        resp = client.get("/api/admin/competitive/acquisition/summary", headers=user_headers)
        assert resp.status_code == 403

    def test_returns_empty_summary_initially(self, client, admin_headers):
        resp = client.get("/api/admin/competitive/acquisition/summary", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_returns_empty_targets_initially(self, client, admin_headers):
        resp = client.get("/api/admin/competitive/acquisition/targets", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_promote_creates_target(self, client, admin_headers):
        resp = client.post(
            "/api/admin/competitive/acquisition/promote",
            json={"source_listing_id": "cmp-stale-dealer", "note": "Review for acquisition"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_listing_id"] == "cmp-stale-dealer"
        assert data["status"] == "new"
        assert data["promotable"] is True

    def test_status_update_persists(self, client, admin_headers):
        promoted = client.post(
            "/api/admin/competitive/acquisition/promote",
            json={"source_listing_id": "cmp-stale-dealer"},
            headers=admin_headers,
        ).json()
        resp = client.post(
            f"/api/admin/competitive/acquisition/{promoted['id']}/status",
            json={"status": "contacted", "notes": "Called dealer"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "contacted"

    def test_draft_generation_returns_payload(self, client, admin_headers):
        promoted = client.post(
            "/api/admin/competitive/acquisition/promote",
            json={"source_listing_id": "cmp-stale-dealer"},
            headers=admin_headers,
        ).json()
        resp = client.post(
            f"/api/admin/competitive/acquisition/{promoted['id']}/draft",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "draft_payload" in data
        assert data["draft_payload"]["competitor_source"] == "machinio"
