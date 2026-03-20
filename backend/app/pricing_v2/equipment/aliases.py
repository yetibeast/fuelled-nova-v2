"""Manufacturer/model alias maps and brand sets.

Pure functions — no database, no async, no side effects.
Centralizes the alias dictionaries scattered across V1 resolver.py.

Source: V1 resolver.py brand lists + domain knowledge from gold tables.
"""
from __future__ import annotations

import re

# ── BRAND SETS (used by parsing.py to classify compound descriptions) ─

DRIVER_BRANDS: frozenset[str] = frozenset({
    "waukesha", "cat", "caterpillar", "cummins", "john deere",
    "detroit diesel", "weg", "siemens", "teco", "abb",
    "rolls-royce", "mtu", "deutz", "perkins", "volvo penta",
    "man", "jenbacher", "wartsila",
})

COMPRESSOR_BRANDS: frozenset[str] = frozenset({
    "ariel", "joy", "cooper", "ge", "ir", "ingersoll rand",
    "dresser-rand", "atlas copco", "sullair", "frick",
    "bitzer", "mycom", "howden", "man turbo", "siemens",
    "elliott", "fs-elliott", "kobelco", "hitachi",
    "gemini", "ajax",
})

GENERATOR_BRANDS: frozenset[str] = frozenset({
    "stamford", "leroy-somer", "marathon", "mecc alte",
    "solar turbines", "heatec",
})

PUMP_BRANDS: frozenset[str] = frozenset({
    "gardner denver", "national oilwell", "nov", "flowserve",
    "grundfos", "sulzer", "ksb", "weir", "goulds",
    "cornell", "pioneer", "magnum", "csm",
})

ALL_EQUIPMENT_BRANDS = COMPRESSOR_BRANDS | GENERATOR_BRANDS | PUMP_BRANDS

# ── MANUFACTURER ALIASES ─────────────────────────────────────────────

MANUFACTURER_ALIASES: dict[str, str] = {
    "cat": "Caterpillar",
    "caterpillar": "Caterpillar",
    "ir": "Ingersoll Rand",
    "ingersoll rand": "Ingersoll Rand",
    "ingersoll-rand": "Ingersoll Rand",
    "ge": "General Electric",
    "general electric": "General Electric",
    "dresser-rand": "Dresser-Rand",
    "dresser rand": "Dresser-Rand",
    "atlas copco": "Atlas Copco",
    "john deere": "John Deere",
    "detroit diesel": "Detroit Diesel",
    "rolls-royce": "Rolls-Royce",
    "volvo penta": "Volvo Penta",
    "gardner denver": "Gardner Denver",
    "national oilwell": "National Oilwell Varco",
    "nov": "National Oilwell Varco",
    "solar turbines": "Solar Turbines",
    "leroy-somer": "Leroy-Somer",
    "mecc alte": "Mecc Alte",
    "man turbo": "MAN Turbo",
    "fs-elliott": "FS-Elliott",
}

# ── MODEL ALIASES ────────────────────────────────────────────────────
# Normalizes common model number variations (missing slashes, dashes)

MODEL_ALIASES: dict[str, str] = {
    "jgk4": "JGK/4",
    "jgk-4": "JGK/4",
    "jgk/4": "JGK/4",
    "jge2": "JGE/2",
    "jge-2": "JGE/2",
    "jge/2": "JGE/2",
    "jgj2": "JGJ/2",
    "jgj-2": "JGJ/2",
    "jgj/2": "JGJ/2",
    "jgc6": "JGC/6",
    "jgc-6": "JGC/6",
    "jgc/6": "JGC/6",
    "jgd4": "JGD/4",
    "jgd-4": "JGD/4",
    "jgd/4": "JGD/4",
    "jgt2": "JGT/2",
    "jgt-2": "JGT/2",
    "jgt/2": "JGT/2",
    "jga2": "JGA/2",
    "jga-2": "JGA/2",
    "jga/2": "JGA/2",
    "kbk4": "KBK/4",
    "kbk-4": "KBK/4",
    "kbb6": "KBB/6",
    "kbb-6": "KBB/6",
}

# ── SUFFIX STRIPPING ─────────────────────────────────────────────────

_STRIP_SUFFIXES = re.compile(
    r"\s*(?:Inc\.?|Corp\.?|Ltd\.?|Co\.?|LLC|LP|International|Corporation|Group|AB)\.?\s*$",
    re.I,
)

# ── FRAME EXTRACTION ─────────────────────────────────────────────────
# Ariel model frames: leading alpha chars before the slash/digit
_FRAME_PATTERN = re.compile(r"^([A-Z]{2,})", re.I)


def normalize_manufacturer(raw: str | None) -> str:
    """Normalize a raw manufacturer string to its canonical form."""
    if not raw or raw.strip().lower() in ("various", "n/a", "unknown", "none", ""):
        return raw or "Unknown"
    cleaned = _STRIP_SUFFIXES.sub("", raw).strip()
    canonical = MANUFACTURER_ALIASES.get(cleaned.lower())
    if canonical:
        return canonical
    return cleaned


def normalize_model(raw: str | None) -> str:
    """Normalize a raw model string to its canonical form."""
    if not raw or raw.strip().lower() in ("various", "n/a", "unknown", "none", ""):
        return raw or "Unknown"
    cleaned = raw.strip()
    canonical = MODEL_ALIASES.get(cleaned.lower())
    if canonical:
        return canonical
    return cleaned


def extract_frame(model: str) -> str | None:
    """Extract the model frame from a model string (e.g. 'JGK/4' → 'JGK')."""
    m = _FRAME_PATTERN.match(model)
    return m.group(1).upper() if m else None
