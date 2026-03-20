"""Compound description parsing — the real domain work.

Parses equipment descriptions like:
    "Waukesha L5774LT / Ariel JGK4 3-Stg Sweet Gas Compressor Package"
    → driver=Waukesha L5774LT, equipment=Ariel JGK4, stages=3,
      drive_type=gas_engine, config=[sweet, package]

Pure functions — no database, no async, no side effects.

Source: V1 resolver.py Step 4, ported with all parsing logic preserved.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.pricing_v2.equipment.aliases import (
    ALL_EQUIPMENT_BRANDS,
    DRIVER_BRANDS,
    extract_frame,
    normalize_manufacturer,
    normalize_model,
)

# ── REGEX PATTERNS ────────────────────────────────────────────────────

DRIVE_TYPE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgas\s*engine\b", re.I), "gas_engine"),
    (re.compile(r"\bgas\s*turbine\b", re.I), "gas_turbine"),
    (re.compile(r"\bturbine\b", re.I), "gas_turbine"),
    (re.compile(r"\belectric\s*motor\b", re.I), "electric_motor"),
    (re.compile(r"\belectric\b", re.I), "electric_motor"),
    (re.compile(r"\bVFD\b"), "electric_motor"),
    (re.compile(r"\bintegral\b", re.I), "integral"),
    (re.compile(r"\bdiesel\b", re.I), "diesel"),
]

STAGE_PATTERN = re.compile(r"(\d+)[\-\s]?(?:stg|stage)", re.I)

CONFIG_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsweet\b", re.I), "sweet"),
    (re.compile(r"\bsour\b", re.I), "sour"),
    (re.compile(r"\bpackage\b", re.I), "package"),
    (re.compile(r"\bbare\b", re.I), "bare"),
    (re.compile(r"\bskid(?:ded)?\b", re.I), "skidded"),
    (re.compile(r"\bNACE\b"), "NACE"),
]

# Electric-motor driver brands (for drive_type inference)
_ELECTRIC_DRIVER_BRANDS = frozenset({"weg", "siemens", "teco", "abb"})


@dataclass
class CompoundParseResult:
    """Result of parsing a compound equipment description."""
    driver_manufacturer: str | None = None
    driver_model: str | None = None
    equipment_manufacturer: str | None = None
    equipment_model: str | None = None
    drive_type: str = "N/A"
    stage_config: str | None = None
    configurations: list[str] = field(default_factory=list)
    model_frame: str | None = None


def parse_compound_description(description: str) -> CompoundParseResult:
    """Parse compound equipment descriptions into structured components."""
    result = CompoundParseResult()
    if not description:
        return result

    # Extract stage_config from full text before splitting
    stage_match = STAGE_PATTERN.search(description)
    if stage_match:
        result.stage_config = f"{stage_match.group(1)}-stage"

    # Extract drive_type from full text
    for pattern, drive_type in DRIVE_TYPE_PATTERNS:
        if pattern.search(description):
            result.drive_type = drive_type
            break

    # Extract configurations from full text
    for pattern, config_name in CONFIG_KEYWORDS:
        if pattern.search(description):
            result.configurations.append(config_name)

    # Split into segments on ' / ', ' with ', ' w/ '
    # Require spaces around slash to avoid splitting model numbers like "JGK/4"
    segments = re.split(r"\s+/\s+|\s+with\s+|\s+w/\s+", description, flags=re.I)

    if len(segments) < 2:
        _classify_single_segment(segments[0], result)
    else:
        for segment in segments:
            segment_clean = segment.strip()
            if not segment_clean:
                continue
            _classify_segment(segment_clean, result)

    # Normalize manufacturer/model through alias maps
    if result.driver_manufacturer:
        result.driver_manufacturer = normalize_manufacturer(result.driver_manufacturer)
    if result.equipment_manufacturer:
        result.equipment_manufacturer = normalize_manufacturer(result.equipment_manufacturer)
    if result.equipment_model:
        result.equipment_model = normalize_model(result.equipment_model)
    if result.driver_model:
        result.driver_model = normalize_model(result.driver_model)

    return result


def _classify_segment(segment: str, result: CompoundParseResult) -> None:
    """Classify a segment as driver or equipment by brand lookup."""
    brand, model = _extract_brand_model(segment)
    if not brand:
        return

    brand_lower = brand.lower()
    if brand_lower in DRIVER_BRANDS:
        result.driver_manufacturer = brand
        result.driver_model = model
        if result.drive_type == "N/A":
            result.drive_type = "electric_motor" if brand_lower in _ELECTRIC_DRIVER_BRANDS else "gas_engine"
    elif brand_lower in ALL_EQUIPMENT_BRANDS:
        result.equipment_manufacturer = brand
        result.equipment_model = model
        if model:
            result.model_frame = extract_frame(model)
    elif result.driver_manufacturer is None:
        result.driver_manufacturer = brand
        result.driver_model = model
    else:
        result.equipment_manufacturer = brand
        result.equipment_model = model


def _classify_single_segment(segment: str, result: CompoundParseResult) -> None:
    """Classify a single segment when there's no split delimiter."""
    brand, model = _extract_brand_model(segment)
    if not brand:
        return
    brand_lower = brand.lower()
    if brand_lower in DRIVER_BRANDS and brand_lower not in ALL_EQUIPMENT_BRANDS:
        result.driver_manufacturer = brand
        result.driver_model = model
    elif brand_lower in ALL_EQUIPMENT_BRANDS:
        result.equipment_manufacturer = brand
        result.equipment_model = model
        if model:
            result.model_frame = extract_frame(model)
    else:
        result.equipment_manufacturer = brand
        result.equipment_model = model


def _extract_brand_model(segment: str) -> tuple[str | None, str | None]:
    """Extract (brand, model) from a text segment using known brand matching."""
    segment_lower = segment.lower().strip()
    all_brands = DRIVER_BRANDS | ALL_EQUIPMENT_BRANDS

    # Try known multi-word brands first (longest match wins)
    for brand in sorted(all_brands, key=len, reverse=True):
        if segment_lower.startswith(brand):
            remainder = segment[len(brand):].strip()
            model_match = re.match(r"^([A-Z0-9][A-Z0-9\-/]*)", remainder, re.I)
            model = model_match.group(1) if model_match else (remainder.split()[0] if remainder.split() else None)
            proper_brand = segment[:len(brand)].strip()
            return proper_brand, model

    # Fallback: first word as brand
    words = segment.split()
    if not words:
        return None, None
    return words[0], words[1] if len(words) > 1 else None
