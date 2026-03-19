# Nova V2 — Stitch UI Brief

## What This Is
A single-page equipment pricing chat interface for Fuelled Energy Marketing Inc. An operator (Harsh) types a question about oilfield equipment, gets back a professional valuation backed by real market data. That's the whole app.

## Design Direction
**Tone:** Quiet authority. This is a senior appraiser with perfect recall, not a chatbot. Professional, clean, not flashy. The data is the star.

**Theme:** Dark mode. Oilfield people work early mornings and late nights. Easy on the eyes.

**Palette:**
- Background: #0F1419 (near-black)
- Surfaces: #1A1F25 (cards, messages)
- Elevated: #242A32 (hover, active)
- Text primary: #E8E6E3 (warm white, not blue-white)
- Text secondary: #8B9098
- Text muted: #5C6370
- Accent: #C4834A (copper — professional without being corporate blue)
- Accent dark: #8B6038
- Borders: #2A3038
- Success: #4CAF50 (high confidence)
- Warning: #FF9800 (medium confidence)
- Danger: #F44336 (low confidence)

**Typography:**
- Display/headers: Space Grotesk
- Body: Inter
- Data/numbers: JetBrains Mono

## Layout — One Page

```
┌─────────────────────────────────────────────────────┐
│  Header: Logo + "Nova" + v2 badge + stats bar       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Scrollable conversation area                       │
│  Max-width ~880px, centered                         │
│                                                     │
│  [Welcome message]                                  │
│  [User message — right aligned]                     │
│  [Nova response — left aligned, with cards]         │
│  [User follow-up]                                   │
│  [Nova response with updated valuation]             │
│                                                     │
├─────────────────────────────────────────────────────┤
│  Input bar: paperclip + text input + send button    │
│  "Drop PDFs, P&IDs, or spreadsheets..."             │
└─────────────────────────────────────────────────────┘
```

## Components

### 1. Header Bar
- Left: Nova logo (copper gradient circle with "N") + "Nova" in Space Grotesk + "v2" badge
- Right: Stats — "25,142 listings • 16 sources • ● Connected" in muted text
- Bottom border: subtle 1px line (#2A3038)
- Minimal height — this isn't the feature, the conversation is

### 2. Welcome Message
First message from Nova on page load:
```
Welcome. I'm Nova, Fuelled's pricing intelligence. Ask me about any 
oilfield or industrial equipment and I'll give you a valuation backed 
by 25,000 market comparables.

You can:
• Ask "What's an Ariel JGK/4 worth?"
• Upload a P&ID or PO for detailed analysis
• Attach a client email for full pricing
```

### 3. User Message Bubble
- Right-aligned
- Subtle elevated background (#242A32)
- Rounded corners (16px top, 4px bottom-right)
- If files attached: show file pills below the text (📎 filename.pdf)

### 4. Nova Response — The Key Component
Left-aligned, with a small copper avatar ("N") and "Nova" label.

A Nova response can contain any combination of:
- **Valuation Card** (structured data)
- **Comparables Table** (market evidence)
- **Risk Factors** (warnings)
- **Text** (explanation, methodology narrative)

#### 4a. Valuation Card
The hero component. This is what makes the app useful.

```
┌──────────────────────────────────────────────────────┐
│ RECIPROCATING GAS COMPRESSOR PACKAGE                 │
│ Waukesha L7044GSI / Ariel JGK/4 — 3-Stage Sweet     │
│                                                      │
│ Fair Market Value                         ┌────────┐ │
│ $320,000 — $420,000                       │  HIGH  │ │
│                                           └────────┘ │
│                                                      │
│ RCN (New)          │                                 │
│ $1,400,000         │                                 │
│                                                      │
│ ┌─────────┐ ┌────────┐ ┌──────────┐ ┌─────────┐    │
│ │Age: 0.50│ │Cond:0.75│ │Hours:1.00│ │Svc: 1.00│    │
│ └─────────┘ └────────┘ └──────────┘ └─────────┘    │
│                                                      │
│ ─────────────────────────────────────────────────    │
│ List at $460,000   Walk-away $295,000   Comps: 5     │
│                                                      │
│ ▸ Show methodology                                   │
└──────────────────────────────────────────────────────┘
```

Design details:
- Card background: #242A32, 1px border #2A3038, 12px radius
- Equipment type: tiny uppercase label, muted (#5C6370)
- Equipment name: 16px semibold white
- FMV range: 28px bold, the biggest thing on the card
- Confidence badge: pill shape, color-coded (green/amber/red)
- RCN: copper accent color (#C4834A), separated by a subtle vertical divider
- Factor pills: small rounded boxes with label:value format, monospace numbers
- Bottom row: list price (green), walk-away (red), comps count
- "Show methodology" toggle: expands to show the calculation in monospace

#### 4b. Comparables Table
```
┌──────────────────────────────────────────────────────┐
│ MARKET COMPARABLES — 5 found                         │
├───────────────────────┬─────────┬──────┬──────┬──────┤
│ Description           │ Price   │ Year │ Loc  │Source│
├───────────────────────┼─────────┼──────┼──────┼──────┤
│ L5774/JGK4 3-Stg      │ $375,000│  —   │  AB  │ ATB  │
│ G3512/JGK4 3-Stg Sweet│ $250,000│  —   │  AB  │ ATB  │
│ G3512/Gemini 3-Stg    │ $240,000│  —   │  AB  │ ATB  │
└───────────────────────┴─────────┴──────┴──────┴──────┘
```

Design details:
- Same card treatment as valuation card
- Compact table, no heavy borders — just bottom borders on rows
- Prices in copper/accent color, monospace
- Muted column headers

#### 4c. Risk Factors
```
┌──────────────────────────────────────────────────────┐
│ ⚠ RISK FACTORS                                      │
│                                                      │
│ │ HIGH HOURS: 45,000 hours approaches major          │
│ │ overhaul threshold. Budget $60K-$100K for          │
│ │ frame overhaul.                                    │
│ │                                                    │
│ │ OVERHAUL ECONOMICS: Total overhaul $110K-$180K.    │
│ │ Post-overhaul value $320K-$420K. Economically      │
│ │ viable for buyer with shop capability.             │
└──────────────────────────────────────────────────────┘
```

Design details:
- Warm dark background (#2A1F1B), amber border (#5C3A20)
- Left accent bar on each risk item (amber)
- Warning icon + "RISK FACTORS" in amber uppercase

#### 4d. Text Response
Plain text below the structured components. 14px, secondary color, comfortable line-height (1.7). This is the narrative explanation — how the number was derived, market context, recommendations.

### 5. Input Bar
- Fixed at bottom of viewport
- Paperclip icon button (left) — opens file picker
- Text input — placeholder "Ask about equipment..."
- Send button (right) — copper when text present, muted when empty
- Arrow icon (→) on the send button
- Below input: "Drop PDFs, P&IDs, or spreadsheets to include with your question" in tiny muted text
- Drag-and-drop zone — border changes to copper when dragging files over

### 6. File Upload States
When files are attached before sending:
- Show file pills between the input and the send button
- Each pill: 📎 filename.pdf with an × to remove
- Accepts: PDF, PNG, JPG, XLSX, CSV, EML

### 7. Loading State
While waiting for Nova's response:
- Show "Nova is thinking..." with a subtle copper pulse animation
- Optional: show tool activity — "Searching 25,142 listings..." / "Calculating FMV..." / "Checking risk factors..."

## Responsive Behavior
- Desktop: centered conversation, max-width 880px
- Tablet: full width with padding
- Mobile: full width, minimal padding, input bar stays fixed at bottom

## Pages
Just one. This is the entire app. No routing, no sidebar, no settings page, no dashboard.

## What This Does NOT Have
- No sidebar navigation
- No dashboard with charts
- No settings page
- No user authentication UI (internal tool)
- No conversation history sidebar
- No dark/light mode toggle (always dark)
- No onboarding flow

## Demo Content for Stitch
Pre-populate the conversation with this flow so the design shows the real product:

**User:** "What's a 2020 Waukesha L7044 / Ariel JGK/4 3-stage sweet gas compressor package worth? Good condition, about 12,000 hours."

**Nova:** [Valuation Card: $320K-$420K, HIGH confidence, RCN $1.4M] + [Comp Table: 5 listings] + [Narrative text explaining the methodology]

**User:** "What about the same unit but with 45,000 hours and needing a top-end overhaul?"

**Nova:** [Valuation Card: $140K-$200K, MEDIUM confidence] + [Risk Factors: high hours, overhaul economics] + [Narrative about target buyer profile]

This shows the full range of the interface in two exchanges.
