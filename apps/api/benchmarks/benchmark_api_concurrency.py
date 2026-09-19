"""
DocuMind AI — FastAPI API Concurrency & Throughput Benchmark.

Measures FastAPI endpoint performance under controlled concurrency (1, 5, 10 workers):
- GET /health (Liveness)
- GET /ready (Readiness)
- GET /api/v1/documents (Authenticated DB query)
- POST /api/v1/documents/signed-url (Authenticated storage URL generation)
- POST /api/v1/search (Authenticated vector retrieval)
Calculates throughput (RPS), error rate, P50, P95, and average latency.
"""

import os
import sys
import time
import json
import asyncio
import httpx
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

BENCHMARK_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BENCHMARK_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

from app.core.security import get_current_user

TEST_USER_ID = "0bbd5bdb-6dca-4b9c-9073-94a25fa44029"

# Set dependency override so FastAPI endpoints treat requests as authenticated
app.dependency_overrides[get_current_user] = lambda: TEST_USER_ID

async def run_worker(client, method, url, headers, json_data, n_reqs):
    latencies = []
    successes = 0
    failures = 0

    for _ in range(n_reqs):
        t0 = time.perf_counter()
        try:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            else:
                resp = await client.post(url, headers=headers, json=json_data)
            
            dur = (time.perf_counter() - t0) * 1000
            latencies.append(dur)
            if resp.status_code in (200, 201):
                successes += 1
            else:
                failures += 1
        except Exception:
            dur = (time.perf_counter() - t0) * 1000
            latencies.append(dur)
            failures += 1
    return latencies, successes, failures

async def benchmark_endpoint(transport, method, url, headers, json_data, concurrency, total_requests=30):
    reqs_per_worker = total_requests // concurrency
    actual_total = reqs_per_worker * concurrency

    t_start = time.perf_counter()
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        tasks = [
            run_worker(client, method, url, headers, json_data, reqs_per_worker)
            for _ in range(concurrency)
        ]
        results = await asyncio.gather(*tasks)

    total_time = time.perf_counter() - t_start
    all_lats = []
    total_succ = 0
    total_fail = 0

    for lats, s, f in results:
        all_lats.extend(lats)
        total_succ += s
        total_fail += f

    rps = actual_total / total_time if total_time > 0 else 0

    return {
        "concurrency": concurrency,
        "total_requests": actual_total,
        "success_count": total_succ,
        "failure_count": total_fail,
        "error_rate_pct": round((total_fail / actual_total) * 100, 2),
        "total_duration_s": round(total_time, 3),
        "throughput_rps": round(rps, 2),
        "avg_latency_ms": round(float(np.mean(all_lats)), 2),
        "median_p50_ms": round(float(np.median(all_lats)), 2),
        "p95_ms": round(float(np.percentile(all_lats, 95)), 2),
        "min_ms": round(float(np.min(all_lats)), 2),
        "max_ms": round(float(np.max(all_lats)), 2),
    }

async def run_api_benchmarks():
    print("=" * 70)
    print("STARTING FASTAPI CONCURRENCY & THROUGHPUT BENCHMARK")
    print("=" * 70)

    headers = {"Authorization": "Bearer mock-benchmark-token"}
    transport = httpx.ASGITransport(app=app)

    concurrency_levels = [1, 5, 10]
    
    endpoints_to_test = [
        {
            "name": "health_check_liveness",
            "method": "GET",
            "url": "/health",
            "headers": {},
            "json": None,
            "requests": 50
        },
        {
            "name": "documents_list_auth",
            "method": "GET",
            "url": "/api/v1/documents",
            "headers": headers,
            "json": None,
            "requests": 30
        },
        {
            "name": "upload_signed_url",
            "method": "POST",
            "url": "/api/v1/documents/signed-url",
            "headers": headers,
            "json": {
                "filename": "bench_test.pdf",
                "file_type": "application/pdf",
                "file_size_bytes": 1024
            },
            "requests": 30
        },
        {
            "name": "vector_search_semantic",
            "method": "POST",
            "url": "/api/v1/search",
            "headers": headers,
            "json": {
                "query": "What is the policy for data retention and GDPR compliance?",
                "top_k": 5
            },
            "requests": 20
        }
    ]

    all_endpoint_results = {}

    for ep in endpoints_to_test:
        name = ep["name"]
        print(f"\n--- Testing Endpoint: {name} ({ep['method']} {ep['url']}) ---")
        all_endpoint_results[name] = []

        for c in concurrency_levels:
            res = await benchmark_endpoint(
                transport=transport,
                method=ep["method"],
                url=ep["url"],
                headers=ep["headers"],
                json_data=ep["json"],
                concurrency=c,
                total_requests=ep["requests"]
            )
            all_endpoint_results[name].append(res)
            print(f"  Concurrency: {c:2d} | Throughput: {res['throughput_rps']:6.2f} req/s | Avg: {res['avg_latency_ms']:6.2f}ms | P95: {res['p95_ms']:6.2f}ms | Errors: {res['error_rate_pct']}%")

    out_file = os.path.join(RESULTS_DIR, "api_concurrency_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "concurrency_levels": concurrency_levels,
            "results": all_endpoint_results
        }, f, indent=2)

    print("\n" + "=" * 70)
    print(f"API CONCURRENCY BENCHMARK COMPLETE (Saved to {out_file})")
    print("=" * 70)
    return all_endpoint_results

if __name__ == "__main__":
    asyncio.run(run_api_benchmarks())
