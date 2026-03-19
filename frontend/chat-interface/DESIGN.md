# Design System: High-End Industrial Intelligence
**Project ID:** 3649376482605941391

## 1. Overview & Creative North Star: "The Digital Surveyor"
This design system rejects the "standard dashboard" aesthetic in favor of a bespoke, high-end editorial experience tailored for the oil and gas sector. Our Creative North Star is **The Digital Surveyor**: an interface that feels like a precision instrument—authoritative, translucent, and deeply layered. 

We move beyond the "flat web" by utilizing **Atmospheric Depth**. Instead of rigid grids and heavy borders, we use light-refracting surfaces (Glassmorphism) and intentional asymmetry. The layout should feel like data floating over a vast, dark horizon, where the most critical information—pricing and market shifts—glows with internal warmth.

---

## 2. Colors & Surface Architecture
The palette is built on a "Deep Sea" foundation with high-contrast, thermal-inspired accents.

### Core Canvas
- **Primary Canvas:** A radial gradient from `center: #001628` to `edges: #000F1C`. This creates a natural vignette that pulls the user’s eye toward the center of the interaction.

### The Surface Hierarchy
- **The "No-Line" Rule:** 1px solid borders are strictly prohibited for sectioning. Use background shifts to define boundaries.
- **Nesting Logic:** 
    - **Base:** `surface` (#041522)
    - **Floating Workspaces:** `surface_container_low` (#0C1D2A)
    - **Active Cards:** `surface_container_highest` (#263645)
- **The Glass & Gradient Rule:** All primary interaction cards must use a custom glass treatment: `background: rgba(255, 255, 255, 0.04)` with a `backdrop-filter: blur(12px)`. This "frosted" effect integrates the UI into the background gradient rather than sitting "on top" of it.

### Accents & Typography Tones
- **Hero CTA:** `primary_container` (#DA7A0A). Use subtle linear gradients (Primary to Primary-Fixed) to give buttons a "machined metal" luster.
- **Secondary/Links:** `secondary` (#4ADBD5). Use for precision labels and navigational cues.
- **Primary Text:** `on_surface` (#D3E4F7) or Warm Cream (#F2E9E1) for high-end readability.
- **Secondary Text:** `on_tertiary_fixed_variant` (#224E49) / Teal-tinted (#A8D5CF) for metadata.

---

### 3. Typography: The Editorial Scale
We mix technical precision with aggressive headline scales to create an "Industrial Journal" feel.

- **Display & Headlines (Space Grotesk):** Use for market headers and equipment names. Space Grotesk’s geometric quirks feel engineered and modern. 
    - *Style:* Tighten letter-spacing by -2% for `display-lg` to create a compact, premium "masthead" look.
- **Body (Inter/DM Sans):** Use for chat transcripts and equipment specifications. Inter provides maximum legibility at `body-md` (0.875rem) for dense pricing data.
- **Data & Metrics (JetBrains Mono):** **Mandatory** for all currency, quantities, and serial numbers. The monospace nature ensures that columns of numbers align perfectly, conveying mechanical accuracy.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are too "soft" for this industry. We use light and opacity to define height.

- **The Layering Principle:** Depth is achieved by "stacking." A `surface_container_lowest` (#00101D) chat input area should sit inside a `surface_container_low` (#0C1D2A) sidebar. This creates a "recessed" look without using an inner shadow.
- **Ambient Glow:** For floating modals, use a shadow with `blur: 40px`, `spread: -10px`, and `color: rgba(0, 182, 177, 0.08)` (Teal tint). This mimics the light refraction from the frosted glass.
- **The Ghost Border:** If a boundary is required for accessibility, use `outline_variant` at **15% opacity**. It should be felt, not seen.

---

## 5. Components

### Buttons & Interaction
- **Primary Action:** `primary_container` (#DA7A0A) background. Use `xl` (0.75rem) roundedness. No border. On hover, increase the `backdrop-filter: brightness(1.2)`.
- **Secondary (Teal):** Ghost style. Transparent background with a `Ghost Border` and `secondary` (#4ADBD5) text.

### High-Precision Chips
- **Confidence Indicators:**
    - **High:** `green` (#4CAF50) text on 10% opacity green background.
    - **Medium:** `amber` (#FF9800) text on 10% opacity amber background.
    - **Low:** `red` (#F44336) text on 10% opacity red background.
- **Style:** Use `JetBrains Mono` for the text inside chips to emphasize the data-driven nature of the confidence score.

### Input Fields (Chat & Search)
- **The "Recessed" Input:** Use `surface_container_lowest` with a `0.2rem` (scale 1) padding-top to create a "sunken" feel. 
- **Focus State:** Instead of a border, use a `1px` outer glow of `primary` (#FFB77B) with 40% opacity.

### Data Cards & Lists
- **Prohibition:** Divider lines are forbidden. Use `spacing-6` (1.3rem) of vertical whitespace to separate equipment line items.
- **Micro-interactions:** On hover, a card’s background should transition from `rgba(255, 255, 255, 0.04)` to `rgba(255, 255, 255, 0.08)`.

---

## 6. Do’s and Don’ts

### Do:
- **Use Intentional Asymmetry:** In the chat interface, let the data cards have slightly different widths or staggered entry animations to feel "bespoke."
- **Embrace White Space:** Use the Spacing Scale (specifically `8` through `16`) to let complex oilfield data "breathe."
- **Mix Typefaces:** Use `JetBrains Mono` specifically for prices ($) and `Space Grotesk` for labels in the same line.

### Don’t:
- **Don’t use Solid Borders:** Never use a 100% opaque border to separate the sidebar from the chat. Use the transition from `surface_dim` to `surface_container_low`.
- **Don’t use Standard Greys:** Every "neutral" in this system is tinted with blue or teal. Pure `#333333` or `#CCCCCC` will break the atmospheric immersion.
- **Don’t use Sharp Corners:** Stick to the `md` (0.375rem) or `lg` (0.5rem) roundedness scale to keep the "Glass" feeling organic rather than aggressive.
