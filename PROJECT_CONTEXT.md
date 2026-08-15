# DocuMind AI — Project Context

## 1. Project Identity

- **Product name:** DocuMind AI
- **Product type:** Multimodal Document Intelligence Web Application / SaaS Platform
- **Current development stage:** Documentation & Design Definition Phase (No application code written yet)
- **One-sentence description:** DocuMind AI is a single, premium workspace where any document can be uploaded, understood multimodally, and queried with AI — with every answer traceable back to source evidence.

---

## 2. What We Are Building

DocuMind AI transforms how knowledge workers interact with their documents. Users can upload PDFs, DOCX files, and images. The system processes text, tables, charts, and scanned content to enable intelligent search, question-answering, summarization, comparison, and structured extraction. 

**Core Purpose:** To close the gap between simple PDF keyword-search tools and complex enterprise document management systems.
**Primary User Problem:** Knowledge workers spend significant time manually searching through documents, cross-referencing information, and extracting data from unstructured sources.
**Main Product Experience:** A premium AI productivity workspace where users can upload documents and get answers that are directly grounded in source evidence with precise citations.
**What Makes it Different:** It is multimodal by default (handles tables/charts/images natively) and prioritizes evidence over assertion (every answer is traceable to source material).

---

## 3. Target Users

- **Researchers & academics:** Read and cross-reference papers; need multi-document Q&A and citation tracing.
- **Legal professionals:** Review contracts and regulations; need precise extraction, comparison, and evidence.
- **Business analysts:** Analyze reports with charts/tables; need table reasoning and summarization.
- **Students:** Study textbooks and papers; need Q&A, summarization, and search.
- **Technical professionals:** Reference technical docs; need targeted search and structured extraction.

---

## 4. Core Product Capabilities

### P0 / MVP
- User authentication (Signup/Login/Logout via Supabase)
- User-specific document storage in Supabase
- PDF/DOCX/image upload
- Document processing pipeline (extract text, tables, metadata via Docling)
- OCR for scanned documents
- Chunking and embeddings
- Vector search via Qdrant
- RAG-based document Q&A
- Evidence-backed citations linking to source pages/sections
- Chat history per document
- Secure user isolation (RLS)
- Document viewer alongside chat

### P1
- Multi-document chat
- Document comparison
- Collections for grouping documents
- Table reasoning
- Chart/image understanding
- Document summaries
- Structured data extraction
- Document actions (rename, delete, re-process)
- AI model routing based on task complexity
- Chat memory (multi-turn context)
- Real-time processing status / job tracking

### P2
- AI-generated visual summaries
- PDF/report export
- Document sharing via links
- Team collaboration features
- Public REST/GraphQL API
- Browser extension for web clipping

---

## 5. Core User Journey

1. **Landing** → User visits marketing page
2. **Authentication** → Signs up or logs in
3. **Dashboard** → Arrives at document list / empty state
4. **Upload** → Uploads a document (PDF/DOCX/image)
5. **Document Processing** → Sees processing indicator until document is 'ready'
6. **Document Workspace** → Opens document in a split viewer (Document Viewer + Chat Panel)
7. **AI Interaction** → Asks a question in the chat panel
8. **Citations / Sources** → Receives AI-generated answer with citations, clicks citation to jump to source
9. **History** → Views chat history and past conversations

---

## 6. Current Technology Stack

| Category | Technology | Status | Purpose | Source |
|---|---|---|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui | DECIDED | UI, interactions, auth state | ARCHITECTURE.md |
| Backend | FastAPI, Python | DECIDED | API, RAG pipeline, orchestration | ARCHITECTURE.md |
| Background Workers | Celery, Redis | DECIDED | Async processing, embeddings | ARCHITECTURE.md |
| Authentication | Supabase Auth (JWT) | DECIDED | User auth, session management | ARCHITECTURE.md |
| Database | Supabase PostgreSQL | DECIDED | Users, metadata, conversations | ARCHITECTURE.md |
| Vector Database | Qdrant | DECIDED | Embeddings, semantic search | ARCHITECTURE.md |
| Document Processing | Docling | DECIDED | Extract text/tables | ARCHITECTURE.md |
| OCR | RapidOCR / Tesseract | OPEN / UNCLEAR | Process scanned images | PRODUCT_SPEC.md |
| AI Gateway | Custom Python abstraction | DECIDED | Provider routing | AI_ARCHITECTURE.md |
| LLM | Groq, Gemini, Ollama | DECIDED | Text generation, Q&A | AI_ARCHITECTURE.md |
| Multimodal AI | Gemini (MVP) | PROPOSED | Vision tasks, chart understanding | AI_ARCHITECTURE.md |
| Embeddings | BGE (bge-base-en-v1.5) | PROPOSED | Chunk embeddings | AI_ARCHITECTURE.md |
| Storage | Supabase Storage | DECIDED | Original uploaded documents | ARCHITECTURE.md |
| Observability | Langfuse | DECIDED | LLM tracing | ARCHITECTURE.md |
| Testing | Pytest (Backend) / Jest or Playwright (Frontend) | OPEN / UNCLEAR | Unit/E2E testing | AGENTS.md |
| Deployment | Docker Compose | PROPOSED | Initial deployment & dev | ARCHITECTURE.md |

---

## 7. Architecture Summary

DocuMind AI is a decoupled full-stack application. The Next.js frontend communicates exclusively via a REST API to a Python FastAPI backend, except for authentication, which interacts directly with Supabase Auth using the client SDK.

The FastAPI backend enforces JWT authentication and RLS via Supabase PostgreSQL, manages metadata, and orchestrates tasks. Heavy lifting (document extraction, chunking, embedding) is offloaded to background Celery workers. Vector embeddings are stored in Qdrant, and original files reside in Supabase Storage. LLM requests go through a custom AI Gateway abstraction layer for routing (Groq, Gemini, Ollama) and tracing (Langfuse).

---

## 8. Data Architecture

- **Supabase PostgreSQL:** Stores structured relational data: user profiles (synced from Supabase Auth), document metadata, conversations, messages, citations, collections, and chunk positional metadata. Enforces Row Level Security (RLS) so users only access their own data.
- **Supabase Auth:** Handles user registration and issues JWTs.
- **Supabase Storage:** Stores the original uploaded files in a private bucket. Accessed via short-lived signed URLs.
- **Qdrant:** Stores chunk vector embeddings and payload metadata (`user_id`, `document_id`). Does not duplicate relational data, but filters strictly by `user_id` on every search.
- **Document files:** Uploaded securely to Supabase Storage.
- **Metadata:** Position data, page numbers, and chunk previews are kept in PostgreSQL.
- **Embeddings/chunks:** Vectors are strictly in Qdrant.
- **Conversations/messages:** Stored in PostgreSQL with relationships to documents and citations.

---

## 9. AI Architecture

- **AI Gateway:** Custom Python abstraction that routes requests across multiple providers, handling retries, fallback chains, and Langfuse tracing.
- **LLM providers:** Groq (primary for fast text), Gemini (multimodal), Ollama (local/private fallback).
- **Model routing:** Capability-based routing is PROPOSED (e.g., text vs vision).
- **Multimodal processing:** Vision models convert images/charts to text descriptions during ingestion so they can be embedded normally.
- **Document understanding:** Docling extracts text/tables. Scanned docs use OCR.
- **Embeddings:** Local BGE-based model from Sentence Transformers.
- **Retrieval:** Qdrant similarity search with strict `user_id` filtering.
- **RAG:** Context is constructed from top-K chunks and conversation history, bounded by token limits.
- **Citations:** LLM is instructed to generate inline citation markers. Backend extracts them, validates them against retrieved chunks (existence, ownership, content match), and stores them.
- **Evaluation:** Offline automated evaluation framework using Recall/Precision for retrieval, and LLM-as-judge for generation quality.

---

## 10. Authentication & Security

- **Authentication:** Supabase Auth (Email/Password). Backend verifies JWT signature and expiry on every `/api/*` route.
- **Authorization:** Enforced at both the API layer (JWT `sub` claim check) and the database layer.
- **User isolation:** Strict multi-tenant isolation.
- **Row Level Security (RLS):** Enabled on all user-scoped PostgreSQL tables (`user_id = auth.uid()`).
- **Document ownership:** Verified on every request. Users can only CRUD their own documents.
- **Vector isolation:** Qdrant lacks built-in RLS; the backend MUST include a `user_id` metadata filter on every single Qdrant query.
- **Storage security:** Supabase Storage policies ensure users can only upload/download to their own folder paths.
- **Secret management:** Secrets (API keys, Supabase Service Role Key) are stored exclusively in backend environment variables and NEVER exposed to the frontend or committed to source control.
- **Prompt injection considerations:** System prompts are strictly separated from user queries and document context, with explicit instructions to treat context as data.

---

## 11. Design Direction

- **Visual Identity:** Premium Monochrome workspace. Technical, trustworthy, and precise (similar to Linear/Notion). No rainbow gradients or heavy glassmorphism.
- **Primary Colors:** True blacks (`#000000`), off-blacks (`#0A0A0A`), crisp whites (`#FFFFFF`), with semantic colors reserved strictly for status/alerts.
- **Typography:** Inter for standard UI headings/body; JetBrains Mono for data, IDs, and code blocks.
- **Dark/Light Mode:** Designed Dark-mode-first.
- **Spacing Philosophy:** Strict 4px/8px grid system.
- **Border Radius:** Minimal (e.g., 8px for containers).
- **Iconography:** Lucide icons.
- **Animation Philosophy:** Fast (150-200ms), subtle fades/slides. No bouncy interactions.
- **Accessibility:** Minimum 4.5:1 contrast for text, 2px solid keyboard focus rings, respect for `prefers-reduced-motion`.
- **Responsive Approach:** Desktop-first.
- **Major Layouts:**
  - **Document Workspace:** Full-height, resizable three-panel desktop layout (Sidebar, Document Viewer, AI Chat). Breaks down to a tab/bottom-sheet layout on mobile.
  - **Dashboard:** Grid-based functional entry points (Quick Actions, Recent Documents).
  - **Chat:** Transparent backgrounds for AI responses to look like structured text, clear Markdown typography, and prominent interactive citation badges.

---

## 12. Important Product & Architecture Decisions

### DECIDED
- Application uses Next.js, Tailwind, shadcn/ui, FastAPI, Celery, Supabase (PostgreSQL, Auth, Storage), and Qdrant.
- All LLM calls pass through a custom AI Gateway.
- Supabase JWT validation is enforced on all API routes (except health).
- Row Level Security (RLS) is required on all PostgreSQL tables.
- Qdrant searches MUST filter by `user_id`.
- The frontend does not talk to LLMs or Qdrant directly.
- The visual design system is Premium Monochrome (Inter + JetBrains Mono).
- Citations must be structurally validated by the backend before returning to the user.
- Health monitoring endpoints are for legitimate operational monitoring, not for bypassing cloud provider inactivity policies.

### PROPOSED
- Single Qdrant collection with payload-based filtering (instead of per-user collections).
- Gemini for MVP vision tasks; Ollama VLM as a future alternative.
- Local BGE embedding model (`bge-base-en-v1.5`).
- Capability-based routing rules in the AI Gateway.
- Docker Compose for initial deployment.
- Rate limiting at the API layer via Redis.

### OPEN / UNCLEAR
- **OCR Engine:** RapidOCR vs Tesseract.
- **Reranking:** Cross-encoder reranking included in MVP vs deferred to P1.
- **Chunking Strategy:** Fixed-size vs semantic vs hybrid.
- **Streaming:** Whether to support SSE streaming for chat responses in MVP.
- **Production Deployment Target:** VPS vs cloud VM vs serverless.
- **Maximum File Upload Size.**
- **LLM Cost Model:** Viability of free tiers for production load.
- **Frontend Testing Framework:** Jest vs Playwright vs Vitest.

---

## 13. Free-Tier & Cost Philosophy

The project follows a free-first development strategy utilizing Supabase Free Tier, Groq/Gemini free tiers, and open-source self-hosted components (Qdrant, Redis, Ollama, Langfuse). The AI Gateway is specifically designed to ensure provider portability, preventing lock-in and allowing seamless switching if free limits are exhausted. 

There is NO guarantee that free tiers will sustain production traffic, and the system design must remain provider-agnostic.

---

## 14. Health Monitoring

Legitimate operational health-monitoring is planned via `/health` (liveness) and `/ready` (readiness) endpoints. 
- **Purpose:** To detect backend process crashes and verify critical infrastructure dependencies (PostgreSQL, Qdrant) are reachable.
- **Constraints:** Endpoints must be lightweight, read-only, and MUST NOT expose secrets, credentials, internal network topologies, or user data.
- **Policy:** This monitoring is NOT intended, and MUST NOT be used, as a mechanism to artificially game or bypass cloud-provider inactivity policies (e.g., Supabase Free tier pausing).
- **Status:** Planned / Not Implemented.

---

## 15. Development Rules

- Inspect existing code before modifying it. Never blindly overwrite.
- Follow the documented architecture (`ARCHITECTURE.md`, `DATABASE_SCHEMA.md`).
- Follow the design system (`DESIGN_SYSTEM.md`, `design-system/MASTER.md`).
- Never bypass authentication or RLS. Every API endpoint requires JWT verification.
- Every Qdrant search must filter by `user_id`.
- Health checks are for operational monitoring only and belong at the infrastructure boundary.
- Do not silently change technology choices or introduce dependencies without justification.
- Ask for clarification when a requirement conflicts with the architecture.
- Do not assume PROPOSED decisions are implemented.

---

## 16. Documentation Map

| File | Purpose | Canonical For |
|---|---|---|
| `PRODUCT_SPEC.md` | Product requirements, user personas, use cases | Features and MVP boundary |
| `ARCHITECTURE.md` | System architecture, components, data flow | Overall technical design |
| `DATABASE_SCHEMA.md` | Relational and vector data model | PostgreSQL tables and RLS |
| `AI_ARCHITECTURE.md` | AI pipeline, Gateway, RAG, embeddings | LLM handling and citations |
| `API_SPEC.md` | REST API contracts and endpoints | API structure and request/response |
| `SECURITY.md` | Security rules, auth, isolation, secrets | Security constraints |
| `EVALUATION.md` | Automated evaluation framework | Retrieval and generation metrics |
| `DESIGN_SYSTEM.md` | High-level design direction | Visual philosophy |
| `USER_FLOWS.md` | Screen-by-screen user journeys | UI flows |
| `AGENTS.md` | AI development behavior rules | Rules for AI agents |
| `design-system/MASTER.md` | Detailed visual system and tokens | Colors, typography, spacing |

---

## 17. Current Project Status

### Completed / Documented
- Product Requirements and MVP boundary.
- Full System Architecture and component diagram.
- Database schema (PostgreSQL ERD + Qdrant payload structure).
- AI Architecture (Gateway, RAG, Vision).
- API Specification (REST contracts).
- Security Architecture (Auth, RLS, Storage, Vectors).
- User Flows and Evaluation Framework.
- Design System definition (Premium Monochrome).

### Planned
- Complete frontend UI development based on the defined design system.
- Backend API and RAG pipeline implementation.

### Not Started
- No frontend application code (Next.js, Tailwind) has been written.
- No backend code (FastAPI, Celery, AI Gateway) has been written.
- No infrastructure (Docker Compose, Supabase tables) has been provisioned.

---

## 18. Current Development Position

We have finished the documentation and design definition phase. All core structural, architectural, and visual decisions for DocuMind AI are documented. 

Next step requires explicit confirmation. (Frontend scaffolding or Backend database initialization is likely next).

---

## 19. Known Contradictions / Open Issues

- **Issue:** Specific OCR engine to use for scanned documents.
  **Status:** OPEN
  **Files:** `PRODUCT_SPEC.md`

- **Issue:** Whether to include cross-encoder reranking in MVP.
  **Status:** OPEN
  **Files:** `AI_ARCHITECTURE.md`

- **Issue:** Should chat responses use SSE streaming in MVP?
  **Status:** OPEN
  **Files:** `API_SPEC.md`, `AI_ARCHITECTURE.md`

- **Issue:** Maximum allowed file upload size.
  **Status:** OPEN
  **Files:** `PRODUCT_SPEC.md`, `API_SPEC.md`, `SECURITY.md`

- **Issue:** Exact frontend testing framework (Jest, Playwright, or Vitest).
  **Status:** OPEN
  **Files:** `AGENTS.md`

---

## 20. AI Model Handoff Instructions

When entering the project, a new AI agent must follow these principles:

1. Read `PROJECT_CONTEXT.md` first.
2. Read `AGENTS.md` before making changes.
3. Identify the relevant canonical document.
4. Read that canonical document before modifying its area.
5. Treat DECIDED decisions as established.
6. Treat PROPOSED decisions as unconfirmed.
7. Treat OPEN / UNCLEAR decisions as unresolved.
8. Never silently resolve contradictions.
9. Inspect existing code before modifying code.
10. Do not create duplicate documentation.
11. Do not introduce new technology without explicit justification.
12. Keep documentation synchronized with implementation.

==================================================
CANONICAL DOCUMENT RULE

`PROJECT_CONTEXT.md` is a handoff and navigation document.

It does not override canonical project documentation.

When detailed information is required, the following documents take precedence:

- `PRODUCT_SPEC.md` → product requirements
- `ARCHITECTURE.md` → system architecture
- `DATABASE_SCHEMA.md` → database/data model
- `AI_ARCHITECTURE.md` → AI/ML architecture
- `API_SPEC.md` → API contracts
- `SECURITY.md` → security requirements
- `DESIGN_SYSTEM.md` → design system
- `design-system/MASTER.md` → detailed visual system
- `AGENTS.md` → AI/development behavior rules
