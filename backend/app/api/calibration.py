"""Calibration API — run golden fixtures or uploaded spreadsheets through the engine."""

from __future__ import annotations

import jwt
from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from app.config import JWT_SECRET
from app.pricing_v2.calibration.fixtures import GOLDEN_FIXTURES
from app.pricing_v2.calibration.harness import run_calibration
from app.pricing_v2.calibration.parser import parse_calibration_file

router = APIRouter(prefix="/admin/calibration", tags=["calibration"])

# Cache last run results in-memory
_last_results: dict | None = None


def _require_admin(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return payload["sub"]


@router.post("/run")
async def run_calibration_upload(
    file: UploadFile = File(...),
    authorization: str = Header(None),
):
    _require_admin(authorization)
    content = await file.read()
    try:
        fixtures = parse_calibration_file(content, file.filename or "upload.csv")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not fixtures:
        raise HTTPException(status_code=400, detail="No valid test cases found")

    results = await run_calibration(fixtures)
    global _last_results
    _last_results = results
    return results


@router.post("/golden")
async def run_golden_fixtures(authorization: str = Header(None)):
    _require_admin(authorization)
    results = await run_calibration(GOLDEN_FIXTURES)
    global _last_results
    _last_results = results
    return results


@router.get("/results")
async def get_results(authorization: str = Header(None)):
    _require_admin(authorization)
    if not _last_results:
        return {"total": 0, "results": [], "message": "No calibration run yet"}
    return _last_results


@router.get("/golden-fixtures")
async def get_golden_fixtures(authorization: str = Header(None)):
    _require_admin(authorization)
    return GOLDEN_FIXTURES
