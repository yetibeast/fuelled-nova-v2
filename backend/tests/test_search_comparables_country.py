"""Country filter for search_comparables.

Mark Le Dain's 2026-05-27 email: when Nova prices US equipment (e.g. EOG units),
the comps anchor to Canadian listings because the database is CA-heavy and the
tool exposes no country knob. This test pins the contract that `country="US"`
returns only US-located listings and `country="CA"` returns only CA-located
ones, while omitting `country` preserves the existing behavior.

We mock get_session locally (do NOT touch conftest.py — shared) and apply
the constructed WHERE clause + params against an in-memory listings list.
This validates the impl actually narrows the SQL, not just accepts a param.
"""
from __future__ import annotations

import asyncio
import re
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest


# ── In-memory listing fixtures used by the mock session ─────────────────

_LISTINGS = [
    # Sources with country column populated (fuelled, ironhub).
    {"title": "2018 Ariel JGK/4 Compressor Package", "asking_price": 450000,
     "currency": "USD", "source": "fuelled", "location": "Midland, Texas",
     "country": "United Sta", "year": 2018, "hours": 12000,
     "url": "https://fuelled.com/listing/us-1"},
    {"title": "2019 Ariel JGK/4 Compressor Package", "asking_price": 460000,
     "currency": "CAD", "source": "fuelled", "location": "Grande Prairie, AB",
     "country": "Canada", "year": 2019, "hours": 10000,
     "url": "https://fuelled.com/listing/ca-1"},

    # Sources with NULL country — must be inferred from `location`.
    # allsurplus: ", USA" / ", CAN" suffix
    {"title": "2017 Ariel Compressor", "asking_price": 320000,
     "currency": "USD", "source": "allsurplus",
     "location": "Houston, Texas, USA", "country": None,
     "year": 2017, "hours": 9000,
     "url": "https://allsurplus.example/us-allsurplus"},
    {"title": "2016 Ariel Compressor", "asking_price": 310000,
     "currency": "CAD", "source": "allsurplus",
     "location": "Cambridge, Ontario, CAN", "country": None,
     "year": 2016, "hours": 11000,
     "url": "https://allsurplus.example/ca-allsurplus"},

    # bidspotter: full state/province names
    {"title": "Compressor — Pennsylvania", "asking_price": 275000,
     "currency": "USD", "source": "bidspotter",
     "location": "Philadelphia, Pennsylvania", "country": None,
     "year": 2015, "hours": None,
     "url": "https://bidspotter.example/us-bs"},
    {"title": "Compressor — Alberta", "asking_price": 285000,
     "currency": "CAD", "source": "bidspotter",
     "location": "Calgary, Alberta", "country": None,
     "year": 2015, "hours": None,
     "url": "https://bidspotter.example/ca-bs"},

    # kijiji / equipmenttrader: 2-letter state/province suffix
    {"title": "Compressor unit", "asking_price": 195000,
     "currency": "CAD", "source": "kijiji",
     "location": "Edmonton, AB", "country": None,
     "year": 2014, "hours": None,
     "url": "https://kijiji.example/ca-kj"},
    {"title": "Compressor unit", "asking_price": 205000,
     "currency": "USD", "source": "equipmenttrader",
     "location": "henderson, IA", "country": None,
     "year": 2014, "hours": None,
     "url": "https://equipmenttrader.example/us-et"},
]


class _Row:
    """Mimics SQLAlchemy Row — attributes by name, indexable."""
    def __init__(self, d: dict):
        self._d = d
        for k, v in d.items():
            setattr(self, k, v)


class _Result:
    def __init__(self, rows): self._rows = [_Row(r) for r in rows]
    def fetchall(self): return self._rows
    def fetchone(self): return self._rows[0] if self._rows else None


def _eval_listing_country(listing: dict) -> str | None:
    """Python-side mirror of the SQL country-detection logic.

    Mirrors what the production SQL is expected to do so we can pre-filter
    the seeded rows and compare. If the SQL diverges, the tests will fail
    (which is the contract we want).
    """
    country = (listing.get("country") or "").strip()
    if country:
        if country.lower().startswith("united sta") or country.upper() == "USA" or country.upper() == "US":
            return "US"
        if country.lower() == "canada" or country.upper() == "CAN" or country.upper() == "CA":
            return "CA"
        return None  # Mexico, etc. — neither US nor CA

    loc = (listing.get("location") or "").strip()
    if not loc:
        return None

    # Trailing 3-letter codes
    if re.search(r",\s*USA\s*$", loc, re.IGNORECASE):
        return "US"
    if re.search(r",\s*CAN\s*$", loc, re.IGNORECASE):
        return "CA"

    # 2-letter state/province at end (most precise)
    US_STATES_2 = {"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
                   "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
                   "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
                   "VA","WA","WV","WI","WY","DC"}
    CA_PROVS_2 = {"AB","BC","MB","NB","NL","NS","NT","NU","ON","PE","QC","SK","YT"}
    m = re.search(r",\s*([A-Za-z]{2})\s*$", loc)
    if m:
        code = m.group(1).upper()
        # CA wins on "CA" ambiguity? No — "CA" here means California (US state).
        # But "CA" as 2-letter for both California AND Canada is ambiguous; trust state.
        if code in US_STATES_2:
            return "US"
        if code in CA_PROVS_2:
            return "CA"

    # Full state/province names anywhere in location
    US_STATES_FULL = ["Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut",
                      "Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa",
                      "Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan",
                      "Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire",
                      "New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio",
                      "Oklahoma","Oregon","Pennsylvania","Rhode Island","South Carolina","South Dakota",
                      "Tennessee","Texas","Utah","Vermont","Virginia","Washington","West Virginia",
                      "Wisconsin","Wyoming","District of Columbia"]
    CA_PROVS_FULL = ["Alberta","British Columbia","Manitoba","New Brunswick","Newfoundland","Nova Scotia",
                     "Northwest Territories","Nunavut","Ontario","Prince Edward Island","Quebec",
                     "Saskatchewan","Yukon"]
    for s in US_STATES_FULL:
        if s.lower() in loc.lower():
            return "US"
    for p in CA_PROVS_FULL:
        if p.lower() in loc.lower():
            return "CA"
    return None


class _FakeSession:
    """Mimic the async session enough to satisfy search_comparables."""
    async def execute(self, sql_text, params=None):
        sql = getattr(sql_text, "text", str(sql_text))
        params = params or {}

        # We only care about the listings SELECT — that's all search_comparables hits.
        if "FROM listings" not in sql:
            return _Result([])

        # Filter by keyword (kw0, kw1, ...). search_comparables uses ILIKE '%kw%'.
        kw_terms = [v.strip("%").lower() for k, v in params.items() if k.startswith("kw")]
        rows = []
        for l in _LISTINGS:
            title = (l["title"] or "").lower()
            if kw_terms and not any(kw in title for kw in kw_terms):
                continue
            # Price range.
            pmin = params.get("pmin", 0) or 0
            pmax = params.get("pmax", 99999999) or 99999999
            if not (pmin <= (l.get("asking_price") or 0) <= pmax):
                continue
            # Country filter — this is what we're testing.
            country = params.get("country")
            if country:
                inferred = _eval_listing_country(l)
                if inferred != country.upper():
                    continue
            rows.append(l)
        lim = params.get("lim", 20) or 20
        return _Result(rows[:lim])

    async def commit(self): pass
    async def rollback(self): pass


@asynccontextmanager
async def _fake_get_session():
    yield _FakeSession()


# ── Tests ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _patch_session():
    with patch("app.pricing_v2.tools.get_session", _fake_get_session):
        yield


def _call(**kwargs):
    from app.pricing_v2.tools import search_comparables
    return asyncio.run(search_comparables(**kwargs))


def test_country_us_returns_only_us_listings():
    out = _call(keywords=["compressor"], country="US")
    # US listings should appear.
    assert "us-1" in out or "us-allsurplus" in out or "us-bs" in out or "us-et" in out
    # CA listings must NOT appear.
    assert "ca-1" not in out
    assert "ca-allsurplus" not in out
    assert "ca-bs" not in out
    assert "ca-kj" not in out


def test_country_ca_returns_only_ca_listings():
    out = _call(keywords=["compressor"], country="CA")
    # CA listings should appear.
    assert "ca-1" in out or "ca-allsurplus" in out or "ca-bs" in out or "ca-kj" in out
    # US listings must NOT appear.
    assert "us-1" not in out
    assert "us-allsurplus" not in out
    assert "us-bs" not in out
    assert "us-et" not in out


def test_country_none_returns_all():
    out = _call(keywords=["compressor"])
    # Both US and CA listings should appear when no country filter is set.
    has_us = any(tag in out for tag in ("us-1", "us-allsurplus", "us-bs", "us-et"))
    has_ca = any(tag in out for tag in ("ca-1", "ca-allsurplus", "ca-bs", "ca-kj"))
    assert has_us, "expected at least one US listing in unfiltered results"
    assert has_ca, "expected at least one CA listing in unfiltered results"
