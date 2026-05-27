"""EnrichmentProvider Protocol + shared dataclasses.

Spec contract (docs/superpowers/specs/2026-05-20-nova-engine-architecture-spec.md
§ "Provider plug-in architecture"):

    class EnrichmentProvider(Protocol):
        name: str
        cost_per_query_usd: float
        async def enrich_seller(self, seller_name: str, source: str,
                                hints: dict) -> ProviderResult: ...

A ProviderResult bundles the contacts produced for one seller-research call
with the measured cost and the raw upstream payload (kept for auditability —
upserted to seller_contact_enrichment.raw_provider_payload in future work).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


@dataclass
class Contact:
    """One discovered contact at a seller."""
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    confidence: Optional[str] = None        # 'high' | 'medium' | 'low' | None
    outreach_notes: Optional[str] = None


@dataclass
class ProviderResult:
    """Output of one enrich_seller call."""
    contacts: list[Contact] = field(default_factory=list)
    cost_usd: float = 0.0
    raw_payload: Any = None
    error: Optional[str] = None             # set when the provider failed


class EnrichmentProvider(Protocol):
    name: str
    cost_per_query_usd: float

    async def enrich_seller(
        self,
        seller_name: str,
        source: str,
        hints: dict,
    ) -> ProviderResult: ...
