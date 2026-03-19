from __future__ import annotations
import base64
import json
from fastapi import APIRouter, Form, File, UploadFile
from fastapi.responses import Response
from app.pricing_v2.service import run_pricing
from app.pricing_v2.report import generate_report

router = APIRouter()

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
):
    attachments = []
    for f in files:
        data = base64.b64encode(await f.read()).decode()
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
    return result


@router.post("/report")
async def post_report(
    structured_data: str = Form(...),
    response_text: str = Form(default=""),
    user_message: str = Form(default="Equipment Valuation"),
):
    structured = json.loads(structured_data)

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
