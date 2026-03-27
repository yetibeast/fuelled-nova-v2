from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from app.db.session import get_session

router = APIRouter()

class RCNCreate(BaseModel):
    canonical_manufacturer: str
    canonical_model: str
    equipment_class: Optional[str] = None
    drive_type: Optional[str] = None
    stage_config: Optional[str] = None
    escalated_rcn_cad: float
    confidence: Optional[float] = None
    validation_status: Optional[str] = "pending"
    notes: Optional[str] = None
    category_id: Optional[str] = None
    source_id: Optional[str] = None
    evidence_intake_id: Optional[str] = None

class RCNUpdate(BaseModel):
    escalated_rcn_cad: Optional[float] = None
    confidence: Optional[float] = None
    validation_status: Optional[str] = None
    notes: Optional[str] = None

@router.get("/admin/gold/rcn")
async def list_rcn():
    async with get_session() as session:
        result = await session.execute(text(
            """SELECT id, canonical_manufacturer, canonical_model, equipment_class,
                      drive_type, stage_config, escalated_rcn_cad, confidence,
                      validation_status, notes, effective_date
               FROM rcn_price_references
               ORDER BY canonical_manufacturer, canonical_model LIMIT 200"""
        ))
        rows = result.fetchall()
    return [
        {"id": str(r[0]), "canonical_manufacturer": r[1], "canonical_model": r[2],
         "equipment_class": r[3], "drive_type": r[4], "stage_config": r[5],
         "escalated_rcn_cad": float(r[6]) if r[6] else None,
         "confidence": float(r[7]) if r[7] else None,
         "validation_status": r[8], "notes": r[9],
         "effective_date": str(r[10]) if r[10] else None}
        for r in rows
    ]

@router.post("/admin/gold/rcn")
async def create_rcn(body: RCNCreate):
    async with get_session() as session:
        result = await session.execute(text(
            """INSERT INTO rcn_price_references
                   (canonical_manufacturer, canonical_model, equipment_class,
                    drive_type, stage_config, escalated_rcn_cad, confidence,
                    validation_status, notes, category_id, source_id, evidence_intake_id)
               VALUES (:mfr, :model, :eq_class, :drive, :stage, :rcn, :conf,
                       :status, :notes, :cat_id, :src_id, :ev_id)
               RETURNING id"""
        ), {"mfr": body.canonical_manufacturer, "model": body.canonical_model,
            "eq_class": body.equipment_class, "drive": body.drive_type,
            "stage": body.stage_config, "rcn": body.escalated_rcn_cad,
            "conf": body.confidence or 0.5, "status": body.validation_status,
            "notes": body.notes, "cat_id": body.category_id,
            "src_id": body.source_id, "ev_id": body.evidence_intake_id})
        new_id = result.scalar()
        await session.commit()
    return {"id": str(new_id)}

@router.put("/admin/gold/rcn/{rcn_id}")
async def update_rcn(rcn_id: str, body: RCNUpdate):
    sets, params = [], {"rid": rcn_id}
    if body.escalated_rcn_cad is not None:
        sets.append("escalated_rcn_cad = :rcn"); params["rcn"] = body.escalated_rcn_cad
    if body.confidence is not None:
        sets.append("confidence = :conf"); params["conf"] = body.confidence
    if body.validation_status is not None:
        sets.append("validation_status = :status"); params["status"] = body.validation_status
    if body.notes is not None:
        sets.append("notes = :notes"); params["notes"] = body.notes
    if not sets:
        raise HTTPException(400, "No fields to update")
    async with get_session() as session:
        await session.execute(text(f"UPDATE rcn_price_references SET {', '.join(sets)} WHERE id = :rid"), params)
        await session.commit()
    return {"status": "updated"}

@router.delete("/admin/gold/rcn/{rcn_id}")
async def delete_rcn(rcn_id: str):
    async with get_session() as session:
        await session.execute(text("DELETE FROM rcn_price_references WHERE id = :rid"), {"rid": rcn_id})
        await session.commit()
    return {"status": "deleted"}

@router.get("/admin/gold/market")
async def list_market():
    async with get_session() as session:
        result = await session.execute(text(
            """SELECT id, canonical_manufacturer, canonical_model, value_type,
                      normalized_value_cad, validation_status, effective_date
               FROM market_value_references
               ORDER BY effective_date DESC NULLS LAST LIMIT 200"""
        ))
        rows = result.fetchall()
    return [
        {"id": str(r[0]), "canonical_manufacturer": r[1], "canonical_model": r[2],
         "value_type": r[3], "normalized_value_cad": float(r[4]) if r[4] else None,
         "validation_status": r[5], "effective_date": str(r[6]) if r[6] else None}
        for r in rows
    ]

@router.get("/admin/gold/depreciation")
async def list_depreciation():
    async with get_session() as session:
        result = await session.execute(text(
            """SELECT id, equipment_class, canonical_manufacturer, canonical_model,
                      age_at_observation, retention_ratio, effective_date
               FROM depreciation_observations
               ORDER BY effective_date DESC NULLS LAST LIMIT 200"""
        ))
        rows = result.fetchall()
    return [
        {"id": str(r[0]), "equipment_class": r[1],
         "canonical_manufacturer": r[2], "canonical_model": r[3],
         "age_years": int(r[4]) if r[4] is not None else None,
         "retention_ratio": float(r[5]) if r[5] is not None else None,
         "effective_date": str(r[6]) if r[6] else None}
        for r in rows
    ]

@router.get("/admin/gold/gaps")
async def coverage_gaps():
    async with get_session() as session:
        result = await session.execute(text(
            """SELECT l.category_normalized, COUNT(*) as listing_count,
                      COUNT(DISTINCT r.id) as rcn_refs,
                      COUNT(DISTINCT m.id) as market_refs
               FROM listings l
               LEFT JOIN rcn_price_references r
                   ON LOWER(r.equipment_class) = LOWER(l.category_normalized)
               LEFT JOIN market_value_references m
                   ON LOWER(m.canonical_manufacturer) = LOWER(l.make)
               WHERE l.category_normalized IS NOT NULL
               GROUP BY l.category_normalized
               HAVING COUNT(DISTINCT r.id) = 0 OR COUNT(DISTINCT m.id) < 3
               ORDER BY COUNT(*) DESC LIMIT 20"""
        ))
        rows = result.fetchall()
    return [
        {"category": r[0], "listing_count": r[1], "rcn_refs": r[2], "market_refs": r[3]}
        for r in rows
    ]
