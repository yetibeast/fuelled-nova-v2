"""Normalize structured pricing output so downstream code never hits missing keys."""

_TOP_LEVEL_DEFAULTS: dict = {
    "valuation": {},
    "comparables": [],
    "risks": [],
    "market_context": None,
    "equipment_context": None,
    "condition_assessment": None,
    "cost_considerations": None,
    "scenario_analysis": None,
    "marketing_guidance": None,
    "missing_data_impact": None,
    "key_value_drivers": [],
    "assumptions": [],
    "sources": [],
}

_VALUATION_DEFAULTS: dict = {
    "fmv_low": None,
    "fmv_high": None,
    "fmv_mid": None,
    "rcn": None,
    "confidence": "LOW",
    "currency": "CAD",
    "list_price": None,
    "walkaway": None,
    "factors": [],
    "type": None,
    "title": None,
}


def normalize_structured(data: dict) -> dict:
    """Return a copy of *data* with all expected keys present and sensible defaults."""
    result = {}
    for key, default in _TOP_LEVEL_DEFAULTS.items():
        if key in data:
            result[key] = data[key]
        else:
            # Copy mutable defaults so callers can't mutate the template
            result[key] = list(default) if isinstance(default, list) else (dict(default) if isinstance(default, dict) else default)

    # Preserve any extra keys the agent returned
    for key in data:
        if key not in result:
            result[key] = data[key]

    # Sub-normalize valuation
    raw_val = result["valuation"]
    val = {}
    for key, default in _VALUATION_DEFAULTS.items():
        if key in raw_val:
            val[key] = raw_val[key]
        else:
            val[key] = list(default) if isinstance(default, list) else default
    # Preserve extra valuation keys
    for key in raw_val:
        if key not in val:
            val[key] = raw_val[key]
    result["valuation"] = val

    return result
