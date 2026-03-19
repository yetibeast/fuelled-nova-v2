from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Query
from app.db.session import get_session
from sqlalchemy import text

router = APIRouter()

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")


# ---------------------------------------------------------------------------
# 1. GET /valuations/recent
# ---------------------------------------------------------------------------

@router.get("/valuations/recent")
async def valuations_recent():
    path = os.path.join(_LOG_DIR, "pricing_log.jsonl")
    if not os.path.exists(path):
        return []

    with open(path, "r") as f:
        lines = f.readlines()

    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        structured = row.get("structured", {})
        valuation = structured.get("valuation", {})

        entries.append({
            "timestamp": row.get("timestamp"),
            "user_message": (row.get("user_message", "") or "")[:60],
            "fmv_low": valuation.get("fmv_low"),
            "fmv_mid": valuation.get("fmv_mid"),
            "fmv_high": valuation.get("fmv_high"),
            "confidence": row.get("confidence"),
            "tools_used": row.get("tools_used", []),
        })

    return entries[-10:]


# ---------------------------------------------------------------------------
# 2. GET /market/categories
# ---------------------------------------------------------------------------

@router.get("/market/categories")
async def market_categories():
    async with get_session() as session:
        result = await session.execute(text(
            """
            SELECT
                category_normalized,
                COUNT(*) as total,
                COUNT(CASE WHEN asking_price > 0 THEN 1 END) as with_price,
                AVG(CASE WHEN asking_price > 0 THEN asking_price END) as avg_price,
                MIN(CASE WHEN asking_price > 0 THEN asking_price END) as min_price,
                MAX(CASE WHEN asking_price > 0 THEN asking_price END) as max_price
            FROM listings
            WHERE asking_price > 0
            GROUP BY category_normalized
            ORDER BY COUNT(*) DESC
            LIMIT 20
            """
        ))
        rows = result.fetchall()

    return [
        {
            "category": row[0],
            "total": row[1],
            "with_price": row[2],
            "avg_price": float(row[3]) if row[3] is not None else None,
            "min_price": float(row[4]) if row[4] is not None else None,
            "max_price": float(row[5]) if row[5] is not None else None,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# 3. GET /market/sources
# ---------------------------------------------------------------------------

@router.get("/market/sources")
async def market_sources():
    async with get_session() as session:
        result = await session.execute(text(
            """
            SELECT
                source,
                COUNT(*) as total,
                COUNT(CASE WHEN asking_price > 0 THEN 1 END) as with_price,
                MAX(last_seen) as last_updated
            FROM listings
            GROUP BY source
            ORDER BY COUNT(*) DESC
            """
        ))
        rows = result.fetchall()

    out = []
    for row in rows:
        last_updated = row[3]
        if isinstance(last_updated, datetime):
            last_updated = last_updated.isoformat()
        elif last_updated is not None:
            last_updated = str(last_updated)

        out.append({
            "source": row[0],
            "total": row[1],
            "with_price": row[2],
            "last_updated": last_updated,
        })

    return out


# ---------------------------------------------------------------------------
# 4. POST /feedback
# ---------------------------------------------------------------------------

@router.post("/feedback")
async def post_feedback(body: dict):
    os.makedirs(_LOG_DIR, exist_ok=True)
    path = os.path.join(_LOG_DIR, "feedback_log.jsonl")

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rating": body.get("rating"),
        "comment": body.get("comment"),
        "conversation_id": body.get("conversation_id"),
        "message_index": body.get("message_index"),
        "structured_data": body.get("structured_data"),
        "user_message": body.get("user_message"),
        "response_text": body.get("response_text"),
    }

    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {"status": "saved"}


# ---------------------------------------------------------------------------
# 5. GET /feedback/recent
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 6. GET /market/opportunities
# ---------------------------------------------------------------------------

@router.get("/market/opportunities")
async def market_opportunities():
    async with get_session() as session:
        result = await session.execute(text(
            """
            WITH category_avg AS (
                SELECT category_normalized, AVG(asking_price) as avg_price, COUNT(*) as cnt
                FROM listings
                WHERE asking_price > 0
                GROUP BY category_normalized
                HAVING COUNT(*) > 20
            )
            SELECT l.title, l.asking_price, l.source, l.location, l.url,
                   ca.avg_price, ca.category_normalized,
                   ROUND((1 - l.asking_price / ca.avg_price) * 100) as discount_pct
            FROM listings l
            JOIN category_avg ca ON l.category_normalized = ca.category_normalized
            WHERE l.asking_price > 0
              AND l.asking_price < ca.avg_price * 0.4
              AND l.asking_price > 1000
            ORDER BY (ca.avg_price - l.asking_price) DESC
            LIMIT 10
            """
        ))
        rows = result.fetchall()

    return [
        {
            "title": row[0],
            "asking_price": float(row[1]) if row[1] is not None else None,
            "source": row[2],
            "location": row[3],
            "url": row[4],
            "avg_price": float(row[5]) if row[5] is not None else None,
            "category": row[6],
            "discount_pct": int(row[7]) if row[7] is not None else None,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# 7. GET /feedback/recent
# ---------------------------------------------------------------------------

@router.get("/feedback/recent")
async def feedback_recent(rating: Optional[str] = Query(default=None)):
    path = os.path.join(_LOG_DIR, "feedback_log.jsonl")
    if not os.path.exists(path):
        return []

    with open(path, "r") as f:
        lines = f.readlines()

    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        entries.append(row)

    if rating is not None:
        entries = [e for e in entries if e.get("rating") == rating]

    return entries[-20:]


# ---------------------------------------------------------------------------
# 8. GET /methodology/risk-rules
# ---------------------------------------------------------------------------

_RISK_RULES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "pricing_v2", "references", "risk_rules.md"
)


@router.get("/methodology/risk-rules")
async def methodology_risk_rules():
    if not os.path.exists(_RISK_RULES_PATH):
        return []

    with open(_RISK_RULES_PATH, "r") as f:
        content = f.read()

    categories: list[dict] = []
    current_category: dict | None = None
    current_rule: dict | None = None

    for line in content.split("\n"):
        stripped = line.strip()

        # Category heading (## level)
        if stripped.startswith("## ") and not stripped.startswith("### "):
            if current_rule and current_category:
                current_category["rules"].append(current_rule)
                current_rule = None
            if current_category:
                categories.append(current_category)
            current_category = {"title": stripped[3:].strip(), "rules": []}
            continue

        # Rule heading (### Rule:)
        if stripped.startswith("### ") and current_category is not None:
            if current_rule:
                current_category["rules"].append(current_rule)
            title = stripped[4:].strip()
            if title.lower().startswith("rule: "):
                title = title[6:]
            elif title.lower().startswith("typical overhaul costs"):
                # Skip table sub-headings, treat as part of previous rule
                continue
            current_rule = {
                "title": title,
                "trigger": "",
                "disclosure": "",
                "cost_impact": "",
                "valuation_impact": "",
            }
            continue

        if current_rule is None:
            continue

        # Parse fields
        if stripped.startswith("**Trigger:**"):
            current_rule["trigger"] = stripped.replace("**Trigger:**", "").strip()
        elif stripped.startswith("**Disclosure:**"):
            val = stripped.replace("**Disclosure:**", "").strip()
            current_rule["disclosure"] = val.strip('"')
        elif stripped.startswith("**Cost impact:**"):
            current_rule["cost_impact"] = stripped.replace("**Cost impact:**", "").strip()
        elif stripped.startswith("**Valuation impact:**"):
            current_rule["valuation_impact"] = stripped.replace("**Valuation impact:**", "").strip()

    # Flush last rule/category
    if current_rule and current_category:
        current_category["rules"].append(current_rule)
    if current_category:
        categories.append(current_category)

    return categories
