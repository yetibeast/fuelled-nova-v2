from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Header, HTTPException

from app.config import JWT_SECRET

router = APIRouter(prefix="/admin")


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

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
_REFS_DIR = os.path.join(os.path.dirname(__file__), "..", "pricing_v2", "references")


def _read_pricing_log() -> list[dict]:
    path = os.path.join(_LOG_DIR, "pricing_log.jsonl")
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


@router.get("/ai/prompt")
async def ai_prompt():
    from app.pricing_v2.prompts import build_system_prompt

    prompt = build_system_prompt()

    ref_files = []
    if os.path.isdir(_REFS_DIR):
        for name in sorted(os.listdir(_REFS_DIR)):
            path = os.path.join(_REFS_DIR, name)
            if os.path.isfile(path):
                ref_files.append({"name": name, "size_bytes": os.path.getsize(path)})

    return {
        "prompt_text": prompt,
        "prompt_length": len(prompt),
        "reference_files": ref_files,
        "model": "claude-sonnet-4-20250514",
    }


@router.get("/ai/usage")
async def ai_usage():
    entries = _read_pricing_log()
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    week_ago = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    today_count = 0
    week_count = 0
    month_count = 0
    total_tools = 0
    confidence_dist: Counter = Counter()

    for e in entries:
        ts = e.get("timestamp", "")
        total_tools += len(e.get("tools_used", []))
        confidence_dist[e.get("confidence", "UNKNOWN")] += 1

        if ts[:10] == today_str:
            today_count += 1
        try:
            dt = datetime.fromisoformat(ts.rstrip("Z")).replace(tzinfo=timezone.utc)
            if dt >= week_ago:
                week_count += 1
            if dt >= month_start:
                month_count += 1
        except (ValueError, TypeError):
            pass

    avg_tools = round(total_tools / len(entries), 1) if entries else 0

    return {
        "total_queries": len(entries),
        "queries_today": today_count,
        "queries_this_week": week_count,
        "queries_this_month": month_count,
        "avg_tools_per_query": avg_tools,
        "confidence_distribution": dict(confidence_dist),
        "estimated_cost": round(len(entries) * 1.50, 2),
    }


@router.get("/ai/tools")
async def ai_tools():
    entries = _read_pricing_log()
    tool_counts: Counter = Counter()

    for e in entries:
        for t in e.get("tools_used", []):
            tool_counts[t] += 1

    total_queries = len(entries) or 1

    return [
        {
            "tool_name": name,
            "call_count": count,
            "avg_per_query": round(count / total_queries, 2),
        }
        for name, count in tool_counts.most_common()
    ]


@router.get("/ai/daily-usage")
async def ai_daily_usage():
    entries = _read_pricing_log()
    now = datetime.now(timezone.utc)
    days: dict[str, int] = {}
    for i in range(7):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        days[d] = 0
    for e in entries:
        ts = e.get("timestamp", "")[:10]
        if ts in days:
            days[ts] += 1
    return [{"date": d, "count": c} for d, c in sorted(days.items())]


@router.get("/ai/recent")
async def ai_recent():
    entries = _read_pricing_log()
    recent = entries[-3:] if len(entries) >= 3 else entries
    recent.reverse()
    return [
        {
            "title": e.get("user_message", "")[:60],
            "confidence": e.get("confidence", "LOW"),
            "timestamp": e.get("timestamp", ""),
        }
        for e in recent
    ]


@router.get("/ai/cost-history")
async def ai_cost_history(authorization: str = Header(None)):
    """30-day daily cost breakdown: queries + estimated cost per day."""
    _require_admin(authorization)
    entries = _read_pricing_log()
    now = datetime.now(timezone.utc)
    cost_per_query = 1.50

    days: dict[str, int] = {}
    for i in range(30):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        days[d] = 0

    for e in entries:
        ts = e.get("timestamp", "")[:10]
        if ts in days:
            days[ts] += 1

    daily = [
        {"date": d, "queries": c, "cost": round(c * cost_per_query, 2)}
        for d, c in sorted(days.items())
    ]

    total_month = sum(d["queries"] for d in daily)
    avg_daily = round(total_month / 30, 1) if total_month else 0
    projected = round(avg_daily * 30 * cost_per_query, 2)

    return {
        "daily": daily,
        "monthly_total": round(total_month * cost_per_query, 2),
        "avg_daily": avg_daily,
        "projected_monthly": projected,
    }


@router.get("/ai/model-breakdown")
async def ai_model_breakdown(authorization: str = Header(None)):
    """Queries and cost grouped by model."""
    _require_admin(authorization)
    entries = _read_pricing_log()
    cost_per_query = 1.50
    model_counts: Counter = Counter()

    for e in entries:
        model = e.get("model", "claude-sonnet-4-20250514")
        model_counts[model] += 1

    return [
        {
            "model": model,
            "queries": count,
            "cost": round(count * cost_per_query, 2),
            "pct": round(count / len(entries) * 100, 1) if entries else 0,
        }
        for model, count in model_counts.most_common()
    ]
