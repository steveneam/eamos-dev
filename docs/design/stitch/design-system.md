# Design System Specification: The Precision Gallery

## 1. Overview & Creative North Star
The "Creative North Star" for this design system is **The Precision Gallery**. 

In the high-stakes world of genomic review, the interface must function as a quiet, authoritative space that eliminates cognitive load. This is not a "dashboard"; it is a curated ledger. We depart from the "template" look by utilizing high-end editorial layouts—think of a premium medical journal reimagined as a digital workspace. We achieve this through **intentional asymmetry**, where data-dense panels are balanced by generous, sweeping "white space" (utilizing the `#F8FAFA` background), and a sophisticated typographic scale that prioritizes scanning over reading.

The experience should feel "Clinical but Human"—cold enough to be credible, yet soft enough to prevent fatigue during a 10-hour review shift.

## 2. Colors & Surface Architecture
Our palette is rooted in a clinical "Super-White" and "Muted Teal" spectrum. This creates a high-contrast environment for data while maintaining a calm atmosphere.

### The "No-Line" Rule
To achieve a signature high-end feel, **1px solid borders are prohibited for sectioning.** Traditional grids feel claustrophobic. Instead, boundaries must be defined solely through:
- **Tonal Shifts:** Placing a `surface-container-lowest` (#FFFFFF) card on a `surface` (#F8FAFA) background.
- **Negative Space:** Using the spacing scale (minimum 32px) to define the end of one data set and the beginning of another.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers of fine paper. 
- **Base Layer:** `surface` (#F8FAFA) — the vast "desk" the work sits on.
- **Level 1 (The Canvas):** `surface-container-low` (#F0F4F5) — for sidebar backgrounds or secondary navigation.
- **Level 2 (The Priority):** `surface-container-lowest` (#FFFFFF) — reserved for the primary genomic data cards and review panels.

### The Luminous Depth
While the user requested "no gradients," we will implement **Luminous Tones**. For primary CTAs (using `primary` #2a6767), use a 0.5px "inner-glow" stroke rather than a gradient to give the button a tactile, machined quality that feels more premium than a flat digital box.

## 3. Typography: The Editorial Engine
We use a dual-typeface system to separate "Content" from "Data."

*   **The Display Voice (Manrope):** Used for Headlines and Display styles. Manrope’s geometric but open curves provide a modern, authoritative tone. 
    *   *Direction:* Use `headline-lg` with tight letter-spacing (-0.02em) for a bold, editorial impact.
*   **The Technical Voice (Inter):** Used for Body, Titles, and Labels. Inter is the industry standard for legibility in dense environments.
    *   *Direction:* For genomic sequences (A, T, C, G), always use `label-md` with increased letter-spacing (+0.05em) to ensure individual characters are unmistakable.

**Hierarchy as Brand:** Use `display-sm` (Manrope) for patient names or case IDs to create a "Hero" moment in an otherwise clinical environment.

## 4. Elevation & Depth
Depth is achieved through **Tonal Layering** rather than structural shadows.

### The Layering Principle
Never use a shadow to separate a card from the background. Instead, stack your tokens:
1.  **Background:** `surface` (#F8FAFA)
2.  **Section:** `surface-container-low` (#F0F4F5)
3.  **Active Card:** `surface-container-lowest` (#FFFFFF)

### Ambient Shadows
Shadows are only permitted for "Floating" elements (e.g., Modals, Tooltips). 
- **Specs:** Blur: 32px | Spread: 0 | Opacity: 4% | Color: `on-surface` (#2a3435).
- This creates an "Ambient Occlusion" effect—as if the element is naturally catching the light of a clinical laboratory, rather than casting a heavy digital drop shadow.

### The "Ghost Border" Fallback
In high-density genomic tables where rows must be separated, use a **Ghost Border**: `outline-variant` (#a9b4b5) at **15% opacity**. It should be felt, not seen.

## 5. Components

### Buttons: The High-Precision Tool
- **Primary:** Background `primary` (#2a6767), text `on-primary` (#d9fffe). Corner radius: `md` (0.375rem).
- **Tertiary (The "Silent" Action):** No background. Use `primary` text. This is for secondary actions like "Export" or "Save Draft" to keep the focus on the genomic data.

### Genomic Data Cards
- **Construction:** Use `surface-container-lowest` (#FFFFFF) with a `lg` (0.5rem) corner radius. 
- **Interaction:** On hover, do not change the background color. Instead, apply a 1px `primary` Ghost Border at 20% opacity.

### Input Fields & Search
- Use a "Minimalist Ledger" style. No 4-sided boxes. Use a 1px bottom-border only (using `outline-variant`) that transforms into a 2px `primary` border on focus. This mimics a professional form.

### The "Sequence" List
- **Constraint:** Forbid the use of divider lines between gene sequences.
- **Solution:** Use vertical white space and a subtle background shift (alternating between `surface` and `surface-container-low`) for every 5th row to help the eye track across the screen.

### Relevant Custom Components: "The Evidence Badge"
For genomic variants, use small `chips` with a `full` (9999px) radius. 
- **Pathogenic:** `error_container` (#fe8983) background with `on_error_container` (#752121) text.
- **Benign:** `secondary_container` (#b9ecec) background with `on_secondary_container` (#27595a) text.

## 6. Do's and Don'ts

### Do
- **DO** use asymmetry. Place the primary data set 1/3rd from the left to create a sophisticated, non-centered layout.
- **DO** lean into high-contrast labels. Small `label-sm` text in all-caps with generous letter-spacing for "Case Status."
- **DO** use "Glassmorphism" (Backdrop Blur: 12px) for top navigation bars to allow the clinical background to bleed through, maintaining a sense of space.

### Don't
- **DON'T** use pure black (#000000). Always use `on-surface` (#2a3435) for text to keep the "calm" medical vibe.
- **DON'T** use "Bubbly" corners. Stick to the `md` and `lg` scale to keep the interface looking professional and precise.
- **DON'T** use 100% opaque dividers. They "cut" the user's vision and create visual friction.
