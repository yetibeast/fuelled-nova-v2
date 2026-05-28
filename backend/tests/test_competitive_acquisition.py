"""Competitive stale-inventory acquisition tests."""


class TestCompetitiveSummary:
    def test_stale_count_excludes_fuelled_rows(self, client, user_headers):
        # Threshold is 60 days (loosened 2026-05-06 — see _CATEGORY_THRESHOLDS).
        # 6 non-fuelled seeded listings are old enough with a recent last_seen
        # and a price (5 with asking_price, 1 auction row with current_bid only —
        # the latter validates the 2026-05-26 COALESCE fix).
        resp = client.get("/api/competitive/summary", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["stale_count"] == 6


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

    def test_score_only_with_cap_zero_is_legacy(self, client, user_headers):
        # sort=score_only & cap=0 reproduces the original pure-score ordering.
        resp = client.get(
            "/api/competitive/stale-targets?sort=score_only&cap_per_seller=0",
            headers=user_headers,
        )
        assert resp.status_code == 200
        ids = {row["source_listing_id"] for row in resp.json()}
        assert "cmp-stale-dealer" in ids
        assert "cmp-stale-bid-only" in ids

    def test_seller_diverse_default_surfaces_distinct_names(self, client, user_headers):
        # Default mode pushes named-seller rows to the top so anonymous
        # high-quality dealer rows don't bury auction sellers with names.
        resp = client.get("/api/competitive/stale-targets", headers=user_headers)
        assert resp.status_code == 200
        rows = resp.json()
        # Every row with a seller_name should precede every row without one.
        seen_anon = False
        for row in rows:
            if row.get("seller_name"):
                assert not seen_anon, (
                    "named-seller row appeared after an anonymous row; "
                    "two-pass ordering broken"
                )
            else:
                seen_anon = True
        # Within the named section each seller appears at most once by default.
        names = [r["seller_name"] for r in rows if r.get("seller_name")]
        assert len(names) == len(set(names)), f"duplicate sellers in default top: {names}"

    def test_bid_only_auction_row_surfaces_with_seller(self, client, user_headers):
        # Regression for 2026-05-26: auction rows priced via current_bid (no
        # asking_price) used to be silently dropped by the asking_price > 0
        # gate, hiding their seller_name from the supply-targets workflow.
        resp = client.get("/api/competitive/stale-targets", headers=user_headers)
        assert resp.status_code == 200
        bid_row = next(
            (row for row in resp.json() if row["source_listing_id"] == "cmp-stale-bid-only"),
            None,
        )
        assert bid_row is not None, "AllSurplus-style bid-only row missing from stale-targets"
        assert bid_row["seller_name"] == "Bid-Only Test Seller"
        assert bid_row["current_bid"] == 285000
        # asking_price field carries the effective list price so the frontend
        # table and CSV column stay populated.
        assert bid_row["asking_price"] == 285000


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
