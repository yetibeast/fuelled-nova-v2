# Equipment Risk Rules

Risk factors that affect buyer confidence and must be disclosed in valuations. Check these after calculating base FMV. Each rule has a trigger condition and a disclosure requirement.

## Idle Equipment Degradation

### Rule: Unused but Aged
**Trigger:** Equipment has zero operating hours BUT age > 5 years
**Disclosure:** "Elastomers, seals, gaskets, and O-rings degrade over time even without operation. A pre-commissioning inspection is recommended before first operation."
**Cost impact:** Budget $3,000-$8,000 for pre-commissioning inspection.
**Valuation impact:** Do NOT use PASC condition A (1.00). Use condition multiplier of 1.50× applied to the age factor instead. A 17-year-old unused unit ≠ a new unit, but it's significantly better than a 17-year-old unit with 50,000 hours.

### Rule: Rotary Vane Compressor Idle
**Trigger:** Rotary vane compressor (Ro-Flo, Corken, Blackmer) + idle > 3 years
**Disclosure:** "Carbon/graphite vanes in rotary vane compressors absorb moisture if not properly preserved during idle storage. Vanes may require inspection and potential replacement before commissioning."
**Cost impact:** Vane replacement $2,000-$5,000 depending on compressor size.

### Rule: Lubricant Degradation
**Trigger:** Any rotating equipment + idle > 5 years
**Disclosure:** "Lubricant has likely degraded if not changed during idle period. Requires full flush and replacement before commissioning."
**Cost impact:** $500-$2,000 depending on sump size.

### Rule: Electrical Moisture Ingress
**Trigger:** Any electric motor or electrical equipment + outdoor installation + idle > 5 years
**Disclosure:** "Electrical components (motor windings, heater elements, fan motors) may have moisture ingress after prolonged outdoor exposure. Insulation resistance testing (megger test) recommended before energizing."
**Cost impact:** Megger test $200-$500. Motor rewind if failed: $3,000-$15,000 depending on HP.

## Controls and PLC Obsolescence

### Rule: Allen-Bradley MicroLogix 1200
**Trigger:** PLC identified as MicroLogix 1200 or PanelView 300
**Disclosure:** "Allen-Bradley discontinued the MicroLogix 1200 in 2017. Replacement parts and programming support (RSLogix 500) are limited. Buyer may need to upgrade to CompactLogix or equivalent."
**Cost impact:** Controls upgrade $8,000-$15,000 including panel, programming, and commissioning.

### Rule: Generic PLC Age Check
**Trigger:** Any PLC/controls system on equipment built before 2015
**Disclosure:** "PLC/controls may be running obsolete firmware or hardware. Verify model, support status, and programming software availability."
**Cost impact:** Varies. $5,000-$20,000 for full controls upgrade.

### Rule: HMI/Operator Interface
**Trigger:** Equipment with HMI panel older than 10 years
**Disclosure:** "Operator interface screens and touchpanels have limited service life (typically 10-15 years). Screen may be dim, unresponsive, or require replacement."
**Cost impact:** HMI replacement $2,000-$8,000.

## Overhaul Economics

### Rule: Overhaul Cost vs. Post-Overhaul Value
**Trigger:** Owner states overhaul costs are too high, or condition = C/D on rotating equipment
**Disclosure:** Calculate and show the overhaul economics:
- Estimated overhaul cost range
- Post-overhaul FMV (condition B)
- If overhaul cost > post-overhaul FMV, recommend sell as-is
- Identify target buyer: "A buyer with in-house overhaul capability could achieve the overhaul for [lower cost], making an as-is purchase at [FMV] economically viable."

### Typical Overhaul Costs (Alberta, 2026)
| Equipment | Scope | Cost Range |
|-----------|-------|------------|
| Small recip compressor (JGP/JGJ class) | Frame + valve overhaul | $40,000-$60,000 |
| Small recip compressor | Engine overhaul (3306 class) | $25,000-$40,000 |
| Mid recip compressor (JGK/4 class) | Frame + valve overhaul | $60,000-$100,000 |
| Mid recip compressor | Engine overhaul (L7044 class) | $50,000-$80,000 |
| Centrifugal pump | Impeller/seal/bearing overhaul | $10,000-$25,000 |
| Large genset (3512/3516) | Top end overhaul | $80,000-$150,000 |

## Market and Pricing Risks

### Rule: Time on Market
**Trigger:** Equipment listed > 2 years with > 500 views and no sale
**Disclosure:** "Listed since [date] with [X] views and no sale indicates price resistance. The market has evaluated this equipment at the current price and passed."
**Valuation impact:** This is evidence for repricing, not a risk factor on the equipment itself.

### Rule: Volume Oversupply
**Trigger:** 10+ identical items listed simultaneously from same seller
**Disclosure:** "Listing [N] identical items simultaneously reduces per-unit pricing power. Every buyer knows there are [N-1] more behind the one they're looking at. Recommend lot sale pricing."
**Valuation impact:** Per-unit FMV should be reduced 10-25% vs. single-unit pricing. Lot sale at 60-75% of aggregate individual pricing.

### Rule: Cross-Border (US to Canada)
**Trigger:** Equipment located in US with likely Canadian buyer pool
**Disclosure:** Include cross-border cost breakdown:
- Transport: $5,000-$15,000 per load depending on size and distance
- ASME → ABSA re-registration: $2,000-$5,000 per pressure vessel
- Customs/brokerage: $500-$1,500
- Currency friction: note CAD/USD rate
**Valuation impact:** Reduce FMV 10-15% vs. equivalent Alberta-located equipment.

### Rule: Integral Compressor Market Decline
**Trigger:** Ajax, Cooper-Bessemer, or other integral slow-speed compressor
**Disclosure:** "Integral slow-speed compressors have declined in market preference relative to separable high-speed units (Ariel, Gemini). The buyer pool is narrower and shrinking."
**Valuation impact:** Apply additional 10-15% discount vs. separable compressor at equivalent HP.

### Rule: Uncommon Frame/Manufacturer
**Trigger:** Compressor frame not in the top 5 (Ariel, Gemini/Dresser-Rand, Frick) or engine not CAT/Waukesha
**Disclosure:** "Parts sourcing for [manufacturer] [model] is harder than for mainstream brands (Ariel, CAT, Waukesha). This reduces buyer confidence and may extend the sales cycle."
**Valuation impact:** Apply 5-10% discount vs. equivalent mainstream brand.

## Registration and Documentation

### Rule: ABSA/CRN Unknown
**Trigger:** Pressure equipment where ABSA/CRN status is not confirmed
**Disclosure:** "ABSA registration status and data sheet availability have not been confirmed. Registered equipment with current data sheets commands a 10% premium. Equipment without documentation may require re-certification at the buyer's expense, reducing effective value by 10-15%."

### Rule: No Data Sheets
**Trigger:** Any equipment where data sheets / spec sheets are not provided
**Disclosure:** "No data sheets or specification documentation provided. This increases buyer risk and reduces value. Recommend obtaining original data sheets if available."
**Valuation impact:** Apply -15% penalty.

## Sour Service / NACE

### Rule: NACE Premium
**Trigger:** Equipment confirmed NACE MR0175 rated
**Disclosure:** "NACE MR0175 sour service rated materials and certification. This commands a premium in the WCSB market where H₂S-containing gas streams are common, particularly in Montney and Duvernay plays."
**Valuation impact:** Apply +15% premium (standard sour) or +25% (high H₂S >10%).

### Rule: NACE Certification Verification
**Trigger:** Equipment claimed as NACE/sour rated but no MTRs or certification docs provided
**Disclosure:** "Sour service rating claimed but material test reports (MTRs) and NACE certification documents not provided. A buyer will require these documents to validate the sour service rating."
