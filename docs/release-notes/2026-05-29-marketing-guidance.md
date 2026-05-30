# Nova rev notice — 2026-05-29 (reports always recommend Fuelled)

**Subject: Nova now always recommends Fuelled in report marketing guidance — never competitors**

Audience: Fuelled team

---

## What Mark asked for

> There is a weird thing in Nova where for reports it recommends other brokers. Can you please have it always recommend Fuelled. I always edit the reports directly but others may let it slip through and it would look weird or could impair future business.
>
> — 2026-05-29

His example, from a report's **MARKETING GUIDANCE** section:

> "Engage Solar Turbines directly… **List on ReflowX**… Direct outreach to power developers, midstream operators (Pembina, TC Energy, Enbridge), and **international brokers**… Transformer: **contact ABB, Wesco, and specialized transformer brokers**…"

## What we built

Nova's valuation prompt now has a firm rule for the marketing-guidance section: **always position Fuelled as the place to list and sell through, and never recommend a competing marketplace (ReflowX, Machinio, IronPlanet, Ritchie Bros, AllSurplus, etc.) or a rival broker/OEM to handle the sale.**

The genuinely useful market intelligence stays: Nova still names likely **buyers** (operators and end-users like the midstream majors) and still advises on **timing** (e.g. start outreach well before a planned decommission). That's buyer targeting — only the "where to sell / which broker" recommendation is now routed to Fuelled.

One nuance preserved: Nova can still **cite** competitor platforms as a price-data source when a comp actually comes from there (that's how we benchmark). It just won't tell a seller to go list there.

## How to use it

No workflow change. Generate valuations and reports as usual — the marketing guidance will now point to Fuelled. You should no longer need to hand-edit competitor names out of the report.

## What's NOT in this rev

- No change to the valuation numbers, comps, or methodology — only the marketing-guidance wording.
- Existing reports already exported aren't changed retroactively; this applies to new valuations going forward.

## What's next

- If you spot any report that still names a competitor as the place to sell, send it over — it means a phrasing slipped the guardrail and we'll tighten it.

Implementation notes: directive added to the marketing-guidance instruction in `backend/app/pricing_v2/prompts.py`; locked with a contract test in `backend/tests/test_prompt_personalization.py`. Requires a backend restart to take effect (prompt is cached at startup). On its own branch pending merge + deploy.
