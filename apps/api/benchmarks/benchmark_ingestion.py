"""
DocuMind AI — Document Ingestion Benchmark.

Measures the complete ingestion pipeline across 20 diverse evaluation documents:
- Parsing / extraction latency (PyMuPDF)
- Chunking latency (Chunker)
- Embedding generation latency (Gemini Embedding API - gemini-embedding-2)
- Qdrant vector upsert latency
- Database insertion latency
- Total ingestion latency
- Document throughput (docs/min, pages/sec, chunks/sec)
- Latency percentiles (P50, P90, P95, Min, Max, Avg) segmented by size tier.
"""

import os
import sys
import time
import json
import uuid
import numpy as np

# Ensure app is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.adapters.pdf_adapter import PdfAdapter
from app.ai.chunker import Chunker
from app.ai.embedding_service import EmbeddingService
from app.ai.qdrant_service import QdrantService
from app.repositories import document_repository, chunk_repository
from app.core.config import settings

BENCHMARK_DIR = os.path.dirname(__file__)
DATASET_DIR = os.path.join(BENCHMARK_DIR, "dataset")
GROUND_TRUTH_FILE = os.path.join(BENCHMARK_DIR, "ground_truth_50.json")
RESULTS_DIR = os.path.join(BENCHMARK_DIR, "results")

os.makedirs(RESULTS_DIR, exist_ok=True)

# Test benchmark user ID (adminA)
BENCHMARK_USER_ID = "0bbd5bdb-6dca-4b9c-9073-94a25fa44029"

def run_ingestion_benchmark():
    print("=" * 70)
    print("STARTING DOCUMIND INGESTION BENCHMARK (20 EVALUATION DOCUMENTS)")
    print("=" * 70)

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    doc_entries = gt_data["documents"]
    
    chunker = Chunker()
    embedding_service = EmbeddingService()
    qdrant_service = QdrantService()
    qdrant_service._initialize()

    detailed_results = []
    total_benchmark_start = time.perf_counter()

    doc_mapping = {} # maps doc_id to created document UUID in DB/Qdrant

    for idx, doc_meta in enumerate(doc_entries, 1):
        doc_key = doc_meta["id"]
        filename = doc_meta["filename"]
        filepath = os.path.join(DATASET_DIR, filename)

        if not os.path.exists(filepath):
            print(f"File not found: {filepath}, skipping...")
            continue

        file_size_bytes = os.path.getsize(filepath)
        with open(filepath, "rb") as f:
            file_bytes = f.read()

        doc_uuid = uuid.uuid4()
        doc_mapping[doc_key] = str(doc_uuid)

        print(f"\n[{idx}/20] Processing {filename} ({file_size_bytes/1024:.1f} KB)...")

        t_doc_start = time.perf_counter()

        # 1. Parse / Extraction
        t0 = time.perf_counter()
        adapter = PdfAdapter(
            document_id=doc_uuid,
            user_id=BENCHMARK_USER_ID,
            file_path=filename,
            mime_type="application/pdf",
            title=filename,
        )
        norm_doc = adapter.parse(file_bytes)
        t_parse = time.perf_counter() - t0

        page_count = norm_doc.page_count
        extracted_text_chars = sum(len(b.content) for b in norm_doc.blocks)

        # 2. Chunking
        t0 = time.perf_counter()
        chunks = chunker.chunk(norm_doc)
        t_chunk = time.perf_counter() - t0
        chunk_count = len(chunks)

        # 3. Embedding Generation (Gemini gemini-embedding-2)
        t0 = time.perf_counter()
        chunks_with_vectors = embedding_service.embed(chunks)
        t_embed = time.perf_counter() - t0

        # 4. Qdrant Vector Store Upsert
        t0 = time.perf_counter()
        for attempt in range(3):
            try:
                qdrant_service.upsert(chunks_with_vectors, BENCHMARK_USER_ID)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(2.0 * (attempt + 1))
        t_qdrant = time.perf_counter() - t0

        # 5. DB Metadata & Postgres Chunk insertion
        t0 = time.perf_counter()
        try:
            document_repository.insert_document(
                document_id=doc_uuid,
                user_id=BENCHMARK_USER_ID,
                title=filename,
                original_filename=filename,
                file_path=filename,
                file_type="application/pdf",
                file_size_bytes=file_size_bytes,
                status="ready"
            )
            chunk_repository.create_chunks(chunks)
        except Exception as e:
            # If already exists or error, continue
            pass
        t_db = time.perf_counter() - t0

        t_total = time.perf_counter() - t_doc_start

        record = {
            "doc_key": doc_key,
            "document_id": str(doc_uuid),
            "filename": filename,
            "doc_type": doc_meta.get("type", "pdf"),
            "file_size_bytes": file_size_bytes,
            "page_count": page_count,
            "extracted_text_chars": extracted_text_chars,
            "chunk_count": chunk_count,
            "parse_latency_s": round(t_parse, 4),
            "chunk_latency_s": round(t_chunk, 4),
            "embed_latency_s": round(t_embed, 4),
            "qdrant_upsert_latency_s": round(t_qdrant, 4),
            "db_insert_latency_s": round(t_db, 4),
            "total_ingestion_latency_s": round(t_total, 4),
        }
        detailed_results.append(record)

        print(f"  Pages: {page_count} | Chunks: {chunk_count} | Chars: {extracted_text_chars}")
        print(f"  Parse: {t_parse*1000:.1f}ms | Chunk: {t_chunk*1000:.1f}ms | Embed: {t_embed:.2f}s | Qdrant: {t_qdrant*1000:.1f}ms | Total: {t_total:.2f}s")
        time.sleep(0.5)

    total_benchmark_time = time.perf_counter() - total_benchmark_start
    total_pages = sum(r["page_count"] for r in detailed_results)
    total_chunks = sum(r["chunk_count"] for r in detailed_results)
    total_chars = sum(r["extracted_text_chars"] for r in detailed_results)
    total_bytes = sum(r["file_size_bytes"] for r in detailed_results)

    # Compute Statistical Metrics
    tot_lats = [r["total_ingestion_latency_s"] for r in detailed_results]
    parse_lats = [r["parse_latency_s"] for r in detailed_results]
    chunk_lats = [r["chunk_latency_s"] for r in detailed_results]
    embed_lats = [r["embed_latency_s"] for r in detailed_results]
    qdrant_lats = [r["qdrant_upsert_latency_s"] for r in detailed_results]

    summary = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "documents_tested": len(detailed_results),
        "total_pages": total_pages,
        "total_chunks": total_chunks,
        "total_bytes": total_bytes,
        "total_chars": total_chars,
        "total_benchmark_duration_s": round(total_benchmark_time, 2),
        "throughput": {
            "documents_per_minute": round((len(detailed_results) / total_benchmark_time) * 60, 2),
            "pages_per_second": round(total_pages / total_benchmark_time, 2),
            "chunks_per_second": round(total_chunks / total_benchmark_time, 2),
            "bytes_per_second": round(total_bytes / total_benchmark_time, 2),
        },
        "total_latency_seconds": {
            "avg": round(float(np.mean(tot_lats)), 4),
            "median_p50": round(float(np.median(tot_lats)), 4),
            "p90": round(float(np.percentile(tot_lats, 90)), 4),
            "p95": round(float(np.percentile(tot_lats, 95)), 4),
            "min": round(float(np.min(tot_lats)), 4),
            "max": round(float(np.max(tot_lats)), 4),
        },
        "stage_latency_avg_seconds": {
            "parse_avg_s": round(float(np.mean(parse_lats)), 4),
            "chunk_avg_s": round(float(np.mean(chunk_lats)), 4),
            "embed_avg_s": round(float(np.mean(embed_lats)), 4),
            "qdrant_upsert_avg_s": round(float(np.mean(qdrant_lats)), 4),
        },
        "stage_latency_p95_seconds": {
            "parse_p95_s": round(float(np.percentile(parse_lats, 95)), 4),
            "chunk_p95_s": round(float(np.percentile(chunk_lats, 95)), 4),
            "embed_p95_s": round(float(np.percentile(embed_lats, 95)), 4),
            "qdrant_upsert_p95_s": round(float(np.percentile(qdrant_lats, 95)), 4),
        },
        "tier_analysis": {
            "small_1_to_2_pages": {
                "count": len([r for r in detailed_results if r["page_count"] <= 2]),
                "avg_total_s": round(float(np.mean([r["total_ingestion_latency_s"] for r in detailed_results if r["page_count"] <= 2])), 4),
            },
            "medium_4_to_10_pages": {
                "count": len([r for r in detailed_results if 3 <= r["page_count"] <= 10]),
                "avg_total_s": round(float(np.mean([r["total_ingestion_latency_s"] for r in detailed_results if 3 <= r["page_count"] <= 10])), 4),
            },
            "large_15_to_30_pages": {
                "count": len([r for r in detailed_results if r["page_count"] >= 15]),
                "avg_total_s": round(float(np.mean([r["total_ingestion_latency_s"] for r in detailed_results if r["page_count"] >= 15])), 4),
            }
        },
        "detailed_results": detailed_results,
        "doc_mapping": doc_mapping
    }

    out_file = os.path.join(RESULTS_DIR, "ingestion_benchmark_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Also save doc_mapping to a shared file for retrieval benchmarks
    mapping_file = os.path.join(RESULTS_DIR, "doc_mapping.json")
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(doc_mapping, f, indent=2)

    print("\n" + "=" * 70)
    print("INGESTION BENCHMARK COMPLETE")
    print(f"Results saved to: {out_file}")
    print(f"Total Docs: {summary['documents_tested']} | Total Pages: {summary['total_pages']} | Total Chunks: {summary['total_chunks']}")
    print(f"Avg Latency: {summary['total_latency_seconds']['avg']}s | Median (P50): {summary['total_latency_seconds']['median_p50']}s | P95: {summary['total_latency_seconds']['p95']}s")
    print(f"Throughput: {summary['throughput']['documents_per_minute']} docs/min | {summary['throughput']['pages_per_second']} pages/sec | {summary['throughput']['chunks_per_second']} chunks/sec")
    print("=" * 70)
    return summary

if __name__ == "__main__":
    run_ingestion_benchmark()
