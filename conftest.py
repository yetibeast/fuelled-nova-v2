"""Worktree-root conftest: makes `backend.app.*` importable from tests/.

Pytest's rootdir-prepend mechanism normally inserts the first parent
directory without `__init__.py` onto sys.path. For tests under
`tests/pricing_v2/tier2/`, that parent is `tests/pricing_v2/` — which
does not contain `backend/`. Inserting the worktree root here makes
imports like `from backend.app.pricing_v2.tier2.column_spec import ...`
resolve in both pytest and ad-hoc `python -c` invocations.

Note: backend/tests/ has its own __init__.py and resolves via
`backend/` on sys.path; those tests use `from app.X import ...` and
are unaffected by this conftest.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
