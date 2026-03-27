"""FastMCP server exposing Nova pricing tools for Claude Desktop / Claude Code."""
from __future__ import annotations

import asyncio
import os
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastmcp import FastMCP

from app.pricing_v2.tools import (
    fetch_listing,
    search_comparables,
    get_category_stats,
    lookup_rcn,
    calculate_fmv,
    check_equipment_risks,
)

mcp = FastMCP("fuelled-nova", port=8150)


@mcp.tool()
async def tool_search_comparables(
    keywords: list[str],
    category: str | None = None,
    price_min: float = 0,
    price_max: float = 99999999,
    max_results: int = 20,
) -> str:
    """Search the Fuelled marketplace database for comparable equipment listings. Keywords are OR'd against listing titles."""
    return await search_comparables(keywords, category, price_min, price_max, max_results)


@mcp.tool()
async def tool_get_category_stats(category: str) -> str:
    """Get aggregate pricing statistics for an equipment category. Returns count, average, min, and max asking price."""
    return await get_category_stats(category)


@mcp.tool()
async def tool_lookup_rcn(
    equipment_type: str,
    manufacturer: str | None = None,
    model: str | None = None,
    drive_type: str | None = None,
    stages: int | None = None,
    hp: int | None = None,
) -> str:
    """Look up Replacement Cost New (RCN) for equipment from gold reference tables. HP scaling: base * (target_hp / base_hp) ^ 0.6"""
    return await lookup_rcn(equipment_type, manufacturer, model, drive_type, stages, hp)


@mcp.tool()
def tool_calculate_fmv(
    rcn: float,
    equipment_class: str,
    age_years: int,
    condition: str = "B",
    hours: int | None = None,
    service: str = "sweet",
    vfd_equipped: bool = False,
    turnkey_package: bool = False,
    nace_rated: bool = False,
) -> str:
    """Calculate Fair Market Value using deterministic depreciation math. Returns FMV range (low/mid/high), list price, and walk-away floor."""
    return calculate_fmv(rcn, equipment_class, age_years, condition, hours, service, vfd_equipped, turnkey_package, nace_rated)


@mcp.tool()
def tool_check_equipment_risks(
    equipment_type: str,
    age_years: int,
    hours: int | None = None,
    idle_years: int | None = None,
    drive_type: str | None = None,
    plc_model: str | None = None,
    manufacturer: str | None = None,
    location_country: str = "CA",
    identical_units: int = 1,
    days_on_market: int | None = None,
    total_views: int | None = None,
) -> str:
    """Check for equipment-specific risk factors affecting valuation. Covers idle degradation, PLC obsolescence, cross-border costs, oversupply, and more."""
    return check_equipment_risks(equipment_type, age_years, hours, idle_years, drive_type, plc_model, manufacturer, location_country, identical_units, days_on_market, total_views)


@mcp.tool()
async def tool_fetch_listing(url: str) -> str:
    """Fetch equipment details from a listing URL. Extracts page content so you can read equipment specs before pricing."""
    return await fetch_listing(url)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
