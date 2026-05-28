"""Enrichment providers.

Each provider implements EnrichmentProvider Protocol. The orchestrator
chains them (claude_parallel first, then apollo for high-value sellers,
hubspot for internal context). For now this dispatch ships claude_parallel
and a MockProvider for deterministic tests.
"""
from app.pricing_v2.intel.providers.base import (
    Contact,
    EnrichmentProvider,
    ProviderResult,
)

__all__ = ["Contact", "EnrichmentProvider", "ProviderResult"]
