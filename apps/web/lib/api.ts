/**
 * DocuMind AI — API Client (lib/api.ts)
 *
 * HTTP client for the FastAPI backend.
 * Will be implemented during the authentication and feature phases.
 *
 * Contract: all requests go through this module.
 * The frontend MUST NOT call LLMs, Qdrant, or Supabase Storage directly.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Base fetch wrapper — to be expanded with auth headers, error handling, etc. */
async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${API_URL}${path}`;
  return fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
}

export { apiFetch, API_URL };
