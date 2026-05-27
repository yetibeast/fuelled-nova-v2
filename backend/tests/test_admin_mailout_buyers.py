"""Tests for GET /api/admin/mailout/buyers.csv — buy-side targets export.

Scope: auth gating, CSV shape, vertical filter, scale ordering, limit param.
Data source: buyer_targets table (populated by import_may10_enrichment.py).
"""
from __future__ import annotations

import csv
import io


def _seed_buyer_targets():
    """Inject buyer_targets rows into the in-memory test DB."""
    from tests import conftest
    if not hasattr(conftest._db, "buyer_targets"):
        conftest._db.buyer_targets = []
    conftest._db.buyer_targets.extend([
        {
            "vertical": "US Upstream O&G",
            "company": "Diamondback Energy",
            "ticker": "FANG",
            "hq": "Midland TX",
            "basin": "Permian (Midland + Delaware)",
            "scale": "13-14 rigs end-2025; ~$45B mkt cap",
            "capex_driver": "Closed Endeavor mega-deal 2024.",
            "suppliers_page": "https://www.diamondbackenergy.com/about/overview",
            "contact_name": "Gwendolyn Smith",
            "contact_title": "Senior Procurement Specialist",
            "contact_email": "gwendolyn.smith@diamondbackenergy.com",
            "contact_linkedin": "https://www.linkedin.com/in/gwendolyn-smith2/",
            "contact_confidence": "likely",
            "location": "Midland TX",
            "outreach_notes": "Senior procurement IC.",
        },
        {
            "vertical": "US Upstream O&G",
            "company": "Diamondback Energy",
            "ticker": "FANG",
            "hq": "Midland TX",
            "basin": "Permian (Midland + Delaware)",
            "scale": "13-14 rigs end-2025; ~$45B mkt cap",
            "capex_driver": "Closed Endeavor mega-deal 2024.",
            "suppliers_page": "https://www.diamondbackenergy.com/about/overview",
            "contact_name": "Cody King",
            "contact_title": "Materials Supervisor",
            "contact_email": "cody.king@diamondbackenergy.com",
            "contact_linkedin": "https://www.linkedin.com/in/cody-king-977b2292/",
            "contact_confidence": "likely",
            "location": "Midland TX",
            "outreach_notes": "Materials coordination.",
        },
        {
            "vertical": "US Midstream",
            "company": "Targa Resources",
            "ticker": "TRGP",
            "hq": "Houston TX",
            "basin": "Permian + Eagle Ford",
            "scale": "Mid-large midstream",
            "capex_driver": "Permian gas gathering buildout.",
            "suppliers_page": "https://www.targaresources.com/suppliers",
            "contact_name": None,
            "contact_title": None,
            "contact_email": None,
            "contact_linkedin": None,
            "contact_confidence": None,
            "location": None,
            "outreach_notes": None,
        },
    ])


_EXPECTED_BUYER_COLUMNS = [
    "vertical",
    "company",
    "ticker",
    "hq",
    "basin",
    "scale",
    "capex_driver",
    "suppliers_page",
    "contact_name",
    "contact_title",
    "contact_email",
    "contact_linkedin",
    "contact_confidence",
    "location",
    "outreach_notes",
]


def _parse_csv(body: str):
    reader = csv.reader(io.StringIO(body))
    rows = list(reader)
    header = rows[0]
    data = [dict(zip(header, r)) for r in rows[1:]]
    return header, data


# ── Auth ──────────────────────────────────────────────────────────────


def test_buyers_requires_token(client):
    resp = client.get("/api/admin/mailout/buyers.csv")
    assert resp.status_code == 401


def test_buyers_rejects_non_admin(client, user_headers):
    resp = client.get("/api/admin/mailout/buyers.csv", headers=user_headers)
    assert resp.status_code == 403


# ── CSV shape ─────────────────────────────────────────────────────────


def test_buyers_returns_csv_with_expected_header(client, admin_headers):
    _seed_buyer_targets()
    resp = client.get("/api/admin/mailout/buyers.csv", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "mailout_buyers_" in resp.headers["content-disposition"]
    header, _ = _parse_csv(resp.text)
    assert header == _EXPECTED_BUYER_COLUMNS


def test_buyers_returns_one_row_per_contact_plus_contactless_companies(client, admin_headers):
    """Diamondback has 2 contact rows → both appear. Targa has none → 1 row with blanks."""
    _seed_buyer_targets()
    resp = client.get("/api/admin/mailout/buyers.csv", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    fang = [r for r in rows if r["company"] == "Diamondback Energy"]
    assert len(fang) == 2
    names = {r["contact_name"] for r in fang}
    assert names == {"Gwendolyn Smith", "Cody King"}
    targa = [r for r in rows if r["company"] == "Targa Resources"]
    assert len(targa) == 1
    assert targa[0]["contact_name"] == ""
    assert targa[0]["contact_email"] == ""


def test_buyers_contact_metadata_surfaces(client, admin_headers):
    _seed_buyer_targets()
    resp = client.get("/api/admin/mailout/buyers.csv", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    gwen = next(r for r in rows if r["contact_name"] == "Gwendolyn Smith")
    assert gwen["vertical"] == "US Upstream O&G"
    assert gwen["ticker"] == "FANG"
    assert gwen["hq"] == "Midland TX"
    assert "Permian" in gwen["basin"]
    assert gwen["contact_title"] == "Senior Procurement Specialist"
    assert gwen["contact_email"] == "gwendolyn.smith@diamondbackenergy.com"
    assert gwen["contact_confidence"] == "likely"


# ── Filters ───────────────────────────────────────────────────────────


def test_buyers_filter_by_vertical(client, admin_headers):
    _seed_buyer_targets()
    resp = client.get(
        "/api/admin/mailout/buyers.csv?vertical=US%20Midstream",
        headers=admin_headers,
    )
    _, rows = _parse_csv(resp.text)
    # Only the Targa row should appear
    assert all(r["vertical"] == "US Midstream" for r in rows)
    assert {r["company"] for r in rows} == {"Targa Resources"}


def test_buyers_limit_caps_rows(client, admin_headers):
    _seed_buyer_targets()
    resp = client.get("/api/admin/mailout/buyers.csv?limit=2", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    assert len(rows) <= 2


# ── Sort ──────────────────────────────────────────────────────────────


def test_buyers_default_sort_vertical_company_contact(client, admin_headers):
    """Default sort: vertical, then company, then contact_name."""
    _seed_buyer_targets()
    resp = client.get("/api/admin/mailout/buyers.csv", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    keys = [(r["vertical"], r["company"], r["contact_name"]) for r in rows]
    assert keys == sorted(keys)
