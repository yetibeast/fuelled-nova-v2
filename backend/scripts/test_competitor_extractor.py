#!/usr/bin/env python3
"""Exercise the extractor against bundled fixture emails — verifies the
end-to-end LLM call + JSON parsing without needing a live Gmail account.

Run:
    PYTHONPATH=backend python3 backend/scripts/test_competitor_extractor.py

Expects ANTHROPIC_API_KEY in env. No DB required — extraction is pure.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.competitor_inbox.extractor import extract_signals  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "competitor_emails"


def parse_fixture(path: Path) -> tuple[str, str, str]:
    """Each fixture starts with From:/Subject: headers then a blank line."""
    text = path.read_text(encoding="utf-8")
    head, _, body = text.partition("\n\n")
    sender = ""
    subject = ""
    for line in head.splitlines():
        if line.lower().startswith("from:"):
            sender = line.split(":", 1)[1].strip()
        elif line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
    return sender, subject, body


async def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set in env", file=sys.stderr)
        return 1
    fixtures = sorted(FIXTURE_DIR.glob("*.txt"))
    if not fixtures:
        print(f"No fixtures found in {FIXTURE_DIR}", file=sys.stderr)
        return 1
    failures = 0
    for fix in fixtures:
        sender, subject, body = parse_fixture(fix)
        print(f"\n=== {fix.name} ===")
        result = await extract_signals(sender=sender, subject=subject, body=body)
        print(f"status: {result.status}")
        if result.error:
            print(f"error:  {result.error}")
        for i, sig in enumerate(result.signals, 1):
            print(f"  signal {i}: {json.dumps(asdict(sig), default=str, indent=2)}")
        if result.status != "success":
            failures += 1
    print(f"\n{len(fixtures) - failures}/{len(fixtures)} fixtures extracted cleanly")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
