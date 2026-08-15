# Document Workspace Design System Overrides

> **Context:** The core interface for reading and interacting with a document.

## 1. Desktop Layout (Three-Panel)

The desktop experience relies on a full-height, resizable three-panel layout.
- **Left Panel (Sidebar):** Navigation (Documents, Collections, History). Width ~260px.
- **Center Panel (Document Viewer):** The PDF/Image rendering area. Flexible width. Background `--bg-surface` to create contrast with the actual document pages (which are usually white).
- **Right Panel (AI Chat):** The conversational interface. Width ~400px.

**Resizing:** Include subtle, 1px vertical borders (`--border-subtle`) between panels with hoverable drag handles (cursor: col-resize).

## 2. Document Viewer Specifics

- **Pages:** Actual document pages render with a crisp shadow (`--shadow-md`) to lift them off the `--bg-surface`.
- **Selected Text:** Highlight color should be a semi-transparent `--accent-primary` or a muted gray to fit the monochrome theme.
- **Citation Highlights:** When a citation is clicked in the chat, the corresponding section in the document should momentarily pulse or receive a subtle border highlight to draw the eye.

## 3. Mobile Layout Transformation

Do NOT force three panels on mobile.
- Use a tabbed interface or bottom sheet.
- Default view: Document Viewer.
- Action: "Open Chat" button floating at the bottom or top, triggering the Chat panel to slide up over the document (or push it away).
