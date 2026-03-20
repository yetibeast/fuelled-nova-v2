"""Resolution audit trail writing.

Simple append-only audit entries for equipment resolution decisions.

Source: V1 resolver.py audit helper, simplified.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def make_audit_entry(
    step: str,
    input_val: str | None,
    output_val: str | None,
    confidence: float,
    method: str,
    entity_id: str | None = None,
    notes: str | None = None,
) -> dict:
    """Create an audit entry dict (for batching before write)."""
    return {
        "step_name": step,
        "input_value": input_val,
        "output_value": output_val,
        "confidence": confidence,
        "method_used": method,
        "matched_entity_id": entity_id,
        "notes": notes,
    }


async def write_audit_entries(
    session: AsyncSession,
    evidence_intake_id: uuid.UUID,
    entries: list[dict],
) -> None:
    """Write a batch of audit entries to resolution_audit table."""
    if not entries:
        return

    for entry in entries:
        await session.execute(
            text("""
                INSERT INTO resolution_audit
                    (id, evidence_intake_id, step_name, input_value, output_value,
                     confidence, method_used, matched_entity_id, notes)
                VALUES
                    (:id, :eid, :step, :inp, :out, :conf, :method, :entity, :notes)
            """),
            {
                "id": uuid.uuid4(),
                "eid": evidence_intake_id,
                "step": entry["step_name"],
                "inp": entry.get("input_value"),
                "out": entry.get("output_value"),
                "conf": entry["confidence"],
                "method": entry["method_used"],
                "entity": entry.get("matched_entity_id"),
                "notes": entry.get("notes"),
            },
        )
