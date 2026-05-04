"""Engine-fallback telemetry — when rcn_engine raises, calculate_fmv falls back to
_simple_fmv AND writes a structured event so we can size how often this happens.

PR-3 surfaced that we had no visibility into the fallback path. This test pins the
logging behaviour so silence here ever again means an intentional removal.
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch


def test_methodology_version_stamped_on_engine_path(tmp_path, monkeypatch):
    """Successful engine path should advertise the methodology version so users who
    re-run an old quote can see why the number moved."""
    # LOG_DIR is read once at app.config import; patch the live attribute directly.
    import app.config
    monkeypatch.setattr(app.config, "LOG_DIR", str(tmp_path))
    from app.pricing_v2 import tools

    out = tools.calculate_fmv(
        rcn=500_000, equipment_class="rotating", age_years=10,
        condition="B", hours=20_000, service="sweet",
    )
    assert "rcn_engine" in out
    assert tools.METHODOLOGY_VERSION in out


def test_engine_failure_writes_fallback_telemetry(tmp_path, monkeypatch):
    # LOG_DIR is read once at app.config import; patch the live attribute directly.
    import app.config
    monkeypatch.setattr(app.config, "LOG_DIR", str(tmp_path))
    # Force a fresh import so the module picks up our LOG_DIR via app.config lookup.
    from app.pricing_v2 import tools

    boom = RuntimeError("simulated engine explosion")
    with patch.object(tools, "_rcn_calculate", side_effect=boom):
        out = tools.calculate_fmv(
            rcn=500_000, equipment_class="rotating", age_years=10,
            condition="B", hours=20_000, service="sweet",
        )

    # User still gets a usable answer via the simple fallback — pricing call must not break.
    assert "FMV CALCULATION" in out
    assert "simple fallback" in out.lower()

    # And the failure was logged for ops visibility.
    log_path = os.path.join(str(tmp_path), "engine_fallback.jsonl")
    assert os.path.exists(log_path), "fallback should have written engine_fallback.jsonl"
    with open(log_path) as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 1
    record = lines[0]
    assert record["error_type"] == "RuntimeError"
    assert record["category"] == "compressor"  # rotating → compressor via _CLASS_TO_CATEGORY
    assert record["age_years"] == 10
    assert record["hours"] == 20_000
    assert "timestamp" in record


def test_telemetry_failure_does_not_break_pricing(tmp_path, monkeypatch):
    """If the telemetry write itself fails (disk full, permission denied), pricing
    must still return a valid answer — telemetry is best-effort."""
    # LOG_DIR is read once at app.config import; patch the live attribute directly.
    import app.config
    monkeypatch.setattr(app.config, "LOG_DIR", str(tmp_path))
    from app.pricing_v2 import tools

    with patch.object(tools, "_rcn_calculate", side_effect=RuntimeError("boom")):
        with patch("builtins.open", side_effect=PermissionError("disk full")):
            # Engine fails AND telemetry fails — pricing still returns a string.
            out = tools.calculate_fmv(
                rcn=500_000, equipment_class="rotating", age_years=10,
                condition="B", hours=20_000, service="sweet",
            )
    assert "FMV CALCULATION" in out
