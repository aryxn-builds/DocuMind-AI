# DocuMind AI — Decision Log

This log records major architectural and technical decisions made during the pre-implementation phase to ensure stability before scaffolding begins.

---

### DEC-001: Background Job Processing
**Date:** 2024-05
**Decision:** Use `FastAPI BackgroundTasks` for the MVP instead of Celery + Redis.
**Rationale:** The MVP is a single-server application. Celery and Redis add operational complexity that isn't justified for the initial launch. The processing flow will be implemented behind a `DocumentProcessor` interface, allowing Celery to be swapped in later if scale demands it.

### DEC-002: Maximum Document Upload Size
**Date:** 2024-05
**Decision:** 25 MB per document for MVP.
**Rationale:** Prevents excessive memory consumption during extraction and chunking on the single server. Balances capability with resource protection.

### DEC-003: Upload Flow Atomicity
**Date:** 2024-05
**Decision:** Backend-orchestrated atomic registration (Option A).
**Rationale:** The two-step upload flow (Storage -> API registration) risks orphaned files in cloud storage. By having the backend generate the signed URL *and* create the `documents` row atomically, we guarantee no orphaned files. The background worker will simply verify the file's presence before processing.

### DEC-004: API Versioning
**Date:** 2024-05
**Decision:** All API endpoints must be versioned under `/api/v1/`.
**Rationale:** Harmonizes a contradiction between `AGENTS.md` and `API_SPEC.md`. Ensures future backward compatibility.

### DEC-005: Real-Time Chat Streaming
**Date:** 2024-05
**Decision:** Server-Sent Events (SSE) for chat responses.
**Rationale:** SSE provides a simpler, stateless mechanism for streaming LLM responses compared to WebSockets, which are overkill for unidirectional text streaming.

### DEC-006: Primary LLM Provider
**Date:** 2024-05
**Decision:** Groq.
**Rationale:** Fast inference speed, ideal for the primary text generation and Q&A tasks. Capability-based routing will fall back as needed.

### DEC-007: Multimodal / Vision Provider
**Date:** 2024-05
**Decision:** Gemini.
**Rationale:** High-quality multimodal capabilities available via API for processing charts and images during MVP.

### DEC-008: Local LLM Fallback
**Date:** 2024-05
**Decision:** Ollama is an optional local fallback.
**Rationale:** Relegating Ollama to an optional fallback rather than a peer dependency simplifies local setup while retaining an offline option.

### DEC-009: Embedding Model
**Date:** 2024-05
**Decision:** BGE model family via Sentence Transformers (local execution).
**Status:** DEPRECATED (Superseded by `gemini-embedding-2`)
**Rationale (Historical):** High quality, free local inference. Start with `BAAI/bge-small-en-v1.5` for speed, with `bge-base` as a fallback if quality requires it.

### DEC-010: Vector Database Architecture
**Date:** 2024-05
**Decision:** Single Qdrant collection with `user_id` payload filtering.
**Rationale:** Creating per-user or per-document collections adds significant management overhead. A single collection with strict metadata filtering is standard practice for multitenant MVP vector databases.

---

*This document serves as the historical record for pre-implementation architectural locks. Future major decisions should be appended here.*
