"""Tests for the EnrichmentProvider Protocol implementations.

Covers MockProvider (used by the runner tests + dry-runs) and the
ClaudeParallelProvider cost-math + response parser. The Claude provider's
network call itself is never exercised — we inject a fake client.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest


# ── MockProvider ──────────────────────────────────────────────────────────


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_mock_provider_returns_canned_contact():
    from app.pricing_v2.intel.providers.mock import MockProvider

    p = MockProvider()
    result = _run(p.enrich_seller("ACME Auctions", "bidspotter", {}))

    assert result.error is None
    assert len(result.contacts) == 1
    c = result.contacts[0]
    assert c.name == "Test Contact 1"
    assert c.email == "contact1@acme-auctions.com"
    assert c.confidence == "medium"
    assert result.cost_usd == pytest.approx(0.01)


def test_mock_provider_records_calls_for_inspection():
    from app.pricing_v2.intel.providers.mock import MockProvider

    p = MockProvider()
    _run(p.enrich_seller("ACME", "kijiji", {"sample_listing_urls": ["x"]}))
    _run(p.enrich_seller("Beta", "allsurplus", {}))

    assert len(p.calls) == 2
    assert p.calls[0][0] == "ACME"
    assert p.calls[1][1] == "allsurplus"


def test_mock_provider_simulates_failure_for_fail_prefix():
    from app.pricing_v2.intel.providers.mock import MockProvider

    p = MockProvider()
    result = _run(p.enrich_seller("fail-bad-seller", "x", {}))

    assert result.error is not None
    assert result.contacts == []


def test_mock_provider_returns_empty_for_empty_prefix():
    from app.pricing_v2.intel.providers.mock import MockProvider

    p = MockProvider()
    result = _run(p.enrich_seller("empty-no-hits", "x", {}))

    assert result.error is None
    assert result.contacts == []


# ── ClaudeParallelProvider — cost math + response parsing ──────────────


def test_compute_cost_combines_tokens_and_web_search_fee():
    from app.pricing_v2.intel.providers.claude_parallel import _compute_cost

    usage = SimpleNamespace(input_tokens=2000, output_tokens=500)
    cost = _compute_cost(usage)

    # 2000 input * $3/M + 500 output * $15/M + $0.01 web search
    # = 0.006 + 0.0075 + 0.01 = 0.0235
    assert cost == pytest.approx(0.0235, rel=1e-4)


def test_compute_cost_zero_when_no_usage():
    from app.pricing_v2.intel.providers.claude_parallel import _compute_cost

    cost = _compute_cost(None)
    # Just the web search fee.
    assert cost == pytest.approx(0.01)


def test_parse_contacts_round_trips_well_formed_json():
    from app.pricing_v2.intel.providers.claude_parallel import _parse_contacts

    payload = (
        '{"contacts": ['
        '{"name": "Jane Doe", "title": "BD Manager", '
        '"email": "jane@acme.com", "linkedin": "https://linkedin.com/in/jane", '
        '"confidence": "high", "outreach_notes": "Active on LinkedIn."}'
        ']}'
    )
    contacts = _parse_contacts(payload)

    assert len(contacts) == 1
    assert contacts[0].name == "Jane Doe"
    assert contacts[0].confidence == "high"


def test_parse_contacts_strips_code_fences():
    from app.pricing_v2.intel.providers.claude_parallel import _parse_contacts

    payload = '```json\n{"contacts": [{"name": "Jane"}]}\n```'
    contacts = _parse_contacts(payload)

    assert len(contacts) == 1
    assert contacts[0].name == "Jane"


def test_parse_contacts_extracts_embedded_object():
    from app.pricing_v2.intel.providers.claude_parallel import _parse_contacts

    payload = 'Sure! Here you go:\n{"contacts": [{"name": "Foo"}]}\nThanks.'
    contacts = _parse_contacts(payload)

    assert len(contacts) == 1
    assert contacts[0].name == "Foo"


def test_parse_contacts_returns_empty_on_malformed_json():
    from app.pricing_v2.intel.providers.claude_parallel import _parse_contacts

    assert _parse_contacts("not json at all") == []
    assert _parse_contacts("") == []


def test_claude_parallel_uses_injected_client_and_records_cost():
    """The provider must route through the injected client and produce a
    ProviderResult with parsed contacts + measured cost. No network."""
    from app.pricing_v2.intel.providers.claude_parallel import ClaudeParallelProvider

    class FakeMessages:
        def __init__(self):
            self.last_kwargs = None

        async def create(self, **kwargs):
            self.last_kwargs = kwargs
            return SimpleNamespace(
                content=[SimpleNamespace(
                    type="text",
                    text='{"contacts": [{"name": "Jane Doe", "title": "BD", '
                         '"email": "jane@acme.com", "confidence": "high"}]}',
                )],
                usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
                stop_reason="end_turn",
            )

    class FakeClient:
        def __init__(self):
            self.messages = FakeMessages()

    fake = FakeClient()
    provider = ClaudeParallelProvider(api_key="not-real", client=fake)

    result = _run(provider.enrich_seller(
        "ACME Auctions", "bidspotter",
        {"sample_listing_urls": ["https://bidspotter.com/lot/1"]},
    ))

    assert result.error is None
    assert len(result.contacts) == 1
    assert result.contacts[0].name == "Jane Doe"
    # 1000*$3/M + 200*$15/M + $0.01 = 0.003 + 0.003 + 0.01 = 0.016
    assert result.cost_usd == pytest.approx(0.016, rel=1e-4)

    # Confirm we passed the web_search tool to the API call.
    kw = fake.messages.last_kwargs
    assert kw["model"]
    assert kw["max_tokens"] == 1024
    tools = kw["tools"]
    assert any(t.get("name") == "web_search" for t in tools)


def test_claude_parallel_returns_error_on_api_failure():
    from app.pricing_v2.intel.providers.claude_parallel import ClaudeParallelProvider

    class BoomMessages:
        async def create(self, **kwargs):
            raise RuntimeError("network unreachable")

    class FakeClient:
        def __init__(self):
            self.messages = BoomMessages()

    provider = ClaudeParallelProvider(api_key="x", client=FakeClient())
    result = _run(provider.enrich_seller("ACME", "bidspotter", {}))

    assert result.contacts == []
    assert result.error and "network unreachable" in result.error


def test_claude_parallel_aborts_when_api_hangs_past_timeout():
    """Bug #11: an Anthropic call that never returns must not lock up the
    batch. Provider must abort within its configured per-call timeout and
    surface a TimeoutError-flavored ProviderResult."""
    import time
    from app.pricing_v2.intel.providers.claude_parallel import ClaudeParallelProvider

    class HangingMessages:
        async def create(self, **kwargs):
            # Simulate a stuck HTTPS call — sleep much longer than the
            # provider's timeout. If the provider doesn't enforce its own
            # timeout, this test will sit here for 30s.
            await asyncio.sleep(30)
            raise AssertionError("should never get here")

    class FakeClient:
        def __init__(self):
            self.messages = HangingMessages()

    provider = ClaudeParallelProvider(
        api_key="x",
        client=FakeClient(),
        per_call_timeout_s=2,
    )

    t0 = time.monotonic()
    result = _run(provider.enrich_seller("ACME", "bidspotter", {}))
    elapsed = time.monotonic() - t0

    # Must abort within timeout window (small headroom for scheduler jitter).
    assert elapsed < 5, f"provider hung for {elapsed:.1f}s (timeout was 2s)"
    assert result.contacts == []
    assert result.error is not None
    assert "timeout" in result.error.lower() or "TimeoutError" in result.error
