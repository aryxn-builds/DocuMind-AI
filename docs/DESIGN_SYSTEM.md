# DocuMind AI — Design System Summary

> **Status:** Finalized Visual Direction
> **Primary Direction:** Premium Monochrome (Linear + Notion + premium AI workspace)
> **Master Reference:** See `design-system/MASTER.md` for the complete token and component specification.
> **Page-Specific Guidance:** See `design-system/pages/*.md`.

---

## 1. Core Visual Philosophy

DocuMind AI is a premium multimodal document intelligence SaaS platform. The product must feel like a serious, intelligent workspace for understanding documents — not an AI toy, generic chatbot, or cyberpunk dashboard.

**Key Adjectives:** Premium, minimal, sophisticated, technical, calm, precise, editorial, modern, trustworthy.

**Design Priorities:**
1. Usability
2. Visual hierarchy
3. Typography
4. Information density
5. Consistency
6. Premium visual polish

## 2. Monochrome Color System (Dark Mode Default)

The UI relies heavily on black, white, and neutral grays to communicate trust and focus the user's attention on their document content and the AI's analysis.

- **Backgrounds:** True black (`#000000`) to off-black (`#0A0A0A`)
- **Surfaces:** Dark gray (`#111111`) to elevated (`#171717`)
- **Borders:** Subtle (`#262626`) to strong (`#404040`)
- **Text:** High contrast white (`#FFFFFF`) for primary, scaling down to grays (`#A3A3A3`, `#737373`) for secondary/muted content.
- **Accents:** We avoid bright neon colors (purple, green, blue). Status colors (success, error, processing) are used sparingly and rely heavily on icons, labels, and borders for accessibility.

## 3. Typography & Spacing

- **Primary UI Font:** Inter (Sans-serif) — chosen for its excellent legibility at small sizes, modern aesthetic, and technical feel.
- **Secondary/Data Font:** JetBrains Mono — used for document metadata, IDs, extracted structured data, and code blocks.
- **Spacing:** A strict 4px/8px-based scale (4, 8, 12, 16, 24, 32, 48, 64, 96).

## 4. Key UI Characteristics

- **Border Radius:** Intentional and restrained. Avoid excessive pill-shaped components. Small (4px), Medium (8px), Large (12px).
- **Shadows:** Kept to a minimum. Hierarchy is established through contrast, borders, and spacing, not heavy elevation.
- **Iconography:** Lucide (SVG-based). Clean, consistent stroke widths. No emojis used as interface icons.
- **Animation:** Motion is used sparingly. 150–200ms micro-interactions for hover states and subtle transitions. Respects `prefers-reduced-motion`.

## 5. Application Layout

The core application utilizes a full-screen workspace layout.
The primary view is a **Three-Panel Desktop Workspace** (Documents sidebar, Document Viewer, AI Chat). This is optimized for desktop as document analysis is a deep-focus desktop workflow. On mobile, this adapts into a tabbed/sheet interface.

## 6. Implementation Rule

**Do not introduce ad-hoc styles.** Any future frontend implementation must strictly follow the tokens and components defined in `design-system/MASTER.md`.
