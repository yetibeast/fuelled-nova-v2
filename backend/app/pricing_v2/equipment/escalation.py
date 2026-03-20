"""Escalation factor lookup and RCN escalation.

Determines the correct IPPI escalation multiplier for a given equipment class
and effective date, then computes escalated RCN in current-year CAD.

FX rates centralized here — single source of truth for all currency conversion.

Source: V1 escalation.py, ported as-is with centralized FX constants.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ── CENTRALIZED FX RATES (approximate, Feb 2026) ─────────────────────
# Single source of truth — do not duplicate elsewhere

FX_RATES: dict[str, float] = {
    "CAD": 1.000,
    "USD": 1.440,
    "AUD": 0.920,
    "EUR": 1.530,
    "GBP": 1.810,
    "NZD": 0.850,
    "KWD": 4.700,
}


def date_to_period_label(effective_date: date) -> str:
    """Convert a date to its half-year period label (e.g. '2022H1')."""
    half = "H1" if effective_date.month <= 6 else "H2"
    return f"{effective_date.year}{half}"


async def get_escalation_factor(
    session: AsyncSession,
    equipment_class: str,
    effective_date: date,
) -> dict | None:
    """Look up escalation factor for class+date, falling back to 'general'.

    Returns dict with {escalation_to_current, period_start} or None.
    """
    period_label = date_to_period_label(effective_date)

    result = await session.execute(
        text("""
            SELECT escalation_to_current, period_start
            FROM escalation_factors
            WHERE equipment_class = :cls AND period_label = :period
        """),
        {"cls": equipment_class, "period": period_label},
    )
    row = result.fetchone()

    if row is None and equipment_class != "general":
        result = await session.execute(
            text("""
                SELECT escalation_to_current, period_start
                FROM escalation_factors
                WHERE equipment_class = 'general' AND period_label = :period
            """),
            {"period": period_label},
        )
        row = result.fetchone()

    if row is None:
        return None

    return {
        "escalation_to_current": float(row.escalation_to_current),
        "period_start": row.period_start,
    }


def compute_escalated_rcn(
    original_value: float,
    original_currency: str,
    escalation_to_current: float,
    fx_rate: float | None = None,
) -> tuple[float, float]:
    """Return (escalated_rcn_cad, fx_rate_applied).

    escalated_rcn_cad = original_value x fx_rate x escalation_to_current
    """
    if fx_rate is None:
        fx_rate = FX_RATES.get(original_currency, 1.0)
    escalated = original_value * fx_rate * escalation_to_current
    return escalated, fx_rate
