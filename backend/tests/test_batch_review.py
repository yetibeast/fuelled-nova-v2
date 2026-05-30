"""Tests for the parse → review → price flow (2026-05-29 batch robustness).

A human review step sits between parse and price so junk extractions (the
"Optimum Tech / Type of Equipment" form-style garbage) can be dropped before
any pricing runs and before a misleading "complete" is shown.
"""
import asyncio
import datetime

from app.api import batch
from app.api.batch import _batch_jobs, _parse_only


def _new_job(job_id: str) -> dict:
    job = {
        "job_id": job_id,
        "status": "parsing",
        "total": 0,
        "completed": 0,
        "current_item": None,
        "results": [],
        "errors": [],
        "summary": None,
        "items": None,
        "created_at": datetime.datetime.utcnow(),
    }
    _batch_jobs[job_id] = job
    return job


# ── Parse phase stops at review, does not price ───────────────────────────
def test_parse_only_sets_awaiting_review_without_pricing():
    job_id = "test-review-parse"
    _new_job(job_id)
    csv = b"title,category\nAriel JGK/4,compressor\nWaukesha VHP,engine\n"
    try:
        asyncio.run(_parse_only(job_id, csv, "f.csv"))
        job = _batch_jobs[job_id]
        assert job["status"] == "awaiting_review"
        assert [it["title"] for it in job["items"]] == ["Ariel JGK/4", "Waukesha VHP"]
        assert job["results"] == []  # nothing priced during parse
    finally:
        _batch_jobs.pop(job_id, None)


def test_parse_only_failure_sets_failed_status():
    job_id = "test-review-parsefail"
    _new_job(job_id)
    try:
        # Schema header present, zero data rows → HTTPException(400) in parse.
        asyncio.run(_parse_only(job_id, b"title,category\n", "f.csv"))
        assert _batch_jobs[job_id]["status"] == "failed"
        assert _batch_jobs[job_id].get("error")
    finally:
        _batch_jobs.pop(job_id, None)


# ── Price phase endpoint ──────────────────────────────────────────────────
def test_price_endpoint_unknown_job_returns_404(client, admin_headers):
    r = client.post(
        "/api/price/batch/nonexistent-job/price",
        json={"items": [{"title": "Pump", "category": ""}]},
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_price_endpoint_empty_items_returns_400(client, admin_headers):
    job_id = "test-review-empty"
    _new_job(job_id)
    _batch_jobs[job_id]["status"] = "awaiting_review"
    try:
        r = client.post(
            f"/api/price/batch/{job_id}/price",
            json={"items": []},
            headers=admin_headers,
        )
        assert r.status_code == 400
    finally:
        _batch_jobs.pop(job_id, None)


def test_price_endpoint_starts_pricing_kept_items(client, admin_headers, monkeypatch):
    async def fake_priced(_msg):
        return {
            "structured": {"valuation": {"fmv_low": 600, "fmv_high": 1100}},
            "response": "ok", "confidence": "MEDIUM",
            "tools_used": ["search_comparables"],
        }

    monkeypatch.setattr(batch, "run_pricing", fake_priced)
    job_id = "test-review-go"
    _new_job(job_id)
    _batch_jobs[job_id]["status"] = "awaiting_review"
    try:
        r = client.post(
            f"/api/price/batch/{job_id}/price",
            json={"items": [{"title": "3in ball valve", "category": "Valve"}]},
            headers=admin_headers,
        )
        assert r.status_code == 200
        # Endpoint flips the job out of review synchronously before backgrounding.
        assert _batch_jobs[job_id]["status"] in ("running", "completed")
    finally:
        _batch_jobs.pop(job_id, None)
