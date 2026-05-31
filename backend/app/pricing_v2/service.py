from __future__ import annotations
import asyncio
import datetime
import json
import logging
import os
import re
import anthropic
from fastapi import HTTPException
from app.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_API_KEY_FALLBACK,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_HOST,
)
from app.pricing_v2.prompts import build_system_prompt
from app.pricing_v2.schemas import TOOLS
from app.pricing_v2 import tools as tool_fns
from app.pricing_v2.normalize import normalize_structured

_log = logging.getLogger(__name__)

# Build the client chain. Primary first (Fuelled's account, tier 1 today).
# Fallback is optional — typically Curt's Arcanos org key at a higher tier
# so that user-facing pricing calls keep working when the primary 429s.
_clients = [
    ("primary", anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)),
]
if ANTHROPIC_API_KEY_FALLBACK:
    _clients.append(("fallback", anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY_FALLBACK)))
    _log.info("Anthropic fallback key configured (%d clients in chain)", len(_clients))

# Primary client (legacy single-client references in this module still use _client)
_client = _clients[0][1]


async def _call_anthropic(**kwargs):
    """Wrap messages.create with structured error responses + key fallback.

    Iterates through the configured client chain on RateLimitError, so when the
    primary key is exhausted the request falls through to the fallback key
    transparently. The user sees a successful response instead of a 429.

    Non-rate-limit errors fail fast (a bad request or model misconfig won't be
    fixed by a different key).

    Anthropic errors that exhaust the chain become HTTPException with structured
    detail = {code, message, ...} so the frontend can map error class → actionable
    user message instead of showing generic "Something went wrong."
    """
    last_429 = None
    for label, client in _clients:
        try:
            response = await client.messages.create(**kwargs)
            if label != "primary":
                _log.info("Anthropic %s key served request after primary 429", label)
            return response
        except anthropic.RateLimitError as e:
            last_429 = e
            _log.warning("Anthropic %s key rate-limited, trying next in chain", label)
            continue
        except anthropic.NotFoundError as e:
            _log.error("Anthropic model not found: %s", e)
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "model_not_found",
                    "message": (
                        "The pricing model is misconfigured (likely a retired model ID). "
                        "Engineering has been notified — please try a different listing in a few minutes."
                    ),
                },
            ) from e
        except anthropic.APITimeoutError as e:
            _log.warning("Anthropic timeout: %s", e)
            raise HTTPException(
                status_code=504,
                detail={
                    "code": "anthropic_timeout",
                    "message": (
                        "The pricing call took longer than expected. "
                        "Try a shorter file, or split the question into two requests."
                    ),
                },
            ) from e
        except anthropic.BadRequestError as e:
            _log.warning("Anthropic bad request: %s", e)
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "anthropic_bad_request",
                    "message": (
                        "Anthropic rejected the request. "
                        "Most often this means the file format isn't supported, or the input is too large."
                    ),
                    "raw": str(e)[:300],
                },
            ) from e
        except anthropic.APIError as e:
            _log.error("Anthropic API error: %s", e)
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "anthropic_error",
                    "message": "Anthropic returned an error. Try again in a moment.",
                    "raw": str(e)[:300],
                },
            ) from e

    # All clients in the chain rate-limited. Surface the structured 429.
    retry_after = 60
    try:
        retry_after = int(last_429.response.headers.get("retry-after", 60))
    except Exception:
        pass
    _log.warning("All Anthropic keys rate-limited (%d in chain): %s", len(_clients), last_429)
    raise HTTPException(
        status_code=429,
        detail={
            "code": "rate_limit_error",
            "message": (
                f"Both Anthropic keys are rate-limited (chain length: {len(_clients)}). "
                f"Try again in ~{retry_after} seconds. Curt is working on raising the cap."
                if len(_clients) > 1 else
                "Anthropic API is rate-limited (Fuelled's quota). "
                f"Try again in ~{retry_after} seconds. Curt is working on raising the limit."
            ),
            "retry_after_seconds": retry_after,
        },
    ) from last_429


# ── Prompt caching ──────────────────────────────────────────────────────
def _cached_system(system_prompt: str) -> list[dict]:
    """Wrap the system prompt in a cache_control block.

    The (tools + system) prefix is ~15K static tokens re-sent on every call and
    every tool-loop iteration. Caching it cuts cost ~90% on that prefix and drops
    the rate-limited input per call from ~19K to ~4K. The breakpoint on the system
    block caches tools + system together (tools render before system).
    """
    return [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]


# Sonnet 4.6 pricing (USD/token). Cache read = 0.1× input; cache write = 1.25× input.
_RATE_IN = 3 / 1_000_000
_RATE_OUT = 15 / 1_000_000


def _compute_cost(input_tokens: int, cache_read: int, cache_creation: int, output_tokens: int) -> float:
    """Accurate cost once caching splits usage. input_tokens is the uncached
    remainder only; cached tokens are billed separately (read 0.1×, write 1.25×)."""
    return round(
        input_tokens * _RATE_IN
        + cache_read * _RATE_IN * 0.1
        + cache_creation * _RATE_IN * 1.25
        + output_tokens * _RATE_OUT,
        6,
    )


# ── Langfuse (optional — graceful no-op when keys are missing) ──────────
_langfuse_ok = False
try:
    from langfuse import observe as _lf_observe, get_client as _lf_get_client

    if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
        _langfuse_ok = True
        observe = _lf_observe
        _log.info("Langfuse observability enabled (%s)", LANGFUSE_HOST)
except Exception:  # pragma: no cover
    _log.debug("Langfuse not available — observability disabled")

if not _langfuse_ok:
    def observe(**_kw):  # type: ignore[misc]
        def _noop(fn):
            return fn
        return _noop

TOOL_MAP = {
    "fetch_listing": tool_fns.fetch_listing,
    "search_comparables": tool_fns.search_comparables,
    "get_category_stats": tool_fns.get_category_stats,
    "lookup_rcn": tool_fns.lookup_rcn,
    "calculate_fmv": tool_fns.calculate_fmv,
    "check_equipment_risks": tool_fns.check_equipment_risks,
}

ASYNC_TOOLS = {"fetch_listing", "search_comparables", "get_category_stats", "lookup_rcn"}


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


@observe()
async def run_pricing(
    user_message: str,
    attachments: list[dict] | None = None,
    conversation_history: list[dict] | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
    conversation_id: str | None = None,
) -> dict:
    system_prompt = build_system_prompt(email=user_email)
    _model = "claude-sonnet-4-6"

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
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_read = 0
    total_cache_creation = 0
    cached_system = _cached_system(system_prompt)

    def _tally(usage):
        nonlocal total_input_tokens, total_output_tokens, total_cache_read, total_cache_creation
        total_input_tokens += getattr(usage, "input_tokens", 0) or 0
        total_output_tokens += getattr(usage, "output_tokens", 0) or 0
        total_cache_read += getattr(usage, "cache_read_input_tokens", 0) or 0
        total_cache_creation += getattr(usage, "cache_creation_input_tokens", 0) or 0

    # Initial API call
    response = await _call_anthropic(
        model=_model,
        system=cached_system,
        tools=TOOLS,
        messages=messages,
        max_tokens=8192,
    )
    _tally(response.usage)

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
        response = await _call_anthropic(
            model=_model,
            system=cached_system,
            tools=TOOLS,
            messages=messages,
            max_tokens=8192,
        )
        _tally(response.usage)

    # Extract final text
    full_text = "".join(b.text for b in response.content if hasattr(b, "text"))

    # Parse structured JSON if present
    structured = _extract_json(full_text)
    if structured:
        structured = normalize_structured(structured)
    clean_text = _strip_json_block(full_text) if structured else full_text

    # Determine confidence
    used_set = set(tools_used)
    if "search_comparables" in used_set and "calculate_fmv" in used_set:
        confidence = "HIGH"
    elif "calculate_fmv" in used_set:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # ── Cost calculation (cache-aware: read 0.1×, write 1.25× input) ─────
    cost_usd = _compute_cost(total_input_tokens, total_cache_read, total_cache_creation, total_output_tokens)

    # ── Langfuse trace metadata ─────────────────────────────────
    trace_id = None
    if _langfuse_ok:
        try:
            lf = _lf_get_client()
            lf.update_current_span(
                metadata={"tools_used": tools_used, "confidence": confidence, "model": _model},
            )
            lf.update_current_trace(
                user_id=user_id,
                session_id=conversation_id,
            )
            # Log a generation observation with token usage + cost
            gen = lf.start_observation(
                name="claude-tool-loop",
                as_type="generation",
                model=_model,
                input=user_message,
                output=clean_text[:500],
                usage_details={"input": total_input_tokens, "output": total_output_tokens},
                cost_details={"total": cost_usd},
                metadata={"tools_used": tools_used, "tool_loop_rounds": len(tools_used)},
            )
            gen.end()
            trace_id = lf.get_current_trace_id()
        except Exception:
            _log.debug("Langfuse trace update failed", exc_info=True)

    result = {
        "response": clean_text,
        "structured": structured or {},
        "tools_used": tools_used,
        "confidence": confidence,
        "trace_id": trace_id,
    }

    # Append log entry (non-blocking)
    from app.config import LOG_DIR as log_dir
    os.makedirs(log_dir, exist_ok=True)
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "user_id": user_id,
        "user_email": user_email,
        "user_message": user_message,
        "tools_used": tools_used,
        "confidence": confidence,
        "structured": structured or {},
        "response_length": len(clean_text),
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "cache_read_tokens": total_cache_read,
        "cache_creation_tokens": total_cache_creation,
        "model": _model,
        "cost_usd": round(cost_usd, 6),
        "trace_id": trace_id,
    }

    def _write_log():
        with open(os.path.join(log_dir, "pricing_log.jsonl"), "a") as f:
            f.write(json.dumps(entry) + "\n")

    await asyncio.to_thread(_write_log)

    return result


# ── Portfolio synthesis ──────────────────────────────────────


def prepare_synthesis_input(results: list[dict]) -> str:
    """Compress batch results for portfolio synthesis — structured JSON only, <50K tokens."""
    items = []
    for r in results:
        s = r.get("structured", {})
        v = s.get("valuation", {})
        items.append({
            "title": r.get("title", ""),
            "fmv_low": v.get("fmv_low"),
            "fmv_high": v.get("fmv_high"),
            "confidence": v.get("confidence"),
            "currency": v.get("currency", "CAD"),
            "risks": s.get("risks", [])[:3],
            "comps_count": len(s.get("comparables", [])),
        })
    return json.dumps(items, indent=None)


async def run_portfolio_synthesis(results: list[dict], summary: dict) -> dict:
    """Generate portfolio-level analysis from batch results using Claude."""
    synthesis_input = prepare_synthesis_input(results)

    # For now, generate synthesis from the structured data without an API call
    # This keeps costs down and is deterministic
    categories: dict[str, dict] = {}
    for r in results:
        v = r.get("structured", {}).get("valuation", {})
        cat = v.get("type") or r.get("title", "Equipment")[:30]
        if cat not in categories:
            categories[cat] = {"count": 0, "fmv_low": 0, "fmv_high": 0}
        categories[cat]["count"] += 1
        categories[cat]["fmv_low"] += v.get("fmv_low", 0) or 0
        categories[cat]["fmv_high"] += v.get("fmv_high", 0) or 0

    total_low = summary.get("total_fmv_low", 0)
    total_high = summary.get("total_fmv_high", 0)

    return {
        "executive_summary": f"Portfolio of {len(results)} items valued at ${total_low:,.0f} — ${total_high:,.0f}.",
        "category_breakdown": [
            {"category": cat, **vals} for cat, vals in categories.items()
        ],
        "data_quality_notes": None,
        "disposition_strategy": None,
    }
