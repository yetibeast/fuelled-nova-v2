"""Merge public-web research findings into the supply-targets workbook.

Takes the latest export and produces an enriched copy:
- New columns on the Sellers sheet for owner/broker classification, location,
  industry, parent, disposition context, direct contact path, confidence
- New 'Research Notes' sheet with full narrative per seller + sources
- New 'LS Managers' sheet with the human-research on the 4 Liquidity Services reps

Research data (2026-05-08) is embedded below — gathered from public web only,
no paid databases. Re-run this script after any new research pass.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


HEADER_FILL = PatternFill("solid", fgColor="EF5D28")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def write_header(ws, headers: list[str]) -> None:
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.freeze_panes = "A2"


def autosize(ws, max_width: int = 60) -> None:
    for col_idx, col in enumerate(ws.columns, start=1):
        try:
            length = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        except ValueError:
            length = 10
        ws.column_dimensions[get_column_letter(col_idx)].width = min(length + 2, max_width)


# -----------------------------------------------------------------------------
# Research data — keyed by exact 'Seller' column value from the workbook.
# Add entries here as new research lands; missing sellers stay blank in the output.
# -----------------------------------------------------------------------------

RESEARCH: dict[str, dict] = {
    # ---- South Africa mining cluster (Liversage's portfolio) ----
    "Assmang Cato Ridge Works": {
        "owner_class": "asset owner",
        "industry": "Ferromanganese smelter",
        "location": "Cato Ridge, KwaZulu-Natal, South Africa",
        "parent": "Assmang Pty Ltd (JV: Assore + ARM)",
        "disposition": "Permanent closure announced July 2025. Plant ceased 31 Aug 2025; ~600 jobs lost. Land sold to Assore PropCo for R453m for redevelopment. Equipment is being cleared, not idled.",
        "direct_contact": "Assore (parent): assore.com/contact-us | ARM: arm.co.za/contact-us | For asset disposition: Assore PropCo team handling the site redevelopment",
        "confidence": "confirmed",
        "notes": "Highest-priority warm lead. Real closure, real equipment moving. Bypass LS via Assore.",
    },
    "Assmang Khumani Iron Ore Mine": {
        "owner_class": "asset owner",
        "industry": "Iron ore surface mine (~14 Mtpa hematite)",
        "location": "30 km south of Kathu, Northern Cape, South Africa",
        "parent": "Assmang Pty Ltd (JV: Assore + ARM)",
        "disposition": "Khumani still producing, but iron-ore portfolio contracting. Sister mine Beeshoek placed on care & maintenance Nov 2025 after AMSA halted offtake. Listings likely fleet renewal + Beeshoek wind-down spillover.",
        "direct_contact": "assmang.co.za | ARM Ferrous: arm.co.za/b/ferrous.php | Procurement via Assore",
        "confidence": "confirmed",
        "notes": "",
    },
    "Glencore Operations South Africa (Pty) Ltd": {
        "owner_class": "asset owner",
        "industry": "Ferrochrome smelting + vanadium + thermal coal",
        "location": "Multiple SA sites: Rustenburg/Boshoek/Wonderkop/Lion smelters; Mpumalanga coal; Rhovan vanadium",
        "parent": "Glencore plc (LSE: GLEN)",
        "disposition": "Boshoek + Wonderkop indefinitely suspended May–June 2025. Rustenburg idled through 2024. S189 retrenchments at SA ferrochrome + vanadium ops Sept 2025. H1 2025 ferrochrome production down 28% YoY. $378m SA coal impairment 2025. Real surplus, not flips.",
        "direct_contact": "glencore.com/south-africa (Johannesburg HQ) | Glencore Merafe Chrome Venture procurement | JV partner Merafe (JSE-listed): merafe.co.za",
        "confidence": "confirmed",
        "notes": "",
    },
    "Northam Booysendal Platinum": {
        "owner_class": "asset owner",
        "industry": "PGM underground mine (4E concentrate)",
        "location": "Limpopo / Mpumalanga border, ~35 km west of Mashishing",
        "parent": "Northam Platinum Holdings Ltd (JSE: NPH)",
        "disposition": "Booysendal South (BSM) suspended 2024–25 while North module (BNM) ramped to ~50,000 oz/y. Surplus = development equipment from completed BNM ramp + BSM suspension.",
        "direct_contact": "northam.co.za/contact (Hyde Park, Johannesburg) | CEO Paul Dunne; CFO Alet Coetzee; IR Memory Johnstone",
        "confidence": "likely",
        "notes": "",
    },
    "MHI Power ZAF (Pty) Ltd": {
        "owner_class": "asset owner",
        "industry": "Coal-fired power-plant boilers (Medupi + Kusile, 800 MW units)",
        "location": "Sandton HQ; equipment likely staged at Medupi (Lephalale, Limpopo) and Kusile (eMalahleni, Mpumalanga) sites",
        "parent": "Mitsubishi Heavy Industries Ltd (TSE: 7011)",
        "disposition": "Medupi + Kusile boiler scopes at end-of-construction. With Eskom's last Kusile units commissioning, MHI winding down site activity — surplus is construction inventory, spares overstock, tooling.",
        "direct_contact": "power.mhi.com/regions/afr/company (Mitsubishi Power Africa, Sandton) | Contact form on power.mhi.com/regions/afr",
        "confidence": "likely",
        "notes": "",
    },
    "ArcelorMittal South Africa  (AMSA)": {  # double-space in seller name preserved
        "owner_class": "asset owner",
        "industry": "Integrated steelmaking — long products + flats",
        "location": "Newcastle (KZN), Vereeniging (Gauteng), Vanderbijlpark, Saldanha",
        "parent": "ArcelorMittal SA (Luxembourg; NYSE: MT)",
        "disposition": "Long Steel Business wind-down confirmed Jan 2025 (Newcastle, Vereeniging) — ~3,500 direct jobs. IDC R1.683bn facility deferred closure to Aug 2025. S189 retrenchment notices began Sept 2025. Auction lots = real, ongoing wind-down. High-quality steelworks equipment.",
        "direct_contact": "arcelormittalsa.com (Vanderbijlpark HQ) | CEO Kobus Verster; IR Tinus Brits | Procurement: arcelormittalsa.com/Procurement",
        "confidence": "confirmed",
        "notes": "Highest-priority warm lead alongside Cato Ridge.",
    },
    "Black Mountain Mining (Pty) Ltd": {
        "owner_class": "asset owner",
        "industry": "Underground zinc/lead/copper + open-pit zinc (Gamsberg)",
        "location": "Aggeneys, Northern Cape, South Africa",
        "parent": "Vedanta Zinc International (Vedanta 69.6% / Exxaro 24.4% / ESOP 6%)",
        "disposition": "Active operations + Gamsberg Phase II expansion (approved March 2022, doubling capacity to 8.5 Mtpa). Single-listing surplus = routine fleet turnover during expansion, not closure.",
        "direct_contact": "vedanta-zincinternational.com/contact-us | aggeneys.com/business/black-mountain-mining | Exxaro alternate route: exxaro.com",
        "confidence": "confirmed",
        "notes": "Lower priority — active mine, just fleet rotation.",
    },
    "SARS": {
        "owner_class": "broker (state agency)",
        "industry": "Mixed seized/forfeited goods (industrial, automotive, agricultural, consumer)",
        "location": "SARS State Warehouses across SA (Cape Town, Durban, JNB/OR Tambo, Beit Bridge)",
        "parent": "South African Revenue Service",
        "disposition": "Routine auctioning of seized/forfeited/unclaimed goods to recover duty + storage costs. AllSurplus is SARS's appointed online auction partner. Original asset owners are unknown third parties.",
        "direct_contact": "sars.gov.za/customs-and-excise/state-warehouses — auction channel IS the disposal channel; no corporate backchannel exists",
        "confidence": "confirmed",
        "notes": "Skip for direct outreach — there is no underlying owner to bypass to.",
    },

    # ---- US oil & gas / refining / utilities cluster (Hernandez + others) ----
    "ConocoPhillips – Permian": {
        "owner_class": "asset owner",
        "industry": "Upstream oil & gas (unconventional shale)",
        "location": "Permian/Delaware Basin, West Texas + New Mexico (likely Midland/Odessa staging)",
        "parent": "ConocoPhillips (NYSE: COP)",
        "disposition": "Active $5B non-core divestiture program post-Marathon merger (closed late 2024). Closed $3.2B in asset sales in 2025. Feb 2026 began exploring ~$2B Delaware Basin sale. Field-level surplus consistent with portfolio rationalization.",
        "direct_contact": "ConocoPhillips Procurement / Supply Chain (925 N. Eldridge Pkwy, Houston) — Investment Recovery falls under SCM. LinkedIn: 'ConocoPhillips Investment Recovery' / 'Surplus Materials' or Permian BU SCM leads in Midland, TX.",
        "confidence": "likely",
        "notes": "Strong warm lead — multi-year divestiture in progress.",
    },
    "Pemex Deer Park": {
        "owner_class": "asset owner",
        "industry": "Petrochemical refinery (340 kbd crude)",
        "location": "Deer Park, TX (Houston Ship Channel) — 5900 Hwy 225",
        "parent": "Petróleos Mexicanos (Pemex)",
        "disposition": "Major maintenance overhaul began 2025 (~$500M+) on largest CDU + several other units. Surplus = turnaround / replace-in-kind, not closure. Pemex investing, not divesting.",
        "direct_contact": "pemex.com/deerpark/en — corporate switchboard (713) 246-7000 | LinkedIn: Pemex Deer Park company page → search Procurement / SCM Manager",
        "confidence": "confirmed",
        "notes": "",
    },
    "Central Valley Renewables (CVRF)": {
        "owner_class": "asset owner",
        "industry": "Renewable diesel refining (~250 MMgal/yr)",
        "location": "Bakersfield, Kern County, CA (former Big West / Alon refinery site)",
        "parent": "Grapevine Energy Holdings, LLC (post-Apr 2025 Ch.11; senior lenders led by OIC + CTCI; was Global Clean Energy Holdings)",
        "disposition": "Project hit $950M EPC dispute with CTCI, 3+ year delays, ExxonMobil exited as offtake. Commercial ops achieved Dec 2024. Restructured 2025 with Vitol as new offtake. Surplus likely from EPC closeout / construction overage / spec'd-out spares.",
        "direct_contact": "cvrenewables.com (Bakersfield site) | Grapevine Energy Holdings (Houston, post-restructuring) | DPSI was EPC services partner",
        "confidence": "confirmed",
        "notes": "Highest-urgency target. Just-restructured single-site operator with EPC-dispute surplus. Small org footprint = direct outreach lands.",
    },
    "Flint Hills Resources Pine Bend, LLC": {
        "owner_class": "asset owner",
        "industry": "Petroleum refining (heavy/sour Canadian crude)",
        "location": "Rosemount / Inver Grove Heights, MN (Twin Cities)",
        "parent": "Koch Industries → Flint Hills Resources, LP",
        "disposition": "No public divestiture announced. Remains FHR's flagship MN refinery. Single AllSurplus listing = routine investment-recovery / capital project surplus.",
        "direct_contact": "fhr.com (Wichita HQ) | pinebendrefinery.com | LinkedIn: 'Flint Hills Resources' + 'Materials Management' / 'Investment Recovery'",
        "confidence": "confirmed",
        "notes": "Lower priority — no closure event.",
    },
    "Valaris - US (SM)": {
        "owner_class": "asset owner",
        "industry": "Offshore drilling (jackups + semisubs)",
        "location": "US Gulf of Mexico stacking yards (Houston / Ingleside / Sabine Pass area)",
        "parent": "Valaris plc (NYSE: VAL) — emerged from Ch.11 Apr 2021",
        "disposition": "Feb 2025 Fleet Rationalization — retiring semisubs DPS-3, DPS-5, DPS-6 (scrap or repurpose) + sold jackup VALARIS 75 for $24M after 5 yrs stacked. Listings = rig dismantlement / cold-stack offload. $4B+ contract backlog = high-grading the fleet.",
        "direct_contact": "valaris.com (5847 San Felipe St #3300, Houston) — +1 713-979-4200 | LinkedIn: Valaris → Supply Chain / Investment Recovery / Asset Manager",
        "confidence": "confirmed",
        "notes": "Strong warm lead — active rig dismantlement.",
    },
    "Entergy Services, Inc.": {
        "owner_class": "asset owner",
        "industry": "Electric utility (Gulf states regulated)",
        "location": "MS/LA/AR/TX service territory; corporate The Woodlands TX / New Orleans LA",
        "parent": "Entergy Corporation (NYSE: ETR)",
        "disposition": "In-house Investment Recovery program. Baxter Wilson steam plant (Vicksburg MS) retired 2018-22, demolished Dec 2025. Site to host new Vicksburg Advanced Power Station gas plant by 2028. Coal-to-gas transition driving plant-retirement surplus.",
        "direct_contact": "entergy.com/operations/investment-recovery — public IR contact form | Fleet via JJ Kane | Aucto seller page: aucto.com/marketplace/seller/entergy/2510",
        "confidence": "confirmed",
        "notes": "Public IR page — easiest direct contact of all the US sellers.",
    },
    "CenterPoint Energy": {
        "owner_class": "asset owner",
        "industry": "Gas LDC + electric T&D utility",
        "location": "Houston, TX HQ; Greater Houston gas/electric territory + IN/MN/OH",
        "parent": "CenterPoint Energy, Inc. (NYSE: CNP)",
        "disposition": "Active modernization cycle (post-Beryl resilience build-out + rate-case capex). 300 mi pipe replaced + 175k new meters in 2023-24. Divested OH gas business to National Fuel Gas for $2.62B (2025). Surplus is steady byproduct of capex cycle.",
        "direct_contact": "surplus.centerpointenergy.com (PRIMARY — dedicated public surplus portal) | corp procurement: 1111 Louisiana St, Houston | centerpointenergy.com/business/about-us/suppliers",
        "confidence": "confirmed",
        "notes": "Public surplus portal already exists. Easiest direct route.",
    },
    "Archer Daniels Midland Company": {
        "owner_class": "asset owner",
        "industry": "Ag processing — soybean crush, cottonseed crush, soy protein, ethanol",
        "location": "Likely one of: Bushnell IL (soy protein, closing); Kershaw SC (soy, closing 2025); Memphis TN (cottonseed, closing Jan 2026)",
        "parent": "Archer-Daniels-Midland Co. (NYSE: ADM)",
        "disposition": "$500-700M cost-cutting program over 3-5 years; up to 700 job cuts. Closing Bushnell IL soy protein, Kershaw SC soybean plant, Memphis TN cottonseed (Jan 2026, 95 layoffs). Memphis JV with Planters Cotton Oil (Pine Bluff AR refinery stays). Surplus tracks footprint rationalization.",
        "direct_contact": "ADM Corporate Procurement / Investment Recovery (77 W. Wacker Dr, Chicago) | adm.com/en-us/suppliers | Site-level: closing-plant managers in Bushnell/Kershaw/Memphis",
        "confidence": "confirmed",
        "notes": "Three plant closures = three direct routes.",
    },

    # ---- Mystery / LS-managed codes ----
    "Seller 23609 - ANCO": {
        "owner_class": "asset owner (CONFIRMED via lot-data triangulation)",
        "industry": "Heavy-civil road construction (asphalt paving, aggregate, dump fleet)",
        "location": "Lake City FL HQ; FL plants at Old Town, Quincy, Marianna, Sumterville; TX yards at Robstown, Weslaco, Corpus Christi (post-2022 Haas-Anderson acquisition), New Braunfels (Tejas Quarry, 2016); GA aggregate ops",
        "parent": "Anderson Columbia Co., Inc. (ACCI) — privately held",
        "disposition": "FLEET ROTATION, not bankruptcy. ACCI is an active operator running a multi-yard equipment-cycling program. The 'ANCO' 5-letter code maps directly to ANderson COlumbia. Asset mix (asphalt paver, asphalt distributor, asphalt-plant drag elevator, McLanahan screen, water trucks, dump trucks, rollers, broom) is a textbook ACCI heavy-civil fleet. ACCI is a documented McLanahan customer; one of the listings is a McLanahan 616TD screen.",
        "direct_contact": "andersoncolumbia.com — Lake City FL HQ. Active operator; corporate procurement / equipment manager is the right route. Recurring dispo channel = relationship play, not one-time auction.",
        "confidence": "confirmed",
        "notes": "BIGGEST WIN of the unmasking pass. 23 listings, was the largest unidentified seller on AllSurplus. ACCI is a recurring fleet rotation, so ongoing buy-side relationship is feasible — not just chasing one auction.",
    },
    "Seller 26812 - ELGLRTNIC": {
        "owner_class": "LS-managed code",
        "industry": "Unknown — only 4 listings",
        "location": "Unknown",
        "parent": "Liquidity Services CAG",
        "disposition": "LS internal code (matches naming/numbering pattern of confirmed LS terms pages in the 19k–28k range).",
        "direct_contact": "Liquidity Services CAG",
        "confidence": "likely",
        "notes": "",
    },
    "Seller 19807 - ASFL": {
        "owner_class": "LS-managed code (CONFIRMED)",
        "industry": "Oilfield (likely)",
        "location": "Unknown — likely Texas-based",
        "parent": "Liquidity Services (T&C page reads 'Liquidity Services – ASFL')",
        "disposition": "Explicitly hosted under 'Liquidity Services –' branding on the AllSurplus T&C page. Underlying client name obfuscated by LS standard practice. Plausible expansion 'Absolute Oil Field Services LLC' (Eagle Ford roustabout) — unverified.",
        "direct_contact": "Liquidity Services CAG — liquidityservices.com/energy-surplus-asset-sales",
        "confidence": "confirmed (LS managed); unverified (underlying entity)",
        "notes": "The smoking gun confirming the LS-code pattern.",
    },
    "Seller 21141 - RELLC": {
        "owner_class": "LS-managed code",
        "industry": "Unknown — only 1 listing",
        "location": "Unknown",
        "parent": "Liquidity Services CAG",
        "disposition": "LS internal code (5-letter acronym ending in 'LLC' suffix collapsed — parallels SBLLC, TKEPTSSLC, VOYMSLC).",
        "direct_contact": "Liquidity Services CAG",
        "confidence": "likely",
        "notes": "",
    },
    "Seller 31459 - AWCTL": {
        "owner_class": "LS-managed code",
        "industry": "Unknown",
        "location": "Unknown",
        "parent": "Liquidity Services CAG",
        "disposition": "Possibly LS code in 31k seller-ID band (newer than ASFL). Plausible expansions: 'Atlantic / American [Water/Well/Wireline] [Co/Tools] Ltd' — none verifiable. Not in TX/DE/OK public registries.",
        "direct_contact": "Liquidity Services CAG (presumed)",
        "confidence": "unverified",
        "notes": "",
    },
    "Global Power Products, LLC": {
        "owner_class": "ambiguous",
        "industry": "Power generation / electrical (residential transfer switches + metering for the GA candidate)",
        "location": "Lawrenceville GA (225 Arnold Rd, 30044) OR Scottsdale AZ (7645 E. Evans Rd #140, 85260)",
        "parent": "Two candidates: Global Power Products, Inc. (Lawrenceville GA — submetering / GenerLink) OR Global Power Products LLC (Scottsdale AZ entity #L20583660). Worldwide Power Products (Houston) is a separate frequently-confused company.",
        "disposition": "Single listing — likely one-off liquidation of demo/returned inventory.",
        "direct_contact": "globalpowerproducts.com (GA candidate) — info@globalpowerproducts.com / (800) 886-3837",
        "confidence": "unverified",
        "notes": "Need actual lot description from AllSurplus to disambiguate which 'Global Power Products' this is.",
    },
    "CV Supply LLC": {
        "owner_class": "asset owner (small)",
        "industry": "Oilfield supply / Eagle Ford South Texas",
        "location": "Pleasanton, TX 78064 (3180 2nd St)",
        "parent": "Standalone LLC (FMCSA USDOT #4196444 — 1 truck, 2 drivers)",
        "disposition": "Single-listing dispo via LS event-manager Ruth Hernandez. Sole-prop / very small LLC — not a portfolio remarketer.",
        "direct_contact": "3180 2nd St, Pleasanton TX 78064 (no website). Reach via LS Ruth Hernandez or directly at the Pleasanton yard.",
        "confidence": "confirmed (entity); likely (owner-not-broker)",
        "notes": "",
    },

    # ---- Government remarketers ----
    "State of California Department of Technology, CA": {
        "owner_class": "direct agency",
        "industry": "IT / data-center hardware",
        "location": "Rancho Cordova CA (3101 Gold Camp Dr) + Vacaville CA",
        "parent": "California Department of Technology (CDT)",
        "disposition": "Routine state IT lifecycle disposal under DGS Surplus Property and Reutilization (SPR) program. No special shutdown event.",
        "direct_contact": "cdt.ca.gov | DGS SPR (STD 152 / STD 158): dgs.ca.gov/OFAM",
        "confidence": "confirmed",
        "notes": "SKIP — IT/data-center only, not Fuelled-relevant.",
    },
    "Solaire Kapuskasing Solar, ON": {
        "owner_class": "asset owner (private/municipal-linked SPV)",
        "industry": "Solar PV (6 MW Kap Solar Park, commissioned 2014)",
        "location": "Kapuskasing, Ontario, Canada (49.375, -82.393); entity registered in Mississauga ON",
        "parent": "Énergie Kapuskasing Energy (municipally-owned utility holding co); operating entity per gem.wiki: 'New Ospvf 7 LP'",
        "disposition": "UNVERIFIED — Kap Solar Park listed as 'operating' on Global Energy Monitor. 4 listings could be (a) routine inverter swap (park is ~12 yrs old, common at year 10-12), (b) repowering, or (c) partial decom. Worth a phone call.",
        "direct_contact": "Town of Kapuskasing — 705-335-2341 / general@kapuskasing.ca | Énergie Kapuskasing Energy (parent)",
        "confidence": "likely (ownership); unverified (disposition reason)",
        "notes": "Investigate further — phone the town.",
    },
    "State of Washington Surplus Operations, WA": {
        "owner_class": "direct agency",
        "industry": "Mixed — fleet vehicles, electronics, office furniture; federal surplus channel can include heavier industrial gear",
        "location": "Washington State (Tumwater/Olympia + Eastern WA warehouses)",
        "parent": "Washington Department of Enterprise Services (DES)",
        "disposition": "Centralized state-wide surplus consolidation for all WA agencies + many local govts. Routine.",
        "direct_contact": "des.wa.gov/purchase/buy-surplus | Surplus@des.wa.gov / 360-407-2270 | AgencySurplusPurch@des.wa.gov / 360-407-2275",
        "confidence": "confirmed",
        "notes": "Multi-agency funnel — single contact point, federal surplus channel attached.",
    },
    "Factor X - Government Remarketing, CA": {
        "owner_class": "third-party remarketer (decom contractor)",
        "industry": "Facility decommissioning + capital-asset resale (HVAC, MEP, lab/process gear likely)",
        "location": "Gilroy, CA (20 Cohansey Avenue, 95020)",
        "parent": "Factor X (private company, est. 2008; MBE/EDWOSB/SDBA-certified)",
        "disposition": "Recurring decom contracts (not a one-off). Source assets from CA government facility decommissioning.",
        "direct_contact": "factorx.com — 408.842.9700 / info@FactorX.com | GovDeals storefront: govdeals.com/factorx",
        "confidence": "confirmed",
        "notes": "Pursue as channel partner. Decom feeds typically include generators, transformers, switchgear, chillers, compressors, pumps.",
    },
    "Municipal Asset Recovery of NE Ohio - Government Remarketing, OH": {
        "owner_class": "likely third-party remarketer",
        "industry": "Unknown",
        "location": "Northeast Ohio (Cleveland / Akron / Youngstown corridor)",
        "parent": "Unknown — no standalone website, LinkedIn, or BBB listing under this exact name",
        "disposition": "Unknown — only 1 listing",
        "direct_contact": "Reach via AllSurplus / Liquidity Services account team (no public corporate site)",
        "confidence": "unverified",
        "notes": "Too thin — 1 listing, no web footprint. Let it accumulate before acting.",
    },
    "Sierra Auction - PHXFLT": {
        "owner_class": "third-party auctioneer (LS-owned channel partner)",
        "industry": "Heavy fleet — trucks, refuse/dump/water trucks, street sweepers, buses, construction gear, generators",
        "location": "Phoenix AZ (3570 Grand Ave); statewide AZ consigners",
        "parent": "Sierra Auction Management Inc. (est. 1986); acquired by Liquidity Services 2023",
        "disposition": "PHXFLT = City of Phoenix Fleet (Sierra is sole auction outlet for City of Phoenix + many AZ govt/police agencies). Ongoing fleet rotation.",
        "direct_contact": "sierraauction.com — (602) 242-7121 | corporate parent now Liquidity Services",
        "confidence": "confirmed",
        "notes": "Pursue as channel — water trucks / dump trucks / construction gear regularly cross municipal fleet auctions.",
    },

    # ---- Smaller named sellers worth pursuing (from triage of the 38 deferred) ----
    "Columbus Fleet Management, OH": {
        "owner_class": "direct agency (HIGH Fuelled relevance)",
        "industry": "Municipal heavy fleet — excavators, scissor lifts, truck tractors, JLG/Genie aerial, Cat/International (confirmed via IronPlanet/GovPlanet listings)",
        "location": "City of Columbus, OH",
        "parent": "City of Columbus Fleet Management Division",
        "disposition": "Ongoing municipal fleet rotation. Auctions consigned through Ritchie/IronPlanet + GovDeals.",
        "direct_contact": "City of Columbus Fleet Management; ironplanet.com/city-of-columbus seller-info form. Ask AllSurplus rep for direct Fleet Management contact.",
        "confidence": "confirmed",
        "notes": "Standout in the smaller-seller triage. Wider catalog on IronPlanet shows excavators + aerial lifts — Fuelled wheelhouse. Worth direct outbound.",
    },
    "King County, WA": {
        "owner_class": "direct agency (HIGH Fuelled relevance)",
        "industry": "County heavy fleet — possibly construction/utility equipment alongside passenger fleet",
        "location": "Seattle, WA — warehouse at 707 S. Orcas St.",
        "parent": "King County Fleet Services (Department of Executive Services)",
        "disposition": "Launched new online surplus auction Oct 2025 — early relationship window.",
        "direct_contact": "Fleet Services warehouse 206-477-0889 | kingcounty.gov/en/dept/executive-services/transit-transportation-roads/fleet-services/surplus",
        "confidence": "confirmed",
        "notes": "New online auction launched Oct 2025 — early outbound timing.",
    },
    "Lake County, IL": {
        "owner_class": "direct agency (HIGH Fuelled relevance)",
        "industry": "Public-works fleet, landscape, municipal heavy equipment",
        "location": "Lake County, IL (north of Chicago)",
        "parent": "Lake County Purchasing Division",
        "disposition": "Live spring/fall auctions via Obenauf + GovDeals year-round.",
        "direct_contact": "Lake County Purchasing Division | lakecountyil.gov/5035/Surplus-Policy",
        "confidence": "confirmed",
        "notes": "",
    },
    "Clean Water Services, OR": {
        "owner_class": "direct agency (MEDIUM Fuelled relevance)",
        "industry": "Wastewater utility — pumps, blowers, motors, valves, service vehicles, possibly process equipment",
        "location": "Washington County, OR",
        "parent": "Clean Water Services (regional wastewater utility)",
        "disposition": "Routine wastewater-treatment-plant equipment rotation.",
        "direct_contact": "cleanwaterservices.org Procurement | bids/surplus on m.publicsurplus.com seller 'Clean Water Services'",
        "confidence": "confirmed",
        "notes": "Real wastewater utility, not parks dept. WWTPs dispose of pumps/blowers/motors over time. Worth a procurement-team intro.",
    },
    "North Baldwin Utilities, AL": {
        "owner_class": "direct agency (MEDIUM Fuelled relevance)",
        "industry": "Small municipal water/electric utility — possible transformers, line trucks, meters",
        "location": "Bay Minette area, AL",
        "parent": "North Baldwin Utilities",
        "disposition": "Unknown — only 1 listing.",
        "direct_contact": "northbaldwinutilities.com — General Manager / Operations",
        "confidence": "likely",
        "notes": "Only true utility on the smaller-seller list. Low volume but profile fits.",
    },
}


# Named contacts at the top warm-lead organizations — feeds a separate sheet.
# Each row is one person at one company. Confidence: verified / likely / pattern-derived.
NAMED_CONTACTS = [
    # CVRF / Grapevine Energy Holdings
    {"company": "Central Valley Renewables (CVRF)", "name": "Mariah Mandt, PE", "title": "VP / GM, Bakersfield Renewable Fuels",
     "linkedin": "https://www.linkedin.com/in/mariah-mandt-pe-22a33895/", "location": "Bakersfield CA",
     "email": "mariah.mandt@bkrenewablefuels.com", "confidence": "likely",
     "notes": "Site GM — owns physical asset decisions at the only operating Grapevine facility. Smallest org has no IR-specific role."},
    {"company": "Central Valley Renewables (CVRF)", "name": "Saket Adhatrao", "title": "DCS Controls Specialist / Operations",
     "linkedin": "https://www.linkedin.com/in/saket-adhatrao/", "location": "Bakersfield CA",
     "email": "saket.adhatrao@bkrenewablefuels.com", "confidence": "likely",
     "notes": "Active operations contact — useful warm node below GM level."},

    # Assmang / Cato Ridge
    {"company": "Assmang Cato Ridge Works", "name": "Devan Kannie", "title": "Manager, Production CRA & Laboratory (Alt Director, Cato Ridge Alloys Pty Ltd)",
     "linkedin": "https://www.linkedin.com/in/devan-kannie-23452aa1/", "location": "Cato Ridge / Durban, KZN, SA",
     "email": "devan.kannie@feralloys.co.za", "confidence": "verified",
     "notes": "Sits inside the actual Cato Ridge Alloys JV being decommissioned. Domain feralloys.co.za is the working ops domain."},
    {"company": "Assmang Cato Ridge Works", "name": "Bastiaan ('Tiaan') van Aswegen", "title": "Deputy CEO, Assore (Group Technical & Ops)",
     "linkedin": "no public match", "location": "Johannesburg, SA",
     "email": "tiaan.vanaswegen@assore.com", "confidence": "pattern-derived",
     "notes": "Group ops head — owns the PropCo land/property transfer that includes equipment disposal."},
    {"company": "Assmang Cato Ridge Works", "name": "Henk Gouws", "title": "Managing Director, Assore South Africa",
     "linkedin": "no public match", "location": "Johannesburg, SA",
     "email": "henk.gouws@assore.com", "confidence": "pattern-derived",
     "notes": "Runs the SA operating subsidiary that owns PropCo."},

    # ArcelorMittal SA
    {"company": "ArcelorMittal South Africa  (AMSA)", "name": "Travesh Ramkhelawan", "title": "Head of Strategic Projects and Properties",
     "linkedin": "https://www.linkedin.com/in/travesh-ramkhelawan-28195a57/", "location": "Vanderbijlpark, Gauteng",
     "email": "travesh.ramkhelawan@arcelormittal.com", "confidence": "verified",
     "notes": "Strongest IR-equivalent match. 'Strategic Projects and Properties' owns idle-site asset disposition at integrated steel mills."},
    {"company": "ArcelorMittal South Africa  (AMSA)", "name": "Werner Venter", "title": "General Manager, AMSA",
     "linkedin": "https://za.linkedin.com/in/werner-venter-00a56b76", "location": "Vanderbijlpark, Gauteng",
     "email": "werner.venter@arcelormittal.com", "confidence": "likely",
     "notes": "GM-level operations contact — practical decision authority on plant-level surplus during Long Steel wind-down."},

    # Glencore SA
    {"company": "Glencore Operations South Africa (Pty) Ltd", "name": "Japie Fullard", "title": "CEO, Glencore Alloys (Ferrochrome + Vanadium SA)",
     "linkedin": "no clean LinkedIn (see theofficialboard.com)", "location": "Rustenburg / Johannesburg, SA",
     "email": "japie.fullard@glencore.co.za", "confidence": "verified",
     "notes": "Public face of the smelter S189 process. Ultimate disposition decisions on suspended ferrochrome assets sit with him."},
    {"company": "Glencore Operations South Africa (Pty) Ltd", "name": "Christof Bester", "title": "GM, Rustenburg Smelter",
     "linkedin": "https://www.linkedin.com/in/christof-bester-246705106/", "location": "Rustenburg, North West, SA",
     "email": "christof.bester@glencore.co.za", "confidence": "likely",
     "notes": "Site-level GM at the largest impacted smelter."},

    # Valaris
    {"company": "Valaris - US (SM)", "name": "Jorge Lebrija", "title": "VP, Global Supply Chain",
     "linkedin": "https://www.linkedin.com/in/jorgelebrija/", "location": "Houston TX",
     "email": "jorge.lebrija@valaris.com", "confidence": "verified",
     "notes": "13-year tenure (joined Ensco 2013). Owns global procurement + asset/spares lifecycle for the rig fleet rationalization."},
    {"company": "Valaris - US (SM)", "name": "Chandler Breaux", "title": "Supply Chain / Materials, Valaris",
     "linkedin": "https://www.linkedin.com/in/chandler-breaux-07a4b246/", "location": "Houston TX area",
     "email": "chandler.breaux@valaris.com", "confidence": "likely",
     "notes": "Working-level entry point into the same supply-chain org."},

    # ConocoPhillips Permian
    {"company": "ConocoPhillips – Permian", "name": "Bryan Morris", "title": "Sr. Supply Chain Coordinator",
     "linkedin": "https://www.linkedin.com/in/bryan-morris-6a213021/", "location": "Midland TX",
     "email": "bryan.morris@conocophillips.com", "confidence": "likely",
     "notes": "Permian BU operational warm node — closest match to plant-side IR contact."},
    {"company": "ConocoPhillips – Permian", "name": "Justin Nolen", "title": "Supply Chain Specialist",
     "linkedin": "https://www.linkedin.com/in/justin-nolen-05660189/", "location": "Midland TX",
     "email": "justin.nolen@conocophillips.com", "confidence": "likely",
     "notes": "Second route into the Midland materials function."},

    # Pemex Deer Park
    {"company": "Pemex Deer Park", "name": "Joe Riley", "title": "Refinery Supply Chain Manager (also Maintenance Lead, DARP)",
     "linkedin": "https://www.linkedin.com/in/joe-riley-965b3842", "location": "Deer Park TX",
     "email": "joe.riley@deerparkrefining.com", "confidence": "verified",
     "notes": "Owns end-to-end procurement, contracts, warehousing & distribution at Deer Park. Direct surplus-equipment decision maker."},
    {"company": "Pemex Deer Park", "name": "Darren Anderson, C.P.M.", "title": "Procurement Manager — Data, Systems & Processes",
     "linkedin": "https://www.linkedin.com/in/darren-anderson-c-p-m-63972242/", "location": "Katy TX",
     "email": "darren.anderson@deerparkrefining.com", "confidence": "likely",
     "notes": "30 yrs O&G procurement, certified purchasing manager."},

    # ADM
    {"company": "Archer Daniels Midland Company", "name": "André Alves", "title": "Source-to-Pay Director (Global Process Owner: Inventory & Investment Recovery)",
     "linkedin": "https://www.linkedin.com/in/andr%C3%A9-alves-74935b25/", "location": "Decatur IL",
     "email": "andre.alves@adm.com", "confidence": "verified",
     "notes": "STRONGEST single target of all 10 warm leads. Explicit Investment Recovery mandate at corporate level. Owns Bushnell + Kershaw + Memphis closures."},
    {"company": "Archer Daniels Midland Company", "name": "Lynn Lee", "title": "ADM employee at Kershaw SC site",
     "linkedin": "https://www.linkedin.com/in/lynn-lee-38a2a49/", "location": "Kershaw SC",
     "email": "lynn.lee@adm.com", "confidence": "pattern-derived",
     "notes": "Local Kershaw site contact — only public LinkedIn hit at that closing facility."},

    # Entergy
    {"company": "Entergy Services, Inc.", "name": "Justin McCabe", "title": "Manager, Investment Recovery",
     "linkedin": "https://theorg.com/org/entergy/org-chart/justin-mccabe", "location": "New Orleans / Jackson MS",
     "email": "justin.mccabe@entergy.com", "confidence": "verified",
     "notes": "DIRECT HIT — explicit Investment Recovery Program Manager. Tenure since May 2015. Owns Baxter Wilson decom assets."},
    {"company": "Entergy Services, Inc.", "name": "Jason Rees", "title": "Director, Supply Chain Commercial Operations",
     "linkedin": "no clean LinkedIn", "location": "New Orleans LA",
     "email": "jason.rees@entergy.com", "confidence": "pattern-derived",
     "notes": "McCabe's reporting line — escalation contact."},

    # CenterPoint
    {"company": "CenterPoint Energy", "name": "Michael Brown, MCA", "title": "Manager, Asset Recovery & Supply Chain Sustainability",
     "linkedin": "https://www.linkedin.com/in/michael-brown-mca-2576578/", "location": "Katy / Houston TX",
     "email": "michael.brown@centerpointenergy.com", "confidence": "verified",
     "notes": "DIRECT HIT — exact title matches the function. MCA = Member Certified Appraiser (IR Association credential). Owns surplus.centerpointenergy.com."},
]


# Liquidity Services event managers (separate sheet — they're people, not sellers)
LS_MANAGERS = [
    {
        "name": "Ruth Hernandez",
        "email": "ruth.hernandez@liquidityservices.com",
        "phone": "713-590-1418 (Houston)",
        "linkedin": "https://www.linkedin.com/in/ruth-hernandez-14866239",
        "title": "Inside Sales Representative, Liquidity Services CAG",
        "region": "US — Houston-based; supports CAG energy/industrial events including ConocoPhillips Permian + Pemex Deer Park",
        "tenure": "unknown",
        "covers_events": "ConocoPhillips Permian, Pemex Deer Park, Central Valley Renewables, several anonymous US events",
        "notes": "Operational point of contact / event coordinator — NOT decision-maker on seller relationships. Treat as gatekeeper.",
        "confidence": "likely",
    },
    {
        "name": "Herman Liversage",
        "email": "herman.liversage@liquidityservices.com",
        "phone": "+27 (0)82 452 8811 (SA mobile)",
        "linkedin": "https://www.linkedin.com/in/herman-liversage-6a08009b/",
        "title": "Associate Director, Liquidity Services SA (Pty) Ltd",
        "region": "Sub-Saharan Africa — mining vertical; Pretoria-based",
        "tenure": "Long-tenured mining-industry insider. Prior: BGS Industrial Equipment, Privest Outsourcing, Durnacal Mine, Hillside Aluminium.",
        "covers_events": "Assmang Cato Ridge, Assmang Khumani, Glencore SA, Northam Booysendal, Black Mountain Mining, Dwarsrivier",
        "notes": "Senior operator at LS-SA, NOT a junior coordinator. The +27 82 mobile is direct. LS-SA team is small — reaching Herman ≈ reaching SA leadership. Pitch as peer-to-peer mining-equipment conversation, not BD pitch.",
        "confidence": "confirmed",
    },
    {
        "name": "Jeff Goddard",
        "email": "goddard@liquidityservices.com",
        "phone": "714-376-1422 (Orange County CA)",
        "linkedin": "https://www.linkedin.com/in/jeff-goddard-cea-34703857/",
        "title": "CAG Account Manager, Liquidity Services (CEA — Certified Equipment Appraiser, AMEA member)",
        "region": "Southern California / US West — UC Irvine alum",
        "tenure": "3+ years in CAG seat (FY22/23/24 quota numbers public on profile). Multi-year appraisal career.",
        "covers_events": "Three smaller anonymous events; verticals incl. Aviation Ground Support, Port Logistics, Electronics/Semi Mfg, govt accounts (GSA, SoCal Edison)",
        "notes": "Real account manager with appraisal credentials. Meaningful seller-side relationships. Worth a direct outreach. Pitch on equipment-data quality, NOT generic marketplace volume.",
        "confidence": "confirmed",
    },
    {
        "name": "Marcin Gadzinski",
        "email": "marcin.gadzinski@liquidityservices.com",
        "phone": "+49 162 491 87 93 (Germany)",
        "linkedin": "https://www.linkedin.com/in/marcin-gadzinski-889265136/",
        "title": "Sales / BD (no formal title disclosed publicly; headline reads marketing tagline)",
        "region": "Continental Europe — likely DACH + CEE under GoIndustry DoveBid / AllSurplus EU operation",
        "tenure": "~15 yrs multi-industry; LS tenure unknown",
        "covers_events": "At least one European event",
        "notes": "Weakest public footprint of the four. LS EU team is small post-GoIndustry-DoveBid integration. Treat as likely BD contact, but seniority unknown — could be senior account exec or mid-level rep.",
        "confidence": "likely",
    },
]


# Top-line insight blocks for a 'Summary' sheet at the front
SUMMARY_BLOCKS = [
    ("ANCO UNMASKED — Anderson Columbia Co., Inc. (CONFIRMED)",
     "The biggest seller on AllSurplus by volume (23 listings) was previously masked as 'Seller 23609 - ANCO.' "
     "Per-lot location triangulation confirms it as Anderson Columbia Co., Inc. (ACCI) — a privately-held heavy-civil road "
     "construction contractor HQ in Lake City FL with plants at Old Town/Quincy/Marianna FL, TX yards at Robstown/Weslaco/"
     "Corpus Christi (post-2022 Haas-Anderson acquisition) + New Braunfels (Tejas Quarry, 2016), and GA aggregate ops. "
     "Every FL location maps to a known ACCI plant; the asset mix (asphalt paver, asphalt distributor, McLanahan screen, "
     "asphalt-plant drag elevator, water trucks, dump trucks, rollers, broom) is textbook ACCI heavy-civil. ACCI is a "
     "documented McLanahan customer. Critically: this is a FLEET ROTATION, not a bankruptcy — meaning ACCI is a "
     "*recurring* dispo channel, suitable for an ongoing buy-side relationship rather than a one-time auction chase. "
     "The other four LS codes (ASFL, ELGLRTNIC, RELLC, AWCTL) have insufficient public fingerprint to identify."),
    ("LS-MANAGED CODES (4 still unidentified, 1 unmasked)",
     "ASFL, ELGLRTNIC, RELLC, AWCTL remain Liquidity Services internal program codes that mask the underlying client. "
     "ASFL is explicitly confirmed via the public AllSurplus T&C page ('Liquidity Services – ASFL'); the others match the "
     "same URL pattern. Each has too thin a fingerprint (1–4 listings) to triangulate without paid registry data. "
     "Playbook: treat LS CAG as a single channel relationship covering these + future LS-managed dispositions, OR wait "
     "for additional listings to accrue more lot-data fingerprint."),
    ("HIGHEST-PRIORITY DIRECT-OWNER WARM LEADS",
     "Real ongoing disposition events with identifiable corporate procurement: ArcelorMittal SA (Long Steel wind-down, "
     "Jan 2025), Assmang/ARM/Assore (Cato Ridge full closure Aug 2025 + Beeshoek care & maintenance Nov 2025), "
     "Glencore Operations SA (ferrochrome smelter suspensions May–June 2025), MHI Power ZAF (Medupi/Kusile end-of-construction), "
     "ConocoPhillips Permian ($5B post-Marathon divest), Pemex Deer Park ($500M+ turnaround), Valaris (Feb 2025 fleet "
     "rationalization), Entergy (active IR program + Baxter Wilson plant retirement), CenterPoint (dedicated public surplus "
     "portal), ADM (3 plant closures: Bushnell IL, Kershaw SC, Memphis TN), CVRF / Grapevine Energy (post-bankruptcy "
     "restart + EPC-dispute surplus — small org, fastest direct landing)."),
    ("LIQUIDITY SERVICES MANAGER HIERARCHY",
     "Herman Liversage = Associate Director, LS-SA (senior, deep mining network — peer-to-peer pitch). "
     "Jeff Goddard = CAG Account Manager + CEA (real BD with appraisal credentials — pitch on data quality). "
     "Ruth Hernandez = Inside Sales Rep (event coordinator / gatekeeper — not decision-maker). "
     "Marcin Gadzinski = EU sales/BD (thin public footprint, seniority unknown)."),
    ("CHANNEL-PARTNER OPPORTUNITIES (third-party remarketers)",
     "Factor X (CA decom contractor — info@factorx.com / 408.842.9700) and Sierra Auction (AZ municipal fleet, now "
     "LS-owned — sierraauction.com / 602-242-7121) are the two real channel-partner candidates. WA DES Surplus "
     "(Surplus@des.wa.gov / 360-407-2270) is the multi-agency direct-agency funnel. Skip CA Dept of Technology (IT only) "
     "and Municipal Asset Recovery NE Ohio (1 listing, no web footprint)."),
    ("INVESTIGATE",
     "Solaire Kapuskasing Solar — 4 listings from a 6 MW operating solar park is unusual. Could be inverter swap (year ~12, "
     "common), repowering, or partial decom. Phone the Town of Kapuskasing — 705-335-2341 / general@kapuskasing.ca."),
    ("NAMED CONTACTS NOW ON FILE (see 'Named Contacts (Direct)' tab)",
     "Public-web research surfaced 18 named humans across the 10 top warm leads — direct procurement / Investment "
     "Recovery / asset-disposition contacts that bypass Liquidity Services. STRONGEST hits (verified, exact-title match): "
     "Justin McCabe (Manager, Investment Recovery, Entergy), Michael Brown MCA (Manager, Asset Recovery & Supply Chain "
     "Sustainability, CenterPoint), André Alves (Source-to-Pay Director with explicit Investment Recovery mandate, ADM), "
     "Joe Riley (Refinery Supply Chain Manager, Pemex Deer Park), Jorge Lebrija (VP Global Supply Chain, Valaris), "
     "Devan Kannie (Production Manager at the Cato Ridge Alloys JV being decommissioned), Travesh Ramkhelawan (Head of "
     "Strategic Projects and Properties at AMSA — owns idle-site disposition). Emails are pattern-derived from public "
     "domain conventions; treat as untested but high-likelihood. These are the prioritized first calls."),
    ("SMALLER SELLERS WORTH PURSUING (after triage of 38 deferred)",
     "33 of 38 deferred sellers are SKIP (police/IT/schools/light fleet). 5 worth pursuing: Columbus Fleet Management OH "
     "(HIGH — excavators + aerial lifts on IronPlanet, Fuelled wheelhouse), King County WA (HIGH — county heavy fleet, "
     "new online auction launched Oct 2025), Lake County IL (HIGH — public-works fleet + landscape), Clean Water Services "
     "OR (MEDIUM — wastewater utility, pumps/blowers/motors), North Baldwin Utilities AL (MEDIUM — small water/electric "
     "utility, only true utility on the list)."),
]


# -----------------------------------------------------------------------------

ENRICH_HEADERS = [
    "Owner Class", "Industry", "Asset Location", "Parent / Group",
    "Disposition Context", "Direct Contact (bypass LS)", "Research Confidence", "Notes",
]


def enrich_sellers_sheet(ws) -> tuple[int, int]:
    """Append research columns to the Sellers sheet. Returns (matched, total)."""
    # Find the 'Seller' column index (1-based)
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    seller_col = headers.index("Seller") + 1

    # Append new headers
    start_col = ws.max_column + 1
    for offset, h in enumerate(ENRICH_HEADERS):
        cell = ws.cell(row=1, column=start_col + offset, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="left", vertical="center")

    matched = 0
    total = ws.max_row - 1
    for row_idx in range(2, ws.max_row + 1):
        seller = ws.cell(row=row_idx, column=seller_col).value
        if not seller:
            continue
        data = RESEARCH.get(seller)
        if not data:
            continue
        matched += 1
        for offset, key in enumerate([
            "owner_class", "industry", "location", "parent",
            "disposition", "direct_contact", "confidence", "notes",
        ]):
            ws.cell(row=row_idx, column=start_col + offset, value=data.get(key, ""))
    return matched, total


def write_summary_sheet(wb) -> None:
    ws = wb.create_sheet(title="Research Summary", index=0)
    write_header(ws, ["Topic", "Insight"])
    for topic, insight in SUMMARY_BLOCKS:
        ws.append([topic, insight])
        # Wrap the insight cell
        ws.cell(row=ws.max_row, column=2).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[ws.max_row].height = 90
    ws.column_dimensions["A"].width = 50
    ws.column_dimensions["B"].width = 130


def write_ls_managers_sheet(wb) -> None:
    ws = wb.create_sheet(title="LS Event Managers")
    headers = [
        "Name", "Email", "Phone", "LinkedIn", "Title", "Region", "Tenure",
        "Events Covered", "Notes for Outreach", "Confidence",
    ]
    write_header(ws, headers)
    for m in LS_MANAGERS:
        ws.append([
            m["name"], m["email"], m["phone"], m["linkedin"], m["title"],
            m["region"], m["tenure"], m["covers_events"], m["notes"], m["confidence"],
        ])
    autosize(ws, max_width=80)


def write_named_contacts_sheet(wb) -> None:
    ws = wb.create_sheet(title="Named Contacts (Direct)")
    headers = [
        "Company", "Name", "Title", "LinkedIn", "Location",
        "Email (likely)", "Confidence", "Outreach Notes",
    ]
    write_header(ws, headers)
    for c in NAMED_CONTACTS:
        ws.append([
            c["company"], c["name"], c["title"], c["linkedin"], c["location"],
            c["email"], c["confidence"], c["notes"],
        ])
    autosize(ws, max_width=80)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input workbook path")
    ap.add_argument("--out", default=None, help="Output workbook path (defaults to <input>_enriched.xlsx)")
    args = ap.parse_args(argv)

    in_path = Path(args.inp)
    if not in_path.exists():
        print(f"ERROR: input not found: {in_path}", file=sys.stderr)
        return 2

    out_path = Path(args.out) if args.out else in_path.with_name(in_path.stem + "_enriched.xlsx")

    wb = load_workbook(in_path)
    sellers_ws = wb["Sellers"]

    matched, total = enrich_sellers_sheet(sellers_ws)
    write_summary_sheet(wb)
    write_ls_managers_sheet(wb)
    write_named_contacts_sheet(wb)

    wb.save(out_path)
    print(f"\nWrote {out_path}")
    print(f"  Enriched: {matched} / {total} sellers")
    print(f"  Summary sheet: {len(SUMMARY_BLOCKS)} insight blocks")
    print(f"  LS Managers sheet: {len(LS_MANAGERS)} people")
    print(f"  Named Contacts sheet: {len(NAMED_CONTACTS)} people")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
