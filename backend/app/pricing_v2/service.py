from __future__ import annotations
import asyncio
import datetime
import json
import os
import re
import anthropic
from app.config import ANTHROPIC_API_KEY
from app.pricing_v2.prompts import build_system_prompt
from app.pricing_v2.schemas import TOOLS
from app.pricing_v2 import tools as tool_fns

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

TOOL_MAP = {
    "search_comparables": tool_fns.search_comparables,
    "get_category_stats": tool_fns.get_category_stats,
    "lookup_rcn": tool_fns.lookup_rcn,
    "calculate_fmv": tool_fns.calculate_fmv,
    "check_equipment_risks": tool_fns.check_equipment_risks,
}

ASYNC_TOOLS = {"search_comparables", "get_category_stats"}


async def _call_tool(name: str, args: dict) -> str:
    fn = TOOL_MAP[name]
    if name in ASYNC_TOOLS:
        return await fn(**args)
    return fn(**args)


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _strip_json_block(text: str) -> str:
    return re.sub(r"```json\s*\{.*?\}\s*```\s*", "", text, flags=re.DOTALL).strip()


async def run_pricing(user_message: str, attachments: list[dict] | None = None,
                      conversation_history: list[dict] | None = None) -> dict:
    system_prompt = build_system_prompt()

    # Build messages
    messages = []
    if conversation_history:
        messages.extend(conversation_history)

    # Build user content
    user_content = []
    if attachments:
        for att in attachments:
            if att.get("type") == "image":
                user_content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": att["media_type"], "data": att["data"]},
                })
            elif att.get("type") == "document":
                user_content.append({
                    "type": "document",
                    "source": {"type": "base64", "media_type": att["media_type"], "data": att["data"]},
                })
    user_content.append({"type": "text", "text": user_message})
    messages.append({"role": "user", "content": user_content})

    tools_used = []

    # Initial API call
    response = _client.messages.create(
        model="claude-sonnet-4-20250514",
        system=system_prompt,
        tools=TOOLS,
        messages=messages,
        max_tokens=8192,
    )

    # Tool loop
    while response.stop_reason == "tool_use":
        # Append assistant response
        messages.append({"role": "assistant", "content": response.content})

        # Process each tool_use block
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tools_used.append(block.name)
            try:
                result_str = await _call_tool(block.name, block.input)
            except Exception as e:
                result_str = f"Tool error: {e}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})

        # Call Claude again
        response = _client.messages.create(
            model="claude-sonnet-4-20250514",
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
            max_tokens=8192,
        )

    # Extract final text
    full_text = "".join(b.text for b in response.content if hasattr(b, "text"))

    # Parse structured JSON if present
    structured = _extract_json(full_text)
    clean_text = _strip_json_block(full_text) if structured else full_text

    # Determine confidence
    used_set = set(tools_used)
    if "search_comparables" in used_set and "calculate_fmv" in used_set:
        confidence = "HIGH"
    elif "calculate_fmv" in used_set:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    result = {
        "response": clean_text,
        "structured": structured or {},
        "tools_used": tools_used,
        "confidence": confidence,
    }

    # Append log entry
    log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "user_message": user_message,
        "tools_used": tools_used,
        "confidence": confidence,
        "structured": structured or {},
        "response_length": len(clean_text),
    }
    with open(os.path.join(log_dir, "pricing_log.jsonl"), "a") as f:
        f.write(json.dumps(entry) + "\n")

    return result
