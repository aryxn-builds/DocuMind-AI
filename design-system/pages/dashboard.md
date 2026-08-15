# Dashboard Design System Overrides

> **Context:** The main landing screen after authentication.

## Purpose
The dashboard exists to provide immediate, useful access to the user's workflow. It must avoid meaningless analytics or empty charts.

## Layout
- **Structure:** Grid-based layout within the main content area (using standard `MASTER.md` padding).
- **Sections:**
  - **Quick Actions:** Upload document, New Chat (prominent `accent-primary` buttons).
  - **Recent Documents:** A horizontal scroll or grid of document cards.
  - **Recent Conversations:** List view of recent chat sessions.
  - **Processing Status:** A dedicated small panel showing documents currently being indexed.

## Visuals
- Keep the dashboard sparse and uncluttered. Use `--bg-base` for the main area and `--bg-elevated` for the section cards.
