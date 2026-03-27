"""C3 — Calibration Harness tests."""
import pytest


class TestGoldenFixtures:
    """GET /api/admin/calibration/golden-fixtures"""

    def test_returns_five_fixtures(self, client, admin_headers):
        resp = client.get("/api/admin/calibration/golden-fixtures", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 5

    def test_fixture_shape(self, client, admin_headers):
        resp = client.get("/api/admin/calibration/golden-fixtures", headers=admin_headers)
        fixture = resp.json()[0]
        assert "id" in fixture
        assert "description" in fixture
        assert "expected_fmv_low" in fixture
        assert "expected_fmv_high" in fixture
        assert "category" in fixture

    def test_fixture_ids(self, client, admin_headers):
        resp = client.get("/api/admin/calibration/golden-fixtures", headers=admin_headers)
        ids = [f["id"] for f in resp.json()]
        assert ids == ["GF-001", "GF-002", "GF-003", "GF-004", "GF-005"]

    def test_fmv_ranges_valid(self, client, admin_headers):
        resp = client.get("/api/admin/calibration/golden-fixtures", headers=admin_headers)
        for f in resp.json():
            assert f["expected_fmv_low"] > 0
            assert f["expected_fmv_high"] > f["expected_fmv_low"]

    def test_requires_admin(self, client, user_headers):
        resp = client.get("/api/admin/calibration/golden-fixtures", headers=user_headers)
        assert resp.status_code == 403

    def test_requires_auth(self, client):
        resp = client.get("/api/admin/calibration/golden-fixtures")
        assert resp.status_code in (401, 422)


class TestCalibrationResults:
    """GET /api/admin/calibration/results"""

    def test_empty_before_run(self, client, admin_headers):
        resp = client.get("/api/admin/calibration/results", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Either empty results or message about no run
        assert "results" in data or "message" in data

    def test_requires_admin(self, client, user_headers):
        resp = client.get("/api/admin/calibration/results", headers=user_headers)
        assert resp.status_code == 403


class TestCalibrationParser:
    """Unit tests for calibration CSV parser."""

    def test_parse_valid_csv(self):
        from app.pricing_v2.calibration.parser import parse_calibration_file

        csv_content = b"description,expected_fmv_low,expected_fmv_high,category\n2019 Ariel JGK/4,380000,480000,Gas Compressors\n"
        fixtures = parse_calibration_file(csv_content, "test.csv")
        assert len(fixtures) == 1
        assert fixtures[0]["description"] == "2019 Ariel JGK/4"
        assert fixtures[0]["expected_fmv_low"] == 380000

    def test_parse_empty_csv(self):
        from app.pricing_v2.calibration.parser import parse_calibration_file

        csv_content = b"description,expected_fmv_low,expected_fmv_high,category\n"
        fixtures = parse_calibration_file(csv_content, "test.csv")
        assert len(fixtures) == 0

    def test_unsupported_format(self):
        from app.pricing_v2.calibration.parser import parse_calibration_file

        with pytest.raises(ValueError):
            parse_calibration_file(b"data", "test.xlsx")
