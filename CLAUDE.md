
# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## 5. Rev Notices — every feature gets documented + communicated

**Every user-visible change ships with a rev notice. One feature batch = one notice. No silent rollouts.**

The Fuelled team needs to know what changed, what it does, and how to use it — controlled and on a cadence we set, not buried in commit history.

### When a rev notice is required

- A new user-visible feature lands (new page, new tool, new endpoint they'll touch).
- Behavior of an existing feature meaningfully changes (pricing math, ranking logic, what data shows up where).
- New data starts being ingested that powers something they'll see (new scraper field, new source).

Internal-only changes (refactors, infra, schema fixes invisible to users) do **not** require a rev notice. Mention them under an "internal" section in the next user-facing notice if they're worth knowing.

### What goes in a rev notice

File: `docs/release-notes/YYYY-MM-DD.md`. Use the existing notes in that folder as the template. Each notice covers:

1. **What was asked for** — the user/customer ask in their own words where possible.
2. **What we built** — concrete capabilities, not implementation details.
3. **What's new this batch** — if it builds on an earlier rev, call out only the delta.
4. **How to use it** — numbered steps, where to click, what to expect.
5. **What's NOT in this rev** — explicitly list adjacent work that shipped separately so the team isn't left wondering.
6. **What's next** — phase B/C, deferred items, known follow-ups.

### One rev = one feature area

Don't bundle unrelated features into a single notice. If pricing mitigations and a new competitive bot both shipped this week, that's two notices. Bundling defeats the "controlled communication" purpose — readers can't tell which ask each item answers.

### Workflow: build → document → communicate

When a feature is complete and merged:

1. Draft the rev notice in `docs/release-notes/YYYY-MM-DD.md` following the structure above.
2. Surface it to Curtis for review before it goes out.
3. Curtis owns the actual send to the Fuelled team. Don't assume a notice is "out" just because the file exists.

If you finish a feature and don't draft a notice, the work isn't done. Treat the rev notice as part of the feature's definition of done, the same as tests.

## 6. Deploy from main only — never from a feature branch

**`railway up --service backend` from a feature branch is a silent regression machine.** Auto-deploy is off, so prod is literally "whatever was last `railway up`'d." If two feature branches deploy in sequence (`feat/A` then `feat/B`), the second deploy strips everything in A that isn't also in B. Tests pass on each branch in isolation; production loses features.

This isn't hypothetical. On 2026-05-27 the batch-timeout hotfix shipped from `hotfix/batch-timeout-120s` at noon. A later `railway up` from `feat/intel-recurring` (which didn't include the hotfix) overwrote it. Container went back to `timeout=60` silently. Caught only during a manual end-of-day audit.

### The rule

1. Feature branches must merge to `main` **before** any `railway up`.
2. Deploy from `main` only. If you need to deploy from a worktree, the worktree must be on `main` with the relevant work merged in.
3. After every `railway up`, spot-check at least one signature line of whatever the previous deploy fixed (e.g. `railway ssh "grep timeout= /app/app/api/batch.py"`). Silence is not success.
4. Never stack uncommitted hotfixes on feature branches — they're easy to lose when a parallel feature deploys.

### Workflow when you have a hotfix during in-flight feature work

The right shape is: cherry-pick or merge the hotfix onto the feature branch *before* deploying it. Or merge to main first, deploy from main, then resume the feature branch from the new main.

Wrong shape: ship the hotfix from its own branch, then ship the feature branch separately. The feature's `railway up` will overwrite the hotfix.
