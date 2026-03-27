"""D1 — Evidence Flywheel tests."""
import pytest


class TestEvidenceCapture:
    """POST /api/evidence/capture"""

    def test_capture_returns_id(self, client, user_headers):
        resp = client.post(
            "/api/evidence/capture",
            json={
                "user_message": "Price a 2019 Ariel JGK/4",
                "structured_data": {
                    "valuation": {
                        "manufacturer": "Ariel",
                        "model": "JGK/4",
                        "category": "Gas Compressors",
                        "fmv_mid": 430000,
                        "fmv_low": 380000,
                    }
                },
                "confidence": "HIGH",
                "tools_used": ["search_comparables", "calculate_fmv"],
            },
            headers=user_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "evidence_id" in data
        assert data["evidence_id"].startswith("ev_")

    def test_capture_requires_auth(self, client):
        resp = client.post("/api/evidence/capture", json={"user_message": "test"})
        assert resp.status_code in (401, 422)


class TestFlagReview:
    """POST /api/evidence/flag-review"""

    def test_flag_existing_evidence(self, client, user_headers):
        # First capture
        capture = client.post(
            "/api/evidence/capture",
            json={
                "user_message": "test item",
                "structured_data": {"valuation": {"fmv_mid": 100000}},
                "confidence": "LOW",
                "tools_used": [],
            },
            headers=user_headers,
        )
        eid = capture.json()["evidence_id"]

        # Flag
        resp = client.post(
            "/api/evidence/flag-review",
            json={"evidence_id": eid, "comment": "Price too high"},
            headers=user_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "flagged"

    def test_flag_with_correction(self, client, user_headers):
        capture = client.post(
            "/api/evidence/capture",
            json={
                "user_message": "correction test",
                "structured_data": {"valuation": {"fmv_mid": 200000}},
                "confidence": "MEDIUM",
                "tools_used": [],
            },
            headers=user_headers,
        )
        eid = capture.json()["evidence_id"]

        resp = client.post(
            "/api/evidence/flag-review",
            json={"evidence_id": eid, "comment": "Should be lower", "user_correction": 150000},
            headers=user_headers,
        )
        assert resp.status_code == 200

    def test_flag_missing_id(self, client, user_headers):
        resp = client.post(
            "/api/evidence/flag-review",
            json={"comment": "no id"},
            headers=user_headers,
        )
        assert resp.status_code == 400

    def test_flag_nonexistent_id(self, client, user_headers):
        resp = client.post(
            "/api/evidence/flag-review",
            json={"evidence_id": "ev_doesnotexist", "comment": "bad"},
            headers=user_headers,
        )
        assert resp.status_code == 404


class TestReviewQueue:
    """GET /api/admin/evidence/review-queue"""

    def test_returns_flagged_items(self, client, admin_headers, user_headers):
        # Capture and flag
        capture = client.post(
            "/api/evidence/capture",
            json={
                "user_message": "queue test",
                "structured_data": {"valuation": {"fmv_mid": 300000}},
                "confidence": "HIGH",
                "tools_used": [],
            },
            headers=user_headers,
        )
        eid = capture.json()["evidence_id"]
        client.post(
            "/api/evidence/flag-review",
            json={"evidence_id": eid, "comment": "review me"},
            headers=user_headers,
        )

        resp = client.get("/api/admin/evidence/review-queue", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        ids = [r["id"] for r in data]
        assert eid in ids

    def test_requires_admin(self, client, user_headers):
        resp = client.get("/api/admin/evidence/review-queue", headers=user_headers)
        assert resp.status_code == 403


class TestPromoteEvidence:
    """POST /api/admin/evidence/promote/:id"""

    def test_promote_works(self, client, admin_headers, user_headers):
        # Capture, flag, then promote
        capture = client.post(
            "/api/evidence/capture",
            json={
                "user_message": "promote test",
                "structured_data": {"valuation": {"fmv_mid": 250000}},
                "confidence": "HIGH",
                "tools_used": [],
            },
            headers=user_headers,
        )
        eid = capture.json()["evidence_id"]
        client.post(
            "/api/evidence/flag-review",
            json={"evidence_id": eid, "comment": "promote this"},
            headers=user_headers,
        )

        resp = client.post(
            f"/api/admin/evidence/promote/{eid}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "promoted"

    def test_promote_nonexistent(self, client, admin_headers):
        resp = client.post(
            "/api/admin/evidence/promote/ev_doesnotexist",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_promoted_not_in_queue(self, client, admin_headers, user_headers):
        # Capture, flag, promote, check queue
        capture = client.post(
            "/api/evidence/capture",
            json={
                "user_message": "queue removal test",
                "structured_data": {"valuation": {"fmv_mid": 500000}},
                "confidence": "HIGH",
                "tools_used": [],
            },
            headers=user_headers,
        )
        eid = capture.json()["evidence_id"]
        client.post(
            "/api/evidence/flag-review",
            json={"evidence_id": eid, "comment": "check removal"},
            headers=user_headers,
        )
        client.post(f"/api/admin/evidence/promote/{eid}", headers=admin_headers)

        queue = client.get("/api/admin/evidence/review-queue", headers=admin_headers)
        ids = [r["id"] for r in queue.json()]
        assert eid not in ids

    def test_requires_admin(self, client, user_headers):
        resp = client.post(
            "/api/admin/evidence/promote/ev_test",
            headers=user_headers,
        )
        assert resp.status_code == 403
