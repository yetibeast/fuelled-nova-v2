"""Dedicated Claude pass for generating report-quality content (Tier 2/3)."""
from __future__ import annotations

import json
import logging
import re

import anthropic

from app.config import ANTHROPIC_API_KEY
from app.pricing_v2.report_prompt import build_report_prompt, build_report_messages

_log = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

_MODEL = "claude-sonnet-4-20250514"


def _extract_json(text: str) -> dict | None:
    """Extract JSON from Claude response, handling optional ```json fences."""
    # Try fenced block first
    match = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try raw JSON
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


async def generate_report_content(
    structured: dict,
    response_text: str,
    user_message: str,
    client: str,
    tier: int = 3,
) -> dict | None:
    """Call Claude to generate report-quality content sections.

    Returns parsed JSON dict on success, None on failure.
    """
    max_tokens = 4096 if tier == 2 else 8192

    try:
        system_prompt = build_report_prompt()
        messages = build_report_messages(
            structured, response_text, user_message, client, tier
        )

        response = await _client.messages.create(
            model=_MODEL,
            system=system_prompt,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3,
        )

        full_text = "".join(
            b.text for b in response.content if hasattr(b, "text")
        )

        sections = _extract_json(full_text)
        if sections is None:
            _log.warning("Report content: failed to parse JSON from Claude response")
            return None

        _log.info(
            "Report content generated: tier=%d, keys=%s, tokens=%d/%d",
            tier,
            list(sections.keys()),
            getattr(response.usage, "input_tokens", 0),
            getattr(response.usage, "output_tokens", 0),
        )
        return sections

    except Exception:
        _log.warning("Report content generation failed", exc_info=True)
        return None
