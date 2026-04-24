"""Reports API — generate and list valuation reports."""
from __future__ import annotations

import json
import os
import datetime

import jwt
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response

from app.config import JWT_SECRET, LOG_DIR as _LOG_DIR
from app.pricing_v2.report import generate_report
from app.pricing_v2.report_onepager import generate_onepager
from app.pricing_v2.report_support import generate_support_report
from app.pricing_v2.portfolio_report import generate_portfolio_report

router = APIRouter(prefix="/reports", tags=["reports"])


def _require_auth(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]


def _log_report(entry: dict):
    os.makedirs(_LOG_DIR, exist_ok=True)
    path = os.path.join(_LOG_DIR, "reports_log.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


@router.get("/recent")
async def reports_recent(authorization: str = Header(None)):
    _require_auth(authorization)
    path = os.path.join(_LOG_DIR, "reports_log.jsonl")
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries[-20:]


@router.post("/generate")
async def generate(body: dict, authorization: str = Header(None)):
    _require_auth(authorization)

    report_type = body.get("type", "single")
    tier = body.get("tier")
    data = body.get("data", {})
    client = body.get("client", "")

    # ── Tier-based routing (takes priority) ──────────────────
    if tier == 1:
        structured = data.get("structured", data)
        user_message = data.get("user_message", "Equipment Valuation")
        docx_bytes = generate_onepager(structured, user_message, client)
        filename = "Fuelled_OnePager.docx"
        v = structured.get("valuation", {})
        title = user_message[:60]
        items = 1
        lo = v.get("fmv_low", 0) or 0
        hi = v.get("fmv_high", 0) or 0
        fmv_range = f"${lo:,.0f} – ${hi:,.0f}" if lo else "---"
    elif tier == 2:
        if isinstance(data, list):
            results = data
        elif "results" in data:
            results = data["results"]
        elif "structured" in data:
            # Single-item export from chat — wrap into results list
            results = [data]
        else:
            results = []
        summary = body.get("summary") or {
            "total": len(results),
            "completed": len(results),
            "failed": 0,
            "total_fmv_low": sum(
                (r.get("structured", {}).get("valuation", {}).get("fmv_low", 0) or 0)
                for r in results
            ),
            "total_fmv_high": sum(
                (r.get("structured", {}).get("valuation", {}).get("fmv_high", 0) or 0)
                for r in results
            ),
        }
        # For single-item reports, generate rich content via Claude report pass
        sections = None
        if len(results) == 1:
            r = results[0]
            structured = r.get("structured", {})
            response_text = r.get("response", "")
            user_msg = r.get("user_message", r.get("title", "Equipment"))
            from app.pricing_v2.report_content import generate_report_content
            sections = await generate_report_content(structured, response_text, user_msg, client, tier=2)
        docx_bytes = generate_support_report(results, summary, client, sections=sections)
        filename = "Fuelled_Support_Report.docx"
        items = len(results)
        title = f"Support Report — {items} items"
        fmv_range = f"${summary['total_fmv_low']:,.0f} – ${summary['total_fmv_high']:,.0f}"
    elif tier == 3:
        structured = data.get("structured", data)
        response_text = data.get("response_text", data.get("response", ""))
        user_message = data.get("user_message", "Equipment Valuation")
        sections = None
        try:
            from app.pricing_v2.report_content import generate_report_content
            sections = await generate_report_content(structured, response_text, user_message, client, tier=3)
        except Exception:
            pass
        docx_bytes = generate_report(
            structured=structured,
            response_text=response_text,
            user_message=user_message,
            sections=sections,
        )
        filename = "Fuelled_Valuation_Report.docx"
        v = structured.get("valuation", {})
        title = user_message[:60]
        items = 1
        lo = v.get("fmv_low", 0) or 0
        hi = v.get("fmv_high", 0) or 0
        fmv_range = f"${lo:,.0f} – ${hi:,.0f}" if lo else "---"

    # ── Legacy type-based routing (backward compat) ──────────
    elif report_type == "portfolio":
        results = data if isinstance(data, list) else data.get("results", [])
        summary = {
            "total": len(results),
            "completed": len(results),
            "failed": 0,
            "total_fmv_low": sum(
                (r.get("structured", {}).get("valuation", {}).get("fmv_low", 0) or 0)
                for r in results
            ),
            "total_fmv_high": sum(
                (r.get("structured", {}).get("valuation", {}).get("fmv_high", 0) or 0)
                for r in results
            ),
        }
        docx_bytes = generate_portfolio_report(results, summary)
        filename = "Fuelled_Portfolio_Report.docx"
        items = len(results)
        title = f"Portfolio — {items} items"
        fmv_range = f"${summary['total_fmv_low']:,.0f} – ${summary['total_fmv_high']:,.0f}"
    else:
        structured = data.get("structured", data)
        response_text = data.get("response_text", data.get("response", ""))
        user_message = data.get("user_message", "Equipment Valuation")
        docx_bytes = generate_report(
            structured=structured,
            response_text=response_text,
            user_message=user_message,
        )
        filename = "Fuelled_Valuation_Report.docx"
        v = structured.get("valuation", {})
        title = user_message[:60]
        items = 1
        lo = v.get("fmv_low", 0) or 0
        hi = v.get("fmv_high", 0) or 0
        fmv_range = f"${lo:,.0f} – ${hi:,.0f}" if lo else "---"

    _log_report({
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "type": report_type,
        "title": title,
        "items": items,
        "fmv_range": fmv_range,
        "status": "Generated",
    })

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
