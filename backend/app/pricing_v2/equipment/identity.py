"""Equipment identity lookup and creation.

Async functions that query the equipment_identity table.

CRITICAL FIX from V1 resolver.py:698:
  V1: category_id=resolved.canonical_category_id or uuid.uuid4()
  V2: If category_id is None, raise ValueError. Never write a random UUID as a FK.

Source: V1 resolver.py Steps 5-6, with bug fixes applied.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

log = logging.getLogger(__name__)


async def resolve_equipment_identity(
    category: str,
    manufacturer: str,
    model: str,
    drive_type: str | None = None,
    stage_config: str | None = None,
) -> dict | None:
    """Look up an existing equipment identity from the gold tables.

    Returns a dict with identity fields, or None if not found.
    Read-only — does not create new identities.
    """
    conditions = ["1=1"]
    params: dict = {}

    if manufacturer and manufacturer != "Unknown":
        conditions.append("canonical_manufacturer ILIKE :mfr")
        params["mfr"] = f"%{manufacturer}%"
    if model and model != "Unknown":
        conditions.append("canonical_model ILIKE :mdl")
        params["mdl"] = f"%{model}%"
    if drive_type:
        conditions.append("drive_type ILIKE :drv")
        params["drv"] = f"%{drive_type}%"
    if stage_config:
        conditions.append("stage_config ILIKE :stg")
        params["stg"] = f"%{stage_config}%"

    # Must have at least manufacturer or model to search
    if not params:
        return None

    where = " AND ".join(conditions)
    sql = f"""
        SELECT id, canonical_manufacturer, canonical_model, model_frame,
               drive_type, stage_config, configuration, equipment_class,
               category_id, valuation_family_id
        FROM equipment_identity
        WHERE {where} AND is_active = true
        ORDER BY
            CASE WHEN canonical_model ILIKE :best THEN 0 ELSE 1 END,
            created_at DESC
        LIMIT 1
    """
    params["best"] = f"%{model}%" if model and model != "Unknown" else "%"

    async with get_session() as session:
        result = await session.execute(text(sql), params)
        row = result.fetchone()

    if not row:
        return None

    return {
        "id": str(row.id),
        "canonical_manufacturer": row.canonical_manufacturer,
        "canonical_model": row.canonical_model,
        "model_frame": row.model_frame,
        "drive_type": row.drive_type,
        "stage_config": row.stage_config,
        "configuration": row.configuration,
        "equipment_class": row.equipment_class,
        "category_id": str(row.category_id),
        "valuation_family_id": str(row.valuation_family_id) if row.valuation_family_id else None,
    }


async def create_equipment_identity(
    session: AsyncSession,
    *,
    canonical_manufacturer: str,
    canonical_model: str,
    model_frame: str | None = None,
    drive_type: str = "N/A",
    stage_config: str = "",
    configuration: str = "",
    equipment_class: str = "general",
    category_id: uuid.UUID | None = None,
    valuation_family_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Create a new equipment_identity row.

    CRITICAL: Raises ValueError if category_id is None.
    V1 wrote uuid.uuid4() as a fake FK — that bug is fixed here.
    """
    if category_id is None:
        raise ValueError(
            f"Cannot create equipment_identity for {canonical_manufacturer} {canonical_model}: "
            f"category_id is required (was None). Resolve the category first."
        )

    new_id = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO equipment_identity
                (id, canonical_manufacturer, canonical_model, model_frame,
                 drive_type, stage_config, configuration, equipment_class,
                 category_id, valuation_family_id, is_active)
            VALUES
                (:id, :mfr, :mdl, :frame, :drv, :stg, :cfg, :cls, :cat, :fam, true)
            ON CONFLICT (canonical_manufacturer, canonical_model, drive_type, stage_config, configuration)
            DO NOTHING
        """),
        {
            "id": new_id, "mfr": canonical_manufacturer, "mdl": canonical_model,
            "frame": model_frame, "drv": drive_type, "stg": stage_config,
            "cfg": configuration, "cls": equipment_class,
            "cat": category_id, "fam": valuation_family_id,
        },
    )
    return new_id
