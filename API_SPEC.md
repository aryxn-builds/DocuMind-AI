# DocuMind AI — API Specification

> **Status:** Draft v1.0 — Logical endpoint design only
> **Last updated:** 2026-08-15
> **Decision key:** DECIDED · PROPOSED · OPEN DECISION
>
> This document defines the intended API surface. No endpoints are implemented.

---

## 1. General Conventions

| Convention | Value |
|------------|-------|
| Base URL | `/api` |
| Protocol | HTTPS (production), HTTP (development) |
| Format | JSON request/response bodies |
| Authentication | Supabase JWT in `Authorization: Bearer <token>` header |
| Error format | `{ "error": { "code": "string", "message": "string", "details": {} } }` |
| Pagination | Cursor-based: `?cursor=<id>&limit=<n>` |
| Date format | ISO 8601 (`2026-08-15T12:00:00Z`) |

**DECIDED:** REST API with JSON. No GraphQL in MVP.

---

## 2. Authentication

Authentication is handled by Supabase Auth on the client side. The backend validates JWTs.

### `GET /api/auth/me`

| Field | Value |
|-------|-------|
| **Purpose** | Return the current authenticated user's profile |
| **Auth** | Required |
| **Response 200** | `{ "id": "uuid", "email": "string", "full_name": "string", "avatar_url": "string", "created_at": "datetime" }` |
| **Response 401** | `{ "error": { "code": "unauthorized", "message": "Invalid or expired token" } }` |

---

## 3. Documents

### `GET /api/documents`

| Field | Value |
|-------|-------|
| **Purpose** | List the authenticated user's documents |
| **Auth** | Required |
| **Query params** | `?status=ready&cursor=<id>&limit=20` |
| **Response 200** | `{ "documents": [Document], "next_cursor": "string | null" }` |

**Document object:**
```json
{
  "id": "uuid",
  "title": "string",
  "original_filename": "string",
  "file_type": "string",
  "file_size_bytes": 123456,
  "status": "pending | processing | ready | failed",
  "page_count": 12,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

### `POST /api/documents`

| Field | Value |
|-------|-------|
| **Purpose** | Register an uploaded document and trigger processing |
| **Auth** | Required |
| **Request body** | `{ "title": "string (optional)", "file_path": "string", "original_filename": "string", "file_type": "string", "file_size_bytes": 123456 }` |
| **Response 201** | `{ "id": "uuid", "status": "pending", "job_id": "uuid" }` |
| **Error 400** | Invalid file type or missing fields |
| **Error 413** | File size exceeds limit |

**Note:** The actual file is uploaded directly to Supabase Storage by the frontend. This endpoint registers the document metadata and dispatches the processing job.

---

### `GET /api/documents/{document_id}`

| Field | Value |
|-------|-------|
| **Purpose** | Get a single document's details |
| **Auth** | Required (must own document) |
| **Response 200** | Full Document object with `processing_metadata` |
| **Error 404** | Document not found or not owned by user |

---

### `PATCH /api/documents/{document_id}`

| Field | Value |
|-------|-------|
| **Purpose** | Update document metadata (title) |
| **Auth** | Required (must own document) |
| **Request body** | `{ "title": "string" }` |
| **Response 200** | Updated Document object |
| **Error 404** | Document not found |

---

### `DELETE /api/documents/{document_id}`

| Field | Value |
|-------|-------|
| **Purpose** | Delete a document and all associated data |
| **Auth** | Required (must own document) |
| **Response 204** | No content |
| **Error 404** | Document not found |

**Side effects:** Removes vectors from Qdrant, file from Supabase Storage, chunks/conversations/citations from PostgreSQL.

---

### `GET /api/documents/{document_id}/status`

| Field | Value |
|-------|-------|
| **Purpose** | Get current processing status |
| **Auth** | Required (must own document) |
| **Response 200** | `{ "status": "string", "progress": 0.0-1.0, "error_details": {} }` |

---

### `POST /api/documents/{document_id}/reprocess`

| Field | Value |
|-------|-------|
| **Purpose** | Re-trigger document processing |
| **Auth** | Required (must own document) |
| **Response 202** | `{ "job_id": "uuid" }` |
| **Error 409** | Document is currently processing |

---

## 4. Conversations

### `GET /api/conversations`

| Field | Value |
|-------|-------|
| **Purpose** | List the user's conversations |
| **Auth** | Required |
| **Query params** | `?document_id=<uuid>&cursor=<id>&limit=20` |
| **Response 200** | `{ "conversations": [Conversation], "next_cursor": "string | null" }` |

**Conversation object:**
```json
{
  "id": "uuid",
  "document_id": "uuid | null",
  "title": "string | null",
  "created_at": "datetime",
  "updated_at": "datetime",
  "message_count": 8
}
```

---

### `POST /api/conversations`

| Field | Value |
|-------|-------|
| **Purpose** | Create a new conversation |
| **Auth** | Required |
| **Request body** | `{ "document_id": "uuid (optional)", "title": "string (optional)" }` |
| **Response 201** | Conversation object |

---

### `DELETE /api/conversations/{conversation_id}`

| Field | Value |
|-------|-------|
| **Purpose** | Delete a conversation and its messages |
| **Auth** | Required (must own conversation) |
| **Response 204** | No content |

---

## 5. Messages

### `GET /api/conversations/{conversation_id}/messages`

| Field | Value |
|-------|-------|
| **Purpose** | Get messages in a conversation |
| **Auth** | Required (must own conversation) |
| **Query params** | `?cursor=<id>&limit=50` |
| **Response 200** | `{ "messages": [Message], "next_cursor": "string | null" }` |

**Message object:**
```json
{
  "id": "uuid",
  "role": "user | assistant",
  "content": "string",
  "citations": [Citation],
  "metadata": {
    "model": "string",
    "provider": "string",
    "latency_ms": 1234
  },
  "created_at": "datetime"
}
```

---

## 6. Chat (RAG Endpoint)

### `POST /api/chat`

This is the primary RAG endpoint — the core of the product.

| Field | Value |
|-------|-------|
| **Purpose** | Send a question and get an AI-generated, cited answer |
| **Auth** | Required |
| **Request body** | See below |
| **Response 200** | See below |
| **Error 404** | Conversation or document not found |
| **Error 422** | Invalid query (empty, too long) |
| **Error 503** | AI service unavailable (all providers failed) |

**Request:**
```json
{
  "conversation_id": "uuid",
  "query": "What are the main findings?",
  "document_ids": ["uuid"],
  "options": {
    "max_chunks": 10,
    "temperature": 0.2,
    "provider": "string (optional override)"
  }
}
```

**Response:**
```json
{
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "The main findings indicate that...",
    "citations": [
      {
        "id": "uuid",
        "document_id": "uuid",
        "document_title": "Research Paper.pdf",
        "page_number": 7,
        "excerpt": "Our analysis demonstrates...",
        "relevance_score": 0.92
      }
    ],
    "metadata": {
      "model": "llama-3.1-8b-instant",
      "provider": "groq",
      "latency_ms": 1847,
      "chunks_retrieved": 8,
      "chunks_used": 5
    }
  }
}
```

**OPEN DECISION:** Whether to support streaming responses via SSE in MVP. If streaming: endpoint returns `text/event-stream` with chunked content + final citation object.

---

## 7. Summaries (P1)

### `POST /api/documents/{document_id}/summarize`

| Field | Value |
|-------|-------|
| **Purpose** | Generate a summary of a document |
| **Auth** | Required (must own document) |
| **Request body** | `{ "style": "executive | detailed | bullet_points", "max_length": 500 }` |
| **Response 200** | `{ "summary": "string", "citations": [Citation] }` |
| **Error 400** | Document not in 'ready' status |

---

## 8. Document Comparison (P1)

### `POST /api/documents/compare`

| Field | Value |
|-------|-------|
| **Purpose** | Compare two documents |
| **Auth** | Required (must own both documents) |
| **Request body** | `{ "document_id_a": "uuid", "document_id_b": "uuid", "focus": "string (optional)" }` |
| **Response 200** | `{ "comparison": { "similarities": [...], "differences": [...], "summary": "string" }, "citations": [Citation] }` |

---

## 9. Collections (P1)

### `GET /api/collections`

| Field | Value |
|-------|-------|
| **Purpose** | List user's collections |
| **Auth** | Required |
| **Response 200** | `{ "collections": [Collection] }` |

**Collection object:**
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string | null",
  "document_count": 5,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

### `POST /api/collections`

| Field | Value |
|-------|-------|
| **Purpose** | Create a new collection |
| **Auth** | Required |
| **Request body** | `{ "name": "string", "description": "string (optional)" }` |
| **Response 201** | Collection object |

---

### `POST /api/collections/{collection_id}/documents`

| Field | Value |
|-------|-------|
| **Purpose** | Add documents to a collection |
| **Auth** | Required (must own collection and documents) |
| **Request body** | `{ "document_ids": ["uuid"] }` |
| **Response 200** | Updated collection with document list |

---

### `DELETE /api/collections/{collection_id}/documents/{document_id}`

| Field | Value |
|-------|-------|
| **Purpose** | Remove a document from a collection |
| **Auth** | Required |
| **Response 204** | No content |

---

### `DELETE /api/collections/{collection_id}`

| Field | Value |
|-------|-------|
| **Purpose** | Delete a collection (does not delete documents) |
| **Auth** | Required |
| **Response 204** | No content |

---

## 10. Citations

### `GET /api/messages/{message_id}/citations`

| Field | Value |
|-------|-------|
| **Purpose** | Get citations for a specific AI message |
| **Auth** | Required (must own the message's conversation) |
| **Response 200** | `{ "citations": [Citation] }` |

**Citation object:**
```json
{
  "id": "uuid",
  "document_id": "uuid",
  "document_title": "string",
  "chunk_id": "uuid",
  "page_number": 3,
  "excerpt": "string",
  "relevance_score": 0.87
}
```

---

## 11. File Upload (Signed URLs)

### `POST /api/upload/signed-url`

| Field | Value |
|-------|-------|
| **Purpose** | Generate a signed URL for direct file upload to Supabase Storage |
| **Auth** | Required |
| **Request body** | `{ "filename": "string", "file_type": "string", "file_size_bytes": 123456 }` |
| **Response 200** | `{ "signed_url": "string", "file_path": "string", "expires_at": "datetime" }` |
| **Error 400** | Invalid file type |
| **Error 413** | File too large |

**Note:** Frontend uses the signed URL to upload directly to Storage, then calls `POST /api/documents` to register it.

---

## 12. Error Codes

| HTTP Status | Code | Meaning |
|-------------|------|---------|
| 400 | `bad_request` | Invalid request body or parameters |
| 401 | `unauthorized` | Missing or invalid JWT |
| 403 | `forbidden` | Valid JWT but insufficient permissions |
| 404 | `not_found` | Resource not found or not owned by user |
| 409 | `conflict` | Resource in conflicting state (e.g., already processing) |
| 413 | `payload_too_large` | File exceeds size limit |
| 422 | `unprocessable_entity` | Valid JSON but semantic validation failed |
| 429 | `rate_limited` | Too many requests |
| 500 | `internal_error` | Unexpected server error |
| 503 | `service_unavailable` | AI provider or external service down |

---

## 14. Health Endpoints

> **Status:** Not implemented. Conceptual design only.

These endpoints serve legitimate operational monitoring. They do not require a user JWT so that an external scheduler can reach them without managing user credentials. However, they must never expose sensitive infrastructure information.

### `GET /health`

| Field | Value |
|-------|-------|
| **Concept** | Liveness — is the backend process running? |
| **Auth** | Not required |
| **Response 200** | `{ "status": "healthy", "timestamp": "datetime" }` |
| **Response 503** | `{ "status": "unhealthy", "timestamp": "datetime" }` |
| **Performance** | Must return in < 100ms. No dependency checks performed. |

---

### `GET /ready`

| Field | Value |
|-------|-------|
| **Concept** | Readiness — are critical infrastructure dependencies reachable? |
| **Auth** | Not required for basic status field; consider IP allowlist or static API key if detailed dependency information is sensitive |
| **Response 200** | All dependencies healthy (see body below) |
| **Response 503** | One or more dependencies failing (see body below) |

**Response 200 — all healthy:**
```json
{
  "status": "healthy",
  "timestamp": "2026-08-15T12:00:00Z",
  "dependencies": {
    "database": "healthy",
    "vector_store": "healthy"
  }
}
```

**Response 503 — dependency failure:**
```json
{
  "status": "unhealthy",
  "timestamp": "2026-08-15T12:00:00Z",
  "dependencies": {
    "database": "unhealthy",
    "vector_store": "healthy"
  }
}
```

**What these responses MUST NOT contain:**

- Database connection strings or credentials
- API keys or tokens
- Internal hostnames, IPs, or ports
- Stack traces or detailed error messages
- User data or document content

**Implementation guidance (for when these endpoints are built):**
- Database check: a lightweight `SELECT 1` through the existing connection pool — do not open a new connection
- Qdrant check: the Qdrant status or collections API — do not run a vector search
- Treat Langfuse as non-critical: its unavailability should not make `/ready` return 503
- Total readiness check must complete within 2 seconds
- The external monitor calls these endpoints; it is for operational observability, not for circumventing provider inactivity policies

---

## 15. Rate Limiting (PROPOSED)

| Endpoint Category | Limit |
|-------------------|-------|
| Authentication | 10 requests/minute |
| Document upload | 10 uploads/hour |
| Chat (RAG) | 30 requests/minute |
| Document operations | 60 requests/minute |
| General API | 120 requests/minute |

**OPEN DECISION:** Exact rate limits. The above are starting proposals. Needs adjustment based on actual usage patterns and LLM cost considerations.

---

## 16. Open Decisions

| ID | Decision | Status |
|----|----------|--------|
| OD-API-01 | Streaming chat responses (SSE) | OPEN DECISION |
| OD-API-02 | Exact rate limits | PROPOSED |
| OD-API-03 | Pagination strategy (cursor vs offset) | PROPOSED: cursor-based |
| OD-API-04 | API versioning strategy | OPEN DECISION (not needed for MVP) |
| OD-API-05 | Maximum file upload size | OPEN DECISION |
| OD-API-06 | `/ready` endpoint access protection (IP allowlist / static API key) | OPEN DECISION |
| OD-API-07 | Separate `/health` + `/ready` vs. single combined endpoint | PROPOSED: separate |
