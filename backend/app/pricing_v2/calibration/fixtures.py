"""Golden fixtures — known-good equipment descriptions with expected FMV ranges."""

from __future__ import annotations

GOLDEN_FIXTURES: list[dict] = [
    {
        "id": "GF-001",
        "description": "2019 Ariel JGK/4 gas compressor, 800 HP Caterpillar G3508 engine, "
                       "4-throw, 6-stage, 1200 RPM, sound attenuated enclosure, 8,400 hours",
        "expected_fmv_low": 380_000,
        "expected_fmv_high": 480_000,
        "category": "Gas Compressors",
    },
    {
        "id": "GF-002",
        "description": "2017 Ariel JGE/2 gas compressor, 400 HP Caterpillar G3406 engine, "
                       "2-throw, 4-stage, 1200 RPM, skid-mounted, 12,500 hours",
        "expected_fmv_low": 160_000,
        "expected_fmv_high": 220_000,
        "category": "Gas Compressors",
    },
    {
        "id": "GF-003",
        "description": "2020 Waukesha VHP P48GLD generator set, 1200 kW, natural gas, "
                       "480V, sound attenuated, 3,200 hours, emissions compliant",
        "expected_fmv_low": 420_000,
        "expected_fmv_high": 540_000,
        "category": "Power Generation",
    },
    {
        "id": "GF-004",
        "description": "2016 Smith Industries dehydration unit, TEG glycol, "
                       "100 MMscf/d capacity, 3-tray contactor, reboiler, skid-mounted",
        "expected_fmv_low": 90_000,
        "expected_fmv_high": 140_000,
        "category": "Process Equipment",
    },
    {
        "id": "GF-005",
        "description": "2021 Ariel JGJ/2 gas compressor, 600 HP Caterpillar G3508A engine, "
                       "2-throw, 4-stage, 1000 RPM, winterized enclosure, 2,100 hours",
        "expected_fmv_low": 320_000,
        "expected_fmv_high": 410_000,
        "category": "Gas Compressors",
    },
]
