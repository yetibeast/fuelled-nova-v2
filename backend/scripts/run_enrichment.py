"""CLI wrapper for the recurring enrichment runner.

Thin entry point — all logic lives in app.pricing_v2.intel.runner.run_enrichment.
This script handles arg parsing, session factory wiring, and final-summary
printing for the cron job.

Usage:
    python backend/scripts/run_enrichment.py \
        --db-url postgres://... \
        --limit 20 \
        --max-cost-usd 10 \
        --trigger cron-weekly

    # Dry-run (call provider, skip writes):
    python backend/scripts/run_enrichment.py --dry-run --limit 5

Required env (or --db-url):
    DATABASE_URL — async-driver URL, e.g. postgresql+asyncpg://...
    ANTHROPIC_API_KEY — for the claude_parallel provider

Triggers (cron schedule):
    cron-weekly     — Monday 08:00, limit 20, max-cost 10
    cron-quarterly  — Jan/Apr/Jul/Oct 1st 03:00, limit 50, max-cost 25
    manual          — ad-hoc

Install on Proxmox runner:
    scp backend/scripts/run_enrichment.py runner:/opt/scraper-runner/run_enrichment.py
    scp backend/scripts/intel-cron.conf runner:/etc/cron.d/fuelled-intel
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from contextlib import asynccontextmanager

# Make `app.*` importable when run from project root or any working dir.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # noqa: E402

from app.pricing_v2.intel.providers.claude_parallel import ClaudeParallelProvider  # noqa: E402
from app.pricing_v2.intel.providers.mock import MockProvider  # noqa: E402
from app.pricing_v2.intel.runner import run_enrichment  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Recurring seller-contact enrichment runner")
    p.add_argument("--db-url", default=None, help="Async PG URL (defaults to $DATABASE_URL)")
    p.add_argument("--limit", type=int, default=20, help="Max sellers to research this run")
    p.add_argument("--max-cost-usd", type=float, default=10.0, help="Abort once cumulative cost reaches this")
    p.add_argument("--trigger", default="manual",
                   help="Audit label for enrichment_runs.trigger (cron-weekly | cron-quarterly | manual)")
    p.add_argument("--provider", default="claude_parallel",
                   choices=["claude_parallel", "mock"],
                   help="Provider to use (default claude_parallel; mock is for dry-runs)")
    p.add_argument("--dry-run", action="store_true",
                   help="Call provider but skip all writes")
    return p.parse_args()


def _make_session_factory(db_url: str):
    # asyncpg-style URL required (sqlalchemy.ext.asyncio).
    engine = create_async_engine(db_url, future=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def factory():
        async with session_maker() as session:
            yield session

    return factory, engine


async def _main_async(args: argparse.Namespace) -> int:
    db_url = args.db_url or os.environ.get("DATABASE_URL")
    if not db_url:
        print("error: DATABASE_URL not set and --db-url not passed", file=sys.stderr)
        return 2

    if args.provider == "claude_parallel":
        provider = ClaudeParallelProvider()
    else:
        provider = MockProvider()

    factory, engine = _make_session_factory(db_url)
    try:
        summary = await run_enrichment(
            factory,
            provider=provider,
            limit=args.limit,
            max_cost_usd=args.max_cost_usd,
            trigger=args.trigger,
            dry_run=args.dry_run,
        )
    finally:
        await engine.dispose()

    print(f"[intel.run_enrichment] run_id={summary.run_id}")
    print(f"  trigger:         {args.trigger}")
    print(f"  provider:        {provider.name}")
    print(f"  sellers_total:   {summary.sellers_total}")
    print(f"  sellers_ok:      {summary.sellers_succeeded}")
    print(f"  sellers_failed:  {summary.sellers_failed}")
    print(f"  contacts_added:  {summary.contacts_added}")
    print(f"  cost_usd:        ${summary.cost_usd:.3f}")
    print(f"  aborted_for_cost:{summary.aborted_for_cost}")
    print(f"  dry_run:         {args.dry_run}")
    return 0


def main():
    args = _parse_args()
    sys.exit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
