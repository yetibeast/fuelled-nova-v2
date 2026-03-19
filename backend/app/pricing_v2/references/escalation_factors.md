# Escalation Factors — Historical RCN to Current-Year CAD

## Why Escalation Matters

An RCN value from a 2020 appraisal is NOT a 2026 RCN. Stats Canada IPPI Manufacturing index went from 100 (Jan 2020) to 137.4 (Jan 2026) — a 37.4% increase in general manufacturing costs. Oilfield fabrication in Alberta ran hotter than the general index in 2021-2022 due to steel pricing, skilled labor shortages, and supply chain constraints.

**Rule:** All historical RCN values MUST be escalated to current-year CAD before use in valuations. Store both original and escalated values.

## Blended Escalation Factors to 2026 CAD

| Period | IPPI Factor | Oilfield Premium | Blended Factor | Source | Confidence |
|--------|-------------|------------------|----------------|--------|------------|
| 2020 H1 | 1.37 | +3% | **1.40** | IPPI + CSM OEM confirmed | 0.80 |
| 2020 H2 | 1.35 | +3% | **1.38** | IPPI + estimated | 0.80 |
| 2021 H1 | 1.28 | +5% | **1.33** | IPPI + estimated (steel rising) | 0.70 |
| 2021 H2 | 1.22 | +5% | **1.27** | IPPI + estimated (peak supply chain) | 0.70 |
| 2022 H1 | 1.15 | +3% | **1.18** | IPPI near peak (132.7 May 2022) | 0.75 |
| 2022 H2 | 1.12 | +2% | **1.14** | IPPI post-peak | 0.75 |
| 2023 H1 | 1.08 | +2% | **1.10** | IPPI moderating | 0.75 |
| 2023 H2 | 1.06 | +1% | **1.07** | IPPI stabilizing | 0.75 |
| 2024 H1 | 1.04 | +1% | **1.05** | Recent | 0.80 |
| 2024 H2 | 1.03 | 0% | **1.03** | Nearly current | 0.80 |
| 2025 H1 | 1.02 | 0% | **1.02** | Essentially current | 0.85 |
| 2025 H2 | 1.01 | 0% | **1.01** | Current | 0.85 |
| 2026 H1 | 1.00 | 0% | **1.00** | Current year | 0.95 |

## Equipment Class Adjustments

For specific equipment classes, apply additional escalation premium over the general factor during 2020-2022:

| Equipment Class | 2020-2022 Additional Premium | Rationale |
|----------------|------------------------------|-----------|
| Electrical (VFD, MCC, switchgear) | +2-3% | Supply chain constraints on electrical components |
| Fabrication (vessels, skids, structural) | +3-5% | Steel pricing + AB labor shortage |
| Rotating (engines, compressors) | +0-2% | Closer to general index |
| Static (tanks, simple vessels) | +3-5% | Steel-heavy, follows fabrication |

## Application

To escalate a historical RCN:
```
escalated_rcn = original_rcn × blended_factor(effective_date)
```

For USD-denominated RCN values, also apply FX conversion:
```
escalated_rcn_cad = original_rcn_usd × blended_factor × fx_rate_at_effective_date
```

Current approximate FX: 1 USD = 1.44 CAD (verify at time of use)

## OEM-Confirmed Data Points

| OEM | Period | Stated Escalation | Equipment | Notes |
|-----|--------|-------------------|-----------|-------|
| CSM Pump Packaging | 2020→2026 | 35% | Pump packages | Nathan Hutzul, direct correspondence Mar 2026 |

OEM-confirmed factors always override index-based estimates for that specific equipment type.

## Data Sources

- **Stats Canada IPPI:** Table 18-10-0265-01, Manufacturing index, Jan 2020=100 base
- **Stats Canada MEPI:** Table 18-10-0283-01, Machinery and Equipment Price Index
- **AACE International:** Cost engineering indices (paywalled, used for cross-reference)
- **OEM correspondence:** Direct quotes from manufacturers (highest confidence)
