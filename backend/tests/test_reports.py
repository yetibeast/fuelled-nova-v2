"""D3 — Reports API tests."""
import pytest


class TestRecentReports:
    """GET /api/reports/recent"""

    def test_returns_array(self, client, user_headers):
        resp = client.get("/api/reports/recent", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_requires_auth(self, client):
        resp = client.get("/api/reports/recent")
        assert resp.status_code in (401, 422)


class TestGenerateReport:
    """POST /api/reports/generate"""

    def test_generate_single_report(self, client, user_headers):
        resp = client.post(
            "/api/reports/generate",
            json={
                "type": "single",
                "data": {
                    "structured": {
                        "valuation": {
                            "manufacturer": "Ariel",
                            "model": "JGK/4",
                            "fmv_low": 380000,
                            "fmv_mid": 430000,
                            "fmv_high": 480000,
                            "rcn": 650000,
                            "category": "Gas Compressors",
                        },
                        "comparables": [],
                        "risks": [],
                    },
                    "response_text": "Based on analysis...",
                    "user_message": "2019 Ariel JGK/4 compressor",
                },
            },
            headers=user_headers,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def test_generate_portfolio_report(self, client, user_headers):
        resp = client.post(
            "/api/reports/generate",
            json={
                "type": "portfolio",
                "data": [
                    {
                        "title": "2019 Ariel JGK/4",
                        "structured": {
                            "valuation": {"fmv_low": 380000, "fmv_high": 480000}
                        },
                        "response": "Valued at...",
                        "confidence": "HIGH",
                    },
                    {
                        "title": "2017 Ariel JGE/2",
                        "structured": {
                            "valuation": {"fmv_low": 160000, "fmv_high": 220000}
                        },
                        "response": "Valued at...",
                        "confidence": "MEDIUM",
                    },
                ],
            },
            headers=user_headers,
        )
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_report_logged_after_generate(self, client, user_headers):
        # Generate
        client.post(
            "/api/reports/generate",
            json={
                "type": "single",
                "data": {
                    "structured": {"valuation": {"fmv_low": 100000, "fmv_high": 200000}},
                    "response_text": "test",
                    "user_message": "test equipment",
                },
            },
            headers=user_headers,
        )

        # Check recent
        resp = client.get("/api/reports/recent", headers=user_headers)
        data = resp.json()
        assert len(data) >= 1
        latest = data[-1]
        assert "timestamp" in latest
        assert latest["status"] == "Generated"

    def test_requires_auth(self, client):
        resp = client.post("/api/reports/generate", json={"type": "single", "data": {}})
        assert resp.status_code in (401, 422)
