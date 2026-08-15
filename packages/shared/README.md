# packages/shared

Shared TypeScript types and configuration intended for use across `apps/web` (frontend) and any future TypeScript tooling.

## Status

**Not implemented.** This package is a structural placeholder.

## Rationale

At the scaffolding stage, forcing type sharing between the Python backend and the TypeScript frontend is impractical. Types will be extracted here when:

1. The API schema is stable enough to generate from (e.g., via `openapi-typescript`).
2. A genuine cross-package need emerges (e.g., shared validation schemas).

## When to populate this package

During the API implementation phase, consider using `openapi-typescript` to generate types from the FastAPI OpenAPI schema:

```bash
npx openapi-typescript http://localhost:8000/openapi.json -o packages/shared/src/api.d.ts
```

Until then, define types locally in `apps/web/types/`.
