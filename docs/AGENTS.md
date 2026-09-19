# DocuMind AI — Development Rules

> These rules apply to all AI-assisted development on this project.

---

## Core Rules

1. **Inspect existing code before modifying it.** Read the file, understand the context, then edit. Never blindly overwrite.
2. **Do not modify unrelated files.** Scope changes to the task at hand.
3. **Do not introduce dependencies without justification.** Every new package must solve a real need that existing code/dependencies cannot.
4. **Do not duplicate existing utilities or services.** Search the codebase before creating new helpers, hooks, or utility functions.
5. **Follow the documented architecture.** Refer to `ARCHITECTURE.md`, `AI_ARCHITECTURE.md`, and `DATABASE_SCHEMA.md` before making structural decisions.
6. **Follow the design system.** Refer to `DESIGN_SYSTEM.md` for colors, typography, spacing, and component patterns. Do not invent ad-hoc styles.
7. **Never hardcode secrets.** All credentials, API keys, and tokens must come from environment variables. Reference `.env.example` for the expected variables.
8. **Never bypass authentication or RLS.** Every API endpoint requires JWT verification. Every database query must respect RLS. Every Qdrant search must filter by `user_id`.
9. **Preserve type safety.** Use TypeScript types and Pydantic models. Avoid `any` in TypeScript and untyped dicts in Python.
10. **Write tests for important business logic.** Especially: authentication, authorization, document processing, RAG pipeline, citation validation.
11. **Update documentation when architectural decisions change.** If you change the schema, API, or system design, update the corresponding `.md` file.
12. **Prefer small, reviewable changes.** One concern per commit. Avoid combining unrelated changes.
13. **Do not rewrite working code without a reason.** Refactoring is welcome when justified (performance, readability, bug). Refactoring for style preference alone is not.
14. **Do not silently change technology choices.** If the architecture says "use X", do not substitute Y without explicit discussion and documentation.
15. **Ask for clarification when a requirement conflicts with the architecture.** Flag the conflict rather than making a unilateral decision.

---

## Health Monitoring Rules

16. **Health checks are for legitimate operational monitoring only.** Their purpose is to detect that the backend process is running and that critical infrastructure dependencies are reachable.
17. **Do not create artificial request loops to game provider inactivity policies.** Scheduling health checks specifically to prevent a free-tier provider from pausing a project is not a valid use of this mechanism and may violate provider terms.
18. **Do not add browser-side polling solely to keep infrastructure active.** Client-side polling for infrastructure health is not operational monitoring — it creates misleading load and hidden coupling.
19. **Do not run health checks at unnecessarily high frequency.** For portfolio or early-stage deployments, very frequent monitoring (sub-minute intervals) is not justified. Choose a cadence appropriate to actual operational needs.
20. **Health endpoints must remain lightweight and read-only where possible.** They must not trigger document processing, LLM calls, embedding generation, or any stateful business logic.
21. **Never expose secrets or sensitive infrastructure details in health responses.** See `SECURITY.md` §15 for the complete list of prohibited content.
22. **Infrastructure health logic belongs at the infrastructure boundary.** Dependency checks (database, vector store) belong inside their respective infrastructure adapters — not scattered through business logic or API route handlers.
23. **Document any production monitoring change.** If the external monitoring provider, schedule, or health check design changes, update `ARCHITECTURE.md` accordingly.

---

## Next.js / TypeScript Conventions

### Project Structure
```
frontend/
├── src/
│   ├── app/              # Next.js App Router pages
│   ├── components/       # Reusable UI components
│   │   ├── ui/           # shadcn/ui primitives
│   │   └── [feature]/    # Feature-specific components
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # Utilities, API client, Supabase client
│   ├── types/            # TypeScript type definitions
│   └── styles/           # Global styles
├── public/               # Static assets
└── next.config.ts
```

### Rules
- Use **App Router** (not Pages Router).
- Use **Server Components** by default. Add `'use client'` only when needed (interactivity, hooks, browser APIs).
- Use **shadcn/ui** components as the base. Do not introduce alternative component libraries.
- Use **Lucide** for icons. Do not mix icon libraries.
- Use **Tailwind CSS** utility classes. Follow design system tokens for colors, spacing, and typography.
- Define API response types as TypeScript interfaces. Share types with the API spec.
- Use `fetch` or a thin wrapper for API calls. No heavy HTTP client libraries unless justified.
- Handle loading, error, and empty states for every data-fetching component.
- All user-facing strings should be directly in components (not i18n for MVP).

### Naming
- Components: `PascalCase` (`DocumentCard.tsx`)
- Hooks: `camelCase` with `use` prefix (`useDocuments.ts`)
- Utilities: `camelCase` (`formatDate.ts`)
- Types: `PascalCase` (`Document`, `ChatMessage`)
- Files: `kebab-case` for routes, `PascalCase` for components

---

## FastAPI / Python Conventions

### Project Structure
```
backend/
├── app/
│   ├── api/              # Route handlers
│   │   └── v1/           # Versioned API routes
│   ├── core/             # Configuration, security, dependencies
│   ├── models/           # Pydantic models (request/response schemas)
│   ├── services/         # Business logic
│   ├── ai/               # AI Gateway, RAG pipeline, embeddings
│   │   ├── gateway.py    # Provider abstraction
│   │   ├── providers/    # Groq, Gemini, Ollama implementations
│   │   ├── retrieval.py  # Qdrant search + reranking
│   │   ├── context.py    # Context construction
│   │   └── prompts.py    # Prompt templates
│   ├── workers/          # Celery task definitions
│   ├── db/               # Database connection, queries
│   └── main.py           # FastAPI app entry point
├── tests/
├── requirements.txt
└── Dockerfile
```

### Rules
- Use **Pydantic v2** models for all request/response schemas.
- Use **dependency injection** (`Depends()`) for authentication, database sessions, and service instances.
- Use **async** endpoints where possible (I/O-bound operations).
- All endpoints must verify JWT via the auth dependency. No exceptions.
- Use **type hints** on all function signatures.
- Return proper HTTP status codes (201 for creation, 204 for deletion, etc.).
- Handle errors with `HTTPException` and structured error responses.
- Log at appropriate levels: `ERROR` for failures, `WARNING` for recoverable issues, `INFO` for request flow, `DEBUG` for development.

### Naming
- Files: `snake_case` (`document_service.py`)
- Classes: `PascalCase` (`DocumentService`)
- Functions: `snake_case` (`get_document_by_id`)
- Constants: `UPPER_SNAKE_CASE` (`MAX_FILE_SIZE_BYTES`)
- Pydantic models: `PascalCase` with suffix (`DocumentCreate`, `DocumentResponse`)

---

## Database Conventions

- Follow the schema defined in `DATABASE_SCHEMA.md`.
- Use **UUIDs** for all primary keys (`gen_random_uuid()`).
- Use **`timestamptz`** for all timestamp columns (timezone-aware).
- Every user-scoped table must have a `user_id` column with an FK to `profiles(id)`.
- RLS must be enabled on every user-scoped table before the table is used.
- Use **parameterized queries** only. Never interpolate user input into SQL strings.
- Migrations should be reviewed before applying. Do not auto-migrate in production.
- Denormalize `user_id` where it simplifies RLS (as documented in the schema).

---

## AI / RAG Conventions

- All LLM calls go through the **AI Gateway**. Never call a provider SDK directly from business logic.
- Every Qdrant search must include a `user_id` filter. No exceptions.
- Prompt templates live in `app/ai/prompts.py`. Do not inline prompts in route handlers.
- Citations must be validated before returning to the user (existence, ownership, content match).
- Log all LLM calls via Langfuse. Include: provider, model, token count, latency.
- Temperature should default to low values (0.1–0.3) for factual Q&A tasks.
- If retrieval returns no relevant results (all scores below threshold), inform the user rather than generating an unsupported answer.
- Do not hardcode model IDs in business logic. Use configuration.

---

## Testing Conventions

- Use **Pytest** for all backend tests.
- Test files mirror the source structure: `tests/api/`, `tests/services/`, `tests/ai/`.
- Test naming: `test_<function_name>_<scenario>` (e.g., `test_get_document_not_found`).
- Use **fixtures** for common setup (authenticated client, test user, test document).
- **Must test:**
  - Authentication middleware (valid token, expired token, missing token)
  - Authorization (user A cannot access user B's documents)
  - Document processing pipeline (happy path, invalid file, OCR path)
  - RAG pipeline (retrieval, context construction, citation generation)
  - API endpoints (request validation, response format, error cases)
- **Frontend testing** strategy is an OPEN DECISION (Jest, Playwright, or Vitest).
- Do not test implementation details. Test behavior and outputs.

---

## Git Conventions

- **Branch naming:** `feat/<short-description>`, `fix/<short-description>`, `docs/<short-description>`
- **Commit messages:** Use conventional commits:
  - `feat: add document upload endpoint`
  - `fix: correct Qdrant user_id filter`
  - `docs: update API_SPEC with chat endpoint`
  - `refactor: extract citation validation to service`
  - `test: add auth middleware tests`
  - `chore: update dependencies`
- **PR scope:** One logical change per PR. Include description of what and why.
- **Never commit:**
  - `.env` files with real credentials
  - `node_modules/`, `__pycache__/`, `.venv/`
  - Large binary files (uploaded test documents go in a separate test fixtures location)
- **Main branch protection:** All changes go through PR review.

---

## File Organization

```
DocuMind AI/
├── frontend/              # Next.js application
├── backend/               # FastAPI application
├── docker-compose.yml     # Local development services
├── .env.example           # Environment variable template
├── README.md
├── AGENTS.md              # This file
├── PRODUCT_SPEC.md
├── ARCHITECTURE.md
├── DATABASE_SCHEMA.md
├── DESIGN_SYSTEM.md
├── USER_FLOWS.md
├── AI_ARCHITECTURE.md
├── API_SPEC.md
├── SECURITY.md
├── EVALUATION.md
└── docs/
    └── decisions/         # Architecture Decision Records
```
