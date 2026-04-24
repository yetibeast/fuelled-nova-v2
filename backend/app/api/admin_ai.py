from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Header, HTTPException

from app.config import JWT_SECRET, LOG_DIR as _LOG_DIR

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

_REFS_DIR = os.path.join(os.path.dirname(__file__), "..", "pricing_v2", "references")

# Sonnet pricing: $3/M input, $15/M output
_FALLBACK_COST = 0.05  # conservative fallback for entries without token data


def _entry_cost(entry: dict) -> float:
    """Return actual cost_usd if logged, else compute from tokens, else fallback."""
    if entry.get("cost_usd"):
        return float(entry["cost_usd"])
    inp = entry.get("input_tokens")
    out = entry.get("output_tokens")
    if inp is not None and out is not None:
        return (inp * 3 + out * 15) / 1_000_000
    return _FALLBACK_COST


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
async def ai_prompt(authorization: str = Header(None)):
    _require_admin(authorization)
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
async def ai_usage(authorization: str = Header(None)):
    _require_admin(authorization)
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
    total_cost = sum(_entry_cost(e) for e in entries)

    return {
        "total_queries": len(entries),
        "queries_today": today_count,
        "queries_this_week": week_count,
        "queries_this_month": month_count,
        "avg_tools_per_query": avg_tools,
        "confidence_distribution": dict(confidence_dist),
        "estimated_cost": round(total_cost, 2),
    }


@router.get("/ai/tools")
async def ai_tools(authorization: str = Header(None)):
    _require_admin(authorization)
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
async def ai_daily_usage(authorization: str = Header(None)):
    _require_admin(authorization)
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
async def ai_recent(authorization: str = Header(None)):
    _require_admin(authorization)
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
    """30-day daily cost breakdown using real token costs from log."""
    _require_admin(authorization)
    entries = _read_pricing_log()
    now = datetime.now(timezone.utc)

    days: dict[str, dict] = {}
    for i in range(30):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        days[d] = {"queries": 0, "cost": 0.0}

    for e in entries:
        ts = e.get("timestamp", "")[:10]
        if ts in days:
            days[ts]["queries"] += 1
            days[ts]["cost"] += _entry_cost(e)

    daily = [
        {"date": d, "queries": v["queries"], "cost": round(v["cost"], 4)}
        for d, v in sorted(days.items())
    ]

    total_cost = sum(d["cost"] for d in daily)
    total_queries = sum(d["queries"] for d in daily)
    avg_daily_queries = round(total_queries / 30, 1) if total_queries else 0
    avg_cost_per_query = total_cost / total_queries if total_queries else 0
    projected = round(avg_daily_queries * 30 * avg_cost_per_query, 2)

    return {
        "daily": daily,
        "monthly_total": round(total_cost, 2),
        "avg_daily": avg_daily_queries,
        "projected_monthly": projected,
    }


@router.get("/ai/model-breakdown")
async def ai_model_breakdown(authorization: str = Header(None)):
    """Queries and cost grouped by model, using real token costs."""
    _require_admin(authorization)
    entries = _read_pricing_log()
    model_data: dict[str, dict] = {}

    for e in entries:
        model = e.get("model", "claude-sonnet-4-20250514")
        if model not in model_data:
            model_data[model] = {"queries": 0, "cost": 0.0}
        model_data[model]["queries"] += 1
        model_data[model]["cost"] += _entry_cost(e)

    total = len(entries) or 1
    return [
        {
            "model": model,
            "queries": d["queries"],
            "cost": round(d["cost"], 2),
            "pct": round(d["queries"] / total * 100, 1),
        }
        for model, d in sorted(model_data.items(), key=lambda x: -x[1]["queries"])
    ]
