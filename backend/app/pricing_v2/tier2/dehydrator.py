"""Dehydrator family — TEG / mole sieve / generic.

RCN scales by gas throughput (MMSCFD). Depreciation follows
dedicated dehydrator curve (see rcn_engine/depreciation.py).
"""
from __future__ import annotations

from typing import Literal

DehydratorVariant = Literal["teg", "mole_sieve", "generic"]

DEHYDRATOR_MATCH_TERMS = (
    "dehydrator", "dehy", "teg", "triethylene glycol", "mole sieve", "molecular sieve",
)


def classify_dehydrator(text: str) -> DehydratorVariant:
    t = text.lower()
    if "teg" in t or "triethylene" in t or "glycol" in t:
        return "teg"
    if "mole sieve" in t or "molecular sieve" in t:
        return "mole_sieve"
    return "generic"


def price_dehydrator(listing: dict) -> "Tier2Row":  # implemented in 2.3
    raise NotImplementedError
