# Design System Specification

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Industrial Observatory."** It is a high-precision, editorial-grade interface that feels like a mission control room for global intelligence. Rather than standard dashboard patterns, this system prioritizes atmospheric depth, high-contrast data visualization, and a sophisticated "glass-on-void" aesthetic.

We break the "template" look by utilizing intentional asymmetry, deep-canvas layering, and ultra-refined data typography. The interface should feel more like a piece of bespoke machinery than a website—heavy, professional, and uncompromisingly technical.

## 2. Colors
The palette is rooted in a deep-space navy, providing a high-contrast foundation for vibrant industrial signals.

*   **Primary Accent (`#EF5D28`):** Used exclusively for high-priority actions, primary brand elements, and critical alerts. It represents the "fuel" of the intelligence system.
*   **Secondary Highlight (Teal):** Used for data values, "Live" status indicators, and secondary navigation highlights. It provides a technical, digital contrast to the industrial orange.
*   **Neutral Canvas (`#05141F` to `#000F1C`):** The absolute foundation. It is not just "black," but a deeply saturated charcoal navy that creates the illusion of infinite depth.

### The "No-Line" Rule
Sectioning must never be achieved through 1px solid decorative lines. Boundaries are defined through:
1.  **Tonal Shifts:** Moving from `surface` to `surface-container-low`.
2.  **Atmospheric Blur:** Glass cards that naturally soften the background.
3.  **Strategic Negative Space:** Using the `Spacing Scale` (specifically `spacing-8` and `spacing-10`) to create structural separation.

### The Glass & Gradient Rule
To move beyond a "standard" flat UI, utilize **Glassmorphism** for all floating components and cards.
*   **Surface:** Use `surface-container` tiers with `0.6` to `0.8` opacity.
*   **Backdrop Blur:** Minimum `12px` to `20px` to create a "frosted slate" feel.
*   **Gradients:** Use subtle top-to-bottom gradients on cards (e.g., `surface-container-high` transitioning into `surface-container-low`) to simulate top-down ambient lighting.

## 3. Typography
The typography system is a dual-engine setup designed for an editorial/technical hybrid.

*   **Space Grotesk (Headers/Display):** Chosen for its geometric, slightly eccentric industrial character. It should be used at `display-lg` and `headline-md` levels with tight letter-spacing (`-0.02em`) to maintain an authoritative, editorial feel.
*   **JetBrains Mono (Data/Code):** Utilized for all quantitative values, status tags, and technical logs. This monospaced font ensures that data columns align perfectly and conveys a "raw intelligence" vibe.
*   **Inter (Body/Label):** The utility workhorse. Used for descriptive text and UI labels at `body-md` and `label-sm` to ensure maximum readability against the dark canvas.

## 4. Elevation & Depth
Depth is achieved through **Tonal Layering** rather than traditional drop shadows.

*   **The Layering Principle:** Treat the UI as a physical stack.
    *   **Layer 0 (Canvas):** `surface` (`#061520`).
    *   **Layer 1 (Main Content Area):** `surface-container-low`.
    *   **Layer 2 (Interactive Cards):** `surface-container-highest` with 15% opacity and a "Ghost Border."
*   **The Ghost Border:** For containers, use the `outline-variant` token at 8-10% opacity (`#FFFFFF14`). This creates a razor-sharp, fine-edged containment that mimics high-end glass hardware without the visual clutter of a solid border.
*   **Ambient Shadows:** If a card must "float" (e.g., a context menu), use an ultra-diffused shadow: `box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4)`. Avoid grey shadows; use black or a darker tint of the background color.

## 5. Components

### Cards
*   **Style:** `surface-container` background at 60% opacity, 20px backdrop-blur, and a `1px` Ghost Border.
*   **Separation:** Strictly forbid internal divider lines. Use `spacing-4` padding and background color shifts to group content.

### Buttons & Inputs
*   **Primary Action:** Solid `#EF5D28` background with `on-primary` text. No border. `radius-md`.
*   **Secondary Action:** Glass style. Transparent background with a `1px` border of `outline-variant` (20% opacity). On hover, increase opacity slightly.
*   **Chat/Search Input:** Deep glass trough. `surface-container-lowest` background with a subtle inner shadow to imply an "etched" look into the interface.

### Chips & Status Indicators
*   **Live Tags:** Teal text (`secondary`) on a low-opacity teal container. Use **JetBrains Mono** for the text to imply a real-time data feed.
*   **Roundedness:** Use `radius-full` for status pills to contrast against the `radius-md` of the structural cards.

### Data Bars & Visualizations
*   **Horizontal Bars:** Use a dual-tone approach. The "track" of the bar should be `surface-container-highest`. The "fill" should be a gradient of `secondary` to `secondary-container`.

## 6. Do's and Don'ts

### Do
*   **Do** use JetBrains Mono for anything that looks like a "reading" or "value."
*   **Do** leverage the full width of the canvas for asymmetric layouts—don't feel forced to center everything.
*   **Do** use the `0.5px` to `1px` Ghost Border on cards to catch the light, but keep the opacity very low.

### Don't
*   **Don't** use pure white (`#FFFFFF`) for body text. Use `on-surface` (`#d5e4f4`) to reduce eye strain and maintain the atmospheric mood.
*   **Don't** use standard "drop shadows" with small blur radii. It breaks the glass-immersion effect.
*   **Don't** use 100% opaque background colors for any component that sits on the main canvas. Transparency is the key to the system's sophistication.