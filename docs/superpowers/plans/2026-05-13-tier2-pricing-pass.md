# Tier 2 Pricing Pass — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development` if subagents are available) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **TDD red/green/refactor on every task — no exceptions.**

**Goal:** Build the Tier 2 pricing pass for `fuelled-nova-v2` — four new family rulesets (heaters, treaters, knockouts with 3-way disambiguation, dehydrators) plus per-row transparency in the workbook output (methodology + 5-factor confidence breakdown + low/mid/high price targets + reasoning trail + factor weights). Output ~348 listings priced with the same workbook shape Mark + Curt locked in on 2026-05-13.

**Architecture:** Workbook-shape-first vertical slice. Chunk 1 locks the per-row column spec via a single spec test that every family must satisfy. Chunk 2 builds dehydrator end-to-end (the family with zero existing scaffolding — forces honest design). Chunks 3-5 fan out knockouts, heaters, treaters against the same locked spec. Chunk 6 wires the batch runner and produces the Tier 2 workbook. **No drift into Tier 3, External Nova, the competitive agent, sold-records ingestion, Notion factor-weight migration, or UI work — those are out of scope (see below).**

**Tech Stack:** Python 3.11+ · FastAPI backend · pytest · openpyxl for workbook writing · existing `backend/app/pricing_v2/` engine (RCN tables, confidence scoring, depreciation curves).

**Anchor commitments from 2026-05-13 Mark sync** (verified via Granola `3cd3ab18-a007-4b9c-b2c5-26fd03ff971a`):
- 100% priced with confidence flags — low-confidence items publish, not held
- NovoCore = engine name (fair market value + factor weights)
- Mark to send full sold-records export (ingestion is a SEPARATE plan)
- Factor weights surfaced per row (UI surface moves to Notion + a report — out of scope here, but the engine must emit the values)
- Tier 2 families: heaters, treaters, knockouts, dehydrators
- Comp Day 1 sequence: T1+T2 join → run against marketplace comps → publish HIGH-confidence deltas (also out of scope; this plan ends at "Tier 2 workbook produced")

---

## Out of Scope (Explicit Non-Goals)

To prevent drift, the following are **not** part of this plan and must not be touched:

- **Tier 3 work** — image-based field capture, manual fallback, long-tail handling
- **External Nova** — separate instance for lead-gen / Fuelled+
- **Competitive Agent** — stale-targets, dealer enrichment, ranked outputs
- **Sold-records ingestion pipeline** — separate plan, runs once Mark's export arrives
- **Frontend / Nova UI changes** — `frontend/nova-app/` stays untouched
- **Notion methodology page** — Mark's deliverable, not engine work
- **Marketplace comps read-access integration** — comps lookups stay disabled in Tier 2 (same as Tier 1 standalone April run)
- **Comp Day 1 join / dashboard update** — happens after Tier 2 ships, not in this plan

---

## File Structure

**Create:**

- `backend/app/pricing_v2/tier2/__init__.py` — Tier 2 module marker
- `backend/app/pricing_v2/tier2/column_spec.py` — locked Tier 2 workbook column spec + schema
- `backend/app/pricing_v2/tier2/dehydrator.py` — dehydrator family ruleset (RCN, curve, factors, match terms)
- `backend/app/pricing_v2/tier2/knockout.py` — knockout family with 3-way disambiguator (FWKO / Gas KO / Flare KO / ambiguous)
- `backend/app/pricing_v2/tier2/heater.py` — heater family ruleset
- `backend/app/pricing_v2/tier2/treater.py` — treater family ruleset
- `backend/app/pricing_v2/tier2/batch.py` — Tier 2 batch runner emitting the locked column spec
- `backend/app/pricing_v2/tier2/reasoning.py` — per-row reasoning-trail builder
- `tests/pricing_v2/tier2/test_column_spec.py` — spec contract test
- `tests/pricing_v2/tier2/test_dehydrator.py`
- `tests/pricing_v2/tier2/test_knockout.py`
- `tests/pricing_v2/tier2/test_heater.py`
- `tests/pricing_v2/tier2/test_treater.py`
- `tests/pricing_v2/tier2/test_batch.py`
- `tests/pricing_v2/tier2/fixtures/` — sample listing inputs per family (one per outcome)
- `docs/superpowers/specs/2026-05-13-tier2-column-spec.md` — human-readable column-spec doc

**Modify:**

- `backend/app/pricing_v2/rcn_engine/rcn_tables.py` — extend `STATIC_BASE_RCN` and add new category mappings for the 4 families
- `backend/app/pricing_v2/rcn_engine/depreciation.py` — add `AGE_CURVES` entries for dehydrator + verify heater/treater have their own curves (not aliased)
- `backend/app/pricing_v2/tools.py:139-142` — **rename** existing `flare` fallback entry to `flare_ko` for explicit scope; this is a precondition for the knockout disambiguator
- `backend/app/pricing_v2/report.py` and/or `report_support.py` — extend workbook writer to emit the locked column spec (per-row methodology, confidence breakdown, L/M/H targets, reasoning, weights)

**Untouched (re-state for clarity):**

- `frontend/nova-app/` — UI work is out of scope
- `backend/app/pricing_v2/calibration/` — sold-records ingestion is a separate plan
- `backend/app/api/competitive.py` (and adjacent) — competitive agent work is out of scope
- `seeds/rcn_price_reference_seed_v2.xlsx` — reference DB stays as-is unless a family RCN requires a new row, in which case the change is additive only

---

## Chunk 0: Worktree + Module Scaffolding

### Task 0.1: Create the worktree

**Files:** none (operates on git state)

- [ ] **Step 1: Verify clean working tree on `main`**

Run: `git -C /Users/lynch/Documents/projects/fuelled-nova-v2 status -uno`
Expected: `nothing to commit, working tree clean` (or only `feat/dealer-contacts-enrichment` style branches present without conflicts).

- [ ] **Step 2: Create a worktree**

Use `superpowers:using-git-worktrees` skill. Worktree dir: `/Users/lynch/Documents/worktrees/fuelled-nova-v2-tier2`. Branch: `feat/tier2-pricing-pass`.

- [ ] **Step 3: Confirm pytest runs in the worktree**

Run: `cd /Users/lynch/Documents/worktrees/fuelled-nova-v2-tier2 && pytest tests/ -q --collect-only | tail -5`
Expected: pytest collects existing tests without errors.

### Task 0.2: Scaffold the Tier 2 module

**Files:**
- Create: `backend/app/pricing_v2/tier2/__init__.py`
- Create: `tests/pricing_v2/tier2/__init__.py`

- [ ] **Step 1: Create empty package files**

```python
# backend/app/pricing_v2/tier2/__init__.py
"""Tier 2 pricing pass — heaters, treaters, knockouts, dehydrators."""
```

```python
# tests/pricing_v2/tier2/__init__.py
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from backend.app.pricing_v2 import tier2; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/pricing_v2/tier2/__init__.py tests/pricing_v2/tier2/__init__.py
git commit -m "feat(tier2): scaffold tier2 module"
```

---

## Chunk 1: Lock the Column Spec (GATE: Curt signoff before Chunk 2)

> **Anti-drift purpose:** Every family in Chunks 2-5 must emit a row that satisfies the spec test created here. The spec is the contract — no per-family deviation allowed.

### Task 1.1: Write the column spec module

**Files:**
- Create: `backend/app/pricing_v2/tier2/column_spec.py`

- [ ] **Step 1: Write the spec module**

```python
# backend/app/pricing_v2/tier2/column_spec.py
"""Tier 2 workbook column spec — LOCKED 2026-05-13.

Every family ruleset must emit a row that satisfies this schema.
The spec test (tests/pricing_v2/tier2/test_column_spec.py) is the
contract — do not bypass it.

Source: Mark Le Dain x Curt 2026-05-13 sync (Granola
3cd3ab18-a007-4b9c-b2c5-26fd03ff971a). Per-row transparency was
new requirement: methodology, confidence breakdown, L/M/H targets,
reasoning trail, factor weights — beyond the Tier 1 portfolio bands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ── REQUIRED COLUMNS (in order, frozen) ────────────────────────────
TIER2_COLUMNS: tuple[str, ...] = (
    # Identity
    "Listing ID",
    "Record ID",
    "Listing Name",
    "Category",
    "Family",            # NEW: which Tier 2 family (heater/treater/knockout-fwko/
                         #      knockout-gas/knockout-flare/dehydrator/ambiguous)
    "Supplier Company",
    "URL",
    # Inputs
    "Size / Basis",
    "Age Assumed (yr)",
    "Condition Assumed",
    # RCN
    "RCN New Low",
    "RCN New Mid",
    "RCN New High",
    "RCN Source",        # gold_table | fallback | sold_anchor
    # Methodology
    "Methodology Path",  # NEW: e.g. "dehydrator/teg/BTU-scaled"
    "Depreciation Curve",
    "Factor Service",
    "Factor Age",
    "Factor Condition",
    "Factor Combined",
    # Factor weights (constants — emitted per row for transparency)
    "Weight RCN Source",
    "Weight Data Volume",
    "Weight Freshness",
    "Weight Specificity",
    "Weight Variance",
    # Confidence breakdown (5 component scores + composite)
    "Conf RCN Source",
    "Conf Data Volume",
    "Conf Freshness",
    "Conf Specificity",
    "Conf Variance",
    "Conf Composite",
    "Conf Class",        # automated | hitl_review | manual
    # Price targets
    "Price Target LOW",  # risk-adjusted floor (walk-away)
    "Price Target MID",  # FMV center
    "Price Target HIGH", # ceiling (asking-anchor)
    # Comparables
    "Comparables Count",
    "Comparables Summary",
    # Reasoning trail
    "Reasoning Trail",   # NEW: multi-line factor-by-factor explanation
    "Review Flag",
    "Review Reason",     # NEW: non-empty when Review Flag is True
    "Hold From Publication",
    # Provenance
    "Sold Anchor Used",  # NEW: bool — true when sold-records corpus contributed
    "Sold Anchor Count", # NEW: number of sold records that influenced this row
)


# ── COLUMN TYPE CONTRACTS ──────────────────────────────────────────
COLUMN_TYPES: dict[str, type] = {
    "Listing ID": str, "Record ID": str, "Listing Name": str, "Category": str,
    "Family": str, "Supplier Company": str, "URL": str,
    "Size / Basis": str, "Age Assumed (yr)": (int, float), "Condition Assumed": str,
    "RCN New Low": (int, float), "RCN New Mid": (int, float), "RCN New High": (int, float),
    "RCN Source": str, "Methodology Path": str, "Depreciation Curve": str,
    "Factor Service": float, "Factor Age": float, "Factor Condition": float,
    "Factor Combined": float,
    "Weight RCN Source": float, "Weight Data Volume": float, "Weight Freshness": float,
    "Weight Specificity": float, "Weight Variance": float,
    "Conf RCN Source": float, "Conf Data Volume": float, "Conf Freshness": float,
    "Conf Specificity": float, "Conf Variance": float, "Conf Composite": float,
    "Conf Class": str,
    "Price Target LOW": (int, float), "Price Target MID": (int, float),
    "Price Target HIGH": (int, float),
    "Comparables Count": int, "Comparables Summary": str,
    "Reasoning Trail": str, "Review Flag": bool, "Review Reason": str,
    "Hold From Publication": bool,
    "Sold Anchor Used": bool, "Sold Anchor Count": int,
}


# ── VALID FAMILY VALUES ────────────────────────────────────────────
VALID_FAMILIES: frozenset[str] = frozenset({
    "dehydrator",
    "heater",
    "treater",
    "knockout-fwko",
    "knockout-gas",
    "knockout-flare",
    "knockout-ambiguous",  # disambiguation failed — flagged for review
})


VALID_CONF_CLASSES: frozenset[str] = frozenset({"automated", "hitl_review", "manual"})


@dataclass(frozen=True)
class Tier2Row:
    """A priced Tier 2 row. Use `.to_dict()` to render to workbook output."""
    data: dict

    def to_dict(self) -> dict:
        """Return ordered dict matching TIER2_COLUMNS order exactly."""
        return {col: self.data.get(col) for col in TIER2_COLUMNS}
```

- [ ] **Step 2: Run import smoke test**

Run: `python -c "from backend.app.pricing_v2.tier2.column_spec import TIER2_COLUMNS, VALID_FAMILIES; print(len(TIER2_COLUMNS), len(VALID_FAMILIES))"`
Expected: `38 7` (or whatever the final count is — record it; this becomes the gate).

### Task 1.2: Write the spec contract test

**Files:**
- Create: `tests/pricing_v2/tier2/test_column_spec.py`

- [ ] **Step 1: Write the spec test (it has no implementation to test yet — that's fine)**

```python
# tests/pricing_v2/tier2/test_column_spec.py
"""Spec contract for Tier 2 row output.

Every family in Chunks 2-5 must produce rows that pass this test.
Adding a column? Add it to TIER2_COLUMNS in column_spec.py first,
then update this test. Never the other way around.
"""
from __future__ import annotations

import pytest

from backend.app.pricing_v2.tier2.column_spec import (
    COLUMN_TYPES,
    TIER2_COLUMNS,
    Tier2Row,
    VALID_CONF_CLASSES,
    VALID_FAMILIES,
)


def assert_row_satisfies_spec(row: Tier2Row) -> None:
    """Universal Tier 2 row validator. Called by every family test."""
    out = row.to_dict()

    # 1. All required columns present, in order
    assert tuple(out.keys()) == TIER2_COLUMNS, (
        f"Row keys do not match TIER2_COLUMNS order. "
        f"Got: {tuple(out.keys())}"
    )

    # 2. Type contract honored
    for col, expected in COLUMN_TYPES.items():
        val = out[col]
        if val is None:
            # None only allowed where Type is str (interpret as empty cell)
            assert expected is str, f"Column '{col}' is None but type is {expected}"
            continue
        if isinstance(expected, tuple):
            assert isinstance(val, expected), (
                f"Column '{col}' = {val!r} (type {type(val).__name__}), "
                f"expected one of {expected}"
            )
        else:
            assert isinstance(val, expected), (
                f"Column '{col}' = {val!r} (type {type(val).__name__}), "
                f"expected {expected.__name__}"
            )

    # 3. Family is a valid value
    assert out["Family"] in VALID_FAMILIES, (
        f"Family '{out['Family']}' not in VALID_FAMILIES"
    )

    # 4. Confidence class is valid
    assert out["Conf Class"] in VALID_CONF_CLASSES

    # 5. Price target ordering
    assert (
        out["Price Target LOW"]
        <= out["Price Target MID"]
        <= out["Price Target HIGH"]
    ), "Price targets out of order"

    # 6. RCN ordering
    assert out["RCN New Low"] <= out["RCN New Mid"] <= out["RCN New High"]

    # 7. Factor weights sum to 1.0 (these are constants — invariant)
    weight_sum = (
        out["Weight RCN Source"]
        + out["Weight Data Volume"]
        + out["Weight Freshness"]
        + out["Weight Specificity"]
        + out["Weight Variance"]
    )
    assert abs(weight_sum - 1.0) < 1e-6, f"Factor weights sum to {weight_sum}, not 1.0"

    # 8. Review flag must come with a reason when True
    if out["Review Flag"]:
        assert out["Review Reason"], "Review Flag True requires non-empty Review Reason"

    # 9. Sold anchor accounting consistent
    if out["Sold Anchor Used"]:
        assert out["Sold Anchor Count"] >= 1
    else:
        assert out["Sold Anchor Count"] == 0


def test_spec_columns_unique():
    """Sanity: no duplicate column names."""
    assert len(TIER2_COLUMNS) == len(set(TIER2_COLUMNS))


def test_spec_column_types_covers_all_columns():
    """Every column has a declared type."""
    missing = set(TIER2_COLUMNS) - set(COLUMN_TYPES.keys())
    assert not missing, f"COLUMN_TYPES missing entries for: {missing}"


def test_valid_families_includes_all_chunks():
    """Every family expected from Chunks 2-5 is declared."""
    required = {
        "dehydrator", "heater", "treater",
        "knockout-fwko", "knockout-gas", "knockout-flare",
        "knockout-ambiguous",
    }
    assert required.issubset(VALID_FAMILIES)


def test_minimal_synthetic_row_passes_validator():
    """The validator function itself runs cleanly on a hand-built valid row."""
    row = Tier2Row(data={
        # Identity
        "Listing ID": "L1", "Record ID": "R1", "Listing Name": "Test", "Category": "dehydrator",
        "Family": "dehydrator", "Supplier Company": "Test Co", "URL": "https://x",
        # Inputs
        "Size / Basis": "5 MMSCFD", "Age Assumed (yr)": 10, "Condition Assumed": "B",
        # RCN
        "RCN New Low": 100_000, "RCN New Mid": 150_000, "RCN New High": 200_000,
        "RCN Source": "fallback",
        # Methodology
        "Methodology Path": "dehydrator/teg/BTU-scaled",
        "Depreciation Curve": "dehydrator",
        "Factor Service": 1.0, "Factor Age": 0.6, "Factor Condition": 0.85,
        "Factor Combined": 0.51,
        # Weights
        "Weight RCN Source": 0.25, "Weight Data Volume": 0.25,
        "Weight Freshness": 0.10, "Weight Specificity": 0.25, "Weight Variance": 0.15,
        # Confidence
        "Conf RCN Source": 0.5, "Conf Data Volume": 0.4,
        "Conf Freshness": 0.6, "Conf Specificity": 0.7, "Conf Variance": 0.3,
        "Conf Composite": 0.5, "Conf Class": "hitl_review",
        # Price targets
        "Price Target LOW": 60_000, "Price Target MID": 76_500, "Price Target HIGH": 102_000,
        # Comps
        "Comparables Count": 0, "Comparables Summary": "no comps (standalone run)",
        # Reasoning
        "Reasoning Trail": "RCN: fallback dehydrator $100-200k.\nAge: 10yr -> 0.6.\nCondition: B -> 0.85.\nCombined: 0.51. FMV mid: $76.5k.",
        "Review Flag": False, "Review Reason": "",
        "Hold From Publication": False,
        # Provenance
        "Sold Anchor Used": False, "Sold Anchor Count": 0,
    })
    assert_row_satisfies_spec(row)
```

- [ ] **Step 2: Run the spec test — expect 4 PASSES, 0 fails**

Run: `pytest tests/pricing_v2/tier2/test_column_spec.py -v`
Expected: 4 tests pass. If any fail, fix `column_spec.py` first.

- [ ] **Step 3: Commit**

```bash
git add backend/app/pricing_v2/tier2/column_spec.py tests/pricing_v2/tier2/test_column_spec.py
git commit -m "feat(tier2): lock column spec + contract test (38 cols, 7 family values)"
```

### Task 1.3: Write the human-readable spec doc

**Files:**
- Create: `docs/superpowers/specs/2026-05-13-tier2-column-spec.md`

- [ ] **Step 1: Write the spec doc**

Doc must include: section per column group (Identity, Inputs, RCN, Methodology, Weights, Confidence, Price Targets, Comparables, Reasoning, Provenance), one paragraph per column explaining what it captures and how it's derived. Reference `column_spec.py` as canonical.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-05-13-tier2-column-spec.md
git commit -m "docs(tier2): human-readable column spec"
```

### Task 1.4: Curt review gate

- [ ] **Step 1: Surface for review**

Present `column_spec.py` and `docs/superpowers/specs/2026-05-13-tier2-column-spec.md` to Curt. Ask: "Any columns to add, remove, or rename? Anything that should be split (e.g. should Methodology Path also have a Methodology Family / Variant pair)?"

- [ ] **Step 2: Apply any feedback and re-commit**

Any changes go through column_spec.py first, then the doc, then re-run the spec test. Do not move to Chunk 2 until Curt signs off.

---

## Chunk 2: Dehydrator Vertical Slice (GATE: Curt review on sample row)

> **Anti-drift purpose:** Dehydrator is the family with zero scaffolding in the engine today. Building it end-to-end forces every part of the per-row transparency design to be real, not theoretical. Every other family follows the pattern this chunk establishes.

### Task 2.1: Dehydrator RCN entries

**Files:**
- Modify: `backend/app/pricing_v2/rcn_engine/rcn_tables.py` — add dehydrator entries to `STATIC_BASE_RCN`
- Modify: `backend/app/pricing_v2/tools.py` — add dehydrator to `_FALLBACK_RCN`
- Create: `tests/pricing_v2/tier2/test_dehydrator.py`

- [ ] **Step 1: Write failing test — dehydrator RCN lookup**

```python
# tests/pricing_v2/tier2/test_dehydrator.py
import pytest

from backend.app.pricing_v2.tier2.dehydrator import (
    DEHYDRATOR_MATCH_TERMS,
    classify_dehydrator,
    price_dehydrator,
)
from tests.pricing_v2.tier2.test_column_spec import assert_row_satisfies_spec


def test_classify_dehydrator_teg():
    assert classify_dehydrator("TEG dehydrator 5 MMSCFD") == "teg"
    assert classify_dehydrator("triethylene glycol unit 10 MMSCFD") == "teg"


def test_classify_dehydrator_mole_sieve():
    assert classify_dehydrator("mole sieve dehydrator skid") == "mole_sieve"


def test_classify_dehydrator_generic():
    assert classify_dehydrator("dehydrator package") == "generic"
```

- [ ] **Step 2: Run test — verify it fails on import**

Run: `pytest tests/pricing_v2/tier2/test_dehydrator.py -v`
Expected: `ImportError: cannot import name 'classify_dehydrator'`

- [ ] **Step 3: Write minimal `dehydrator.py` to pass classification tests**

```python
# backend/app/pricing_v2/tier2/dehydrator.py
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
```

- [ ] **Step 4: Run classification tests — verify PASS**

Run: `pytest tests/pricing_v2/tier2/test_dehydrator.py::test_classify_dehydrator_teg tests/pricing_v2/tier2/test_dehydrator.py::test_classify_dehydrator_mole_sieve tests/pricing_v2/tier2/test_dehydrator.py::test_classify_dehydrator_generic -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/pricing_v2/tier2/dehydrator.py tests/pricing_v2/tier2/test_dehydrator.py
git commit -m "feat(tier2/dehydrator): variant classification (TEG/mole-sieve/generic)"
```

### Task 2.2: Dehydrator RCN scaling

**Files:**
- Modify: `backend/app/pricing_v2/tier2/dehydrator.py`
- Modify: `tests/pricing_v2/tier2/test_dehydrator.py`

- [ ] **Step 1: Add failing test for RCN scaling by throughput**

```python
def test_dehydrator_rcn_small():
    rcn = dehydrator_rcn(variant="teg", mmscfd=2.0)
    assert rcn.low == 50_000 and rcn.mid == 100_000 and rcn.high == 150_000

def test_dehydrator_rcn_medium():
    rcn = dehydrator_rcn(variant="teg", mmscfd=15.0)
    assert rcn.low == 150_000 and rcn.mid == 275_000 and rcn.high == 400_000

def test_dehydrator_rcn_large():
    rcn = dehydrator_rcn(variant="teg", mmscfd=50.0)
    assert rcn.low == 400_000 and rcn.mid == 700_000 and rcn.high == 1_000_000

def test_dehydrator_rcn_mole_sieve_premium():
    teg = dehydrator_rcn(variant="teg", mmscfd=10.0)
    mole = dehydrator_rcn(variant="mole_sieve", mmscfd=10.0)
    assert mole.mid > teg.mid  # mole sieve carries premium
```

> **NOTE — RCN bracket values are placeholders.** Before this chunk closes, Curt confirms numbers against `seeds/rcn_price_reference_seed_v2.xlsx` and/or his domain knowledge. Replace placeholders in one commit; do not let placeholder values reach production output.

- [ ] **Step 2: Run failing tests**
- [ ] **Step 3: Implement `dehydrator_rcn()` with bracket logic + `RcnBand` dataclass**
- [ ] **Step 4: Run tests — PASS**
- [ ] **Step 5: Commit:** `feat(tier2/dehydrator): RCN scaling by MMSCFD throughput`

### Task 2.3: Dehydrator depreciation curve

**Files:**
- Modify: `backend/app/pricing_v2/rcn_engine/depreciation.py` — add `AGE_CURVES["dehydrator"]`
- Modify: `tests/pricing_v2/tier2/test_dehydrator.py`

- [ ] **Step 1: Read existing depreciation curves**

Run: `grep -n "AGE_CURVES" backend/app/pricing_v2/rcn_engine/depreciation.py`
Confirm the structure (likely `dict[str, list[tuple[int, float]]]`).

- [ ] **Step 2: Write failing test**

```python
def test_dehydrator_age_factor_curve():
    from backend.app.pricing_v2.rcn_engine.depreciation import age_factor
    assert age_factor("dehydrator", years=0) == pytest.approx(1.00, rel=0.01)
    assert age_factor("dehydrator", years=10) == pytest.approx(0.60, rel=0.05)
    assert age_factor("dehydrator", years=20) == pytest.approx(0.35, rel=0.05)
```

- [ ] **Step 3: Add dehydrator curve to `AGE_CURVES`**

Curve milestones (placeholder — confirm with Curt; production vessel similar to treater but slightly steeper early due to glycol fouling):
```python
"dehydrator": [(0, 1.00), (5, 0.78), (10, 0.60), (15, 0.45), (20, 0.35), (25, 0.28)],
```

- [ ] **Step 4: Run tests — PASS**
- [ ] **Step 5: Commit:** `feat(tier2/dehydrator): depreciation curve added to AGE_CURVES`

### Task 2.4: Dehydrator service factor & reasoning trail

**Files:**
- Modify: `backend/app/pricing_v2/tier2/dehydrator.py`
- Create: `backend/app/pricing_v2/tier2/reasoning.py`

- [ ] **Step 1: Write failing test for service factor (sweet vs sour)**

```python
def test_dehydrator_service_factor_sweet():
    assert dehydrator_service_factor("sweet gas") == 1.00

def test_dehydrator_service_factor_sour():
    assert dehydrator_service_factor("sour gas H2S 2%") == 1.15
```

- [ ] **Step 2: Write `reasoning.py` skeleton**

```python
# backend/app/pricing_v2/tier2/reasoning.py
"""Per-row reasoning-trail builder.

Captures the step-by-step pricing path so a reader can reconstruct
how a row got its number without re-running the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReasoningTrail:
    lines: list[str] = field(default_factory=list)

    def add(self, label: str, detail: str) -> None:
        self.lines.append(f"{label}: {detail}")

    def render(self) -> str:
        return "\n".join(self.lines)
```

- [ ] **Step 3: Implement service factor + reasoning use**
- [ ] **Step 4: Tests PASS**
- [ ] **Step 5: Commit:** `feat(tier2/dehydrator): service factor + reasoning-trail builder`

### Task 2.5: Dehydrator end-to-end — `price_dehydrator()` returns a spec-compliant row

**Files:**
- Modify: `backend/app/pricing_v2/tier2/dehydrator.py`
- Modify: `tests/pricing_v2/tier2/test_dehydrator.py`
- Create: `tests/pricing_v2/tier2/fixtures/dehydrator_5mmscfd_teg.json`

- [ ] **Step 1: Add fixture — a realistic dehydrator listing**

```json
{
  "listing_id": "FX-DEHY-001",
  "record_id": "fixture-dehy-1",
  "listing_name": "5 MMSCFD TEG Dehydrator Skid, 2014",
  "category": "dehydrator",
  "supplier_company": "FixtureSupplier Ltd.",
  "url": "https://example.test/fx-dehy-001",
  "description": "5 MMSCFD TEG dehydrator package, sweet gas, condition B, year 2014, includes regen package, glycol pump, reboiler.",
  "year": 2014,
  "condition": "B"
}
```

- [ ] **Step 2: Write failing end-to-end test**

```python
import json
from pathlib import Path

from backend.app.pricing_v2.tier2.dehydrator import price_dehydrator
from tests.pricing_v2.tier2.test_column_spec import assert_row_satisfies_spec


def test_dehydrator_end_to_end_5mmscfd_teg():
    fx = json.loads((Path(__file__).parent / "fixtures" / "dehydrator_5mmscfd_teg.json").read_text())
    row = price_dehydrator(fx)
    # 1. Spec contract holds
    assert_row_satisfies_spec(row)
    # 2. Family routed correctly
    assert row.to_dict()["Family"] == "dehydrator"
    # 3. Methodology path traceable
    assert "teg" in row.to_dict()["Methodology Path"].lower()
    # 4. Reasoning trail is multi-line
    assert row.to_dict()["Reasoning Trail"].count("\n") >= 3
    # 5. Sold anchor not used (standalone run)
    assert row.to_dict()["Sold Anchor Used"] is False
    # 6. Confidence is composite-classified consistently
    composite = row.to_dict()["Conf Composite"]
    cls = row.to_dict()["Conf Class"]
    if composite >= 0.75: assert cls == "automated"
    elif composite >= 0.40: assert cls == "hitl_review"
    else: assert cls == "manual"
    # 7. Price targets bracket the FMV mid
    d = row.to_dict()
    fmv_mid = d["RCN New Mid"] * d["Factor Combined"]
    assert d["Price Target LOW"] < fmv_mid < d["Price Target HIGH"]
```

- [ ] **Step 3: Implement `price_dehydrator()` end-to-end**

The function pulls together: classify variant → RCN bracket → age factor (using `rcn_engine.depreciation.age_factor`) → condition factor (using existing `rcn_engine.condition`) → service factor → combined factor → confidence breakdown (using existing `rcn_engine.confidence.calculate_confidence`) → reasoning trail → row assembly conforming to `TIER2_COLUMNS`.

Use the existing `rcn_engine` functions — don't re-implement confidence or depreciation. Family-specific logic lives in `dehydrator.py`, infrastructure stays in `rcn_engine/`.

- [ ] **Step 4: Tests PASS**
- [ ] **Step 5: Commit:** `feat(tier2/dehydrator): end-to-end pricing produces spec-compliant row`

### Task 2.6: Curt review gate on a real sample row

- [ ] **Step 1: Run the end-to-end test and dump the row**

```bash
pytest tests/pricing_v2/tier2/test_dehydrator.py::test_dehydrator_end_to_end_5mmscfd_teg -v -s
```

- [ ] **Step 2: Render the row as a single-row workbook for Curt to inspect**

Write `backend/scripts/tier2_sample_dehydrator.py` that produces `docs/May 13 2026 - pricing strategy/Tier2_Sample_Dehydrator.xlsx` using the same writer Chunks 6 will use (write a thin first-pass writer here; Chunk 6 generalizes it).

- [ ] **Step 3: Present to Curt**

Ask: "Does this row look right — methodology path, factor breakdown, reasoning trail, price targets? Anything missing for Mark to read this and understand how it got priced?"

- [ ] **Step 4: Apply feedback and re-commit if needed**

Do not start Chunk 3 until Curt signs off.

---

## Chunk 3: Knockout Disambiguation (FWKO / Gas KO / Flare KO / Ambiguous)

> **Reference:** `reference_knockout_disambiguation.md` in memory. FWKO ≠ Gas KO ≠ Flare KO; bare "knockout" is a flag, not a guess.

### Task 3.1: Rename existing `flare` fallback to `flare_ko`

**Files:**
- Modify: `backend/app/pricing_v2/tools.py:139-142`
- (Search for any tests referencing the `"flare"` fallback key and update them)

- [ ] **Step 1: grep for `"flare"` usage**

Run: `grep -rn '"flare"' backend/ tests/`

- [ ] **Step 2: Rename `flare` → `flare_ko` in fallback dict**

Keep match terms but make the key explicit:

```python
"flare_ko": {
    "match_terms": ["flare stack", "flare knockout", "flare ko"],
    "rcn_low": 15000, "rcn_mid": 25000, "rcn_high": 40000,
    "note": "Flare knockout drum + stack, size dependent.",
},
```

- [ ] **Step 3: Update any test references**
- [ ] **Step 4: Run full pytest — no regressions**
- [ ] **Step 5: Commit:** `refactor(tools): rename flare fallback to flare_ko for explicit family scope`

### Task 3.2: Knockout disambiguator function

**Files:**
- Create: `backend/app/pricing_v2/tier2/knockout.py`
- Create: `tests/pricing_v2/tier2/test_knockout.py`

- [ ] **Step 1: Write failing test for 4-way disambiguator**

```python
from backend.app.pricing_v2.tier2.knockout import disambiguate_knockout, KnockoutVariant

@pytest.mark.parametrize("text,expected", [
    # FWKO
    ("48 inch FWKO vessel", "fwko"),
    ("free water knockout 60-inch", "fwko"),
    ("free-water knock out, internals included", "fwko"),
    ("knockout vessel — oil/water separator service", "fwko"),
    # Gas KO
    ("suction scrubber 1st stage compressor", "gas"),
    ("inlet scrubber gas service", "gas"),
    ("gas knockout drum, compressor discharge", "gas"),
    # Flare KO
    ("flare stack with knockout", "flare"),
    ("flare knockout drum", "flare"),
    ("vent stack KO", "flare"),
    # Ambiguous
    ("KO drum", "ambiguous"),
    ("knockout vessel", "ambiguous"),
    ("knock out 36 inch", "ambiguous"),
])
def test_disambiguate_knockout(text, expected):
    assert disambiguate_knockout(text) == expected
```

- [ ] **Step 2: Run — fails on import**
- [ ] **Step 3: Implement `disambiguate_knockout()` per `reference_knockout_disambiguation.md` rules**
- [ ] **Step 4: Run — all 13 parameterized cases PASS**
- [ ] **Step 5: Commit:** `feat(tier2/knockout): 4-way disambiguator (FWKO/gas/flare/ambiguous)`

### Task 3.3: FWKO family ruleset (RCN + curve + factors)

Apply the same TDD pattern as dehydrator. Steps:

- [ ] **Step 1: Test RCN scaling for FWKO (by diameter, 36"-72"+)**
- [ ] **Step 2: Implement `fwko_rcn()`**
- [ ] **Step 3: Add `AGE_CURVES["fwko"]` (similar to treater curve; FWKOs are production vessels)**
- [ ] **Step 4: Test FWKO age factor**
- [ ] **Step 5: Test FWKO service factor (sweet/sour, NACE)**
- [ ] **Step 6: Commit:** `feat(tier2/knockout): FWKO family ruleset (RCN/curve/service)`

### Task 3.4: Gas Knockout family ruleset

- [ ] **Steps 1-5: Mirror Task 3.3 for gas KO. Sizing is stage/pressure-dependent rather than diameter.**
- [ ] **Commit:** `feat(tier2/knockout): gas KO family ruleset`

### Task 3.5: Knockout end-to-end + ambiguous-flag path

**Files:**
- Modify: `backend/app/pricing_v2/tier2/knockout.py`
- Modify: `tests/pricing_v2/tier2/test_knockout.py`
- Create: 4 fixture listings — one per disambiguation outcome

- [ ] **Step 1: Write failing E2E tests — one per outcome (FWKO / Gas / Flare / Ambiguous)**

```python
def test_knockout_e2e_fwko():
    fx = load_fixture("knockout_fwko_48in.json")
    row = price_knockout(fx)
    assert_row_satisfies_spec(row)
    assert row.to_dict()["Family"] == "knockout-fwko"

def test_knockout_e2e_gas():
    ...

def test_knockout_e2e_flare():
    ...

def test_knockout_e2e_ambiguous_flags_for_review():
    fx = load_fixture("knockout_ambiguous_36in.json")
    row = price_knockout(fx)
    assert_row_satisfies_spec(row)
    d = row.to_dict()
    assert d["Family"] == "knockout-ambiguous"
    assert d["Review Flag"] is True
    assert "ambiguous" in d["Review Reason"].lower()
    # Bands must be widened, not hidden:
    spread = (d["Price Target HIGH"] - d["Price Target LOW"]) / d["Price Target MID"]
    assert spread >= 0.50  # widened bands on ambiguous
```

- [ ] **Step 2: Implement `price_knockout()` dispatching to fwko/gas/flare/ambiguous paths**
- [ ] **Step 3: Run — all 4 PASS, spec test PASS for each row**
- [ ] **Step 4: Commit:** `feat(tier2/knockout): end-to-end pricing for 4 disambiguation outcomes`

---

## Chunk 4: Heater Family (Promote from Fallback)

> Heater fallback exists in `tools.py:144-148` with limited specs (0.5-1.5 MMBTU). Tier 2 promotes to real RCN table + own depreciation curve.

### Task 4.1: Heater RCN by BTU bracket

Pattern: same as dehydrator (Tasks 2.1-2.2).

- [ ] **Step 1: Failing tests for `heater_rcn(mmbtu=X)` brackets — small (≤1.5), medium (1.5-5), large (5-15), industrial (15+)**
- [ ] **Step 2-4: Implement, tests PASS**
- [ ] **Step 5: Commit:** `feat(tier2/heater): RCN scaling by MMBTU`

### Task 4.2: Heater depreciation curve

Currently aliased to treater curve. Give heaters their own — they age slower (simpler equipment, fewer wear surfaces) but coils need replacement.

- [ ] **Step 1: Failing test**
- [ ] **Step 2: Add `AGE_CURVES["heater"]` — milestones: (0, 1.00), (5, 0.82), (10, 0.65), (15, 0.50), (20, 0.40), (25, 0.32)**
- [ ] **Step 3: Tests PASS**
- [ ] **Step 4: Commit:** `feat(tier2/heater): dedicated depreciation curve (no longer aliased to treater)`

### Task 4.3: Heater end-to-end

- [ ] **Steps 1-5: Fixture + E2E test + implementation + spec validation + commit**
- [ ] **Commit:** `feat(tier2/heater): end-to-end pricing produces spec-compliant row`

---

## Chunk 5: Treater Family (Promote from Fallback)

Mirrors Chunk 4. Treaters currently have fallback only ($80-250k for 48-72"). Add real RCN table, own depreciation curve, firetube/internals factor.

- [ ] **Task 5.1: Treater RCN by diameter × length × firetube BTU**
- [ ] **Task 5.2: Treater depreciation curve (production vessel — similar shape to FWKO but separate curve)**
- [ ] **Task 5.3: Internals factor (firetube material, coil presence)**
- [ ] **Task 5.4: End-to-end**

---

## Chunk 6: Tier 2 Batch Runner + 348-Row Dry Run

### Task 6.1: Tier 2 input loader

**Files:**
- Create: `backend/app/pricing_v2/tier2/batch.py`
- Create: `tests/pricing_v2/tier2/test_batch.py`

- [ ] **Step 1: Failing test — load a 10-row xlsx into the engine input shape**
- [ ] **Step 2: Implement `load_tier2_input(xlsx_path) -> list[dict]`**
- [ ] **Step 3: Tests PASS**
- [ ] **Step 4: Commit:** `feat(tier2/batch): input loader from xlsx`

### Task 6.2: Family router

**Files:** `backend/app/pricing_v2/tier2/batch.py`

- [ ] **Step 1: Failing test — router classifies a list of 5 listings into the right family functions**
- [ ] **Step 2: Implement `route_listing(listing) -> family_callable` using existing match-term sets per family + the knockout disambiguator**
- [ ] **Step 3: Tests PASS — covers heater, treater, knockout (all 4 outcomes), dehydrator, AND a non-Tier-2 listing that gets rejected**
- [ ] **Step 4: Commit:** `feat(tier2/batch): family router with reject path for non-T2 listings`

### Task 6.3: Workbook writer for Tier 2 shape

**Files:**
- Modify: `backend/app/pricing_v2/report.py` and/or `report_support.py` — extend existing writer infrastructure, do NOT fork
- Modify: `backend/app/pricing_v2/tier2/batch.py`

- [ ] **Step 1: Failing test — `write_tier2_workbook(rows, output_path)` produces an xlsx with the 5 tabs (Priced Listings, Summary, Flagged for Review, Lot Sale Opportunities, Methodology), Priced Listings sheet has all TIER2_COLUMNS in order**
- [ ] **Step 2: Implement the writer**
- [ ] **Step 3: Test PASS — output xlsx opens, columns match `TIER2_COLUMNS` exactly**
- [ ] **Step 4: Commit:** `feat(tier2/batch): workbook writer emits locked column spec`

### Task 6.4: 10-row smoke test (fake portfolio mixing all 4 families)

**Files:**
- Create: `tests/pricing_v2/tier2/fixtures/sample_portfolio_10.xlsx` — 10 rows: 3 dehydrators, 2 heaters, 2 treaters, 1 FWKO, 1 gas KO, 1 ambiguous knockout

- [ ] **Step 1: Build the fixture portfolio**
- [ ] **Step 2: Failing test — `run_tier2_batch(fixture_path) -> workbook` produces a valid xlsx with 10 priced rows, all passing `assert_row_satisfies_spec`, summary tab portfolio totals computed**
- [ ] **Step 3: Implement `run_tier2_batch()` orchestrating loader → router → family pricers → writer**
- [ ] **Step 4: Tests PASS**
- [ ] **Step 5: Commit:** `feat(tier2/batch): orchestration + 10-row smoke test`

### Task 6.5: 348-row dry run (real input from Mark, when available)

**Files:**
- Create: `backend/scripts/run_tier2_batch.py` — CLI entrypoint

- [ ] **Step 1: Write CLI: `python backend/scripts/run_tier2_batch.py --input PATH --output PATH`**
- [ ] **Step 2: When the 348-row input arrives (from Mark or DB export), run the script**
- [ ] **Step 3: Spot-check 10 random rows manually — methodology path, reasoning trail, factor breakdown all make sense**
- [ ] **Step 4: Generate flagged-for-review tab; expect ambiguous knockouts + LOW confidence rows to surface there**
- [ ] **Step 5: Commit:** `feat(tier2/batch): CLI entrypoint + 348-row dry run output`

### Task 6.6: Curt + Mark review on the 348-row workbook

- [ ] **Step 1: Surface the workbook**
- [ ] **Step 2: Curt review — sample 20 rows across families, signoff on transparency surface**
- [ ] **Step 3: Mark sync — walk through 5 representative rows, confirm methodology + reasoning clarity**
- [ ] **Step 4: Iterate on any feedback, re-run, commit**

---

## Done Definition

Tier 2 is complete when:

1. ✅ All four family rulesets (heater, treater, knockout with 3-way disambiguation, dehydrator) emit spec-compliant rows
2. ✅ `tests/pricing_v2/tier2/` is green
3. ✅ A 348-row workbook has been generated with every row passing `assert_row_satisfies_spec`
4. ✅ Curt has signed off on a sample of 20 rows (manual review)
5. ✅ Mark has reviewed 5 representative rows in a sync and confirmed the per-row transparency reads cleanly
6. ✅ Open Mark loop "supplier batch confirmation Phase 1 progress" has been audited and a status reply drafted (separate from engine work but blocks closing the meeting commitments — flag for Curt)

---

## Anti-Drift Reminders (for the executing agent)

1. **Spec test is the contract.** Any family row failing `assert_row_satisfies_spec` is a bug in the family, NOT in the spec. Don't modify `column_spec.py` to make a family pass; fix the family.

2. **No scope expansion.** The Out-of-Scope list in the header is binding. If you find yourself wanting to touch competitive agent code, External Nova infra, sold-records ingestion, Notion, or the frontend — stop and surface to Curt. Do not absorb adjacent work.

3. **TDD discipline.** Every task is red → green → commit. Never write implementation before test. Never skip the failing-test step.

4. **Placeholder RCN values are flagged.** Tasks 2.2, 3.3, 3.4, 4.1, 5.1 ship with placeholder bracket values that MUST be calibrated against `seeds/rcn_price_reference_seed_v2.xlsx` and/or Curt's direct input before the final 348-row run.

5. **Sold-records boundary.** This plan accepts `Sold Anchor Used = False` for every row. When Mark's sold export arrives, a separate plan adds the anchor layer; the column spec is already prepared for it.

6. **Use existing primitives.** `rcn_engine/confidence.py` already computes the 5-factor breakdown. `rcn_engine/depreciation.py` already does curve interpolation. `rcn_engine/condition.py` already does condition scoring. Family work is composition, not reinvention.

7. **Commit frequently.** Every task ends in a commit. If you've been working for 15+ minutes without a commit, you're off-pattern.
