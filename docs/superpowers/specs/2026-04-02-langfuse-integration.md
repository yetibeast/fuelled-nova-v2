# Langfuse Integration — Observability & Token Tracking
**Date:** April 2, 2026
**Status:** Approved

---

## Problem

1. **No real cost tracking.** Currently estimating flat $1.50/query. Actual costs vary by model and tokens used. Sonnet pricing is $3/M input, $15/M output — a typical query costs ~$0.04, not $1.50.
2. **No conversation tracing.** Can't see what tools the agent called, how many tokens each step used, or where time was spent.
3. **No quality metrics.** No way to track which queries produce good valuations vs. poor ones over time.

---

## What Langfuse Gives Us

[Langfuse](https://langfuse.com) is an open-source LLM observability platform. It captures:

- **Traces** — full request lifecycle (user message → tool calls → response)
- **Token usage** — input/output tokens per API call, with cost calculation
- **Latency** — time per step (tool calls, Claude API, total)
- **Conversations** — threaded view of multi-turn interactions
- **Scores** — user feedback (thumbs up/down) linked to traces
- **Dashboards** — daily cost, token usage, latency percentiles, model breakdown

### Deployment Options

**(A) Langfuse Cloud** (recommended to start)
- Free tier: 50K observations/month
- No infrastructure to manage
- Sign up at langfuse.com, get API keys

**(B) Self-hosted on Proxmox**
- Docker compose with Postgres + Langfuse server
- Full control, no observation limits
- More setup, but free

**Recommendation:** Start with Cloud, move to self-hosted if volume exceeds free tier.

---

## Integration Points

### 1. Pricing Service (service.py) — Main Integration

The Anthropic SDK has a native Langfuse integration via the `langfuse` Python package.

```python
# backend/app/pricing_v2/service.py

from langfuse.decorators import observe, langfuse_context
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
    host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

@observe()
async def run_pricing(user_message, attachments=None, conversation_history=None):
    # Existing code...
    
    # Wrap the Anthropic client call
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system_prompt,
        messages=messages,
    )
    
    # Langfuse automatically captures:
    # - Input/output tokens from response.usage
    # - Model name
    # - Latency
    # - Full prompt and response (optional, configurable)
    
    # Update the current trace with metadata
    langfuse_context.update_current_observation(
        metadata={
            "tools_used": tools_used,
            "confidence": confidence,
        }
    )
```

### 2. Tool Calls — Span Tracking

Each tool call (search_comparables, lookup_rcn, etc.) gets its own span within the trace:

```python
@observe(as_type="span")
async def _call_tool(name, args):
    # Existing tool dispatch...
    return result
```

This gives us a timeline view:
```
Trace: run_pricing (4.2s, $0.042)
├── Generation: Claude API call 1 (1.8s, 3200 in / 800 out)
├── Span: search_comparables (0.3s)
├── Span: lookup_rcn (0.1s)
├── Span: calculate_fmv (0.05s)
├── Generation: Claude API call 2 (1.9s, 4100 in / 1200 out)
└── Span: check_equipment_risks (0.08s)
```

### 3. User Feedback — Scores

When users click thumbs up/down, attach the score to the Langfuse trace:

```python
# backend/app/api/admin.py — in post_feedback()

if trace_id:
    langfuse.score(
        trace_id=trace_id,
        name="user_feedback",
        value=1 if rating == "up" else 0,
        comment=comment,
    )
```

To enable this, `run_pricing()` returns the `trace_id` so the frontend can pass it back with feedback.

### 4. Batch Processing — Session Tracking

For batch jobs, group all item traces under a session:

```python
@observe()
async def run_pricing(user_message, session_id=None, ...):
    if session_id:
        langfuse_context.update_current_trace(session_id=session_id)
```

Batch jobs pass a shared `session_id` so all 143 items appear as one session in Langfuse.

---

## Environment Variables

Add to Railway backend:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...      # from langfuse.com
LANGFUSE_SECRET_KEY=sk-lf-...      # from langfuse.com
LANGFUSE_HOST=https://cloud.langfuse.com  # or self-hosted URL
```

If env vars are missing, Langfuse gracefully no-ops — no crashes, just no tracking.

---

## AI Management Page Updates

Replace the flat $1.50/query estimates with real data from Langfuse.

### Option A: Query Langfuse API directly

Langfuse has a REST API for metrics. The AI Management page can query:
- Daily cost breakdown (real token costs)
- Model usage breakdown
- Average latency per query
- Tool call frequency

### Option B: Compute from logged data (simpler)

Since we already log to `pricing_log.jsonl`, add token counts to each entry:

```python
# In run_pricing(), after Claude responds:
entry = {
    "timestamp": ...,
    "user_message": ...,
    "input_tokens": response.usage.input_tokens,
    "output_tokens": response.usage.output_tokens,
    "model": "claude-sonnet-4-20250514",
    "cost": (response.usage.input_tokens * 3 / 1_000_000) + 
            (response.usage.output_tokens * 15 / 1_000_000),
    # ... existing fields
}
```

Then `admin_ai.py` computes real costs from the log instead of `queries * 1.50`.

**Recommendation:** Do both. Langfuse for deep observability (traces, spans, sessions). Token logging in JSONL for the simple cost dashboard that already exists.

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/requirements.txt` | Add `langfuse` |
| `backend/app/pricing_v2/service.py` | Add `@observe()` decorators, token logging |
| `backend/app/api/admin.py` | Attach feedback scores to traces |
| `backend/app/api/admin_ai.py` | Compute real costs from token data |
| `frontend/nova-app/app/(app)/ai-management/page.tsx` | Display real costs instead of estimates |

---

## Implementation Steps

1. **Sign up for Langfuse Cloud** → get API keys
2. **Add `langfuse` to requirements.txt** and install
3. **Wrap `run_pricing()` with `@observe()`** — immediate token + cost tracking
4. **Add spans to tool calls** — `@observe(as_type="span")` on `_call_tool()`
5. **Log tokens to pricing_log.jsonl** — add input_tokens, output_tokens, cost fields
6. **Update admin_ai.py** — compute real costs from token data instead of flat $1.50
7. **Update AI Management page** — show real costs
8. **Wire feedback scores** — pass trace_id through to thumbs up/down
9. **Set env vars on Railway** — LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY
10. **Verify in Langfuse dashboard** — traces appearing, costs accurate

---

## Cost Estimates

**Langfuse Cloud free tier:** 50K observations/month. At ~5 tool calls per valuation, that's ~10K valuations/month — more than enough for current volume.

**Actual Claude costs** (vs. $1.50/query estimate):
- Typical valuation: ~4K input tokens + ~2K output tokens = $0.042/query
- Heavy valuation (multiple tool loops): ~8K input + ~4K output = $0.084/query
- Batch of 143 items: ~143 × $0.05 = ~$7.15 (vs. $214.50 at $1.50/query)

Real costs are approximately **30x lower** than current estimates.

---

## Verification

| Test | Expected |
|------|----------|
| Run a pricing query | Trace appears in Langfuse dashboard |
| Check token counts | input_tokens and output_tokens in pricing_log.jsonl |
| AI Management cost | Shows real cost (~$0.04/query) not $1.50 |
| Thumbs down feedback | Score appears on trace in Langfuse |
| Batch job | All items grouped under one session in Langfuse |
| Missing env vars | App runs normally, just no Langfuse tracking |
