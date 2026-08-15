# DocuMind AI — Master Design System

> **Source of Truth:** This file contains the canonical design tokens and component rules for DocuMind AI. Any frontend implementation must adhere to these rules.
> If a page requires specific overrides, they are documented in `design-system/pages/[page].md`.

---

## 1. Design Philosophy

**Premium Monochrome**
The product is a serious AI productivity workspace. It relies on a high-contrast, black-and-white, neutral gray aesthetic (think Linear + Notion). It communicates trust, precision, and technical capability.

**Avoid:** Neon gradients, heavy glassmorphism, 3D elements, cyberpunk themes, emoji icons, oversized chat bubbles, and layout-shifting animations.

---

## 2. Color System (Dark Mode Default)

The UI is monochrome-first. Color is used strictly for semantic meaning (status, accessibility) and never as a primary brand decoration.

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-base` | `#000000` | Main application background |
| `--bg-surface` | `#0A0A0A` | Secondary background (sidebar, panels) |
| `--bg-elevated` | `#111111` | Cards, popovers, dropdowns |
| `--bg-floating` | `#171717` | Dialogs, tooltips, high-elevation surfaces |
| `--border-subtle` | `#262626` | Dividers, panel separators |
| `--border-strong` | `#404040` | Inputs, focused elements, active cards |
| `--text-primary` | `#FFFFFF` | Headings, primary body text, active icons |
| `--text-secondary` | `#A3A3A3` | Secondary text, inactive tabs, standard icons |
| `--text-muted` | `#737373` | Placeholder text, disabled text, timestamp |
| `--accent-primary`| `#FFFFFF` | Primary buttons, active selections (inverted text to #000000) |

### Status Colors (Semantic Only)
For success, warning, error, and processing states, prioritize iconography and labels. Color is a subtle enhancement, usually applied to borders or small indicator dots, not large solid background fills.
- `--status-error`: `#DC2626` (Red - Destructive actions, system errors)
- `--status-warning`: `#F59E0B` (Amber - Warnings, missing data)
- `--status-success`: `#10B981` (Emerald - Completion, ready states)
- `--status-process`: `#3B82F6` (Blue - Active AI processing, uploading)

---

## 3. Typography

- **Primary UI Font:** **Inter**. (Clean, highly legible sans-serif, excellent for dense technical UI).
- **Secondary/Data Font:** **JetBrains Mono**. (Used for IDs, metadata, code blocks, structured data tables).

### Scale
- `--text-xs`: 12px / 16px line-height (Badges, small metadata)
- `--text-sm`: 14px / 20px line-height (Secondary text, sidebar items, tooltips)
- `--text-base`: 16px / 24px line-height (Body text, chat messages, inputs)
- `--text-lg`: 18px / 28px line-height (Section headers, subheadings)
- `--text-xl`: 20px / 28px line-height (Page titles, dialog headers)
- `--text-2xl`: 24px / 32px line-height (Major page headers)
- `--text-3xl`: 30px / 36px line-height (Landing page hero, prominent stats)

---

## 4. Spacing System

Strict adherence to a 4px/8px scale.
- `--space-1`: 4px (Tight element spacing, icon + text)
- `--space-2`: 8px (List items, small padding)
- `--space-3`: 12px (Inner card padding, input padding)
- `--space-4`: 16px (Standard component padding, layout gaps)
- `--space-6`: 24px (Large padding, distinct layout sections)
- `--space-8`: 32px (Section margins, dialog padding)
- `--space-12`: 48px (Major section breaks)
- `--space-16`: 64px (Page margins, landing page sections)
- `--space-24`: 96px (Hero section margins)

---

## 5. Shape & Elevation

### Border Radius
Avoid pill-shaped UI (except for specific small badges).
- `--radius-sm`: 4px (Checkboxes, small tooltips, inner elements)
- `--radius-md`: 8px (Buttons, inputs, dropdown menus)
- `--radius-lg`: 12px (Cards, dialogs, image previews)
- `--radius-full`: 9999px (Avatars, notification dots, specific status badges)

### Shadows
The UI relies on borders and contrast for separation. Shadows are extremely subtle.
- `--shadow-sm`: `0 1px 2px 0 rgba(0,0,0,0.4)` (Dropdowns)
- `--shadow-md`: `0 4px 6px -1px rgba(0,0,0,0.5)` (Dialogs)
- `--shadow-lg`: `0 10px 15px -3px rgba(0,0,0,0.6)` (Floating panels, command palette)

---

## 6. Iconography

- **Library:** Lucide Icons.
- **Rules:** No emojis. Consistent stroke width (1.5px or 2px depending on visual weight).
- **Sizes:** 16px (inline text), 20px (standard buttons/sidebar), 24px (empty states).

---

## 7. Core Components

### 7.1 Buttons
- **Primary:** Background `--accent-primary` (#FFF), Text `#000`, Radius `8px`. Hover: opacity 0.9.
- **Secondary:** Background transparent, Border `--border-strong`, Text `--text-primary`. Hover: Background `--bg-elevated`.
- **Ghost:** Background transparent, Text `--text-secondary`. Hover: Background `--bg-surface`, Text `--text-primary`.
- **Destructive:** Background transparent, Border `--status-error`, Text `--status-error`.

### 7.2 Inputs & Forms
- **Style:** Background `--bg-base`, Border `--border-subtle`, Radius `8px`, Text `--text-base`.
- **Focus:** Border `--text-primary`, no glowing ring, crisp contrast change.
- **Disabled:** Background `--bg-surface`, Text `--text-muted`, opacity 0.5.

### 7.3 Cards
- **Style:** Background `--bg-elevated`, Border `--border-subtle`, Radius `12px`.
- **Interactive:** Hover state changes border to `--border-strong`. No Y-axis translation.

### 7.4 Dialogs & Modals
- **Style:** Background `--bg-floating`, Border `--border-subtle`, Radius `12px`, Shadow `--shadow-md`.
- **Backdrop:** rgba(0,0,0,0.8) with optional subtle blur (max 4px).

### 7.5 AI Chat Messages
- **User Message:** Right-aligned (or distinct avatar), Background `--bg-surface`, subtle border.
- **AI Response:** Left-aligned, transparent background, highly legible markdown typography (headings, lists, code blocks with syntax highlighting using JetBrains Mono).
- **Citations:** Inline numeric citations `[1]`. Style: subtle badge. Hover: Tooltip showing source context. Click: Navigates document viewer.

### 7.6 Source Cards / Citations
- **Style:** Small horizontal cards below AI response or in a side-panel. Shows Document Name, Page Number, and a tiny snippet. Mono font for page numbers.

### 7.7 Processing Indicators
- **Style:** Minimal text labels ("Extracting text...", "Indexing...") with a subtle, smooth linear progress bar or a simple Lucide `loader` spinning at a constant rate. No fake percentage numbers.

---

## 8. Interaction & Animation

- **Timing:** Fast micro-interactions. Hover/focus states transition over `150ms ease`.
- **Modals/Sidebar:** Enter/exit over `200ms ease-out`.
- **Motion:** No continuous floating, no parallax, no bouncy springs. Simple fades and subtle slides.
- **Accessibility:** Respect `prefers-reduced-motion` strictly (disable slides/scaling, fallback to instant or fast cross-fade).

---

## 9. Accessibility (A11y)

- **Contrast:** Minimum 4.5:1 for all text. Minimum 3:1 for active UI components (borders of inputs).
- **Focus:** Keyboard focus must be explicitly visible. Do NOT remove outlines. Use a solid 2px outline matched to `--text-primary` with a 2px offset.
- **Color Independence:** Never rely on color alone to convey state (e.g., use an alert icon + red border for error, not just a red background).

---

## 10. Application Layout (Desktop-First)

- **Main Structure:** Topbar (minimal, breadcrumbs/user context) + Left Sidebar + Main Content Area.
- **Sidebar:** 260px fixed width, collapsible to icon-only (64px) or fully hidden.
- **Max Width:** Fluid for workspace. Constrained (e.g., 800px) for settings/forms.
