# DocuMind AI

Multimodal document intelligence — upload, understand, and reason over your documents with AI.

> **Project Status: Scaffolding complete. Product functionality is not implemented yet.**

---

## What is DocuMind AI?

DocuMind AI is a web-based AI workspace where users upload documents (PDFs, DOCX, images) and interact with them through natural language. The system extracts text, tables, charts, and scanned content, then enables intelligent Q&A backed by citations that point to exact source pages and sections.

Every answer is grounded in your documents — not hallucinated.

---

## Architecture

```
┌──────────────┐        ┌──────────────┐        ┌──────────────────┐
│   Next.js    │──────▶ │   FastAPI    │──────▶ │   AI Gateway     │
│   Frontend   │        │   Backend    │        │                  │
│              │        │              │        │  ┌─ Groq (text)  │
│  TypeScript  │        │   Python     │        │  ├─ Gemini (vis) │
│  Tailwind    │        │   FastAPI    │        │  └─ Ollama (opt) │
│  shadcn/ui   │        │   BgTasks    │        │                  │
└──────────────┘        └──────┬───────┘        └──────────────────┘
                               │
               ┌───────────────┼───────────────┐
               │               │               │
       ┌───────▼──────┐  ┌─────▼────┐  ┌───────▼─────┐
       │  Supabase    │  │  Qdrant  │  │  Langfuse   │
       │  Auth + DB   │  │ Vectors  │  │  Tracing    │
       │  + Storage   │  │          │  │             │
       └──────────────┘  └──────────┘  └─────────────┘
```

**Background jobs:** FastAPI `BackgroundTasks` (MVP). No Redis or Celery.  
**Chat streaming:** Server-Sent Events (SSE).  
**Upload flow:** Backend-orchestrated atomic registration (prevents orphaned files).

---

## Repository Structure

```
DocuMind AI/
├── apps/
│   ├── web/           # Next.js frontend (TypeScript, Tailwind, shadcn/ui)
│   └── api/           # FastAPI backend (Python)
├── packages/
│   └── shared/        # Shared types (placeholder — see packages/shared/README.md)
├── infra/
│   └── docker/        # Docker service fragments
├── supabase/
│   └── migrations/    # SQL migrations (not created yet)
├── docs/
│   ├── DECISION_LOG.md
│   └── decisions/
├── docker-compose.yml  # Local dev: Qdrant
├── .env.example        # Environment variable template
├── AGENTS.md           # Development rules & conventions
└── PROJECT_CONTEXT.md  # AI model handoff document
```

---

## Technology Stack

| Layer              | Technology                           |
|--------------------|--------------------------------------|
| Frontend           | Next.js 16, TypeScript, Tailwind v4  |
| Backend            | Python 3.14, FastAPI                 |
| Background Jobs    | FastAPI BackgroundTasks (MVP)        |
| Authentication     | Supabase Auth                        |
| Database           | Supabase PostgreSQL                  |
| File Storage       | Supabase Storage                     |
| Vector Database    | Qdrant                               |
| Document Processing| Docling (not yet implemented)        |
| Embeddings         | Gemini API (gemini-embedding-2)      |
| LLM — Text         | Groq (primary), Gemini (fallback)    |
| LLM — Vision       | Gemini                               |
| LLM — Local        | Ollama (optional)                    |
| Observability      | Langfuse                             |
| Containerization   | Docker                               |

---

## Local Development

### Prerequisites

- **Node.js** 18+ (tested with v24)
- **Python** 3.11+ (tested with 3.14)
- **Docker Desktop** — for running Qdrant locally
- **Supabase account** — [supabase.com](https://supabase.com) (free tier)
- **Groq API key** — [console.groq.com](https://console.groq.com) (free tier)
- **Google Gemini API key** — [aistudio.google.com](https://aistudio.google.com) (free tier)

---

### 1. Clone and configure environment

```bash
# Copy the environment template
cp .env.example .env

# Edit .env and fill in your actual values
# See .env.example for required variables
```

---

### 2. Start Qdrant (local vector database)

```bash
# Requires Docker Desktop
docker compose up -d qdrant

# Verify Qdrant is running
curl http://localhost:6333/healthz
```

---

### 3. Start the backend (FastAPI)

```bash
cd apps/api

# Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start the development server
python -m uvicorn app.main:app --reload --port 8000
```

**Verify backend:**

```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"0.1.0"}

curl http://localhost:8000/ready
# → {"status":"ready","version":"0.1.0"}

curl http://localhost:8000/api/v1/ping
# → {"ping":"pong"}
```

API docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 4. Start the frontend (Next.js)

```bash
cd apps/web

# Dependencies were installed during scaffolding
# If running fresh: npm install

npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

### 5. TypeScript check

```bash
cd apps/web
npx tsc --noEmit
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [PRODUCT_SPEC.md](./PRODUCT_SPEC.md) | Product vision, features, personas, MVP scope |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, component design, flows |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | Relational data model, ER diagram |
| [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md) | AI gateway, RAG pipeline, embeddings, citations |
| [API_SPEC.md](./API_SPEC.md) | REST API endpoint specification |
| [SECURITY.md](./SECURITY.md) | Security architecture, RLS, secrets management |
| [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) | Visual design direction |
| [design-system/MASTER.md](./design-system/MASTER.md) | Canonical design tokens and component rules |
| [USER_FLOWS.md](./USER_FLOWS.md) | User journeys and flow diagrams |
| [AGENTS.md](./AGENTS.md) | AI development rules and conventions |
| [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md) | AI model handoff context document |
| [docs/DECISION_LOG.md](./docs/DECISION_LOG.md) | Architectural decision record |

---

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 0 | Documentation & architecture | ✅ Complete |
| Phase 1 | Project scaffolding | ✅ Complete |
| Phase 2 | Authentication & database | 🔲 Not started |
| Phase 3 | Document ingestion pipeline | 🔲 Not started |
| Phase 4 | RAG & chat | 🔲 Not started |
| Phase 5 | UI implementation | 🔲 Not started |

---

## License

TBD
