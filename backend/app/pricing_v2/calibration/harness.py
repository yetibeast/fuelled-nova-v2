"""Calibration harness — run pricing engine against test fixtures and score results."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from app.pricing_v2.service import run_pricing


async def run_calibration(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    """Run each fixture through the pricing engine and compare to expected range."""
    results: list[dict[str, Any]] = []
    passed = 0
    failed = 0
    errors = 0

    for fixture in fixtures:
        try:
            resp = await run_pricing(fixture["description"])
            fmv = _extract_fmv(resp)
            low = fixture.get("expected_fmv_low", 0)
            high = fixture.get("expected_fmv_high", 0)

            if fmv is not None and low <= fmv <= high:
                status = "PASS"
                passed += 1
            elif fmv is not None:
                status = "FAIL"
                failed += 1
            else:
                status = "NO_FMV"
                failed += 1

            results.append({
                "id": fixture["id"],
                "description": fixture["description"][:80],
                "category": fixture.get("category", ""),
                "expected_low": low,
                "expected_high": high,
                "actual_fmv": fmv,
                "confidence": resp.get("confidence", "LOW"),
                "status": status,
                "tools_used": resp.get("tools_used", []),
            })
        except Exception as e:
            errors += 1
            results.append({
                "id": fixture["id"],
                "description": fixture["description"][:80],
                "category": fixture.get("category", ""),
                "expected_low": fixture.get("expected_fmv_low", 0),
                "expected_high": fixture.get("expected_fmv_high", 0),
                "actual_fmv": None,
                "confidence": "ERROR",
                "status": "ERROR",
                "error": str(e),
                "tools_used": [],
            })

    total = len(results) or 1
    return {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "accuracy_pct": round(passed / total * 100, 1),
        "results": results,
    }


def _extract_fmv(resp: dict) -> float | None:
    """Pull FMV from structured data or response text."""
    structured = resp.get("structured", {})
    if structured:
        for key in ("fmv", "fair_market_value", "estimated_value", "value"):
            val = structured.get(key)
            if val is not None:
                try:
                    return float(str(val).replace(",", "").replace("$", ""))
                except (ValueError, TypeError):
                    pass

    text = resp.get("response", "")
    patterns = [
        r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:USD)?",
        r"fair\s+market\s+value[^$]*\$\s*([\d,]+)",
        r"FMV[^$]*\$\s*([\d,]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue

    return None
