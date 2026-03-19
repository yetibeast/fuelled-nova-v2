# Comparable Query Templates

These SQL templates run against the Fuelled Nova PostgreSQL database (fuelled-agent1).
Replace `{{VARIABLES}}` with actual values for each valuation.

## Query 1: Direct Match by Equipment Type + Keywords

```sql
SELECT id, title, canonical_manufacturer, canonical_model,
       category_normalized, price, currency, source_name,
       location, year, condition, hours, specs, url, scraped_at
FROM listings
WHERE category_normalized ILIKE ANY(ARRAY[
    '%{{CATEGORY_1}}%', '%{{CATEGORY_2}}%'
])
AND (
    title ILIKE '%{{KEYWORD_1}}%'
    OR title ILIKE '%{{KEYWORD_2}}%'
    OR title ILIKE '%{{MANUFACTURER}}%'
    OR title ILIKE '%{{MODEL}}%'
)
AND price IS NOT NULL
AND price > {{MIN_PRICE}}
ORDER BY scraped_at DESC
LIMIT 50;
```

**Variable guide:**
- CATEGORY: Use `category_normalized` values from `shared/categories.json` (e.g., 'pump', 'compressor', 'generator', 'separator')
- KEYWORDS: Equipment-specific terms (e.g., 'centrifugal', 'water%pump', 'transfer%pump', 'triplex', 'reciprocating')
- MANUFACTURER: OEM name (e.g., 'Pioneer', 'Cornell', 'Ariel', 'Caterpillar')
- MODEL: Model number (e.g., 'JGK', '3406', 'SC10B')
- MIN_PRICE: Filter out noise (typically $5,000-$20,000 depending on equipment class)

## Query 2: Broader Package Search with Drive Type

```sql
SELECT id, title, canonical_manufacturer, canonical_model,
       category_normalized, price, currency, source_name,
       location, year, condition, hours, specs, url, scraped_at
FROM listings
WHERE (
    title ILIKE '%{{EQUIPMENT_TYPE}}%package%'
    OR title ILIKE '%{{EQUIPMENT_TYPE}}%station%'
)
AND (
    title ILIKE '%electric%'
    OR title ILIKE '%motor%'
    OR title ILIKE '%vfd%'
    OR title ILIKE '%gas%engine%'
    OR title ILIKE '%{{HP_VALUE}}%hp%'
)
AND price IS NOT NULL
AND price > {{MIN_PRICE}}
ORDER BY price DESC
LIMIT 30;
```

## Query 3: Category Statistics

```sql
SELECT category_normalized,
       COUNT(*) as listing_count,
       AVG(price) as avg_price,
       MIN(price) as min_price,
       MAX(price) as max_price,
       COUNT(CASE WHEN price > {{THRESHOLD}} THEN 1 END) as above_threshold
FROM listings
WHERE category_normalized ILIKE '%{{CATEGORY}}%'
AND price IS NOT NULL
AND price > 5000
GROUP BY category_normalized
ORDER BY listing_count DESC;
```

## Query 4: HP Range from Specs JSONB

```sql
SELECT id, title, price, currency, source_name, location, year, hours,
       specs->>'horsepower' as hp,
       specs->>'drive_type' as drive_type,
       specs->>'motor' as motor,
       url
FROM listings
WHERE category_normalized ILIKE '%{{CATEGORY}}%'
AND (
    (specs->>'horsepower')::numeric BETWEEN {{HP_LOW}} AND {{HP_HIGH}}
    OR title ~ '({{HP_REGEX}})\s*[hH][pP]'
)
AND price IS NOT NULL
ORDER BY price DESC
LIMIT 30;
```

**HP_REGEX example:** For 500-800HP range, use `500|550|600|650|700|750|800`

## Query 5: Manufacturer-Specific Search

```sql
SELECT id, title, price, currency, source_name, location, year,
       hours, condition, url, scraped_at
FROM listings
WHERE (
    canonical_manufacturer ILIKE '%{{MANUFACTURER}}%'
    OR title ILIKE '%{{MANUFACTURER}}%'
)
AND category_normalized ILIKE '%{{CATEGORY}}%'
AND price IS NOT NULL
ORDER BY price DESC
LIMIT 20;
```

## Interpreting Results

### Strong comparables (confidence boost):
- Same manufacturer AND similar HP AND same service AND Alberta location
- Package configuration (not just bare equipment)
- Recent listing (within last 12 months)

### Moderate comparables (directional):
- Same equipment type, different manufacturer
- Similar HP, different service (water vs. gas)
- Bare equipment when we're valuing a package (validates one component)

### Weak comparables (context only):
- Different HP range (>2x difference)
- Different drive type without adjustment
- Different geography without freight adjustment
- Misclassified equipment (tractors in pump category, etc.)

### When comps are thin:
State this explicitly. It's normal for high-spec packages. Use language like:
> "The Fuelled database contains X listings in the [category] category, but no listings match the specific configuration of [full spec]. This is typical for high-specification industrial equipment, which generally trades through direct operator-to-operator negotiation or equipment brokers."
