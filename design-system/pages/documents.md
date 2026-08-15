# Documents Page Design System Overrides

> **Context:** The library view managing all uploaded files.

## Layout
- **Header:** Title on left, actions (Upload, Bulk Delete) on right.
- **Controls:** A single clean toolbar for Search, Filter (by type/date), and Sort.
- **View:** A data table or structured list.

## Document List / Table
- **Columns:** Name, Upload Date, Size, Status.
- **Typography:** Use JetBrains Mono for sizes and dates for tabular alignment.
- **Status Indicators:** Use minimal text + small colored dot (e.g., green for Ready, blue for Processing, red for Error).

## Upload Interaction
- **Dropzone:** A dashed border (`--border-strong`) area.
- **Drag State:** When dragging a file, the background shifts slightly (`--bg-surface`) to indicate it's active.
- **Progress:** Show a subtle linear progress bar during upload and processing. Do not show fake percentages; state "Extracting..." or "Indexing...".
