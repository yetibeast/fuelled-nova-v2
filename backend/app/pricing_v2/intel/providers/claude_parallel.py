"""ClaudeParallelProvider — Anthropic Sonnet + web-search tool.

Default broad-pass provider per spec. Single web_search tool call per
seller, then structured JSON synthesis. Target cost ≤$0.30 per seller.

Pricing (Sonnet 4.6 as of 2026-05-27):
  * $3 / 1M input tokens
  * $15 / 1M output tokens

The web_search tool itself bills $10/1000 searches; we limit to max_uses=1
so it's a flat $0.01 per seller for the search step.

Reference: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool

NOTE: tests use MockProvider; this provider is never exercised in the
test suite. First real invocation will be by Curtis with ANTHROPIC_API_KEY
set against the prod queue.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Optional

from app.pricing_v2.intel.providers.base import Contact, ProviderResult

_log = logging.getLogger(__name__)


_SONNET_MODEL = "claude-sonnet-4-5-20250929"

# Per-million token rates (USD).
_PRICE_INPUT_PER_M = 3.0
_PRICE_OUTPUT_PER_M = 15.0
# Web-search tool: $10 per 1000 calls, max_uses=1 here.
_PRICE_WEB_SEARCH_PER_CALL = 0.01


_SYSTEM_PROMPT = (
    "You're researching contact info for a B2B equipment seller or auction "
    "house in the oil-and-gas / heavy-equipment secondary market.\n\n"
    "Use one web_search call to find named contacts (sales, BD, operations, "
    "owner) at the seller. Then return a structured JSON object — and "
    "nothing else — matching this shape exactly:\n\n"
    "{\n"
    '  "contacts": [\n'
    "    {\n"
    '      "name": "Full Name",\n'
    '      "title": "Job Title",\n'
    '      "email": "name@company.com or null",\n'
    '      "phone": "+1-555-... or null",\n'
    '      "linkedin": "https://linkedin.com/in/... or null",\n'
    '      "location": "City, ST or null",\n'
    '      "confidence": "high | medium | low",\n'
    '      "outreach_notes": "1-2 sentences on how to reach them."\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
    "Confidence rubric:\n"
    '  * "high" — verified email pattern and LinkedIn match.\n'
    '  * "medium" — found a person + title; email inferred from pattern.\n'
    '  * "low" — guessed contact, sparse evidence.\n\n'
    "If you find zero contacts return {\"contacts\": []}. Never invent "
    "people. Return JSON only — no prose, no markdown fences."
)


def _build_user_prompt(seller_name: str, source: str, hints: dict) -> str:
    sample_urls = hints.get("sample_listing_urls") or []
    location = hints.get("location")
    lines = [
        f"Seller: {seller_name}",
        f"Source platform: {source}",
    ]
    if location:
        lines.append(f"Known location hint: {location}")
    if sample_urls:
        lines.append("Sample listings (use these to identify the company):")
        for url in sample_urls[:3]:
            lines.append(f"  - {url}")
    lines.append("\nFind named contacts at this company. Return JSON only.")
    return "\n".join(lines)


def _compute_cost(usage: Any) -> float:
    """Cost in USD: input tokens + output tokens + 1 web-search call."""
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    return (
        (in_tok / 1_000_000.0) * _PRICE_INPUT_PER_M
        + (out_tok / 1_000_000.0) * _PRICE_OUTPUT_PER_M
        + _PRICE_WEB_SEARCH_PER_CALL
    )


def _extract_text(response: Any) -> str:
    """Pull the assistant's text out of a Messages API response."""
    pieces: list[str] = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "text":
            pieces.append(getattr(block, "text", "") or "")
    return "\n".join(pieces).strip()


def _parse_contacts(text: str) -> list[Contact]:
    """Robustly extract the contacts list from Claude's response."""
    if not text:
        return []
    # Strip code fences if model added them despite instructions.
    if text.startswith("```"):
        text = text.strip("`")
        # Drop optional "json" language tag on first line.
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON object substring.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return []
    raw_contacts = data.get("contacts") if isinstance(data, dict) else None
    if not isinstance(raw_contacts, list):
        return []
    out: list[Contact] = []
    for c in raw_contacts:
        if not isinstance(c, dict):
            continue
        out.append(Contact(
            name=c.get("name") or None,
            title=c.get("title") or None,
            email=c.get("email") or None,
            phone=c.get("phone") or None,
            linkedin=c.get("linkedin") or None,
            location=c.get("location") or None,
            confidence=c.get("confidence") or None,
            outreach_notes=c.get("outreach_notes") or None,
        ))
    return out


class ClaudeParallelProvider:
    """Default broad-pass provider. Uses Anthropic SDK + web_search tool."""

    name = "claude_parallel"
    cost_per_query_usd = 0.30   # budget ceiling per spec

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = _SONNET_MODEL,
        max_tokens: int = 1024,
        client: Any = None,
        per_call_timeout_s: float = 120.0,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self._client = client    # injectable for offline tests
        # Hard ceiling on a single messages.create() round-trip. The SDK's
        # built-in timeout has been observed to silently never fire (see
        # 2026-05-27 incident: 36-min hang on a single seller during a 200-
        # seller batch). asyncio.wait_for is the belt to the SDK's braces.
        self.per_call_timeout_s = per_call_timeout_s

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        # Lazy import — tests should never reach this branch.
        import anthropic  # type: ignore
        self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def enrich_seller(
        self,
        seller_name: str,
        source: str,
        hints: dict,
    ) -> ProviderResult:
        client = self._get_client()
        user_prompt = _build_user_prompt(seller_name, source, hints)
        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=_SYSTEM_PROMPT,
                    tools=[{
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": 1,
                    }],
                    messages=[{"role": "user", "content": user_prompt}],
                ),
                timeout=self.per_call_timeout_s,
            )
        except asyncio.TimeoutError:
            _log.warning(
                "claude_parallel timed out after %.1fs for %s",
                self.per_call_timeout_s, seller_name,
            )
            return ProviderResult(
                contacts=[],
                cost_usd=0.0,
                raw_payload=None,
                error=f"TimeoutError: per-call timeout {self.per_call_timeout_s}s exceeded",
            )
        except Exception as exc:   # network / auth / model failure
            _log.exception("claude_parallel failed for %s", seller_name)
            return ProviderResult(
                contacts=[],
                cost_usd=0.0,
                raw_payload=None,
                error=f"{type(exc).__name__}: {exc}",
            )

        cost = _compute_cost(getattr(response, "usage", None))
        text = _extract_text(response)
        contacts = _parse_contacts(text)
        return ProviderResult(
            contacts=contacts,
            cost_usd=cost,
            raw_payload={"text": text, "stop_reason": getattr(response, "stop_reason", None)},
        )
