"""Smoke tests for POST /api/v2/price — Nova Core pricing capability.

Scope: A2 dispatch only — deterministic Tier 1 happy path + unsupported-family
miss. LLM-driven identity resolution + reasoning composition land in the next
dispatch.
"""
from __future__ import annotations


def _ad_hoc_compressor_body() -> dict:
    """A compressor package with full structured fields — should hit Tier 1."""
    return {
        "ad_hoc": {
            "category": "Compressor Package",
            "make": "Ariel",
            "model": "JGK/4",
            "year": 2018,
            "horsepower": 540,
            "hours": 12000,
            "condition": "Good",
            "location": "Alberta, Canada",
        }
    }


def _ad_hoc_unsupported_body() -> dict:
    """Coiled tubing has no Tier 1 family ruleset — should return unsupported."""
    return {
        "ad_hoc": {
            "category": "Coiled Tubing Unit",
            "make": "Stewart & Stevenson",
            "model": "CTU-100",
            "year": 2015,
            "condition": "Good",
        }
    }


def test_tier1_compressor_returns_deterministic_pricing(client, admin_headers):
    """Tier 1 hit: compressor with year + HP + condition returns FMV range + methodology."""
    resp = client.post("/api/v2/price", json=_ad_hoc_compressor_body(), headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Required output fields per architecture spec
    assert body["status"] == "success"
    assert body["fmv_low"] > 0
    assert body["fmv_mid"] > body["fmv_low"]
    assert body["fmv_high"] > body["fmv_mid"]
    assert body["currency"] == "CAD"

    # Methodology string format: nova_v2/<family>/<rcn_source>
    methodology = body["methodology"]
    assert methodology.startswith("nova_v2/"), methodology
    assert methodology.count("/") == 2, methodology
    assert "compressor" in methodology.lower()

    # Tier 1 = deterministic path = no LLM tokens
    assert body["tier"] == 1
    assert isinstance(body["tools_used"], list)
    assert "rcn_engine" in body["tools_used"]
    assert "trace_id" in body
    assert body["confidence"] in ("LOW", "MEDIUM", "HIGH")


def test_unsupported_family_returns_structured_miss(client, admin_headers):
    """No Tier 1 ruleset for coiled tubing — should return unsupported_family,
    not 500. Tier 2 rulesets land in a parallel agent's worktree."""
    resp = client.post("/api/v2/price", json=_ad_hoc_unsupported_body(), headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["status"] == "unsupported_family"
    assert body["methodology"] == "nova_v2/unsupported"
    assert body["fmv_low"] is None
    assert body["fmv_mid"] is None
    assert body["fmv_high"] is None
    assert "trace_id" in body


def test_missing_input_returns_400(client, admin_headers):
    """Neither listing_id nor ad_hoc supplied — caller error."""
    resp = client.post("/api/v2/price", json={}, headers=admin_headers)
    assert resp.status_code == 400


def test_auth_required(client):
    """No bearer token — 401."""
    resp = client.post("/api/v2/price", json=_ad_hoc_compressor_body())
    assert resp.status_code == 401
