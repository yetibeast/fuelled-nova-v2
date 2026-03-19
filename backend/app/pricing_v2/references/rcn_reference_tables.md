# RCN Price Reference Tables

## Overview

The `rcn_price_references` table (PostgreSQL) contains seed data for equipment replacement costs by valuation family, frame, stage count, and drive type.

The canonical spreadsheet is: `rcn_price_reference_seed_v2.xlsx`

## Table Structure

Key fields:
- `reference_key` — Lookup key (e.g., `comp:recip:ariel:jgk4:2stg:gas:pkg`)
- `valuation_family` — Pricing curve group (e.g., `recip_gas_pkg`)
- `canonical_manufacturer` / `canonical_model` — Equipment identity
- `configuration` — bare_frame | package_standard | package_full
- `stages` — Compression/pump stages
- `drive_type` — gas_engine | electric_motor | gas_turbine | integral
- `rcn_new_low` / `rcn_new_mid` / `rcn_new_high` — CAD price range
- `base_hp` — Reference HP for scaling
- `scaling_exponent` — Default 0.6 for rotating equipment
- `confidence` — 0.00 to 1.00

## HP Scaling Formula

For rotating equipment:
```
scaled_rcn = base_rcn × (target_hp / base_hp) ^ scaling_exponent
```

Default scaling_exponent = 0.6 (six-tenths rule, industry standard for rotating equipment)

## Valuation Families (34 defined)

### Compressor Families
| Family | Drive | Description |
|--------|-------|-------------|
| recip_gas_pkg_lp | gas_engine | Low pressure recip (VRU, gas lift) |
| recip_gas_pkg | gas_engine | Standard gas gathering 2-stage |
| recip_gas_pkg_hp | gas_engine | High pressure 4-stage (injection, sales gas) |
| recip_gas_elec_pkg | electric_motor | Electric drive standard |
| recip_gas_elec_pkg_hp | electric_motor | Electric drive high pressure |
| recip_gas_integral | integral | Slow-speed integral (Ajax) |
| recip_frame | N/A | Bare frame only |
| screw_air_pkg | electric_motor | Industrial air compressor |
| screw_gas_pkg | gas/electric | Gas service screw |
| centrifugal_pkg | electric/turbine | Large centrifugal |

### Driver Families
| Family | Type | Description |
|--------|------|-------------|
| engine_driver | gas_engine | Bare gas engine <800HP |
| engine_driver_lg | gas_engine | Large gas engine 800HP+ |
| motor_driver | electric_motor | Electric motor <400HP |
| motor_driver_lg | electric_motor | Large electric motor 400HP+ |
| vfd_drive | electric_motor | Variable frequency drive |
| mcc_electrical | electric_motor | MCC / switchgear |
| turbine_driver | gas_turbine | Mid-size turbine |
| turbine_driver_lg | gas_turbine | Large turbine |

### Generator Families
| Family | Drive | Description |
|--------|-------|-------------|
| genset_gas | gas_engine | Gas engine genset |
| genset_gas_large | gas_engine | Large genset / cogen |
| turbine_genset | gas_turbine | Turbine generator set |

### Static / Pump Families
| Family | Type | Description |
|--------|------|-------------|
| separator_2phase | static | 2-phase separator |
| separator_3phase | static | 3-phase separator |
| separator_3phase_lg | static | Large 3-phase (60"+) |
| prod_tank | static | Production tank ≤400 BBL |
| prod_tank_lg | static | Large production tank 750+ BBL |
| line_heater | static | Line heater |
| emulsion_treater | static | Emulsion treater |
| glycol_dehy | static | Small/mid glycol dehydrator |
| glycol_dehy_lg | static | Large glycol dehydrator |
| triplex_pump_gas | rotating | Gas-driven triplex |
| triplex_pump_elec | rotating | Electric triplex |
| centrifugal_pump_elec | rotating | Electric centrifugal pump |
| centrifugal_pump_elec_lg | rotating | Large electric centrifugal |
| pc_pump_elec | rotating | Progressive cavity pump |
| pump_jack | pump_jack | Beam pumping unit (API size lookup) |

## Key Reference Points (high confidence)

These are the most common AB equipment with best-known pricing:

- **Ariel JGK/4 2-stg gas pkg**: $380K-$620K, base 400HP (conf 0.75)
- **CAT 3406 bare engine**: $80K-$160K, base 350HP (conf 0.70)
- **Waukesha L7044GSI bare engine**: $200K-$440K, base 1200HP (conf 0.70)
- **Waukesha L7044GSI genset pkg**: $600K-$1.1M, base 1200HP (conf 0.70)
- **Production tanks**: $8K-$60K by BBL size (conf 0.75)
- **Pump jacks**: $25K-$270K by API size (conf 0.55-0.70)
