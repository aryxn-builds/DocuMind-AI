# Chat Experience Design System Overrides

> **Context:** The conversational interface within the workspace.

## Philosophy
The chat must feel like a serious research interface, not a messaging app. Avoid oversized, colorful chat bubbles.

## Chat Layout
- **Container:** Standard padding (`--space-4`).
- **User Message:** Right-aligned text block. Background `--bg-surface`. Very subtle border radius (`8px`).
- **AI Response:** Left-aligned. **Transparent background**. It should look like structured text appearing directly on the panel.
- **Typography:** The AI response uses strong Markdown styling. `h1`-`h4` are clearly differentiated. Code blocks use JetBrains Mono with a `--bg-surface` background.

## Composer (Input Area)
- **Position:** Fixed at the bottom of the chat panel.
- **Style:** A solid block (`--bg-elevated`) with `--border-subtle`. Radius `8px`.
- **Actions:** Minimal icons (Lucide) for "Attach/Add Context" and "Send".

## Citations
Citations are the most critical differentiating feature.
- **Inline:** `[1]`, `[2]`. Styled as small, interactive badges. Font: JetBrains Mono.
- **Hover:** Show a tooltip (`--bg-floating`) with a snippet of the source text.
- **Source Cards:** Displayed at the end of the AI response. Small horizontal cards detailing the Document Name and Page.

## Animations
- **Text Generation:** Use a smooth streaming effect. Do not use bouncy or overly dramatic typing indicators. A simple pulsing cursor or 3-dot fade is sufficient.
