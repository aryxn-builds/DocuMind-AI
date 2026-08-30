"""
DocuMind AI — Qdrant Cloud Keep-Alive Health Check
===================================================

Purpose
-------
Performs a single lightweight, read-only authenticated request to the
configured Qdrant cluster.  This keeps the cluster active during
development / testing without modifying any collections, vectors, or
user data.

Usage
-----
    python scripts/qdrant_health_check.py

Required environment variables
-------------------------------
    QDRANT_URL      – Full URL of the Qdrant cluster
                      (e.g. https://xyz.qdrant.io:6333)
    QDRANT_API_KEY  – Qdrant API key for authenticated access

Exit codes
----------
    0  – Cluster reachable and authenticated successfully.
    1  – Missing environment variable.
    2  – Connection or API error.
    3  – qdrant-client library not installed.

Security
--------
- Credentials are read ONLY from environment variables.
- The API key is NEVER printed under any circumstances.
- The URL is referenced in log output only as a masked hostname.
- This script performs NO upsert / delete / update operations.
"""

import os
import sys
from urllib.parse import urlparse


def _masked_host(url: str) -> str:
    """Return only the hostname:port portion of a URL for safe logging."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "<unknown-host>"
        port = f":{parsed.port}" if parsed.port else ""
        return f"{host}{port}"
    except Exception:
        return "<url-parse-error>"


def main() -> int:
    print("Qdrant health check started")

    # ------------------------------------------------------------------
    # 1. Validate required environment variables
    # ------------------------------------------------------------------
    qdrant_url = os.environ.get("QDRANT_URL", "").strip()
    qdrant_api_key = os.environ.get("QDRANT_API_KEY", "").strip()

    if not qdrant_url:
        print(
            "Qdrant health check failed: "
            "QDRANT_URL environment variable is not set or empty."
        )
        return 1

    if not qdrant_api_key:
        print(
            "Qdrant health check failed: "
            "QDRANT_API_KEY environment variable is not set or empty."
        )
        return 1

    # ------------------------------------------------------------------
    # 2. Import qdrant-client (already in apps/api/requirements.txt)
    # ------------------------------------------------------------------
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        print(
            "Qdrant health check failed: "
            "qdrant-client is not installed. "
            "Run: pip install qdrant-client"
        )
        return 3

    # ------------------------------------------------------------------
    # 3. Perform a single read-only request: list collections
    # ------------------------------------------------------------------
    safe_host = _masked_host(qdrant_url)
    print(f"Connecting to Qdrant cluster at {safe_host} ...")

    try:
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=30,
        )

        # get_collections() is authenticated, read-only, and lightweight.
        # It returns an empty list on a brand-new cluster — that is fine.
        result = client.get_collections()
        collection_names = [c.name for c in result.collections]
        collection_count = len(collection_names)

        print(
            f"Qdrant connection successful. "
            f"Collections visible: {collection_count}"
        )

    except Exception as exc:
        # Sanitize: never include the raw exception string if it might
        # contain the API key or full URL (some client errors embed them).
        exc_type = type(exc).__name__
        # Strip anything that looks like a key or the raw URL from the message.
        exc_msg = str(exc)
        if qdrant_api_key and qdrant_api_key in exc_msg:
            exc_msg = exc_msg.replace(qdrant_api_key, "***")
        if qdrant_url and qdrant_url in exc_msg:
            exc_msg = exc_msg.replace(qdrant_url, f"<{safe_host}>")

        print(
            f"Qdrant health check failed: "
            f"{exc_type}: {exc_msg}"
        )
        return 2

    print("Qdrant health check completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
