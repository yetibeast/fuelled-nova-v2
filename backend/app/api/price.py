from __future__ import annotations
import base64
import json
import logging
from fastapi import APIRouter, Form, File, Header, HTTPException, UploadFile
from fastapi.responses import Response
from app.pricing_v2.service import run_pricing
from app.pricing_v2.report import generate_report
from app.api.admin import _require_auth

router = APIRouter()
_log = logging.getLogger(__name__)

MEDIA_MAP = {
    "application/pdf": "document",
    "image/png": "image",
    "image/jpeg": "image",
    "image/webp": "image",
}


@router.post("/price")
async def post_price(
    message: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    history: str = Form(default=""),
    authorization: str = Header(default=""),
):
    _require_auth(authorization)
    attachments = []
    for f in files:
        content = await f.read(10_485_761)
        if len(content) > 10_485_760:
            raise HTTPException(413, "File too large (10MB max)")
        data = base64.b64encode(content).decode()
        media_type = f.content_type or "application/octet-stream"
        att_type = MEDIA_MAP.get(media_type, "document")
        attachments.append({"type": att_type, "media_type": media_type, "data": data})

    conversation_history = None
    if history:
        try:
            conversation_history = json.loads(history)
        except json.JSONDecodeError:
            pass

    result = await run_pricing(
        message,
        attachments if attachments else None,
        conversation_history,
    )

    # Auto-capture evidence (fire-and-forget)
    try:
        from app.api.evidence import capture_evidence
        await capture_evidence(
            {
                "user_message": message,
                "structured_data": result.get("structured", {}),
                "confidence": result.get("confidence", "LOW"),
                "tools_used": result.get("tools_used", []),
            },
            authorization=authorization,
        )
    except Exception as e:
        _log.warning("Evidence capture failed: %s", e)

    return result


@router.post("/report")
async def post_report(
    structured_data: str = Form(...),
    response_text: str = Form(default=""),
    user_message: str = Form(default="Equipment Valuation"),
    authorization: str = Header(default=""),
):
    _require_auth(authorization)
    try:
        structured = json.loads(structured_data)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON in structured_data")

    docx_bytes = generate_report(
        structured=structured,
        response_text=response_text,
        user_message=user_message,
    )

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=Fuelled_Valuation_Report.docx"},
    )
