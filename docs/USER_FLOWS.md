# DocuMind AI — User Flows

> **Status:** Draft v1.0
> **Last updated:** 2026-08-15

---

## 1. Landing → Signup → Dashboard

```mermaid
flowchart TD
    A[User visits landing page] --> B{Has account?}
    B -->|No| C[Click 'Get Started' / 'Sign Up']
    C --> D[Signup form<br/>Email + Password]
    D --> E{Valid input?}
    E -->|No| F[Show validation errors]
    F --> D
    E -->|Yes| G[Supabase creates account]
    G --> H[Email confirmation sent]
    H --> I[User confirms email]
    I --> J[Redirect to Dashboard]
    J --> K[Empty state:<br/>'Upload your first document']

    B -->|Yes| L[Click 'Log In']
    L --> M[Login flow - see Flow 2]
```

**Screens involved:**
1. Landing page (marketing)
2. Signup form
3. Email confirmation notice
4. Dashboard (empty state)

---

## 2. Login → Dashboard

```mermaid
flowchart TD
    A[User visits login page] --> B[Enter email + password]
    B --> C{Credentials valid?}
    C -->|No| D[Show error message]
    D --> B
    C -->|Yes| E[Supabase returns JWT]
    E --> F[Redirect to Dashboard]
    F --> G{Has documents?}
    G -->|Yes| H[Show document list<br/>sorted by recent]
    G -->|No| I[Show empty state<br/>with upload CTA]
```

**Screens involved:**
1. Login form
2. Dashboard (populated or empty)

---

## 3. Upload Document → Processing → Ready

```mermaid
flowchart TD
    A[User on Dashboard] --> B[Click 'Upload' or<br/>drag-and-drop file]
    B --> C{File type valid?<br/>PDF / DOCX / PNG / JPG}
    C -->|No| D[Show rejection message<br/>with accepted types]
    C -->|Yes| E{File size within limit?}
    E -->|No| F[Show size limit error]
    E -->|Yes| G[Upload to Supabase Storage]
    G --> H[Create document record<br/>status: pending]
    H --> I[Show document card<br/>with processing indicator]
    I --> J[Celery worker picks up job]
    J --> K[Extract text + tables]
    K --> L{Scanned content?}
    L -->|Yes| M[Run OCR]
    L -->|No| N[Continue]
    M --> N
    N --> O[Chunk document]
    O --> P[Generate embeddings]
    P --> Q[Store in Qdrant + PostgreSQL]
    Q --> R[Update status: ready]
    R --> S[Document card updates<br/>to 'Ready' state]
    S --> T[User can now open<br/>and ask questions]

    J -->|Error| U[Update status: failed]
    U --> V[Show error on document card<br/>with retry option]
```

**Screens involved:**
1. Dashboard with upload zone
2. Upload progress indicator
3. Document card (processing → ready → failed states)

**OPEN DECISION:** Whether processing status updates via polling or real-time (WebSocket/SSE).

---

## 4. Open Document → Ask Question → Answer → Citation → Page

```mermaid
flowchart TD
    A[User clicks document<br/>on Dashboard] --> B[Open Document View]
    B --> C[Left: Document Viewer<br/>Right: Chat Panel]
    C --> D[User types question<br/>in chat input]
    D --> E[Send to backend<br/>POST /api/chat]
    E --> F[Backend: embed query]
    F --> G[Backend: search Qdrant<br/>filtered by user + document]
    G --> H[Backend: retrieve top-K chunks]
    H --> I[Backend: construct prompt<br/>with context + history]
    I --> J[Backend: call AI Gateway → LLM]
    J --> K[Backend: parse response<br/>+ extract citations]
    K --> L[Return answer + citations<br/>to frontend]
    L --> M[Display AI answer<br/>with citation badges]
    M --> N{User clicks citation?}
    N -->|Yes| O[Highlight cited section<br/>in document viewer]
    N -->|No| P[User types next question<br/>or exits]
    O --> P
    P --> Q{Continue chatting?}
    Q -->|Yes| D
    Q -->|No| R[Return to Dashboard<br/>or close document]
```

**Screens involved:**
1. Document view (split: viewer + chat)
2. Chat panel with messages and citations
3. Document viewer with citation highlighting

**Key interactions:**
- Chat messages appear in real-time as the LLM streams (if streaming is supported)
- Citation badges [1] [2] are clickable
- Clicking a citation scrolls the document viewer to the relevant page/section
- Previous conversation turns are visible and scrollable

---

## 5. Chat History

```mermaid
flowchart TD
    A[User opens document] --> B[Chat panel shows<br/>conversation list]
    B --> C{Previous conversations?}
    C -->|Yes| D[Show list of past conversations<br/>with titles and dates]
    C -->|No| E[Show empty state:<br/>'Start a new conversation']
    D --> F{User action}
    F -->|Select existing| G[Load conversation<br/>with full message history]
    F -->|New conversation| H[Create new conversation<br/>with empty chat]
    G --> I[User continues<br/>asking questions]
    H --> I
    E --> H
```

**Screens involved:**
1. Conversation list (sidebar or dropdown in chat panel)
2. Chat panel with loaded history

---

## 6. Multi-Document Chat (P1)

```mermaid
flowchart TD
    A[User on Dashboard] --> B[Select multiple documents<br/>via checkboxes]
    B --> C[Click 'Chat with selected']
    C --> D[Create multi-document<br/>conversation]
    D --> E[Chat panel opens<br/>with document list indicator]
    E --> F[User asks question]
    F --> G[Backend: search Qdrant<br/>across selected document IDs]
    G --> H[Retrieve chunks from<br/>multiple documents]
    H --> I[Construct prompt with<br/>multi-source context]
    I --> J[LLM generates answer<br/>with per-document citations]
    J --> K[Display answer with<br/>document-labeled citations]
    K --> L{User clicks citation?}
    L -->|Yes| M[Open/navigate to<br/>source document + page]
    L -->|No| N[Continue conversation]
```

**Screens involved:**
1. Dashboard with multi-select mode
2. Multi-document chat view
3. Citation with document source labels

---

## 7. Document Comparison (P1)

```mermaid
flowchart TD
    A[User selects two documents] --> B[Click 'Compare']
    B --> C[Comparison view opens<br/>side-by-side or diff]
    C --> D[System analyzes structure<br/>and content differences]
    D --> E[Display comparison results:<br/>similarities, differences, key changes]
    E --> F{User asks follow-up<br/>question about differences?}
    F -->|Yes| G[Chat with comparison context]
    F -->|No| H[User reviews results<br/>or exits]
    G --> I[AI answers with<br/>citations from both documents]
    I --> H
```

**Screens involved:**
1. Comparison selection
2. Comparison results view
3. Comparison chat panel

**OPEN DECISION:** Comparison UI layout (side-by-side panels, unified diff view, or structured summary).

---

## 8. Create Collection → Add Documents → Ask Collection (P1)

```mermaid
flowchart TD
    A[User clicks 'New Collection'] --> B[Enter collection name<br/>+ optional description]
    B --> C[Collection created]
    C --> D[Add documents to collection<br/>from existing uploads]
    D --> E{Documents selected}
    E -->|Yes| F[Documents added<br/>to collection]
    F --> G[Open collection view]
    G --> H[See list of documents<br/>in collection]
    H --> I{User action}
    I -->|Chat| J[Open collection chat]
    I -->|Add more| D
    I -->|Remove doc| K[Remove document<br/>from collection]
    J --> L[Ask question across<br/>all collection documents]
    L --> M[Same RAG flow as<br/>multi-document chat]
```

**Screens involved:**
1. Collection creation modal/form
2. Collection detail view (document list)
3. Document picker (add to collection)
4. Collection chat

---

## 9. Settings

```mermaid
flowchart TD
    A[User clicks profile/settings] --> B[Settings page opens]
    B --> C{Settings section}
    C -->|Profile| D[Edit name, avatar]
    C -->|Appearance| E[Theme: dark/light/system]
    C -->|Account| F[Change password,<br/>delete account]
    D --> G[Save changes]
    E --> G
    F --> H{Delete account?}
    H -->|Yes| I[Confirmation dialog]
    I --> J[Delete all user data<br/>Documents, conversations,<br/>vectors, files]
    J --> K[Redirect to landing page]
    H -->|No| G
```

**Screens involved:**
1. Settings page with section tabs
2. Confirmation dialogs for destructive actions

**OPEN DECISION:** Additional settings (notification preferences, AI model preferences, default behavior). Defer to post-MVP.

---

## 10. Logout

```mermaid
flowchart TD
    A[User clicks 'Log Out'<br/>in sidebar or settings] --> B[Supabase client<br/>signs out]
    B --> C[Clear local state<br/>and tokens]
    C --> D[Redirect to<br/>login page]
```

**Screens involved:**
1. Any screen with logout action
2. Login page (post-logout)

---

## 11. Screen Inventory

| Screen | Priority | Flows |
|--------|----------|-------|
| Landing page | P0 | 1 |
| Signup form | P0 | 1 |
| Login form | P0 | 2 |
| Dashboard (documents list) | P0 | 2, 3, 6, 7, 8 |
| Document view (viewer + chat) | P0 | 4, 5 |
| Upload zone / modal | P0 | 3 |
| Settings page | P0 | 9 |
| Collection detail view | P1 | 8 |
| Multi-document chat | P1 | 6 |
| Comparison view | P1 | 7 |
| Empty states (per screen) | P0 | All |
| Error states (per screen) | P0 | All |
