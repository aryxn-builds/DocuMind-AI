# Settings Page Design System Overrides

> **Context:** Application and user configuration.

## Layout
- **Structure:** Two-column layout on desktop.
- **Left Column:** Vertical tabs (Profile, Account, API Keys, Appearance).
- **Right Column:** Configuration forms. Max-width constraint (e.g., 600px) for readability.

## Forms & Inputs
- Follow `MASTER.md` strictly. No elaborate floating labels. 
- Use standard labels above inputs.
- Use explicit helper text below inputs for technical settings (e.g., API key requirements).
- **Save Actions:** Sticky footer or inline button depending on form length. Provide clear success toasts (`--bg-elevated`, bordered) upon saving.
