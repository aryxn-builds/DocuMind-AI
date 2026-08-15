# DocuMind AI — Design System

> **Status:** Draft v1.0 — Initial direction
> **Last updated:** 2026-08-15
> **Decision key:** DECIDED · PROPOSED · OPEN DECISION
>
> **Note:** This document establishes the design direction. The UI UX Pro Max skill will be used later to refine tokens, validate accessibility, and finalize component specifications.

---

## 1. Visual Principles

1. **Monochrome premium.** The palette is black, white, and neutral grays. Color is used only for semantic meaning (errors, warnings, success) and interactive accents — never for decoration.
2. **Calm precision.** The interface should feel quiet and controlled. No visual noise, no competing elements, no unnecessary embellishment.
3. **Typography-driven.** Strong type hierarchy carries the design. Headings, body text, and captions are clearly differentiated by size, weight, and spacing.
4. **Generous whitespace.** Components breathe. Density is a deliberate choice (dashboards), not a default.
5. **Subtle depth.** Use borders over shadows. When shadows are used, they are nearly imperceptible. No drop-shadow-heavy card stacking.
6. **Dark-first.** Dark mode is the primary/default experience. Light mode is fully supported but secondary in design priority.

**Design inspiration:** Linear, Notion, Vercel, Raycast, Arc Browser.

---

## 2. Color Tokens

### 2.1 Dark Mode (Default)

| Token | Value | Usage |
|-------|-------|-------|
| `--background` | `#09090B` | Page background |
| `--background-secondary` | `#18181B` | Sidebar, panels, elevated surfaces |
| `--card` | `#18181B` | Card backgrounds |
| `--card-hover` | `#27272A` | Card hover state |
| `--border` | `#27272A` | Default borders |
| `--border-subtle` | `#1E1E22` | Very subtle separators |
| `--foreground` | `#FAFAFA` | Primary text |
| `--foreground-secondary` | `#A1A1AA` | Secondary/muted text |
| `--foreground-tertiary` | `#71717A` | Placeholder text, disabled labels |
| `--accent` | `#FAFAFA` | Primary interactive elements (buttons, links) |
| `--accent-foreground` | `#09090B` | Text on accent backgrounds |
| `--destructive` | `#EF4444` | Error states, destructive actions |
| `--warning` | `#F59E0B` | Warning states |
| `--success` | `#22C55E` | Success states |
| `--info` | `#3B82F6` | Informational indicators |
| `--ring` | `#D4D4D8` | Focus ring color |

### 2.2 Light Mode

| Token | Value | Usage |
|-------|-------|-------|
| `--background` | `#FFFFFF` | Page background |
| `--background-secondary` | `#F4F4F5` | Sidebar, panels |
| `--card` | `#FFFFFF` | Card backgrounds |
| `--card-hover` | `#F4F4F5` | Card hover state |
| `--border` | `#E4E4E7` | Default borders |
| `--border-subtle` | `#F4F4F5` | Very subtle separators |
| `--foreground` | `#09090B` | Primary text |
| `--foreground-secondary` | `#71717A` | Secondary text |
| `--foreground-tertiary` | `#A1A1AA` | Placeholder text |
| `--accent` | `#18181B` | Primary interactive elements |
| `--accent-foreground` | `#FAFAFA` | Text on accent backgrounds |
| `--destructive` | `#DC2626` | Error states |
| `--warning` | `#D97706` | Warning states |
| `--success` | `#16A34A` | Success states |
| `--info` | `#2563EB` | Informational indicators |
| `--ring` | `#18181B` | Focus ring color |

**DECIDED:** Zinc-based gray scale from Tailwind CSS for consistency with shadcn/ui defaults.

**OPEN DECISION:** Exact accent color. Currently proposing white-on-dark / black-on-light (monochrome). A subtle tinted accent (e.g., blue-gray) may be considered later.

---

## 3. Typography Direction

| Role | Size | Weight | Line Height | Tracking |
|------|------|--------|-------------|----------|
| Display | 36–48px | 700 | 1.1 | -0.02em |
| H1 | 30px | 700 | 1.2 | -0.02em |
| H2 | 24px | 600 | 1.3 | -0.01em |
| H3 | 20px | 600 | 1.4 | 0 |
| H4 | 16px | 600 | 1.5 | 0 |
| Body | 14–15px | 400 | 1.6 | 0 |
| Body small | 13px | 400 | 1.5 | 0 |
| Caption | 12px | 400 | 1.4 | 0.01em |
| Code / Mono | 13px | 400 | 1.5 | 0 |

**OPEN DECISION:** Exact font family. Candidates:
- **Inter** — Clean, highly readable, excellent for UI
- **Geist Sans** — Modern, used by Vercel/Linear ecosystem
- **System font stack** — Zero network requests, native feel

Monospace: **Geist Mono**, **JetBrains Mono**, or **Fira Code**.

The UI UX Pro Max skill will be used to finalize font pairing.

---

## 4. Spacing Scale

Based on a 4px grid:

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Tight internal padding |
| `--space-2` | 8px | Small gaps, icon margins |
| `--space-3` | 12px | Default component padding |
| `--space-4` | 16px | Standard spacing |
| `--space-5` | 20px | Medium spacing |
| `--space-6` | 24px | Section padding |
| `--space-8` | 32px | Large section gaps |
| `--space-10` | 40px | Page-level spacing |
| `--space-12` | 48px | Major section breaks |
| `--space-16` | 64px | Page margins, hero spacing |

---

## 5. Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 4px | Small badges, pills |
| `--radius-md` | 6px | Inputs, buttons, cards |
| `--radius-lg` | 8px | Modals, large cards |
| `--radius-xl` | 12px | Containers, prominent surfaces |
| `--radius-full` | 9999px | Avatars, circular elements |

**DECIDED:** Subtle rounding, not heavily rounded. The aesthetic is technical/precise, not playful.

---

## 6. Shadows

Shadows are minimal. Borders are preferred for separation.

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift (light mode only) |
| `--shadow-md` | `0 2px 8px rgba(0,0,0,0.08)` | Dropdowns, tooltips |
| `--shadow-lg` | `0 4px 16px rgba(0,0,0,0.12)` | Modals, command palette |

In dark mode, shadows are generally invisible against dark backgrounds. Use `border` instead.

---

## 7. Component Direction

### 7.1 Buttons

| Variant | Background | Text | Border | Usage |
|---------|-----------|------|--------|-------|
| Primary | `--accent` | `--accent-foreground` | none | Primary actions (Submit, Upload) |
| Secondary | transparent | `--foreground` | `--border` | Secondary actions |
| Ghost | transparent | `--foreground-secondary` | none | Tertiary actions, icon buttons |
| Destructive | `--destructive` | white | none | Delete, remove actions |

- Height: 36px (default), 32px (small), 40px (large)
- Font weight: 500
- Padding: `8px 16px`
- Transition: background 150ms ease
- Hover: subtle background shift
- Focus: 2px ring offset

### 7.2 Inputs

- Height: 36px
- Background: `--background` (dark) or `--background-secondary` (light)
- Border: 1px `--border`
- Border on focus: `--ring`
- Placeholder color: `--foreground-tertiary`
- Padding: `8px 12px`
- Font size: 14px

### 7.3 Cards

- Background: `--card`
- Border: 1px `--border`
- Border radius: `--radius-lg`
- Padding: `--space-4` to `--space-6`
- Hover (interactive cards): background shifts to `--card-hover`
- No heavy shadows in dark mode

### 7.4 Sidebar

- Width: 260px (desktop), collapsible
- Background: `--background-secondary`
- Border-right: 1px `--border`
- Navigation items: 36px height, 12px padding, full-width
- Active state: subtle background highlight + foreground color change
- Icons: 16px, Lucide

### 7.5 Navigation / Top Bar

- Height: 48px
- Background: `--background` with subtle bottom border
- Content: breadcrumbs or page title, user menu, theme toggle

### 7.6 Chat Messages

| Element | Specification |
|---------|--------------|
| User message | Right-aligned or left-aligned with user indicator, `--background-secondary` bg |
| Assistant message | Left-aligned, no background or very subtle bg, body text styling |
| Citations | Inline citation badges [1] [2] with hover tooltip showing excerpt |
| Timestamp | Caption size, `--foreground-tertiary` |
| Input area | Fixed bottom, textarea with send button, border-top separator |

### 7.7 Citation Components

- Inline badge: small pill with citation number, monochrome
- Citation panel: expandable sidebar or footer showing referenced excerpts
- Click behavior: navigate to document page/section
- Relevance indicator: subtle opacity or order-based (most relevant first)

### 7.8 Document Cards

- Show: title, file type icon, page count, processing status, date
- File type icon: distinct icons for PDF, DOCX, image
- Status badge: processing (animated), ready (green dot), failed (red dot)
- Actions: open, delete (via menu or icon)

### 7.9 Upload Components

- Drag-and-drop zone: dashed border, centered icon + text
- Active drag: border color change, subtle background shift
- File list: queued files with name, size, progress bar
- Accepted types indicator: "PDF, DOCX, PNG, JPG"

### 7.10 Tables

- Header: `--foreground-secondary`, uppercase caption size, bottom border
- Rows: alternating subtle background (optional, only if density is high)
- Borders: horizontal only (clean, minimal)
- Cell padding: `--space-2` vertical, `--space-4` horizontal
- Hover: row highlight with `--card-hover`

---

## 8. States

### 8.1 Loading States

- Skeleton screens preferred over spinners for content areas
- Skeleton: `--background-secondary` rectangles with subtle pulse animation
- Inline loading: small spinner (16px) for buttons, submission
- Page loading: centered skeleton matching the expected layout
- Processing: progress bar or status text with animated indicator

### 8.2 Empty States

- Centered illustration or icon (monochrome, Lucide-based)
- Heading: clear statement ("No documents yet")
- Subtext: brief guidance ("Upload a PDF or DOCX to get started")
- CTA button: primary action to resolve the empty state
- Tone: helpful, not apologetic

### 8.3 Error States

- Inline errors: red text below the relevant field, `--destructive` color
- Toast notifications: top-right, auto-dismiss, destructive variant for errors
- Full-page errors: centered message with retry action
- Processing errors: status badge on document card + expandable error details

---

## 9. Accessibility

| Requirement | Standard |
|-------------|----------|
| Color contrast | WCAG AA minimum (4.5:1 for body text, 3:1 for large text) |
| Focus indicators | Visible focus ring on all interactive elements, never removed |
| Keyboard navigation | All actions reachable via keyboard, logical tab order |
| Screen reader support | Semantic HTML, ARIA labels on icons and interactive elements |
| Reduced motion | Respect `prefers-reduced-motion`, disable non-essential animations |
| Font scaling | UI scales correctly with browser font size changes |
| Touch targets | Minimum 44×44px for mobile/touch interactions |

**DECIDED:** Accessibility is a hard requirement, not a nice-to-have. All components must meet WCAG AA.

---

## 10. Responsive Principles

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | < 768px | Single column, sidebar hidden, bottom nav possible |
| Tablet | 768px–1024px | Sidebar collapsible, main content adapts |
| Desktop | 1024px–1440px | Full sidebar + main content area |
| Wide | > 1440px | Content max-width with centered layout |

- **Sidebar:** Always collapsible. Hidden on mobile, toggle on tablet, visible on desktop.
- **Document viewer + chat:** Side-by-side on desktop, stacked or tabbed on mobile.
- **Content max-width:** Body text max 720px for readability.

---

## 11. Animation Principles

- **Duration:** 150ms for micro-interactions (hover, focus), 200–300ms for transitions (panel open, page change)
- **Easing:** `ease-out` for entries, `ease-in` for exits
- **Scope:** Animate opacity and transform only (never width/height for performance)
- **Restraint:** If an animation doesn't improve understanding or usability, remove it
- **Reduced motion:** All animations must be skippable via `prefers-reduced-motion`

---

## 12. Next Steps

- [ ] Use UI UX Pro Max skill to validate/refine color tokens
- [ ] Use UI UX Pro Max skill to finalize font pairing
- [ ] Build shadcn/ui theme configuration based on these tokens
- [ ] Create Tailwind CSS configuration with design tokens
- [ ] Build component library in Storybook or equivalent
