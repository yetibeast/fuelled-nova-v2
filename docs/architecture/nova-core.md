# Nova Core — Living Architecture

**This is the current truth, kept up to date as work lands** (per CLAUDE.md §8).
Design rationale and full vision: `docs/superpowers/specs/2026-05-20-nova-engine-architecture-spec.md`.

Naming (Curtis owns this): **Nova Core** = the capability APIs (the engine — math, lookups, defensible outputs). **Nova agent** = the orchestration layer (NL routing, conversation, multi-step workflows, file ingest) that calls Nova Core + LLM reasoning.

---

## The direction

Nova becomes a set of **pure, deterministic capability APIs** with the LLM pushed to the edges (intake/routing/explanation), not in the per-row hot path. Pricing is the first capability; sizing, cost estimation, lookups, and document intake follow. Any consumer — chat UI, customer app, internal admin, batch worker — calls the same capabilities the same way.

**Why:** every priced row today burns a full LLM tool-loop (~19K tokens, ~5 calls). Deterministic-first collapses per-row cost ~10× and removes the rate-limit footprint. The LLM stays for what it's good at (messy intake, narrative, routing).

---

## Current state (built vs planned)

### Layer map (today)

```
  Consumers:   Chat UI (Next.js)   Batch upload   (future: customer app)
                     │                  │
                     ▼                  ▼
  Nova agent:   run_pricing() tool-loop  ──────────────  ← LLM orchestration (service.py)
                     │  (LLM decides which tools to call)
                     ▼
  Capabilities: tools.py  →  rcn_engine/ + equipment/   ← deterministic today, but
                              + DB (listings, refs)        reached ONLY via the LLM loop
```

### Built
- **Deterministic pricing engine** — `backend/app/pricing_v2/rcn_engine/` (calculator, condition, confidence, depreciation, market_factors, rcn_tables) and `equipment/` (identity resolution, compound parsing, aliases, promoter, escalation, audit). Pure Python, no LLM. ✅
- **Capability tools** — `pricing_v2/tools.py`: `search_comparables`, `get_category_stats`, `lookup_rcn`, `calculate_fmv`, `check_equipment_risks`. These wrap the engine + DB for the LLM. ✅
- **Agent loop** — `pricing_v2/service.py::run_pricing`: Claude Sonnet 4.6 tool-use loop; system prompt in `prompts.py`. ✅
- **Batch capability path** — `api/batch.py`: file → extract → **human review** → price (parse/price split, 2026-05-29). ✅
- **Reference data** — Postgres `listings` (+ country tagging), RCN/depreciation/market reference tables, `seeds/` xlsx loaded at startup. ✅

### Planned (not yet built)
- **Pricing as a direct deterministic API** — callable without the LLM loop for the bulk/structured path (the core of the Nova Core shift). The engine exists; what's missing is a clean deterministic entrypoint that consumers call directly, with the LLM reserved for messy/ambiguous inputs.
- **Capability boundary formalized** — stable input/output contracts per capability, independent of the agent.
- **Additional capabilities** — sizing, cost estimation, document intake as first-class APIs.
- **Bulk runner on the deterministic path** (+ Batches API for any residual LLM calls).

---

## Decision log

Append-only. One short entry per significant architectural / cross-cutting decision: what we chose, what we rejected, the tradeoff.

### 2026-05-20 — Adopt deterministic-first capability APIs + thin agent
Nova Core = pure capability APIs; Nova agent = orchestration. LLM moves to the edges. **Rejected:** keeping the LLM tool-loop as the only pricing path (every row an LLM call — ~$5–15K/mo at batch scale, and a hard rate-limit ceiling). **Tradeoff:** larger up-front refactor, but ~10× lower per-row cost and a reusable engine across consumers. Full design in the 2026-05-20 spec.

### 2026-05-29 — Batch pricing splits parse → review → price
Extraction is a capability; the review checkpoint is an agent/UX concern. A human approves extracted items before any pricing runs, and empty/$0 valuations are reported as failures, not "priced." **Rejected:** auto-pricing whatever the parser emitted (it silently priced garbage at $0). **Tradeoff:** one extra click; eliminates silent-garbage runs and false "complete."

### 2026-05-31 — Prompt caching on the pricing system prompt (interim, pre-Nova-Core)
`cache_control: {ephemeral}` on the ~15K-token system block (caches tools + system together; hits across the tool loop and across requests). Cuts the rate-limited input per call from ~19K to a few hundred tokens (~5–6× Tier-2 throughput headroom) and ~90% off the prefix on cost. Cost accounting made cache-aware (`_compute_cost`; new `cache_read_tokens`/`cache_creation_tokens` log fields). **Rejected:** paying ~$400 for Anthropic Tier 3 (caching gives comparable headroom and *lowers* spend). **Tradeoff:** none functional — interim runway until Nova Core removes the per-row LLM call entirely.

### 2026-05-31 — Slow LLM artifacts call the backend directly, bypassing the Next.js proxy
The multi-item portfolio report (~90s Claude pass) and interactive pricing call the backend directly via `getBackendUrl()` rather than the Next.js rewrite proxy, which times out on long requests. **Tradeoff:** requires prod CORS to allow the frontend origin (it does). Pattern to reuse for any future >~30s capability call.
