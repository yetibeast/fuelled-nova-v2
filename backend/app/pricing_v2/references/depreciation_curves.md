# Depreciation Curves — Retention Multipliers

Fair Value = RCN × age_factor × condition_factor × hours_factor × service_factor × geo_factor

## Age Retention Curves (multiply × RCN)

### Rotating Equipment (Reciprocating Compressors, Gensets, Pumps)
| Age | 0-1 yr | 2-3 yr | 4-5 yr | 6-8 yr | 9-12 yr | 13-15 yr | 16-20 yr | 21-25 yr | 26-30 yr | 30+ yr |
|-----|--------|--------|--------|--------|---------|----------|----------|----------|----------|--------|
| Factor | 0.90 | 0.80 | 0.65 | 0.50 | 0.38 | 0.28 | 0.20 | 0.15 | 0.10 | 0.08 |

### Rotating Equipment (Screw/Centrifugal Compressors)
| Age | 0-1 yr | 2-3 yr | 4-5 yr | 6-8 yr | 9-12 yr | 13-15 yr | 16-20 yr | 21-25 yr | 26-30 yr | 30+ yr |
|-----|--------|--------|--------|--------|---------|----------|----------|----------|----------|--------|
| Factor | 0.88 | 0.75 | 0.60 | 0.45 | 0.35 | 0.25 | 0.18 | 0.12 | 0.08 | 0.05 |

### Static Equipment (Separators, Tanks, Heaters, Treaters)
| Age | 0-1 yr | 2-3 yr | 4-5 yr | 6-8 yr | 9-12 yr | 13-15 yr | 16-20 yr | 21-25 yr | 26-30 yr | 30+ yr |
|-----|--------|--------|--------|--------|---------|----------|----------|----------|----------|--------|
| Factor | 0.92 | 0.85 | 0.75 | 0.65 | 0.55 | 0.45 | 0.35 | 0.25 | 0.18 | 0.12 |

### Pump Jacks (Beam Pumping Units)
| Age | 0-1 yr | 2-3 yr | 4-5 yr | 6-8 yr | 9-12 yr | 13-15 yr | 16-20 yr | 21-25 yr | 26-30 yr | 30+ yr |
|-----|--------|--------|--------|--------|---------|----------|----------|----------|----------|--------|
| Factor | 0.92 | 0.85 | 0.78 | 0.70 | 0.60 | 0.50 | 0.40 | 0.30 | 0.22 | 0.15 |

### Gas Turbines
| Age | 0-1 yr | 2-3 yr | 4-5 yr | 6-8 yr | 9-12 yr | 13-15 yr | 16-20 yr | 21-25 yr | 26-30 yr | 30+ yr |
|-----|--------|--------|--------|--------|---------|----------|----------|----------|----------|--------|
| Factor | 0.88 | 0.78 | 0.65 | 0.52 | 0.40 | 0.30 | 0.22 | 0.15 | 0.10 | 0.07 |

### Electrical Equipment (MCC, VFD, E-Houses)
| Age | 0-1 yr | 2-3 yr | 4-5 yr | 6-8 yr | 9-12 yr | 13-15 yr | 16-20 yr | 21-25 yr | 26-30 yr | 30+ yr |
|-----|--------|--------|--------|--------|---------|----------|----------|----------|----------|--------|
| Factor | 0.90 | 0.82 | 0.72 | 0.60 | 0.48 | 0.38 | 0.28 | 0.20 | 0.14 | 0.10 |

## Condition Multipliers (PASC Rating)

| Rating | Description | Multiplier | When to Apply |
|--------|-------------|------------|---------------|
| A — Excellent | Like new, minimal wear, recently overhauled | 1.00 | Documented overhaul within last 2 years |
| B — Good | Normal wear, operational, no major issues | 0.75 | **Default when condition unknown** |
| C — Fair | Significant wear, operational but needs work | 0.50 | Known deferred maintenance or issues |
| D — Poor/Salvage | Non-operational, scrap, major damage | 0.20 | Scrap + component recovery only |

## Operating Hours Adjustment (rotating equipment only)

| Hours Range | Multiplier | Notes |
|-------------|------------|-------|
| 0 - 5,000 | 1.10 | Low hours premium |
| 5,000 - 15,000 | 1.00 | **Normal baseline** |
| 15,000 - 30,000 | 0.85 | Approaching overhaul interval |
| 30,000 - 50,000 | 0.70 | Likely needs major overhaul |
| 50,000+ | 0.55 | Extreme. Component life consumed |

## Service / Special Condition Multipliers

| Factor | Multiplier | Notes |
|--------|------------|-------|
| Sweet service (standard) | 1.00 | Baseline |
| Sour service (NACE/H2S rated) | 1.15 | NACE materials/certification premium |
| Sour service (high H2S, >10%) | 1.25 | Specialized metallurgy |
| Alberta / Texas (premium market) | 1.05 | Strong demand |
| Saskatchewan / Louisiana | 1.00 | Baseline |
| Northern BC / NWT (remote) | 0.85 | Freight penalty |
| US Gulf Coast (export) | 0.95 | CAD/USD + freight |
| ABSA certified with data sheets | 1.10 | Registration adds resale value |
| No data sheet / no registration | 0.85 | Buyer must re-certify |
| VFD equipped (electric drive) | 1.05 | Energy savings, reduced mechanical stress |
| Complete turnkey package (building + MCC) | 1.05 | Buyer gets operational system |
| Across-the-line electric start | 1.00 | Standard |
