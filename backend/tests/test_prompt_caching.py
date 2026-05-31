"""Tests for Anthropic prompt caching on the pricing system prompt.

Caching fails silently (cache_read_input_tokens stays 0, no error), so we test
two things separately:
  1. structure — the system block carries cache_control (unit, here)
  2. cost accounting — cached tokens are priced correctly so the cost log stays
     accurate once input_tokens becomes the uncached-remainder only (unit, here)

The load-bearing "does it actually cache against the real API" check is a live
2-call verification run separately (needs a key + network), not in this file.
"""
from app.pricing_v2.service import _cached_system, _compute_cost


# ── System block carries cache_control ────────────────────────────────────
def test_cached_system_wraps_prompt_with_ephemeral_cache_control():
    blocks = _cached_system("SYSTEM TEXT")
    assert blocks == [
        {"type": "text", "text": "SYSTEM TEXT", "cache_control": {"type": "ephemeral"}}
    ]


def test_cached_system_preserves_prompt_text_exactly():
    # Byte-stability matters — any drift invalidates the cache prefix.
    prompt = "line1\nline2 with {braces} and unicode ✓"
    assert _cached_system(prompt)[0]["text"] == prompt


# ── Cost accounting with cached tokens (Sonnet 4.6: $3/M in, $15/M out) ────
# cache read = 0.1 × input = $0.30/M ; cache creation (5-min) = 1.25 × input = $3.75/M
def test_compute_cost_full_price_input_output():
    # 1M input ($3) + 1M output ($15), no cache
    assert _compute_cost(1_000_000, 0, 0, 1_000_000) == 18.0


def test_compute_cost_cache_read_priced_at_one_tenth():
    assert _compute_cost(0, 1_000_000, 0, 0) == 0.30


def test_compute_cost_cache_creation_priced_at_1_25x():
    assert _compute_cost(0, 0, 1_000_000, 0) == 3.75


def test_compute_cost_full_breakdown():
    # input 3 + read 0.30 + creation 3.75 + output 15 = 22.05
    assert _compute_cost(1_000_000, 1_000_000, 1_000_000, 1_000_000) == 22.05
