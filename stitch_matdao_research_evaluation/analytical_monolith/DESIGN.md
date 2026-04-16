# Design System: Analytical Monolith Protocol

## 1. Overview & Creative North Star
### Creative North Star: "The Obsidian Intelligence"
This design system is not a dashboard; it is a high-precision instrument. It is built to evoke the atmosphere of a deep-tech command center—silent, authoritative, and immensely powerful. We move away from the "web-page" aesthetic by embracing **Obsidian Depth**. 

The interface relies on high-contrast technical typography and luminous accents emerging from an infinite dark void. By utilizing intentional asymmetry, wide tracking in labels, and glassmorphic layering, we create a digital experience that feels like it exists on a futuristic heads-up display (HUD). The goal is to make the user feel like an operator of sophisticated, proprietary machinery.

---

## 2. Colors & Surface Logic
The palette is rooted in the `background: #131313` (Obsidian), punctuated by `primary: #97FDFF` (Cyan Glow).

### The "No-Line" Rule
Standard 1px solid borders are strictly prohibited for structural sectioning. To define regions, use **Background Tonal Shifts**. For example, a main navigation sidebar should use `surface_container_low`, while the main workspace remains on `surface`. The eye should perceive the boundary through the shift in value, not a drawn line.

### Surface Hierarchy & Nesting
Depth is achieved through the physical stacking of tones:
1.  **Base Layer:** `surface` (#131313) - The absolute floor.
2.  **Sectional Layer:** `surface_container_low` (#1C1B1B) - Large regional blocks.
3.  **Component Layer:** `surface_container_high` (#2A2A2A) - Cards and interactive modules.
4.  **Elevation Layer:** `surface_bright` (#3A3939) - Modals or "active" floating elements.

### The "Glass & Gradient" Rule
To achieve the signature "Deep Tech" feel, use **Glassmorphism**. High-priority cards should utilize a semi-transparent `surface_variant` with a `backdrop-blur` of 12px–20px. 
*   **Signature Gradient:** For primary CTAs, use a linear gradient transitioning from `primary_container` (#3FE6E8) to `primary` (#97FDFF) at a 135-degree angle. This adds a "lithographic" soul to the UI.

---

## 3. Typography
The system uses a bi-font strategy to balance technical precision with readability.

*   **The Technical Voice (Space Grotesk):** Used for all `display`, `headline`, and `label` roles. This typeface conveys a scientific, geometric rigor. 
    *   *Directorial Note:* For `label-sm`, use `text-transform: uppercase` and `letter-spacing: 0.1em` to mimic data-readouts.
*   **The Analytical Voice (Inter):** Used for `body` and `title` roles. Inter provides the necessary legibility for complex research data and long-form insights.

| Scale | Font | Size | Intent |
| :--- | :--- | :--- | :--- |
| **Display-LG** | Space Grotesk | 3.5rem | High-level metrics / Scores |
| **Headline-MD** | Space Grotesk | 1.75rem | Section headers |
| **Body-MD** | Inter | 0.875rem | Descriptions and insights |
| **Label-MD** | Space Grotesk | 0.75rem | Technical Metadata |

---

## 4. Elevation & Depth
We eschew traditional "drop shadows" for **Luminous Ambient Depth**.

*   **Tonal Layering:** Place a `surface_container_lowest` card inside a `surface_container_high` wrapper to create an "etched" look rather than a raised one.
*   **Ambient Shadows:** Floating elements (Modals) should use a shadow with a 40px blur, 0px offset, and a 6% opacity of the `primary` color (#97FDFF). This creates a "glow" rather than a shadow, implying the component is light-emissive.
*   **The "Ghost Border":** When containment is required for accessibility, use the `outline_variant` token at **15% opacity**. It should feel like a faint wireframe, not a solid container.
*   **Data Motifs:** Inject subtle `grid` patterns (0.05 opacity `on_surface`) into the background of `surface_container_low` to reinforce the analytical aesthetic.

---

## 5. Components

### Buttons
*   **Primary:** Gradient fill (`primary_container` to `primary`). `rounded: sm` (0.125rem). No border. Text is `on_primary`.
*   **Secondary/Ghost:** `outline-variant` (20% opacity) border. On hover, the border glows with 100% `primary` opacity.

### Progress Bars (Data Visualization)
The core of this system. Use a "Glow-Track" style:
*   **Track:** `surface_container_highest` (#353534).
*   **Indicator:** `primary` (#97FDFF) with a 4px outer glow (box-shadow) of the same color.
*   **Segmented look:** Use 2px gaps between percentage increments for a "digital readout" feel.

### Analytical Cards
*   **Styling:** Background of `surface_container` at 80% opacity + `backdrop-blur`. 
*   **Top Edge:** A 1px "Top-Light" using `primary` at 30% opacity gives the card a finished, premium edge.
*   **No Dividers:** Separate card sections with 24px of vertical whitespace or a subtle background shift to `surface_container_lowest`.

### Input Fields
*   **State:** Underline-only or subtle "Ghost Border" (0.125rem radius).
*   **Active State:** The bottom border transforms into a `primary` glow. Helper text uses `label-sm` in `primary` color.

---

## 6. Do's and Don'ts

### Do:
*   **DO** use intentional asymmetry. Align high-level scores to the left while keeping secondary data visualizations weighted to the right.
*   **DO** use "Primary Glow" sparingly. It should highlight the path forward (CTAs) or critical data points.
*   **DO** utilize technical icons (monolinear, 1.5px stroke width) that match the `on_surface_variant` color.

### Don't:
*   **DON'T** use 100% opaque, white borders. This breaks the "Obsidian" immersion.
*   **DON'T** use standard Material Design "Floating Action Buttons." All actions should feel integrated into the "Command Center" console.
*   **DON'T** use rounded corners above `md` (0.375rem) for functional components. High-precision tools have sharp, defined edges; keep the `DEFAULT` at 0.25rem.
*   **DON'T** use pure grey for shadows. Always tint shadows with the `surface_tint` or `primary` value to maintain the "deep tech" atmosphere.