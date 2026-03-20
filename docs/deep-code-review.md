# Fuelled Nova V1 -- Deep Code Review

> Date: 2026-03-20
> Goal: separate real engineering from AI slop before porting anything to V2
> Scope: equipment intelligence, valuation, Claude Agent V2, RCN v2, calibration, observability, DB models, Analyst V2 frontend

## Executive Summary

There is real engineering here, but it is concentrated in a few places:

- The equipment intelligence schema is mostly solid and matches the migration well.
- The RCN v2 calculator is the strongest code in the repo: mostly pure functions, coherent domain rules, and meaningful tests around it.
- The resolver contains real domain heuristics, especially compound-description parsing.

Most of the slop is in orchestration layers:

- Claude Agent V2 adds a large prompt/tool shell around deterministic valuation, but several parts are stubbed, fake, or misleading.
- Observability is mostly disconnected from runtime behavior.
- Analyst V2 frontend has a broken backend contract, dead components, and duplicated UI logic.
- The valuation engine duplicates the same factor-chain logic already present in RCN v2 instead of building a thinner layer on top of it.

The biggest trust problem is not style. It is silent correctness drift:

- Gold-table promotion writes raw manufacturer/model into `canonical_*` fields.
- The resolver can create an `equipment_identity` with a random category UUID.
- The pricing agent reports fake listing similarity/freshness metrics.
- The frontend expects step outputs that the backend never sends.
- Core ORM models have drifted away from the migrations.

## Final Verdict Table

| Module | Verdict | Bottom line |
|---|---|---|
| Equipment Intelligence | PORT WITH CLEANUP | Keep the schema and pipeline concept, but fix integrity bugs and split the resolver. |
| Valuation Engine | REBUILD | The concepts are good; the current engine duplicates math and hides DB failures as missing data. |
| Claude Agent V2 | SKIP | Too much code for too little value, with fake metrics and incomplete features. |
| RCN v2 Calculator | PORT WITH CLEANUP | This is real engineering and worth carrying over, with some boundary cleanup. |
| Calibration | REBUILD | Useful concept, weak validation harness. Not trustworthy as an accuracy gate as written. |
| Observability | SKIP | Mostly premature optimization and disconnected instrumentation. |
| DB Models | PORT WITH CLEANUP | Equipment schema is good; the rest has real migration drift. |
| Analyst V2 Frontend | REBUILD | Broken data contract, dead UI paths, and duplicated component logic. |

## Real Engineering Worth Keeping

- `backend/app/pricing/rcn_v2/*`
  The deterministic valuation kernel is coherent and materially richer than a simple `calculate_fmv`.
- `backend/app/db/equipment_models.py`
  The 12-table schema is justified by the domain and mostly lines up with migration `014`.
- `backend/app/services/equipment/resolver.py`
  The compound-description parsing logic is real domain work, not generic scaffolding.
- Test coverage is a positive signal.
  The repo has substantial tests around equipment intelligence, valuation, RCN v2, calibration, and the pricing agent. The tests did not catch every defect below, but they are more than performative.

## Cross-Cutting Assessment

### Unnecessary abstraction

- This codebase is not dominated by inheritance. Over-inheritance is not the main problem.
- The recurring smell is DTO proliferation and orchestration wrappers:
  - `backend/app/services/equipment/valuation_models.py`
  - `backend/app/services/equipment/pricing_agent_models.py`
  - `backend/app/db/user_model.py`
  - `frontend/components/analyst-v2/V2ChatPanel.tsx`
- `backend/app/pricing/valuation_service.py` is the worst example of “enterprise patterns on a simple problem”: a callback soup with many `Callable[...]` aliases and dependency-injection ceremony on top of straightforward pricing flow.

### Functions over 50 lines

- `backend/app/services/equipment/resolver.py` is a god file at 813 lines.
- `backend/app/services/equipment/valuation_engine.py:38-232` is one long orchestration function.
- `backend/app/services/equipment/pricing_agent_v2.py:126-257` is a 132-line tool loop.
- `backend/app/services/equipment/pricing_agent_tools.py:45-209` and `:215-309` both mix query logic, ranking, and response shaping in one place.
- `frontend/components/analyst-v2/V2AssistantMessage.tsx:83-258` and `ValuationCard.tsx:112-251` each do too much in a single component.

### Silent error handling

This is a real quality problem.

- `backend/app/services/equipment/valuation_queries.py:80-82`, `125-127`, `160-162`, `189-191`, `211-213`, `241-243`
  DB errors are logged and converted into `[]`, `None`, or `False`. The engine cannot distinguish “no gold data” from “the query path is broken”.
- `backend/app/services/equipment/pricing_agent_tools.py:207-209`, `304-309`
  Identity and market lookup failures become empty results, which makes the agent look data-poor instead of broken.
- `backend/app/services/equipment/calibration_harness.py:118-128`
  Engine failures become warnings in the report, which is okay for an eval harness, but means this is not a strong validation gate.
- `backend/app/observability/cost_tracker.py:95-100`
  Observability failures become `0.0` spend, which is operationally misleading.

### Logging quality

- Some modules declare logging and never use it:
  - `backend/app/services/equipment/resolver.py:35`
  - `backend/app/services/equipment/promoter.py:39`
- Some logs are meaningful:
  - API failure logging in `pricing_agent_v2.py:271-279`
  - suppression warning in `valuation_math.py:141-145`
- Observability logging is often just noise around no-op behavior.

### Dependency check

- Python imports in the reviewed backend target directories are mostly clean.
  I ran `pyflakes` on `backend/app/services/equipment`, `backend/app/pricing/rcn_v2`, `backend/app/observability`, and `backend/app/db` and it did not flag unused Python imports there.
- Third-party dependencies that look replaceable or removable:
  - `pybreaker` in `backend/app/observability/circuit_breaker.py` because the breakers are not actually wrapped around live calls.
  - Some internal Pydantic DTOs in `valuation_models.py` and `pricing_agent_models.py`; many could be plain dataclasses or typed dicts.
  - `pandas` in `backend/app/pricing/service.py` is probably overkill for what is mostly filtering, outlier removal, and summary stats.
- I did not find a hard circular import in the reviewed keep paths.
  The bigger issue is import gymnastics:
  - `backend/app/db/user_model.py` is just a re-export wrapper.
  - `backend/app/services/equipment/valuation_math.py:23-29` imports private helpers from `app.pricing.rcn_v2.calculator`.

## Module 1: Equipment Intelligence

### Files reviewed

- `backend/app/services/equipment/escalation.py`
- `backend/app/services/equipment/promoter.py`
- `backend/app/services/equipment/resolver.py`

### Architecture

The pipeline idea is clean:

1. resolve category
2. normalize manufacturer/model
3. parse compound descriptions
4. map to valuation family
5. upsert equipment identity
6. promote staged evidence into gold tables

This is mostly procedural code, which is the right shape for the problem. The issue is not over-engineering. The issue is that a few shortcuts break the contract the module is supposed to enforce.

### What is real

- `resolver.py` has genuine domain heuristics.
  `parse_compound_description()` in `resolver.py:364-449` is doing real equipment parsing work.
- `promoter.py` is structurally simple.
  It promotes into three gold targets without unnecessary factories or class hierarchies.
- `escalation.py` is small and focused.

### Findings

- Critical: `backend/app/services/equipment/resolver.py:698`
  `category_id=resolved.canonical_category_id or uuid.uuid4()` can create an `equipment_identity` with a random foreign key. That is a hard data-integrity bug.
- Critical: `backend/app/services/equipment/promoter.py:221`
  `_promote_to_depreciation()` falls back to `evidence.source_id` for `category_id`. That is the wrong entity type entirely.
- High: `backend/app/services/equipment/promoter.py:135-136`, `179-180`, `223-224`
  Gold rows write `raw_manufacturer` and `raw_model` into `canonical_manufacturer` and `canonical_model`. That defeats the resolver.
- Medium: `backend/app/services/equipment/resolver.py`
  One file mixes parsing, alias resolution, family lookup, identity persistence, and audit writing. The logic is not over-abstracted, but it is under-separated.
- Medium: duplicate alias/frame logic in `resolver.py`
  The alias lookup pattern is repeated across manufacturer, model, compound parse, and frame extraction. `_lookup_alias()` and `_extract_frame()` should exist.
- Low: `backend/app/services/equipment/promoter.py:36`
  `date_to_period_label` is imported and unused.
- Low: FX normalization is duplicated across the repo:
  - `backend/app/services/equipment/escalation.py:17-21`
  - `backend/scripts/import_evidence_workbook.py:83-86`
  - `backend/app/pricing/rcn_v2/market_factors.py:116-121`

### Simplicity assessment

The resolver/promoter pipeline is not fundamentally over-engineered. It is simpler than it looks. The better version is:

- pure parsing helpers
- explicit DB lookup helpers
- one persistence function per table
- no random FK fallbacks
- gold rows always populated from resolved canonical fields

### Final verdict

**PORT WITH CLEANUP**

### Cleanup required before porting

- Fix the FK bugs in `resolver.py:698` and `promoter.py:221`.
- Populate gold `canonical_*` columns from resolved fields, not raw evidence.
- Split `resolver.py` into:
  - pure parsing
  - alias/category/family lookup
  - identity persistence
  - audit writing
- Centralize FX constants.
- Add tests that fail on category-FK corruption and raw-to-canonical leakage.

## Module 2: Valuation Engine

### Files reviewed

- `backend/app/services/equipment/valuation_models.py`
- `backend/app/services/equipment/valuation_math.py`
- `backend/app/services/equipment/valuation_queries.py`
- `backend/app/services/equipment/valuation_engine.py`
- Comparison points:
  - `backend/app/pricing/valuation.py`
  - `backend/app/pricing/service.py`
  - `backend/app/pricing/valuation_service.py`

### Architecture

The idea is reasonable:

- query gold data
- choose a base RCN
- apply family scaling
- run depreciation/market adjustments
- reconcile against gold market observations
- score confidence

The implementation is heavier than it needs to be.

### What is real

- `valuation_math.py` has real business logic.
  The diversity gate, scaling hooks, reconciliation, and depreciation validation are all conceptually useful.
- `valuation_queries.py` is a clean separation point in theory.

### Findings

- High: `backend/app/services/equipment/valuation_math.py:23-29`
  It imports private helpers `_compute_base_rcn` and `_normalize_category` from `app.pricing.rcn_v2.calculator`. That is a brittle cross-module dependency.
- High: duplicate factor-chain logic
  - `backend/app/services/equipment/valuation_math.py:200-256`
  - `backend/app/pricing/valuation.py:63-103`
  - `backend/app/pricing/rcn_v2/calculator.py:361-467`
  The repo now has multiple places that effectively compute FMV from RCN using the same underlying factors.
- High: `backend/app/services/equipment/valuation_queries.py:80-82`, `125-127`, `160-162`, `189-191`, `211-213`, `241-243`
  DB failures are swallowed and presented as “no data”. That makes fallback behavior look legitimate when it may actually be masking an outage.
- Medium: `backend/app/services/equipment/valuation_engine.py:38-232`
  `valuate()` is one long orchestration function. It is readable, but it is still a god function.
- Medium: internal DTO bloat
  - `GoldRCNRef`
  - `GoldMarketRef`
  - `GoldDepreciationObs`
  - `FamilyParams`
  These are lightweight projections used in one path. Plain dataclasses or rows would likely do.
- Medium: `backend/app/pricing/service.py:63-229`
  `PricingService` is a class that only wraps a session and procedural helpers. It should probably be module functions or one smaller service function.
- Medium: `backend/app/pricing/valuation_service.py`
  This is generic callback-heavy orchestration, not a clean valuation module. It looks like generated dependency-indirection more than deliberate design.

### Does it do the same thing as V2 `calculate_fmv` with more ceremony?

Mostly yes.

What it genuinely adds beyond a simple `calculate_fmv`:

- gold-table base RCN selection
- diversity gating
- valuation-family scaling
- reconciliation against gold FMV observations
- depreciation-observation validation

What it does not need:

- duplicated factor-chain math
- internal DTO sprawl
- silent query fallbacks

### Final verdict

**REBUILD**

### Rebuild target

Keep the concepts, not the structure:

- one small valuation service
- explicit query helpers that raise on failure
- one source of truth for the factor chain: RCN v2
- thin post-processing for gold reconciliation and confidence adjustments

## Module 3: Claude Agent V2

### Files reviewed

- `backend/app/services/equipment/pricing_agent_models.py`
- `backend/app/services/equipment/pricing_agent_tools.py`
- `backend/app/services/equipment/pricing_agent_executor.py`
- `backend/app/services/equipment/pricing_agent_v2.py`
- `backend/app/api/pricing_v2.py`

### Architecture

This is a large prompt/tool loop wrapped around deterministic valuation.

Compared to a clean 136-line V2 service, this module is doing the same job with much more surface area:

- request model
- tool schemas
- executor
- tool functions
- Anthropic loop
- parser
- step tracking
- data-source tracking

The extra code would be defensible if it delivered better truthfulness. It does not.

### Findings

- Critical: fake listing quality metrics in `backend/app/services/equipment/pricing_agent_tools.py:287-289`
  - `best_similarity = 1.0 if matches else 0.0`
  - `oldest_match_years = current_year - oldest_year`
  This is not similarity or freshness. It is fake signal.
- Critical: external search is defined but not implemented.
  `backend/app/services/equipment/pricing_agent_executor.py:286-299` returns a stubbed `WebSearchResult` with `results=[]` and `reason="Web search not yet implemented. Use internal data."`
- High: conversation continuity is broken.
  - request model includes `conversation_id` in `pricing_agent_models.py:19-23`
  - API drops it in `backend/app/api/pricing_v2.py:45-49`
  - agent creates a brand new UUID in `pricing_agent_v2.py:140`
- High: steps store tool input, not tool output.
  `backend/app/services/equipment/pricing_agent_v2.py:227-231`
  The frontend cannot reconstruct comps or evidence from this.
- Medium: more DTO bloat than value.
  `pricing_agent_models.py` defines several small Pydantic models for one narrow call path.
- Medium: mutable default list style in Pydantic models.
  - `steps: list[AgentStep] = []`
  - `data_sources: list[DataSourceUsed] = []`
- Medium: `_track_data_source()` takes `external_search_used` and `external_search_reason` parameters but does not use them.
  `pricing_agent_v2.py:282-316`

### Comparison to clean V2 service style

This module is not “more capable”. It is “more layered”.

The only irreplaceable thing here is the idea of returning:

- a valuation result
- a narrative
- structured follow-up questions

The current implementation adds too many failure modes to justify porting.

### Final verdict

**SKIP**

### Codex Next Steps

- Do not port any of Claude Agent V2 code into V2.
- Freeze this module as reference only so you can steal response ideas, not implementation.
- Build the V2 pricing path as a deterministic service:
  - normalize request
  - resolve identity
  - run RCN v2
  - apply gold-table reconciliation
  - return one structured response object
- If you want narrative text in V2, add it after the deterministic valuation result exists. Do not put an LLM in the control loop.
- Rebuild the frontend against the real V2 response contract, not against agent steps.
- Revisit tool-use / multi-step agent behavior only after the clean deterministic path is stable, testable, and trusted by analysts.

## Module 4: RCN v2 Calculator

### Files reviewed

- `backend/app/pricing/rcn_v2/calculator.py`
- `backend/app/pricing/rcn_v2/condition.py`
- `backend/app/pricing/rcn_v2/confidence.py`
- `backend/app/pricing/rcn_v2/depreciation.py`
- `backend/app/pricing/rcn_v2/market_factors.py`

### Architecture

This is the cleanest module in the repo.

- mostly pure functions
- explicit rule tables
- clear separation of condition, depreciation, market factors, and confidence
- the big file is big because the domain tables live there

### What it adds beyond a simple `calculate_fmv`

It is not just `calculate_fmv` with extra steps.

It adds:

- input normalization through `RCNInputSpec`
- category-specific base RCN selection
- size scaling
- drive/material/NACE/spec modifiers
- confidence breakdown
- defaulting logic for year/condition/hours gaps

### Findings

- Medium: `backend/app/pricing/rcn_v2/calculator.py:196-277`
  `RCNInputSpec` is useful, but if you port this into a smaller V2 service you may not need a full Pydantic boundary for every internal call.
- Medium: the module exposes private helpers that other code has started importing.
  That is not a calculator problem by itself, but it shows the current API boundary is leaky.
- Low: constants are hardcoded.
  That is acceptable for this stage, but porting should make it obvious which tables are policy/config and which are code.

### Math quality

I did not find obvious math theater here. The formulas are internally consistent and materially cleaner than the surrounding orchestration code.

### Final verdict

**PORT WITH CLEANUP**

### Cleanup required before porting

- Keep the pure functions and rule tables.
- Tighten the public API so callers do not import private helpers.
- Decide whether `RCNInputSpec` remains Pydantic or becomes a slimmer dataclass/typed dict at the boundary.
- Centralize shared constants like FX tables if V2 uses them elsewhere.

## Module 5: Calibration

### Files reviewed

- `backend/app/services/equipment/calibration_models.py`
- `backend/app/services/equipment/calibration_parser.py`
- `backend/app/services/equipment/calibration_harness.py`

### Architecture

The structure is fine:

- models
- parser
- harness

The weakness is not shape. It is what the harness actually validates.

### Findings

- High: `backend/app/services/equipment/calibration_harness.py:65-72`
  `map_row_to_request()` only maps make, model, category, year, hours, and location. It omits the primary size drivers the engine actually depends on: horsepower, capacity, drive type, stage configuration.
- High: because of that mapping gap, this harness is not a reliable accuracy validator. It is closer to a coarse regression smoke test.
- Medium: `evaluate_single_row()` in `calibration_harness.py:75-128` mixes mapping, engine execution, error handling, and metric computation.
- Medium: `calibration_models.py` uses several Pydantic models that are fine, but not all of them need to be models if this becomes an internal V2 tool.
- Positive: `calibration_parser.py` is small, clean, and worth salvaging.

### Is it genuinely useful?

Useful for:

- coarse benchmarking
- regression comparison between engine versions
- category-level error summaries

Not useful enough for:

- certifying valuation accuracy
- confidence calibration
- making “ship / do not ship” decisions about engine quality

### Final verdict

**REBUILD**

### Rebuild target

- keep the parser ideas
- redesign the dataset mapping around the actual engine input drivers
- make engine failures distinct from “row out of scope”
- separate row execution from aggregate reporting

## Module 6: Observability

### Files reviewed

- `backend/app/observability/alerting.py`
- `backend/app/observability/circuit_breaker.py`
- `backend/app/observability/cost_tracker.py`
- `backend/app/observability/error_tracking.py`
- `backend/app/observability/health.py`
- `backend/app/observability/tracing.py`

### Architecture

This package looks more mature than it is. A lot of it is status-page code around features that are not actually wired into runtime paths.

### Findings

- High: `backend/app/observability/circuit_breaker.py`
  The breakers exist, but repo search shows they are only read for status and ops narration. They are not actually used to wrap live LLM, scraper, or DB calls.
- High: `backend/app/observability/cost_tracker.py:17-30`
  `MODEL_COSTS` does not include the actual pricing-agent model `claude-sonnet-4-5-20250929` from `pricing_agent_v2.py:36`.
- Medium: `backend/app/observability/cost_tracker.py:52-55`, `103-112`
  `session` is accepted and then ignored.
- Medium: `backend/app/observability/health.py:65-74`
  Langfuse and GlitchTip health is just env-var presence, not actual connectivity or credential validation.
- Medium: `backend/app/observability/tracing.py:121`, `165`, `201`, `252`
  The module flushes Langfuse on every trace/span/query path.
- Medium: `backend/app/observability/tracing.py`
  There is no real parent/child trace context across agent, tool, and DB layers.
- Low: `alerting.py` is fine for a best-effort webhook helper, but it is not evidence of production-grade observability on its own.

### Production-ready or premature optimization?

Mostly premature optimization.

The only thing here with clear practical value is the idea of a light tracing decorator. The package as a whole is not worth porting.

### Final verdict

**SKIP**

## Module 7: DB Models

### Files reviewed

- `backend/app/db/base.py`
- `backend/app/db/models.py`
- `backend/app/db/equipment_models.py`
- `backend/app/db/platform_models.py`
- `backend/app/db/scrape_models.py`
- `backend/app/db/user_model.py`
- Schema cross-check against migrations:
  - `005_add_scrape_targets_llm_usage_users.py`
  - `006_widen_listing_columns.py`
  - `008_add_normalization_columns.py`
  - `011_add_api_keys_table.py`
  - `012_add_scraper_recon_and_onboarding.py`
  - `014_equipment_intelligence_foundation.py`

### Architecture

The model layer is not over-abstracted.

- `base.py` is a legitimate declarative base plus two small mixins.
- There is no inheritance tree problem.
- The biggest problem is schema drift and one wrapper file that should not exist.

### Findings

- Positive: `backend/app/db/equipment_models.py`
  This file largely matches migration `014_equipment_intelligence_foundation.py`. It is big because the schema is genuinely big.
- High: `backend/app/db/models.py:42-43`, `65`
  The ORM still says:
  - `external_id = String(100)`
  - `url = String(500)`
  - `image_url = String(500)`
  But migration `006_widen_listing_columns.py:20-22` widened them to `255`, `1000`, and `1000`.
- High: `backend/app/db/models.py:87-88`
  The model uses `index=True` for `category_normalized` and `make_normalized`, but migration `008_add_normalization_columns.py:29-38` created explicit named indexes. That is drift waiting to produce noisy autogenerate diffs.
- Medium: `backend/app/db/platform_models.py`
  It is missing migration-defined indexes from:
  - `005_add_scrape_targets_llm_usage_users.py:40`, `61`, `80`
  - `011_add_api_keys_table.py:37-39`
  - `012_add_scraper_recon_and_onboarding.py:29-32`, `69-77`
- Medium: `backend/app/db/user_model.py:1-8`
  This is a re-export wrapper to dodge duplicate declarative registration. It is not a real model file and should not survive a cleanup port.
- Low: `backend/app/db/equipment_models.py`
  Relationship loading is consistently `lazy="selectin"`. That is not wrong, but it is blanket policy rather than deliberate per-query tuning.

### Do the models match the actual database schema?

- `equipment_models.py`: mostly yes.
- `models.py` and `platform_models.py`: no, not fully.

### Final verdict

**PORT WITH CLEANUP**

### Cleanup required before porting

- Bring ORM types and indexes back in sync with migrations.
- Delete `user_model.py`.
- Keep `base.py` and the equipment schema model set.
- Decide which relationships deserve eager loading instead of using `selectin` everywhere.

## Module 8: Analyst V2 Frontend

### Files reviewed

- `frontend/app/(authenticated)/analyst-v2/page.tsx`
- `frontend/hooks/useValuationChat.ts`
- `frontend/lib/v2-types.ts`
- `frontend/components/analyst-v2/CompCard.tsx`
- `frontend/components/analyst-v2/CompsPanel.tsx`
- `frontend/components/analyst-v2/PriceDistributionChart.tsx`
- `frontend/components/analyst-v2/V2AssistantMessage.tsx`
- `frontend/components/analyst-v2/V2ChatInput.tsx`
- `frontend/components/analyst-v2/V2ChatPanel.tsx`
- `frontend/components/analyst-v2/V2ClarificationChips.tsx`
- `frontend/components/analyst-v2/V2MessageList.tsx`
- `frontend/components/analyst-v2/V2SuggestedActions.tsx`
- `frontend/components/analyst-v2/ValuationCard.tsx`
- `frontend/components/analyst-v2/ValuationSkeleton.tsx`

### Architecture

This is over-componentized in the shallow-wrapper sense and under-designed in the contract sense.

The main problem is not visual polish. The main problem is that the frontend and backend disagree about what data exists.

### Findings

- Critical: comps extraction is broken in both places.
  - `frontend/hooks/useValuationChat.ts:21-33` explicitly returns `[]` with a TODO.
  - `frontend/app/(authenticated)/analyst-v2/page.tsx:17-26` looks for `step.tool_input.result.matches`, but the backend only stores tool input, not tool output.
- Critical: type contract is wrong.
  - `frontend/lib/v2-types.ts:38` says `factors_applied: Record<string, number>`
  - backend returns mixed nested data, for example `confidence_breakdown` in `backend/app/pricing/rcn_v2/calculator.py:453-460`
  - `valuation_engine.py:228` also passes a rich dict through
- Critical: runtime crash path in `frontend/components/analyst-v2/ValuationCard.tsx:74-78`
  It blindly calls `val.toFixed(3)` for every `factors_applied` entry. That will blow up when `val` is an object or string.
- High: `frontend/components/analyst-v2/CompCard.tsx`
  Search found no usage outside the file itself. It is dead code.
- Medium: duplicate UI logic
  - `CompCard.tsx` and `CompsPanel.tsx` both define `formatCAD()` and `monthsSince()`
  - `V2ClarificationChips.tsx:27-47` and `V2SuggestedActions.tsx:38-58` duplicate near-identical button styling/hover logic
- Medium: `frontend/components/analyst-v2/V2ChatPanel.tsx:17-44`
  This component is mostly a pass-through wrapper around `V2MessageList` and `V2ChatInput`.
- Medium: `frontend/components/analyst-v2/PriceDistributionChart.tsx:71-76`, `103-105`
  The component computes coefficient of variation and labels it `Sigma`. That is mathematically wrong.
- Low: `frontend/components/analyst-v2/ValuationCard.tsx:6`
  `cn` is imported and unused.
- Low: `frontend/app/(authenticated)/analyst-v2/page.tsx:68`
  PDF export is a dead TODO.

### Are the components well-structured React?

Not really.

What is fine:

- `V2ChatInput.tsx` is small and focused.
- `PriceDistributionChart.tsx` is cohesive aside from the sigma label issue.
- `ValuationSkeleton.tsx` is fine.

What is not fine:

- wrapper components with minimal value
- duplicate data-formatting helpers
- duplicated hover logic via imperative DOM style mutation
- broken contract with backend response shape

### Final verdict

**REBUILD**

### Rebuild target

- 4 to 6 components, not 11 plus wrappers
- one shared response type generated from backend or mirrored accurately
- one comps extraction path based on actual backend output
- shared formatting helpers
- no dead `CompCard`

## Cross-Cutting Slop Signals

These are the strongest “AI slop” indicators in the reviewed keep paths:

- prompt/tool orchestration around deterministic code instead of a smaller service
- DTO/model proliferation for single-path internal data
- wrapper modules and wrapper components with almost no behavior
- duplicated helper logic instead of one shared function
- dead TODO paths and stubbed features presented as architecture
- metrics with authoritative-sounding names that do not measure what they claim

## Recommended Port Plan

### Port first

- `backend/app/pricing/rcn_v2/*`
- `backend/app/db/equipment_models.py`
- the good parts of resolver parsing from `backend/app/services/equipment/resolver.py`

### Port after cleanup

- equipment resolver/promoter pipeline
- core ORM models after migration reconciliation

### Rebuild from concepts only

- valuation engine
- calibration harness
- Analyst V2 frontend

### Do not port

- Claude Agent V2
- observability package as a package

## Bottom Line

If you port this codebase naively, you will import a lot of ceremony and a few serious truthfulness bugs.

If you port selectively, there is a strong V2 hiding inside it:

- keep the equipment schema
- keep the RCN v2 math
- salvage the compound parser ideas
- throw away most of the agent shell
- throw away most of the observability shell
- rewrite the frontend against a real response contract

## Cursor — Next Steps

### Minimal V2-ready contracts (lock these first)

1. Agent step schema (needs tool outputs, not just tool inputs)

Backend already defines `AgentStep` with:
- `tool_name: string`
- `tool_input: dict`
- `tool_summary: string`
- `duration_ms: int`

For the frontend to deterministically extract comps, you need one of:
- Add `tool_output: unknown` to `AgentStep`, and populate it with the raw tool result
- Or add a dedicated top-level `comps: MarketListing[]` field to the agent response

Suggested “minimal and explicit” TS shape (prefer this over parsing tool input):
```ts
export interface AgentStep {
  tool_name: string
  tool_input: Record<string, unknown>
  tool_output?: unknown // must be present for `search_market_listings` extraction
  tool_summary: string
  duration_ms: number
}
```

2. Comps payload (match existing frontend `MarketListing`)

Comps panel and chart want:
```ts
export interface MarketListing {
  source: string
  title: string
  price_cad: number | null
  year: number | null
  manufacturer: string | null
  model: string | null
  location: string | null
  url: string | null
  scraped_date: string | null
}
```

Backend tool should return `search_market_listings` with a deterministic wrapper like:
```py
class MarketListingsResult(BaseModel):
  matches: list[MarketListing]
  total_found: int
  best_similarity: float
  oldest_match_years: int
  price_cv: float | None
```

3. Valuation result typing (align frontend + backend)

Keep the valuation typing strict and numeric where the UI calls `.toFixed()`:
```ts
export interface ValuationResult {
  rcn_cad: number
  fmv_cad: number
  olv_cad: number
  flv_cad: number
  confidence: number
  rcn_source: string
  fmv_source: string
  depreciation_curve: string
  effective_age: number
  condition_tier: string
  factors_applied: Record<string, number> // must be numbers only
  reconciliation: ReconciliationDetail | null
  evidence_references: string[]
  warnings: string[]
}
```

### Port checklist + tests (turn verdicts into work items)

Use this order so you don’t build UI on drifting contracts.

1. REBUILD: `Analyst V2 Frontend` (contract-first)
   - Port checklist
     - Fix comps extraction: do not parse `step.tool_input.result.matches`
     - Update the UI to use either `step.tool_output` (for `search_market_listings`) or a top-level `comps` payload
     - Remove dead UI paths (`CompCard`, dead PDF export TODO)
     - Ensure `ValuationCard` never calls `.toFixed()` on non-numbers (validate `factors_applied` values)
   - Tests to add
     - Unit test `extractComps()` to verify it returns `MarketListing[]` when tool output contains `matches`
     - Type-level (tsc) check: `PricingAgentResponse` matches the backend payload shape
     - Runtime test: `ValuationCard` renders with `factors_applied` values as numbers only (and gracefully handles empty/unknown)

2. PORT WITH CLEANUP: `Equipment Intelligence`
   - Port checklist
     - Fix promotion integrity: no random/placeholder UUIDs in canonical fields
     - Fix category assignment correctness (the resolver bug class mentioned in the review)
     - Split resolver so identity resolution and evidence normalization are testable units
   - Tests to add
     - Resolver unit tests for identity matching (manufacturer/model + drive type + stages)
     - Promotion integration test: staging row -> gold row, verifying provenance + escalation + FK integrity

3. REBUILD: `Valuation Engine` (thin orchestration)
   - Port checklist
     - Stop hiding DB failures as “empty data”
     - Make valuation failures explicit as warnings (and confidence downgrades)
     - Keep deterministic math as a single source of truth (prefer calling `rcn_v2` directly)
   - Tests to add
     - Golden tests: for a fixed input valuation request, verify the same `ValuationResult` each run
     - DB error propagation tests: simulated query failure returns a response with `warnings` and reduced confidence

4. PORT WITH CLEANUP: `RCN v2 Calculator`
   - Port checklist
     - Keep pure functions and boundary validations
     - Ensure all returned numeric fields are actual numbers (no strings/None creeping into factors)
   - Tests to add
     - Property/edge tests around depreciation/condition (inputs outside range -> warning + safe output)

5. REBUILD: `Calibration`
   - Port checklist
     - Convert calibration harness into a reliable gate: parse, run engine, compute metrics, and persist results
     - Ensure harness errors fail loudly (no silent fallback-to-empty)
   - Tests to add
     - CSV parsing tests with messy-row fixtures
     - Harness aggregation tests (median abs error, within-25/50) on a small synthetic dataset

6. PORT WITH CLEANUP: `DB Models`
   - Port checklist
     - Reconcile ORM models vs alembic schema so production migrations don’t drift
     - Add FK/index checks for the 3 gold tables
   - Tests to add
     - Migration smoke test: `alembic upgrade head` + metadata introspection for each table

7. SKIP (don't port): `Claude Agent V2`, `Observability package as a package`
   - Port checklist
     - Keep only the parts that are already aligned with the Phase 3 agent contract
     - Treat observability as opt-in wrappers around real runtime events, not as "framework scaffolding"

## Claude Code — Next Steps

My assessment diverges from Cursor's above in ordering, priorities, and what actually matters first.

### Where I disagree with Cursor

**Cursor says: rebuild frontend first (contract-first).**
I say: fix the data layer first. The frontend is downstream of everything. Rebuilding it before the backend contracts are stable means you rebuild it twice. The frontend is cheap to redo once the API is locked.

**Cursor says: skip Claude Agent V2 entirely.**
I say: skip the current *implementation*, but the concept of a tool-use agent loop is the right architecture for this product. The V1 agent is bad because it has fake metrics and broken conversation continuity — not because tool-use agents are wrong. V2 should have a clean agent, just not *this* agent.

**Cursor's port checklist mixes concerns.**
Each item blends "what to fix" with "what tests to add" without prioritizing which fixes are load-bearing vs cosmetic. Some of the listed tests (e.g., "tsc type check matches backend payload") are good hygiene but not blocking issues for a port.

### My priorities for V2

**Phase 0: Establish the V2 project foundation (do this before porting anything)**

1. Define the V2 API contract in one place. Not in Pydantic models, not in TypeScript interfaces, not in a spec doc — in an OpenAPI schema that both sides generate from. This kills the contract drift problem permanently.
2. Set up the V2 database with a clean migration `001`. Port `equipment_models.py` with the FK/index fixes, reconcile `models.py` string lengths against migration 006, and drop `user_model.py`. Start clean.
3. Establish the V2 test harness. Copy the existing test patterns that work (valuation math unit tests, equipment intelligence integration tests). Don't port the calibration harness yet — it needs a redesign.

**Phase 1: Port the math (the stuff that actually values equipment)**

This is the core product. Everything else is UI/orchestration around it.

1. Port `rcn_v2/*` as-is with three changes:
   - Make `_compute_base_rcn` and `_normalize_category` public (they're already imported externally, so stop pretending they're private)
   - Replace `extra="allow"` on `RCNInputSpec` with explicit optional fields
   - Extract the ~30 magic numbers into a config section at the top of each file, clearly labeled as policy constants
2. Port `escalation.py` as-is (it's 72 lines and clean)
3. Port the *concepts* from `valuation_math.py` but rewrite against `rcn_v2` as the single source of truth for the factor chain. The diversity gate, scaling hooks, and reconciliation logic are real — the duplicate FMV computation is not.
4. Write golden tests: fixed inputs → expected outputs, run on every commit. This is the regression gate the calibration harness was supposed to be.

**Phase 2: Port the data pipeline (resolver + promoter)**

1. Split `resolver.py` (814 lines) into four files:
   - `parsing.py` — compound description parsing, frame extraction, size extraction (the real domain work)
   - `aliases.py` — manufacturer/model alias maps, category normalization (centralize the 8+ dicts scattered across the codebase)
   - `identity.py` — equipment identity creation/lookup/upsert
   - `audit.py` — resolution audit trail writing
2. Fix the two critical bugs before anything else:
   - `resolver.py:698` — random UUID FK fallback → raise ValueError
   - `promoter.py:221` — source_id as category_id → raise ValueError
3. Fix gold table canonical field population — write resolved values, not raw evidence
4. Port `promoter.py` with the integrity fixes. It's only 282 lines and structurally simple.

**Phase 3: Build the new agent (not port, not skip — build)**

The current Claude Agent V2 is skip-worthy as code, but the *product* needs an agent layer. The user asks a question, the system needs to resolve what they're asking about, fetch relevant data, run valuation, and explain the result. That's a tool-use loop.

Build it clean:
1. One file, under 200 lines. The agent loop is: receive query → resolve identity → compute valuation → format response. Three tool calls max.
2. No fake metrics. `best_similarity` is either a real cosine/trigram score or it doesn't exist. `oldest_match_years` is either listing scrape date minus today or it doesn't exist.
3. Conversation continuity works or doesn't exist. No `conversation_id` field that gets silently dropped.
4. Tool outputs stored in steps, not just tool inputs. The frontend needs the data the tools returned.
5. Response is a discriminated union: `valuation | clarification | error`. Not `valuation | clarification | preliminary` where "preliminary" means "I couldn't find data but I'll guess anyway."

**Phase 4: Build the frontend**

Now — and only now — build the frontend, because:
- The API contract is locked (Phase 0)
- The math is ported and tested (Phase 1)
- The data pipeline works (Phase 2)
- The agent returns real data in a known shape (Phase 3)

Build it as:
1. 5-6 components max. No wrapper components. No `V2ChatPanel` pass-throughs.
2. One `formatCAD()` utility, one `monthsSince()` utility, shared across all components.
3. Comps come from a top-level `comps` field on the response, not parsed out of step tool inputs.
4. `factors_applied` values are validated as numbers before `.toFixed()`. If the backend sends non-numbers, show a warning, don't crash.
5. CV is labeled as CV, not Sigma.

**Phase 5: Rebuild calibration as a real gate**

After the engine is ported and the agent works:
1. Redesign the dataset mapping to include the actual input drivers: horsepower, capacity, drive type, stage count. Without these, the harness is testing "can the engine guess from make/model/year" which is not the real use case.
2. Make engine failures distinct from "row out of scope." A row where the engine crashes is a bug. A row where the engine says "I don't have data for this" is expected. These should not both become warnings in a summary report.
3. Set pass/fail thresholds. A calibration harness that always says "here are the numbers" is a dashboard, not a gate.

### What I would not port at all

- **The entire `observability/` package.** Not because observability is unimportant, but because this implementation is disconnected from runtime. When V2 needs tracing, add it around real calls, not as a pre-built framework.
- **`pricing_agent_models.py`, `pricing_agent_tools.py`, `pricing_agent_executor.py`, `pricing_agent_v2.py`** — all four files. The agent concept is right; the code has too many integrity problems (fake metrics, broken continuity, swallowed exceptions, stubbed features) to clean up. Faster to write 200 clean lines than fix 1,100 broken ones.
- **`valuation_service.py`** — callback soup with dependency injection ceremony around a simple computation. Delete.
- **`CompCard.tsx`** — dead code. Never imported.
- **`V2ChatPanel.tsx`** — pass-through wrapper. Inline its 3 lines of layout into the parent.
- **`user_model.py`** — re-export wrapper. Import the model directly.

### The one thing that matters most

The single highest-impact action for V2 quality is: **make the valuation pipeline end-to-end testable with golden fixtures.**

Right now, the calibration harness is the closest thing to an integration test, and it's unreliable because it omits key input fields. If V2 has a test that says "given this exact equipment description, the engine produces this exact FMV ± 2%," then every other bug becomes catchable. Without that test, you're shipping on vibes.
