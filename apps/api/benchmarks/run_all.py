"""
DocuMind AI — Master Benchmark Suite Orchestrator.

Runs all benchmark modules sequentially:
1. Ingestion Benchmark (20 documents)
2. Retrieval Benchmark (50 queries)
3. End-to-End Latency & RAG Quality Benchmark
4. LLM Performance & Fallback Routing Benchmark
5. FastAPI Concurrency & Throughput Benchmark
6. Resource Usage & Vector Database Audit

Generates unified master_benchmark_report.json.
"""

import os
import sys
import time
import json
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from benchmarks.benchmark_ingestion import run_ingestion_benchmark
from benchmarks.benchmark_retrieval import run_retrieval_benchmark
from benchmarks.benchmark_rag_and_e2e import run_rag_and_e2e_benchmark
from benchmarks.benchmark_llm_routing import run_llm_routing_benchmark
from benchmarks.benchmark_api_concurrency import run_api_benchmarks
from benchmarks.benchmark_resources_and_db import run_resources_and_db_benchmark

BENCHMARK_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BENCHMARK_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

async def run_all():
    suite_start = time.perf_counter()
    print("=" * 80)
    print("DOCUMIND AI — COMPLETE PRODUCTION PERFORMANCE & EVALUATION SUITE")
    print("=" * 80)

    # 1. Ingestion
    print("\n>>> STAGE 1: INGESTION BENCHMARK")
    ingestion_results = run_ingestion_benchmark()

    # 2. Retrieval
    print("\n>>> STAGE 2: RETRIEVAL BENCHMARK")
    retrieval_results = run_retrieval_benchmark()

    # 3. End-to-End RAG & Quality
    print("\n>>> STAGE 3: END-TO-END RAG & ANSWER QUALITY BENCHMARK")
    rag_results = await run_rag_and_e2e_benchmark(max_queries=35)

    # 4. LLM Routing & Fallback
    print("\n>>> STAGE 4: LLM PERFORMANCE & ROUTING BENCHMARK")
    llm_results = await run_llm_routing_benchmark(trials=20)

    # 5. API Concurrency
    print("\n>>> STAGE 5: FASTAPI CONCURRENCY BENCHMARK")
    api_results = await run_api_benchmarks()

    # 6. Resource Usage & DB Audit
    print("\n>>> STAGE 6: RESOURCE USAGE & VECTOR DB BENCHMARK")
    resource_results = run_resources_and_db_benchmark()

    suite_duration = time.perf_counter() - suite_start

    master_report = {
        "suite_metadata": {
            "title": "DocuMind AI Production Performance Benchmark",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_suite_duration_seconds": round(suite_duration, 2),
            "environment": {
                "os": "Windows 11",
                "python_version": sys.version.split()[0],
                "vector_store": "Qdrant Cloud AWS (sa-east-1)",
                "database": "Supabase PostgreSQL (AWS)",
                "embedding_model": "Google Gemini gemini-embedding-2 (768d)",
                "primary_llm": "Groq qwen/qwen3.8-27b",
                "fallback_llm": "Google Gemini gemini-3.5-flash",
                "parser": "PyMuPDF (fitz) v1.28.2"
            }
        },
        "ingestion": ingestion_results,
        "retrieval": retrieval_results,
        "rag_and_e2e": rag_results,
        "llm_routing": llm_results,
        "api_concurrency": api_results,
        "resources_and_db": resource_results
    }

    master_file = os.path.join(RESULTS_DIR, "master_benchmark_report.json")
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(master_report, f, indent=2)

    print("\n" + "=" * 80)
    print("ALL BENCHMARKS SUCCESSFULLY COMPLETED!")
    print(f"Master evidence report written to: {master_file}")
    print(f"Total Suite Runtime: {suite_duration:.1f} seconds")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_all())
