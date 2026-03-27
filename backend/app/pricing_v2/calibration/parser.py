"""Parse uploaded calibration spreadsheets (CSV/Excel) into test cases."""

from __future__ import annotations

import csv
import io
from typing import Any


def parse_calibration_file(content: bytes, filename: str) -> list[dict[str, Any]]:
    """Parse a calibration file into a list of test cases.

    Expected columns: description, expected_fmv_low, expected_fmv_high, category (opt).
    """
    if filename.endswith(".csv"):
        return _parse_csv(content)
    raise ValueError(f"Unsupported file type: {filename}. Use .csv")


def _parse_csv(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    cases: list[dict[str, Any]] = []
    for i, row in enumerate(reader):
        desc = (row.get("description") or row.get("Description") or "").strip()
        if not desc:
            continue

        low = _parse_number(row.get("expected_fmv_low") or row.get("low") or "0")
        high = _parse_number(row.get("expected_fmv_high") or row.get("high") or "0")
        category = (row.get("category") or row.get("Category") or "").strip()

        cases.append({
            "id": f"CSV-{i + 1:03d}",
            "description": desc,
            "expected_fmv_low": low,
            "expected_fmv_high": high,
            "category": category,
        })

    return cases


def _parse_number(val: str) -> float:
    try:
        return float(val.replace(",", "").replace("$", "").strip())
    except (ValueError, AttributeError):
        return 0.0
