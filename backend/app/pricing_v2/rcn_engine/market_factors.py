"""Market and adjustment factors.

Consolidates NACE compliance premiums, H2S exposure, material/drive factors,
geography normalization, and WTI-based market heat.

Source: V1 rcn_v2/market_factors.py — all tables and formulas preserved exactly.
"""
from __future__ import annotations

# ── POLICY CONSTANTS ──────────────────────────────────────────────────

DEFAULT_NACE_PREMIUM = 1.15
DEFAULT_GEOGRAPHY_FACTOR = 1.0

NACE_COMPLIANCE_PREMIUM: dict[str, float] = {
    "compressor_package": 1.20,
    "compressor": 1.20,
    "compressors": 1.20,
    "separator": 1.18,
    "separators": 1.18,
    "vessel": 1.18,
    "tank": 1.15,
    "tanks": 1.15,
    "treater": 1.18,
    "treaters": 1.18,
    "heater": 1.15,
    "pump": 1.15,
    "pumps": 1.15,
    "generator": 1.05,
    "generators": 1.05,
    "e_house": 1.05,
    "electrical": 1.05,
    "pump_jack": 1.10,
    "trucks": 1.0,
    "truck": 1.0,
}

MATERIAL_FACTORS: dict[str, float] = {
    "carbon": 1.0,
    "carbon_steel": 1.0,
    "stainless": 2.5,
    "stainless_316": 2.5,
    "duplex": 3.0,
    "inconel": 4.0,
}

DRIVE_TYPE_FACTORS: dict[str, float] = {
    "electric": 1.0,
    "gas_engine": 1.15,
    "natural_gas": 1.15,
    "gas": 1.15,
    "diesel": 1.10,
}

GEOGRAPHY_FACTORS: dict[str, float] = {
    "alberta": 1.05, "ab": 1.05,
    "saskatchewan": 1.00, "sk": 1.00,
    "british_columbia": 0.98, "british columbia": 0.98, "bc": 0.98,
    "northern_bc": 0.90, "northern bc": 0.90,
    "ontario": 0.93, "on": 0.93,
    "quebec": 0.90, "qc": 0.90,
    "atlantic": 0.88,
    "permian": 1.12,
    "eagle_ford": 1.05, "eagle ford": 1.05,
    "texas": 1.08, "tx": 1.08,
    "dj_basin": 1.02, "dj basin": 1.02,
    "colorado": 1.02, "co": 1.02,
    "bakken": 0.98,
    "north_dakota": 0.98, "north dakota": 0.98, "nd": 0.98,
    "montana": 0.95, "mt": 0.95,
    "wyoming": 0.98, "wy": 0.98,
    "oklahoma": 1.00, "ok": 1.00,
    "louisiana": 1.00, "la": 1.00,
    "gulf_coast": 1.02, "gulf coast": 1.02,
    "midcontinent": 0.98,
    "appalachian": 0.92,
    "pennsylvania": 0.92, "pa": 0.92,
    "ohio": 0.92, "oh": 0.92,
    "west_virginia": 0.92, "west virginia": 0.92, "wv": 0.92,
    "michigan": 0.95, "mi": 0.95,
    "middle_east": 1.10, "middle east": 1.10,
    "north_sea": 1.10, "north sea": 1.10,
    "australia": 0.95,
    "latin_america": 0.88, "latin america": 0.88,
}

# WTI-based market heat: static fallbacks per category
STATIC_MARKET_FACTORS: dict[str, float] = {
    "compressor_package": 1.05, "compressor": 1.05, "compressors": 1.05,
    "separator": 1.05, "separators": 1.05,
    "tank": 1.05, "tanks": 1.05,
    "generator": 1.00, "generators": 1.00,
    "pump": 0.95, "pumps": 0.95,
    "treater": 1.00,
    "e_house": 1.00, "electrical": 1.00,
    "pump_jack": 1.00,
    "loader": 1.00, "loaders": 1.00,
    "excavator": 1.00, "excavators": 1.00,
    "truck": 1.00, "trucks": 1.00,
}

# WTI sensitivity by category (0.0 = immune, 1.0 = fully correlated)
COMMODITY_SENSITIVITY: dict[str, float] = {
    "compressor_package": 1.0, "compressor": 1.0, "compressors": 1.0,
    "separator": 1.0, "separators": 1.0, "vessel": 1.0,
    "pump_jack": 1.0,
    "treater": 0.9, "heater": 0.9,
    "tank": 0.8, "tanks": 0.8,
    "pump": 0.7, "pumps": 0.7,
    "generator": 0.5, "generators": 0.5,
    "e_house": 0.8, "electrical": 0.8,
    "loader": 0.2, "loaders": 0.2,
    "excavator": 0.2, "excavators": 0.2,
    "truck": 0.3, "trucks": 0.3,
    "trailer": 0.3, "trailers": 0.3,
}

# H2S NACE aging: max multipliers
H2S_MAX_NACE = 1.50
H2S_MAX_NON_NACE = 2.00


def _normalize_key(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def get_nace_premium(category: str | None, is_nace_compliant: bool) -> float:
    if not is_nace_compliant:
        return 1.0
    normalized = _normalize_key(category)
    return NACE_COMPLIANCE_PREMIUM.get(normalized, DEFAULT_NACE_PREMIUM)


def get_h2s_age_multiplier(
    years_h2s_exposure: float | int | None,
    is_nace_compliant: bool,
) -> float:
    """Return H2S-driven effective-age multiplier."""
    if years_h2s_exposure is None:
        return 1.0
    years = float(years_h2s_exposure)
    if years <= 0:
        return 1.0

    if is_nace_compliant:
        if years <= 5:
            return 1.0 + (0.02 * years)
        if years <= 15:
            return 1.10 + (0.02 * (years - 5))
        return min(H2S_MAX_NACE, 1.30 + (0.01 * (years - 15)))

    if years <= 3:
        return 1.0 + (0.10 * years)
    if years <= 10:
        return 1.30 + (0.05 * (years - 3))
    return min(H2S_MAX_NON_NACE, 1.65 + (0.03 * (years - 10)))


def get_material_factor(material: str | None) -> float:
    return MATERIAL_FACTORS.get(_normalize_key(material), 1.0)


def get_drive_factor(drive_type: str | None) -> float:
    return DRIVE_TYPE_FACTORS.get(_normalize_key(drive_type), 1.0)


def get_geography_factor(region: str | None) -> float:
    return GEOGRAPHY_FACTORS.get(_normalize_key(region), DEFAULT_GEOGRAPHY_FACTOR)


def get_market_heat_factor(
    wti_price: float | None,
    category: str | None,
) -> float:
    """Calculate market heat factor from WTI price and category sensitivity."""
    normalized = _normalize_key(category)
    if wti_price is None:
        return STATIC_MARKET_FACTORS.get(normalized, 1.0)

    sensitivity = COMMODITY_SENSITIVITY.get(normalized, 0.5)
    price = float(wti_price)

    if price > 80:
        raw_heat = min(1.20, 1.0 + (0.002 * (price - 80)))
    elif price >= 60:
        raw_heat = 1.0
    elif price >= 45:
        raw_heat = 1.0 - (0.007 * (60 - price))
    elif price >= 30:
        raw_heat = 0.895 - (0.010 * (45 - price))
    else:
        raw_heat = max(0.50, 0.745 - (0.008 * (30 - price)))

    return round(1.0 + (sensitivity * (raw_heat - 1.0)), 3)
