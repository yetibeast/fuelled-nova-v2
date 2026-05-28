"""MockProvider — deterministic enrichment for tests and dry-runs.

Returns canned contacts based on the seller_name. Lets us exercise the
runner + upsert path without burning Anthropic credits.
"""
from __future__ import annotations

from app.pricing_v2.intel.providers.base import (
    Contact,
    ProviderResult,
)


class MockProvider:
    """Deterministic provider for tests.

    Behaviour:
      * "fail-*" sellers raise (simulates provider error → run records failure).
      * "empty-*" sellers return zero contacts (provider succeeded but no hits).
      * Anything else returns one synthetic contact per seller.
    """

    name = "mock"
    cost_per_query_usd = 0.01

    def __init__(self, contacts_per_seller: int = 1, cost_usd: float = 0.01):
        self.contacts_per_seller = contacts_per_seller
        self.cost_usd = cost_usd
        self.calls: list[tuple[str, str, dict]] = []

    async def enrich_seller(
        self,
        seller_name: str,
        source: str,
        hints: dict,
    ) -> ProviderResult:
        self.calls.append((seller_name, source, hints))

        if seller_name.startswith("fail-"):
            return ProviderResult(
                contacts=[],
                cost_usd=self.cost_usd,
                raw_payload={"error": "simulated provider failure"},
                error="simulated provider failure",
            )

        if seller_name.startswith("empty-"):
            return ProviderResult(
                contacts=[],
                cost_usd=self.cost_usd,
                raw_payload={"contacts": []},
            )

        contacts = [
            Contact(
                name=f"Test Contact {i + 1}",
                title="Operations Lead",
                email=f"contact{i + 1}@{_slug(seller_name)}.com",
                linkedin=f"https://linkedin.com/in/{_slug(seller_name)}-{i + 1}",
                location="Houston, TX",
                confidence="medium",
                outreach_notes=f"Mock contact for {seller_name}",
            )
            for i in range(self.contacts_per_seller)
        ]
        return ProviderResult(
            contacts=contacts,
            cost_usd=self.cost_usd,
            raw_payload={"seller": seller_name, "source": source, "n": len(contacts)},
        )


def _slug(s: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")
