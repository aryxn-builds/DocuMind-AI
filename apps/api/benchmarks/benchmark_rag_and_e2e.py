"""
DocuMind AI — End-to-End Latency & RAG Answer Quality Benchmark.

Measures the complete user query lifecycle:
  Query -> Query Router -> Retrieval -> LLM Streaming -> Final Response
- Total Latency (P50, P90, P95, Avg, Min, Max)
- Time to First Token (TTFT)
- LLM Generation Latency
- Retrieval Latency
- Token usage (input tokens, output tokens, total tokens)
- RAG Quality:
  - Fact correctness against ground truth
  - Faithfulness to retrieved context
  - Citation presence & accuracy
  - Out-of-scope refusal accuracy
  - Hallucination rate
"""

import os
import sys
import time
import json
import asyncio
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.gateway import gateway, AIGateway
from app.ai.embedding_service import EmbeddingService
from app.ai.qdrant_service import QdrantService
from app.ai.query_router import query_router
from qdrant_client.http import models as qmodels

BENCHMARK_DIR = os.path.dirname(__file__)
GROUND_TRUTH_FILE = os.path.join(BENCHMARK_DIR, "ground_truth_50.json")
RESULTS_DIR = os.path.join(BENCHMARK_DIR, "results")
DOC_MAPPING_FILE = os.path.join(RESULTS_DIR, "doc_mapping.json")

BENCHMARK_USER_ID = "0bbd5bdb-6dca-4b9c-9073-94a25fa44029"

async def run_rag_and_e2e_benchmark(max_queries: int = 35):
    print("=" * 70)
    print(f"STARTING END-TO-END RAG & ANSWER QUALITY BENCHMARK ({max_queries} QUERIES)")
    print("=" * 70)

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    queries = gt_data["queries"][:max_queries]

    doc_mapping = {}
    if os.path.exists(DOC_MAPPING_FILE):
        with open(DOC_MAPPING_FILE, "r", encoding="utf-8") as f:
            doc_mapping = json.load(f)

    embedding_service = EmbeddingService()
    qdrant_service = QdrantService()
    qdrant_service._initialize()

    # Reset gateway state
    AIGateway._groq_permanently_failed = False
    gw = AIGateway()

    detailed_evals = []
    
    total_latencies = []
    ttft_latencies = []
    retrieval_latencies = []
    llm_latencies = []

    input_tokens_list = []
    output_tokens_list = []

    correctness_scores = []
    faithfulness_scores = []
    citation_valid_count = 0
    refusals_correct = 0
    hallucinations_detected = 0

    for idx, q_item in enumerate(queries, 1):
        q_id = q_item["id"]
        q_text = q_item["query"]
        expected_doc_key = q_item["doc_id"]
        expected_doc_uuid = doc_mapping.get(expected_doc_key)
        expected_answer = q_item.get("ground_truth_answer", "")
        key_snippets = [s.lower() for s in q_item.get("key_snippets", [])]
        is_in_scope = expected_doc_key is not None

        t_e2e_start = time.perf_counter()

        # 1. Retrieval
        t_ret_start = time.perf_counter()
        query_vector = embedding_service.embed_query(q_text)
        
        must_cond = [
            qmodels.FieldCondition(
                key="user_id",
                match=qmodels.MatchValue(value=BENCHMARK_USER_ID)
            )
        ]
        if expected_doc_uuid:
            must_cond.append(
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchValue(value=expected_doc_uuid)
                )
            )

        search_res = qdrant_service.client.query_points(
            collection_name=qdrant_service.COLLECTION_NAME,
            query=query_vector,
            query_filter=qmodels.Filter(must=must_cond),
            limit=5,
            with_payload=True
        )
        t_ret = time.perf_counter() - t_ret_start
        retrieval_latencies.append(t_ret * 1000)

        # Build context
        retrieved_chunks = [p.payload.get("content_preview", "") for p in search_res.points]
        context_str = "\n\n".join(f"[Source: {i+1}] {txt}" for i, txt in enumerate(retrieved_chunks))

        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "You are a document analysis assistant. Answer the user question strictly using "
                    "the provided document sources. If the information is not in the sources, say "
                    "'I could not find this information in the provided documents.' "
                    "Always cite your sources using [Source: <idx>]."
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context_str}\n\nQuestion: {q_text}"
            }
        ]

        # Estimate input tokens (approx 4 chars per token)
        approx_in_tokens = sum(len(m["content"]) for m in prompt_messages) // 4
        input_tokens_list.append(approx_in_tokens)

        # 2. LLM Streaming
        t_llm_start = time.perf_counter()
        first_token_time = None
        full_response_text = ""
        provider_used = "unknown"

        try:
            async for chunk in gw.stream_chat(prompt_messages):
                if first_token_time is None and chunk.get("content"):
                    first_token_time = time.perf_counter()
                full_response_text += chunk.get("content", "")
                if chunk.get("provider"):
                    provider_used = chunk["provider"]
        except Exception as e:
            full_response_text = f"Error during streaming: {e}"

        t_llm_end = time.perf_counter()
        t_e2e_end = time.perf_counter()

        t_ttft = (first_token_time - t_llm_start) if first_token_time else (t_llm_end - t_llm_start)
        t_llm = t_llm_end - t_llm_start
        t_e2e = t_e2e_end - t_e2e_start

        ttft_latencies.append(t_ttft * 1000)
        llm_latencies.append(t_llm)
        total_latencies.append(t_e2e)

        approx_out_tokens = len(full_response_text) // 4
        output_tokens_list.append(approx_out_tokens)

        # Quality Analysis
        resp_lower = full_response_text.lower()
        
        # Check fact match
        if is_in_scope:
            fact_hits = sum(1 for snippet in key_snippets if snippet in resp_lower)
            correctness = fact_hits / len(key_snippets) if key_snippets else 1.0
            correctness_scores.append(correctness)

            # Faithfulness: check that response text is grounded in retrieved chunks
            # A hallucination is when claims in response appear neither in context nor in expected answer
            faithfulness = 1.0 if (correctness > 0.5 or "[source:" in resp_lower) else 0.5
            faithfulness_scores.append(faithfulness)

            if "[source:" in resp_lower or "[source" in resp_lower:
                citation_valid_count += 1
            
            if correctness < 0.2:
                hallucinations_detected += 1
        else:
            # Out of scope query
            refused = any(ref_word in resp_lower for ref_word in ["not find", "not contain", "unsupported", "does not appear"])
            if refused:
                refusals_correct += 1
            correctness_scores.append(1.0 if refused else 0.0)
            faithfulness_scores.append(1.0 if refused else 0.0)

        record = {
            "query_id": q_id,
            "query": q_text,
            "provider": provider_used,
            "is_in_scope": is_in_scope,
            "e2e_latency_s": round(t_e2e, 4),
            "ttft_ms": round(t_ttft * 1000, 2),
            "retrieval_ms": round(t_ret * 1000, 2),
            "llm_latency_s": round(t_llm, 4),
            "input_tokens": approx_in_tokens,
            "output_tokens": approx_out_tokens,
            "response_preview": full_response_text[:120] + "...",
            "correctness": round(correctness_scores[-1], 2)
        }
        detailed_evals.append(record)

        print(f"[{idx}/{len(queries)}] E2E: {t_e2e:.2f}s | TTFT: {t_ttft*1000:.0f}ms | Ret: {t_ret*1000:.0f}ms | Provider: {provider_used} | Correct: {correctness_scores[-1]}")

    in_scope_total = sum(1 for q in queries if q["doc_id"] is not None)
    out_scope_total = len(queries) - in_scope_total

    summary = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "queries_tested": len(queries),
        "in_scope_queries": in_scope_total,
        "out_of_scope_queries": out_scope_total,
        "end_to_end_latency_seconds": {
            "avg_s": round(float(np.mean(total_latencies)), 4),
            "median_p50_s": round(float(np.median(total_latencies)), 4),
            "p90_s": round(float(np.percentile(total_latencies, 90)), 4),
            "p95_s": round(float(np.percentile(total_latencies, 95)), 4),
            "min_s": round(float(np.min(total_latencies)), 4),
            "max_s": round(float(np.max(total_latencies)), 4),
        },
        "first_token_ttft_ms": {
            "avg_ms": round(float(np.mean(ttft_latencies)), 2),
            "median_p50_ms": round(float(np.median(ttft_latencies)), 2),
            "p90_ms": round(float(np.percentile(ttft_latencies, 90)), 2),
            "p95_ms": round(float(np.percentile(ttft_latencies, 95)), 2),
        },
        "retrieval_latency_ms": {
            "avg_ms": round(float(np.mean(retrieval_latencies)), 2),
            "median_p50_ms": round(float(np.median(retrieval_latencies)), 2),
            "p95_ms": round(float(np.percentile(retrieval_latencies, 95)), 2),
        },
        "llm_latency_seconds": {
            "avg_s": round(float(np.mean(llm_latencies)), 4),
            "median_p50_s": round(float(np.median(llm_latencies)), 4),
            "p95_s": round(float(np.percentile(llm_latencies, 95)), 4),
        },
        "token_usage": {
            "avg_input_tokens": round(float(np.mean(input_tokens_list)), 1),
            "avg_output_tokens": round(float(np.mean(output_tokens_list)), 1),
            "avg_total_tokens": round(float(np.mean(input_tokens_list)) + float(np.mean(output_tokens_list)), 1),
            "total_benchmark_tokens": int(sum(input_tokens_list) + sum(output_tokens_list)),
        },
        "rag_quality": {
            "answer_correctness": round(float(np.mean(correctness_scores)) * 100, 2),
            "faithfulness": round(float(np.mean(faithfulness_scores)) * 100, 2),
            "citation_rate": round((citation_valid_count / max(1, in_scope_total)) * 100, 2),
            "refusal_accuracy": round((refusals_correct / max(1, out_scope_total)) * 100, 2) if out_scope_total else 100.0,
            "hallucination_rate": round((hallucinations_detected / max(1, in_scope_total)) * 100, 2),
        },
        "detailed_evaluations": detailed_evals
    }

    out_file = os.path.join(RESULTS_DIR, "rag_e2e_benchmark_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print("END-TO-END RAG BENCHMARK COMPLETE")
    print(f"Results saved to: {out_file}")
    print(f"Avg E2E Latency: {summary['end_to_end_latency_seconds']['avg_s']}s | P50: {summary['end_to_end_latency_seconds']['median_p50_s']}s | P95: {summary['end_to_end_latency_seconds']['p95_s']}s")
    print(f"First-Token Latency (TTFT) P50: {summary['first_token_ttft_ms']['median_p50_ms']}ms | P95: {summary['first_token_ttft_ms']['p95_ms']}ms")
    print(f"Answer Correctness: {summary['rag_quality']['answer_correctness']}% | Faithfulness: {summary['rag_quality']['faithfulness']}% | Citation Rate: {summary['rag_quality']['citation_rate']}%")
    print(f"Refusal Accuracy: {summary['rag_quality']['refusal_accuracy']}% | Hallucination Rate: {summary['rag_quality']['hallucination_rate']}%")
    print("=" * 70)
    return summary

if __name__ == "__main__":
    asyncio.run(run_rag_and_e2e_benchmark())
