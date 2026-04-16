"""NF — Auth guard tests for all admin endpoints."""
import pytest


# All endpoints that require admin role
ADMIN_ENDPOINTS = [
    ("GET", "/api/admin/ai/cost-history"),
    ("GET", "/api/admin/ai/model-breakdown"),
    ("GET", "/api/admin/calibration/golden-fixtures"),
    ("GET", "/api/admin/calibration/results"),
    ("GET", "/api/admin/evidence/review-queue"),
    ("GET", "/api/admin/competitive/acquisition/summary"),
    ("GET", "/api/admin/competitive/acquisition/targets"),
]


class TestAdminEndpointsRejectNoAuth:
    """All admin endpoints must reject requests without auth token."""

    @pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
    def test_no_token(self, client, method, path):
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path)
        assert resp.status_code in (401, 403, 422), f"{method} {path} returned {resp.status_code}"


class TestAdminEndpointsRejectNonAdmin:
    """All admin endpoints must reject non-admin users."""

    @pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
    def test_user_token(self, client, user_headers, method, path):
        if method == "GET":
            resp = client.get(path, headers=user_headers)
        else:
            resp = client.post(path, headers=user_headers)
        assert resp.status_code == 403, f"{method} {path} returned {resp.status_code}"


class TestExpiredToken:
    """Expired tokens should be rejected."""

    def test_expired_token_rejected(self, client, expired_token):
        resp = client.get(
            "/api/admin/calibration/golden-fixtures",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401
