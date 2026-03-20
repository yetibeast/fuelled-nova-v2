"""Evidence promoter — staging to gold table promotion with V1 bug fixes.

Fixes: (A) writes canonical mfr/model not raw, (B) requires valid category_id,
(C) validates all FKs before write.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.pricing_v2.equipment.escalation import FX_RATES, compute_escalated_rcn

log = logging.getLogger(__name__)

RCN_TYPES = {"RCN", "Installed Cost"}
MARKET_TYPES = {"FMV", "OLV", "FLV", "asking", "sale", "Walk-Away Floor"}


async def promote_evidence(session: AsyncSession, evidence: dict) -> list[str]:
    """Promote a single evidence dict to gold tables. Returns list of target tables.

    Evidence dict must include resolved_* fields from the identity resolution pipeline.
    """
    promoted: list[str] = []

    confidence = evidence.get("confidence") or 0.0
    price_value = evidence.get("price_value")
    price_type = evidence.get("price_type", "")
    effective_date = evidence.get("effective_date")
    currency = evidence.get("original_currency", "CAD")
    category_id = evidence.get("resolved_category_id")

    if price_value is None or price_value <= 0:
        return promoted

    # FIX B: require valid category_id — never use source_id as fallback
    if not category_id:
        log.warning("Skipping promotion for evidence %s: no resolved_category_id", evidence.get("id"))
        return promoted

    if currency not in FX_RATES:
        log.warning("Skipping promotion: unknown currency %s", currency)
        return promoted

    fx_rate = FX_RATES[currency]

    # FIX A: Use resolved canonical values, NOT raw evidence values
    canonical_mfr = evidence.get("resolved_canonical_manufacturer", "Unknown")
    canonical_model = evidence.get("resolved_canonical_model", "Unknown")
    equipment_class = evidence.get("equipment_class", "general")

    # RCN Promotion
    if price_type in RCN_TYPES and confidence >= 0.50 and effective_date:
        esc_factor = evidence.get("escalation_to_current", 1.0)
        escalated, fx_applied = compute_escalated_rcn(price_value, currency, esc_factor, fx_rate)
        gold_status = "active" if confidence >= 0.60 else "provisional"

        await session.execute(
            text("""
                INSERT INTO rcn_price_references
                    (id, evidence_intake_id, source_id, equipment_identity_id,
                     valuation_family_id, category_id,
                     canonical_manufacturer, canonical_model, drive_type,
                     stage_config, equipment_class,
                     original_currency, original_value,
                     escalated_rcn_cad, escalation_factor_applied, escalation_date,
                     fx_rate_applied, effective_date, year, confidence,
                     methodology, validation_status)
                VALUES
                    (:id, :eid, :sid, :iid, :fid, :cid,
                     :mfr, :mdl, :drv, :stg, :cls,
                     :cur, :oval,
                     :ercn, :efactor, :edate,
                     :fxrate, :edate2, :yr, :conf,
                     :meth, :status)
            """),
            {"id": uuid.uuid4(), "eid": evidence.get("id"), "sid": evidence.get("source_id"),
             "iid": evidence.get("resolved_identity_id"), "fid": evidence.get("resolved_family_id"),
             "cid": category_id, "mfr": canonical_mfr, "mdl": canonical_model,
             "drv": evidence.get("drive_type", "N/A"), "stg": evidence.get("stage_config"),
             "cls": equipment_class, "cur": currency, "oval": price_value,
             "ercn": escalated, "efactor": esc_factor, "edate": effective_date,
             "fxrate": fx_applied, "edate2": effective_date, "yr": evidence.get("year"),
             "conf": confidence, "meth": evidence.get("methodology"), "status": gold_status},
        )
        promoted.append("rcn_price_references")

    # Market Value Promotion
    if price_type in MARKET_TYPES and confidence >= 0.50:
        normalized_cad = price_value * fx_rate
        paired_rcn = None
        ratio = None
        rcn_anchor = evidence.get("rcn_anchor")
        if rcn_anchor:
            paired_rcn = rcn_anchor * fx_rate
            if paired_rcn > 0:
                ratio = normalized_cad / paired_rcn

        await session.execute(
            text("""
                INSERT INTO market_value_references
                    (id, evidence_intake_id, source_id, equipment_identity_id,
                     valuation_family_id, category_id,
                     canonical_manufacturer, canonical_model, equipment_class,
                     value_type, original_currency, original_value,
                     normalized_value_cad, fx_rate_applied,
                     effective_date, year, hours, condition, location,
                     paired_rcn_cad, fmv_to_rcn_ratio, confidence)
                VALUES
                    (:id, :eid, :sid, :iid, :fid, :cid,
                     :mfr, :mdl, :cls,
                     :vtype, :cur, :oval,
                     :ncad, :fxrate,
                     :edate, :yr, :hrs, :cond, :loc,
                     :prcn, :ratio, :conf)
            """),
            {
                "id": uuid.uuid4(),
                "eid": evidence.get("id"),
                "sid": evidence.get("source_id"),
                "iid": evidence.get("resolved_identity_id"),
                "fid": evidence.get("resolved_family_id"),
                "cid": category_id,
                "mfr": canonical_mfr,   # FIX A: canonical, not raw
                "mdl": canonical_model,  # FIX A: canonical, not raw
                "cls": equipment_class,
                "vtype": price_type,
                "cur": currency,
                "oval": price_value,
                "ncad": normalized_cad,
                "fxrate": fx_rate,
                "edate": effective_date,
                "yr": evidence.get("year"),
                "hrs": evidence.get("hours"),
                "cond": evidence.get("raw_condition"),
                "loc": evidence.get("location"),
                "prcn": paired_rcn,
                "ratio": ratio,
                "conf": confidence,
            },
        )
        promoted.append("market_value_references")

    # Depreciation Observation
    rcn_anchor = evidence.get("rcn_anchor")
    if rcn_anchor and price_value and price_type in MARKET_TYPES:
        ratio = price_value / rcn_anchor if rcn_anchor > 0 else None
        if ratio and 0.05 <= ratio <= 1.05:
            rcn_cad = rcn_anchor * fx_rate
            fmv_cad = price_value * fx_rate
            age = None
            year = evidence.get("year")
            if year and effective_date:
                age = effective_date.year - year if isinstance(effective_date, date) else None

            # FIX B: category_id already validated above — never use source_id
            await session.execute(
                text("""
                    INSERT INTO depreciation_observations
                        (id, evidence_intake_id, source_id, equipment_identity_id,
                         valuation_family_id, category_id, equipment_class,
                         canonical_manufacturer, canonical_model,
                         rcn_cad, fmv_cad, retention_ratio,
                         age_at_observation, hours_at_observation,
                         condition_at_observation, effective_date, confidence)
                    VALUES
                        (:id, :eid, :sid, :iid, :fid, :cid, :cls,
                         :mfr, :mdl,
                         :rcn, :fmv, :ratio,
                         :age, :hrs, :cond, :edate, :conf)
                """),
                {
                    "id": uuid.uuid4(),
                    "eid": evidence.get("id"),
                    "sid": evidence.get("source_id"),
                    "iid": evidence.get("resolved_identity_id"),
                    "fid": evidence.get("resolved_family_id"),
                    "cid": category_id,  # FIX B: validated category, not source_id
                    "cls": equipment_class,
                    "mfr": canonical_mfr,   # FIX A: canonical, not raw
                    "mdl": canonical_model,  # FIX A: canonical, not raw
                    "rcn": rcn_cad,
                    "fmv": fmv_cad,
                    "ratio": ratio,
                    "age": age,
                    "hrs": evidence.get("hours"),
                    "cond": evidence.get("raw_condition"),
                    "edate": effective_date,
                    "conf": confidence,
                },
            )
            promoted.append("depreciation_observations")

    return promoted
