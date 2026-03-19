TOOLS = [
    {
        "name": "search_comparables",
        "description": "Search the Fuelled marketplace database for comparable equipment listings. Use this to find real asking prices for similar equipment. Keywords are OR'd together against listing titles.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Search terms to match against listing titles (OR'd together)"},
                "category": {"type": "string", "description": "Optional category filter (matches category_normalized column)"},
                "price_min": {"type": "number", "default": 0, "description": "Minimum asking_price filter"},
                "price_max": {"type": "number", "default": 99999999, "description": "Maximum asking_price filter"},
                "max_results": {"type": "integer", "default": 20, "description": "Max listings to return"},
            },
            "required": ["keywords"],
        },
    },
    {
        "name": "get_category_stats",
        "description": "Get aggregate pricing statistics for an equipment category. Returns count, average, min, and max asking_price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Equipment category to look up (matches category_normalized column)"},
            },
            "required": ["category"],
        },
    },
    {
        "name": "lookup_rcn",
        "description": "Look up Replacement Cost New (RCN) for equipment. Currently returns guidance to use RCN reference tables in system context. HP scaling: base × (target_hp / base_hp) ^ 0.6",
        "input_schema": {
            "type": "object",
            "properties": {
                "equipment_type": {"type": "string", "description": "Type of equipment (compressor, separator, etc.)"},
                "manufacturer": {"type": "string", "description": "Equipment manufacturer"},
                "model": {"type": "string", "description": "Model number/name"},
                "drive_type": {"type": "string", "description": "Drive type (electric, gas engine, integral, etc.)"},
                "stages": {"type": "integer", "description": "Number of compression stages"},
                "hp": {"type": "integer", "description": "Horsepower rating"},
            },
            "required": ["equipment_type"],
        },
    },
    {
        "name": "calculate_fmv",
        "description": "Calculate Fair Market Value using deterministic depreciation math. Applies age, condition, hours, service, and premium factors to RCN. Returns FMV range (low/mid/high), list price, and walk-away floor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rcn": {"type": "number", "description": "Replacement Cost New in CAD"},
                "equipment_class": {"type": "string", "enum": ["rotating", "static", "pump_jack", "electrical"], "description": "Equipment class for depreciation curve selection"},
                "age_years": {"type": "integer", "description": "Age of equipment in years"},
                "condition": {"type": "string", "enum": ["A", "B", "C", "D"], "default": "B", "description": "Condition grade: A=excellent, B=good, C=fair, D=poor"},
                "hours": {"type": "integer", "description": "Operating hours (affects rotating equipment only)"},
                "service": {"type": "string", "enum": ["sweet", "sour", "sour_high_h2s"], "default": "sweet", "description": "Service type"},
                "vfd_equipped": {"type": "boolean", "default": False, "description": "Has variable frequency drive (1.05x premium)"},
                "turnkey_package": {"type": "boolean", "default": False, "description": "Complete turnkey package (1.05x premium)"},
                "nace_rated": {"type": "boolean", "default": False, "description": "NACE MR0175 rated (1.15x premium)"},
            },
            "required": ["rcn", "equipment_class", "age_years"],
        },
    },
    {
        "name": "check_equipment_risks",
        "description": "Check for equipment-specific risk factors that affect valuation. Covers idle degradation, PLC obsolescence, cross-border costs, oversupply, stale listings, declining markets, and uncommon frames.",
        "input_schema": {
            "type": "object",
            "properties": {
                "equipment_type": {"type": "string", "description": "Type of equipment"},
                "age_years": {"type": "integer", "description": "Age in years"},
                "hours": {"type": "integer", "description": "Operating hours"},
                "idle_years": {"type": "integer", "description": "Years idle/not operated"},
                "drive_type": {"type": "string", "description": "Drive type (integral, electric, gas engine)"},
                "plc_model": {"type": "string", "description": "PLC controller model name"},
                "manufacturer": {"type": "string", "description": "Equipment manufacturer"},
                "location_country": {"type": "string", "default": "CA", "description": "ISO country code where equipment is located"},
                "identical_units": {"type": "integer", "default": 1, "description": "Number of identical units being sold together"},
                "days_on_market": {"type": "integer", "description": "Days the listing has been active"},
                "total_views": {"type": "integer", "description": "Total listing views"},
            },
            "required": ["equipment_type", "age_years"],
        },
    },
]
