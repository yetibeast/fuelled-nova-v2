from __future__ import annotations
import logging
import re as _re
import aiohttp
from sqlalchemy import text
from app.db.session import get_session
from app.pricing_v2.rcn_engine.calculator import calculate_rcn as _rcn_calculate
from app.pricing_v2.equipment.parsing import parse_compound_description
from app.pricing_v2.equipment.aliases import normalize_manufacturer, normalize_model

log = logging.getLogger(__name__)


async def fetch_listing(url: str) -> str:
    """Fetch equipment details from a Fuelled or competitor listing URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return f"Could not fetch URL (status {resp.status}). Please paste the listing description directly."
                html = await resp.text()
                text = _re.sub('<[^<]+?>', ' ', html)
                text = _re.sub(r'\s+', ' ', text).strip()
                return f"Listing content from {url}:\n{text[:3000]}"
    except Exception as e:
        return f"Could not fetch URL: {str(e)}. Please paste the listing description directly."


async def search_comparables(keywords: list[str], category: str | None = None,
                             price_min: float = 0, price_max: float = 99999999,
                             max_results: int = 20) -> str:
    if not keywords:
        return "No keywords provided."
    where = " OR ".join(f"title ILIKE :kw{i}" for i in range(len(keywords)))
    params = {f"kw{i}": f"%{kw}%" for i, kw in enumerate(keywords)}
    sql = f"SELECT title, asking_price, currency, source, location, year, hours, url FROM listings WHERE ({where}) AND asking_price IS NOT NULL AND asking_price BETWEEN :pmin AND :pmax"
    params["pmin"], params["pmax"] = price_min, price_max
    if category:
        sql += " AND category_normalized ILIKE :cat"
        params["cat"] = f"%{category}%"
    sql += f" ORDER BY asking_price DESC LIMIT :lim"
    params["lim"] = max_results
    async with get_session() as session:
        result = await session.execute(text(sql), params)
        rows = result.fetchall()
    if not rows:
        return f"No comparables found for {keywords}. Normal for high-spec equipment."
    lines = [f"Found {len(rows)} comparables:"]
    for r in rows:
        yr = f"{r.year} " if r.year else ""
        hrs = f" ({r.hours}hrs)" if r.hours else ""
        loc = f" — {r.location}" if r.location else ""
        lines.append(f"  {yr}{r.title} | ${r.asking_price:,.0f} {r.currency or 'CAD'}{hrs}{loc} | {r.source} | {r.url or 'no link'}")
    return "\n".join(lines)


async def get_category_stats(category: str) -> str:
    sql = """SELECT COUNT(*) as total, COUNT(CASE WHEN asking_price > 0 THEN 1 END) as with_price,
             AVG(CASE WHEN asking_price > 0 THEN asking_price END) as avg_price,
             MIN(CASE WHEN asking_price > 0 THEN asking_price END) as min_price,
             MAX(CASE WHEN asking_price > 0 THEN asking_price END) as max_price
             FROM listings WHERE category_normalized ILIKE :cat"""
    async with get_session() as session:
        result = await session.execute(text(sql), {"cat": f"%{category}%"})
        r = result.fetchone()
    if not r or r.total == 0:
        return f"No listings found for category '{category}'."
    return (f"Category '{category}': {r.total} listings ({r.with_price} with price)\n"
            f"  Avg: ${r.avg_price:,.0f}  Min: ${r.min_price:,.0f}  Max: ${r.max_price:,.0f}")


# ── Fallback RCN dictionary — last resort if database returns nothing ──

_FALLBACK_RCN = {
    "vru": {
        "match_terms": ["vru", "vapor recovery", "vapour recovery", "rotary vane"],
        "rcn_low": 200000, "rcn_mid": 240000, "rcn_high": 280000,
        "note": "Complete VRU package 30-50HP class with shelter, condensate handling, PLC, NACE piping.",
    },
    "incinerator": {
        "match_terms": ["incinerator", "enclosed combustor", "ecd"],
        "rcn_low": 50000, "rcn_mid": 75000, "rcn_high": 100000,
        "note": "Enclosed combustion device 48-60 inch.",
    },
    "flare": {
        "match_terms": ["flare stack", "flare knockout"],
        "rcn_low": 15000, "rcn_mid": 25000, "rcn_high": 40000,
        "note": "Flare knockout + stack, size dependent.",
    },
    "line_heater": {
        "match_terms": ["line heater", "gas production unit"],
        "rcn_low": 30000, "rcn_mid": 50000, "rcn_high": 80000,
        "note": "Line heater 0.5-1.5 MMBTU with separator package.",
    },
    "meter_skid": {
        "match_terms": ["meter skid", "meter run", "meter building"],
        "rcn_low": 8000, "rcn_mid": 15000, "rcn_high": 25000,
        "note": "Meter skid/run 2-4 inch ANSI 600.",
    },
    "treater": {
        "match_terms": ["treater", "heater treater", "emulsion treater"],
        "rcn_low": 80000, "rcn_mid": 150000, "rcn_high": 250000,
        "note": "Heater treater 48-72 inch.",
    },
}


def _check_fallback(query: str) -> str | None:
    q = query.lower()
    for key, d in _FALLBACK_RCN.items():
        if any(term in q for term in d["match_terms"]):
            return (f"Found 1 RCN match(es):\n\n  [fallback:{key}] (Fallback)\n"
                    f"  RCN: ${d['rcn_low']:,} — ${d['rcn_mid']:,} — ${d['rcn_high']:,} (stored as CAD — convert if valuing in USD)\n"
                    f"  Notes: {d['note']} (fallback dictionary)\n"
                    f"\nApply depreciation factors for age, condition, hours.")
    return None


async def lookup_rcn(equipment_type: str, manufacturer: str | None = None, model: str | None = None,
                     drive_type: str | None = None, stages: int | None = None, hp: int | None = None) -> str:
    # ── Parse compound descriptions before DB search ──
    # If manufacturer contains a compound like "Waukesha L5774 / Ariel JGK4",
    # parse it to extract the actual equipment manufacturer and model
    compound_input = " / ".join(p for p in [manufacturer or "", model or ""] if p)
    if "/" in (manufacturer or "") or "/" in (model or ""):
        parsed = parse_compound_description(compound_input)
        if parsed.equipment_manufacturer:
            manufacturer = parsed.equipment_manufacturer
        if parsed.equipment_model:
            model = parsed.equipment_model
        if parsed.drive_type != "N/A" and not drive_type:
            drive_type = parsed.drive_type
        if parsed.stage_config and not stages:
            try:
                stages = int(parsed.stage_config.split("-")[0])
            except (ValueError, IndexError):
                pass
        log.info("Parsed compound: mfr=%s model=%s drive=%s stages=%s",
                 manufacturer, model, drive_type, stages)

    # Normalize through alias maps
    if manufacturer:
        manufacturer = normalize_manufacturer(manufacturer)
    if model:
        model = normalize_model(model)

    # Build dynamic WHERE clauses and scoring
    conditions = []
    params: dict = {}

    if manufacturer:
        conditions.append("canonical_manufacturer ILIKE :mfr")
        params["mfr"] = f"%{manufacturer}%"
    if model:
        conditions.append("canonical_model ILIKE :mdl")
        params["mdl"] = f"%{model}%"
    if equipment_type:
        conditions.append("equipment_class ILIKE :eqtype")
        params["eqtype"] = f"%{equipment_type}%"

    if not conditions:
        return "No search criteria provided for RCN lookup."

    # Score: model match is worth most, then manufacturer, then equipment_class
    score_parts = []
    if manufacturer:
        score_parts.append("CASE WHEN canonical_manufacturer ILIKE :mfr THEN 2 ELSE 0 END")
    if model:
        score_parts.append("CASE WHEN canonical_model ILIKE :mdl THEN 3 ELSE 0 END")
    if equipment_type:
        score_parts.append("CASE WHEN equipment_class ILIKE :eqtype THEN 1 ELSE 0 END")

    # Optional stage filter adds to score
    if stages:
        score_parts.append("CASE WHEN stage_config ILIKE :stg THEN 2 ELSE 0 END")
        params["stg"] = f"%{stages}-stage%"

    score_expr = " + ".join(score_parts) if score_parts else "0"
    where_expr = " OR ".join(conditions)

    sql = f"""
        SELECT canonical_manufacturer, canonical_model, stage_config, drive_type,
               equipment_class, escalated_rcn_cad, confidence, horsepower, notes,
               validation_status,
               ({score_expr}) as match_score
        FROM rcn_price_references
        WHERE ({where_expr})
          AND escalated_rcn_cad > 0
        ORDER BY match_score DESC,
                 CASE WHEN validation_status = 'active' THEN 0 ELSE 1 END,
                 confidence DESC NULLS LAST
        LIMIT 3
    """

    async with get_session() as session:
        result = await session.execute(text(sql), params)
        rows = result.fetchall()

    if rows:
        lines = [f"Found {len(rows)} RCN match(es) from gold reference table:"]
        for r in rows:
            rcn_mid = float(r.escalated_rcn_cad)
            rcn_low = round(rcn_mid * 0.85)
            rcn_high = round(rcn_mid * 1.15)
            rcn_mid_r = round(rcn_mid)
            conf = f"{r.confidence:.0%}" if r.confidence is not None else "—"
            status = r.validation_status or "unknown"
            hp_str = f"  HP: {r.horsepower:,.0f}" if r.horsepower else ""
            notes = r.notes or ""
            lines.append(f"\n  [{r.canonical_manufacturer} {r.canonical_model}] ({r.equipment_class} — {status})")
            lines.append(f"  RCN: ${rcn_low:,} — ${rcn_mid_r:,} — ${rcn_high:,} (escalated to current year, stored as CAD — convert if valuing in USD)")
            if r.stage_config:
                lines.append(f"  Config: {r.stage_config}")
            if r.drive_type:
                lines.append(f"  Drive: {r.drive_type}")
            if hp_str:
                lines.append(hp_str)
            lines.append(f"  Confidence: {conf}")
            if notes:
                lines.append(f"  Notes: {notes}")
        lines.append("\nApply depreciation factors for age, condition, hours.")
        return "\n".join(lines)

    # Database returned nothing — try fallback dictionary
    query = " ".join(p.lower() for p in [equipment_type, manufacturer or "", model or ""] if p)
    fb = _check_fallback(query)
    if fb:
        return fb

    return ("No RCN anchor found in reference tables. Estimate from general knowledge. "
            "HP scaling: base * (target_hp / base_hp) ^ 0.6")


# ── Simple fallback curves (kept if rcn_engine fails) ────────────────

_SIMPLE_AGE_CURVES = {
    "rotating":    [(1,0.90),(3,0.80),(5,0.65),(8,0.50),(12,0.38),(15,0.28),(20,0.20),(25,0.15),(30,0.10),(999,0.08)],
    "static":      [(1,0.92),(3,0.85),(5,0.75),(8,0.65),(12,0.55),(15,0.45),(20,0.35),(25,0.25),(30,0.18),(999,0.12)],
    "pump_jack":   [(1,0.92),(3,0.85),(5,0.78),(8,0.70),(12,0.60),(15,0.50),(20,0.40),(25,0.30),(30,0.22),(999,0.15)],
    "electrical":  [(1,0.90),(3,0.82),(5,0.72),(8,0.60),(12,0.48),(15,0.38),(20,0.28),(25,0.20),(30,0.14),(999,0.10)],
}
_SIMPLE_CONDITION = {"A": 1.00, "B": 0.75, "C": 0.50, "D": 0.20}
_SIMPLE_HOURS = [(5000,1.10),(15000,1.00),(30000,0.85),(50000,0.70),(999999,0.55)]
_SIMPLE_SERVICE = {"sweet": 1.00, "sour": 1.15, "sour_high_h2s": 1.25}

# Map simple condition grades to rcn_engine condition strings
_CONDITION_GRADE_MAP = {"A": "EXCELLENT", "B": "GOOD", "C": "FAIR", "D": "POOR"}

# Map simple equipment_class to rcn_engine category
_CLASS_TO_CATEGORY = {
    "rotating": "compressor",
    "static": "separator",
    "pump_jack": "pump_jack",
    "electrical": "electrical",
}


def _lookup(table, value):
    for threshold, factor in table:
        if value <= threshold:
            return factor
    return table[-1][1]


def _simple_fmv(rcn, equipment_class, age_years, condition, hours, service,
                vfd_equipped, turnkey_package, nace_rated):
    """Original simple FMV calculation — used as fallback."""
    curve = _SIMPLE_AGE_CURVES.get(equipment_class, _SIMPLE_AGE_CURVES["rotating"])
    age_f = _lookup(curve, age_years)
    cond_f = _SIMPLE_CONDITION.get(condition.upper(), 0.75)
    hrs_f = _lookup(_SIMPLE_HOURS, hours) if hours is not None and equipment_class == "rotating" else 1.00
    svc_f = _SIMPLE_SERVICE.get(service, 1.00)
    prem = (1.05 if vfd_equipped else 1.0) * (1.05 if turnkey_package else 1.0) * (1.15 if nace_rated else 1.0)
    combined = age_f * cond_f * hrs_f * svc_f * prem
    mid = rcn * combined
    low, high = mid * 0.85, mid * 1.15
    list_price, walkaway = mid * 1.12, low * 0.92
    factors = f"Age({age_years}yr)={age_f:.2f} × Cond({condition})={cond_f:.2f}"
    if hours is not None and equipment_class == "rotating":
        factors += f" × Hours({hours:,})={hrs_f:.2f}"
    factors += f" × Service({service})={svc_f:.2f}"
    if prem != 1.0:
        factors += f" × Premiums={prem:.2f}"
    return (f"FMV CALCULATION (simple fallback):\n"
            f"  RCN: ${rcn:,.0f}\n"
            f"  Factors: {factors}\n"
            f"  Combined factor: {combined:.4f}\n"
            f"  FMV Range: ${low:,.0f} — ${mid:,.0f} — ${high:,.0f}\n"
            f"  Recommended list price: ${list_price:,.0f}\n"
            f"  Walk-away floor: ${walkaway:,.0f}")


def calculate_fmv(rcn: float, equipment_class: str, age_years: int, condition: str = "B",
                  hours: int | None = None, service: str = "sweet",
                  vfd_equipped: bool = False, turnkey_package: bool = False,
                  nace_rated: bool = False) -> str:
    """Calculate FMV using the rcn_engine v2, with simple-curve fallback."""
    try:
        category = _CLASS_TO_CATEGORY.get(equipment_class, equipment_class)
        condition_str = _CONDITION_GRADE_MAP.get(condition.upper(), "GOOD")
        is_sour = service in ("sour", "sour_high_h2s")

        result = _rcn_calculate(category, {
            "year": 2026 - age_years,
            "hours": hours,
            "condition": condition_str,
            "is_nace_compliant": nace_rated,
            "years_h2s_exposure": age_years if is_sour else None,
            "drive_type": None,
            "material": None,
            "spec_modifiers": None,
        })

        # Use the provided RCN (from lookup_rcn) rather than the engine's computed base
        # The engine gives us the factor breakdown; we apply those factors to the caller's RCN
        fa = result.factors_applied
        age_f = fa["age_factor"]
        cond_f = fa["condition_factor"]
        market_heat = fa["market_heat"]
        geo_f = fa["geography_factor"]
        h2s_mult = fa["h2s_age_multiplier"]

        # Build premium from caller's flags (engine handles nace separately)
        prem = (1.05 if vfd_equipped else 1.0) * (1.05 if turnkey_package else 1.0)

        combined = age_f * cond_f * market_heat * geo_f * prem
        mid = rcn * combined
        low, high = mid * 0.85, mid * 1.15
        list_price, walkaway = mid * 1.12, low * 0.92

        conf = fa.get("confidence_breakdown", {})
        conf_score = conf.get("composite", 0)
        curve_used = result.depreciation_curve_used

        factors_str = (
            f"Age({age_years}yr, eff={fa['effective_age']:.1f})={age_f:.4f}"
            f" × Cond({condition_str})={cond_f:.4f}"
        )
        if h2s_mult > 1.0:
            factors_str += f" × H2S_aging={h2s_mult:.2f}"
        if market_heat != 1.0:
            factors_str += f" × MarketHeat={market_heat:.4f}"
        if geo_f != 1.0:
            factors_str += f" × Geo={geo_f:.2f}"
        if prem != 1.0:
            factors_str += f" × Premiums={prem:.2f}"

        return (
            f"FMV CALCULATION (rcn_engine v2):\n"
            f"  RCN: ${rcn:,.0f}\n"
            f"  Curve: {curve_used} (category: {fa['category_key']})\n"
            f"  Factors: {factors_str}\n"
            f"  Combined factor: {combined:.4f}\n"
            f"  FMV Range: ${low:,.0f} — ${mid:,.0f} — ${high:,.0f}\n"
            f"  Recommended list price: ${list_price:,.0f}\n"
            f"  Walk-away floor: ${walkaway:,.0f}\n"
            f"  Confidence: {conf_score:.1%} (rcn_src={conf.get('rcn_source_score', 0):.2f}"
            f" vol={conf.get('data_volume_score', 0):.2f}"
            f" spec={conf.get('specificity_score', 0):.2f})"
        )
    except Exception as exc:
        log.warning("rcn_engine failed, using simple fallback: %s", exc)
        return _simple_fmv(rcn, equipment_class, age_years, condition, hours, service,
                           vfd_equipped, turnkey_package, nace_rated)


def check_equipment_risks(equipment_type: str, age_years: int, hours: int | None = None,
                          idle_years: int | None = None, drive_type: str | None = None,
                          plc_model: str | None = None, manufacturer: str | None = None,
                          location_country: str = "CA", identical_units: int = 1,
                          days_on_market: int | None = None, total_views: int | None = None) -> str:
    risks = []
    if idle_years and idle_years > 5:
        risks.append(f"IDLE DEGRADATION ({idle_years}yr idle): Elastomer/seal degradation likely. Pre-commissioning inspection required — budget $3,000–$8,000.")
    if idle_years and idle_years > 3 and "rotary vane" in (equipment_type or "").lower():
        risks.append("VANE MOISTURE DAMAGE: Rotary vane units idle >3yr risk vane swelling/moisture damage. Inspection mandatory before valuation.")
    if plc_model and "micrologix" in plc_model.lower():
        risks.append(f"PLC OBSOLESCENCE: {plc_model} discontinued 2017. Budget $8,000–$15,000 for controls upgrade (CompactLogix or Micro800).")
    if age_years > 10:
        risks.append(f"CONTROLS CHECK: At {age_years}yr, verify PLC/HMI platform is still supported and parts are available.")
    if location_country and location_country.upper() != "CA":
        risks.append(f"CROSS-BORDER: Equipment in {location_country}. Transport $5,000–$15,000 + ASME→ABSA re-certification $2,000–$5,000.")
    if identical_units > 10:
        risks.append(f"OVERSUPPLY: {identical_units} identical units — recommend lot sale strategy to avoid cannibalizing individual pricing.")
    elif identical_units > 3:
        risks.append(f"VOLUME DISCOUNT: {identical_units} identical units — expect 5–10% volume discount pressure.")
    if days_on_market and total_views and days_on_market > 730 and total_views > 500:
        risks.append(f"STALE LISTING: {days_on_market} days on market with {total_views} views — price resistance confirmed. Recommend 15–20% reduction.")
    mfr = (manufacturer or "").lower()
    dt = (drive_type or "").lower()
    if mfr in ["ajax", "cooper"] or dt == "integral":
        risks.append("DECLINING MARKET: Integral/slow-speed engines face shrinking buyer pool. Extended sale timeline 6–18 months.")
    if mfr in ["worthington", "energy industries", "dresser"]:
        risks.append(f"UNCOMMON FRAME: {manufacturer} — limited aftermarket parts, smaller buyer pool. Discount 10–20% vs common frames.")
    if not risks:
        return "No significant risk factors identified."
    return "RISK FACTORS:\n• " + "\n• ".join(risks)
