# DocuMind AI

**Multimodal document intelligence platform — upload, understand, and reason over your documents with AI.**

> ⚠️ **Project Status:** Documentation & Architecture phase. No application code has been written yet.

---

## What is DocuMind AI?

DocuMind AI is a web-based AI workspace where users upload documents (PDFs, DOCX, images) and interact with them through natural language. The system extracts text, tables, charts, and scanned content, then enables intelligent Q&A with evidence-backed citations pointing to exact source pages and sections.

Every answer is grounded in your documents — not hallucinated.

---

## Planned Features

### MVP (P0)
- User authentication and secure isolation
- PDF, DOCX, and image upload with processing
- OCR for scanned documents
- Text and table extraction
- Semantic search over document content
- RAG-based document Q&A
- Evidence-backed citations with page references
- Chat history per document
- Document viewer alongside chat

### Enhanced Intelligence (P1)
- Multi-document chat
- Document comparison
- Collections (group documents)
- Table and chart understanding
- Document summaries
- Structured data extraction

### Platform (P2)
- PDF/report export
- Document sharing
- Team collaboration
- Public API
- Browser extension

---

## Architecture Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Next.js    │────▶│   FastAPI    │────▶│  AI Gateway  │
│   Frontend   │     │   Backend    │     │              │
│              │     │              │     │  ┌─ Groq     │
│  TypeScript  │     │   Python     │     │  ├─ Gemini   │
│  Tailwind    │     │   Celery     │     │  └─ Ollama   │
│  shadcn/ui   │     │   Workers    │     │              │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼──────┐ ┌───▼────┐ ┌──────▼──────┐
       │  Supabase   │ │ Qdrant │ │    Redis    │
       │  Auth + DB  │ │Vectors │ │  Task Queue │
       │  + Storage  │ │        │ │             │
       └─────────────┘ └────────┘ └─────────────┘
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui, Lucide |
| Backend | Python, FastAPI |
| Background Jobs | Celery, Redis |
| Authentication | Supabase Auth |
| Database | Supabase PostgreSQL |
| File Storage | Supabase Storage |
| Vector Database | Qdrant |
| Document Processing | Docling |
| OCR | RapidOCR / Tesseract (evaluating) |
| Embeddings | BGE / Sentence Transformers |
| LLM Providers | Groq, Google Gemini, Ollama |
| Observability | Langfuse |
| Testing | Pytest |
| Containerization | Docker |

---

## Planned Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 0 | Documentation & architecture | ✅ In progress |
| Phase 1 | MVP — core document Q&A | 🔲 Not started |
| Phase 2 | Multi-document intelligence | 🔲 Not started |
| Phase 3 | Multimodal depth | 🔲 Not started |
| Phase 4 | Platform features | 🔲 Not started |

---

## Documentation

| Document | Description |
|----------|-------------|
| [PRODUCT_SPEC.md](./PRODUCT_SPEC.md) | Product vision, features, personas, MVP scope |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, component design, flows |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | Relational data model, ER diagram |
| [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) | Visual design direction, tokens, components |
| [USER_FLOWS.md](./USER_FLOWS.md) | User journeys and flow diagrams |
| [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md) | AI gateway, RAG pipeline, embeddings, citations |
| [API_SPEC.md](./API_SPEC.md) | REST API endpoint specification |
| [SECURITY.md](./SECURITY.md) | Security architecture, RLS, isolation |
| [EVALUATION.md](./EVALUATION.md) | AI evaluation framework and metrics |
| [AGENTS.md](./AGENTS.md) | AI development rules and conventions |

---

## Development

> Development setup instructions will be added when implementation begins.

### Prerequisites (Planned)
- Node.js 18+
- Python 3.11+
- Docker & Docker Compose
- Supabase account (free tier)
- Groq API key (free tier)
- Google Gemini API key (free tier)

---

## License

TBD
