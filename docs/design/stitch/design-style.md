## 2. Colors & Surface Architecture
Our palette is rooted in a clinical "Super-White" and "Muted Teal" spectrum. This creates a high-contrast environment for data while maintaining a calm atmosphere.

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

### Ambient Shadows
Shadows are only permitted for "Floating" elements (e.g., Modals, Tooltips). 
- **Specs:** Blur: 32px | Spread: 0 | Opacity: 4% | Color: `on-surface` (#2a3435).
- This creates an "Ambient Occlusion" effect—as if the element is naturally catching the light of a clinical laboratory, rather than casting a heavy digital drop shadow.

## 5. Components

### Buttons: The High-Precision Tool
- **Primary:** Background `primary` (#2a6767), text `on-primary` (#d9fffe). Corner radius: `md` (0.375rem).
- **Tertiary (The "Silent" Action):** No background. Use `primary` text. This is for secondary actions like "Export" or "Save Draft" to keep the focus on the genomic data.

### Genomic Data Cards
- **Construction:** Use `surface-container-lowest` (#FFFFFF) with a `lg` (0.5rem) corner radius. 
- **Interaction:** On hover, do not change the background color. Instead, apply a 1px `primary` Ghost Border at 20% opacity.

### Input Fields & Search
- Use a "Minimalist Ledger" style. No 4-sided boxes. Use a 1px bottom-border only (using `outline-variant`) that transforms into a 2px `primary` border on focus. This mimics a professional form.

### Relevant Custom Components: "The Evidence Badge"
For genomic variants, use small `chips` with a `full` (9999px) radius. 
- **Pathogenic:** `error_container` (#fe8983) background with `on_error_container` (#752121) text.
- **Benign:** `secondary_container` (#b9ecec) background with `on_secondary_container` (#27595a) text.

## 6. Do's and Don'ts
