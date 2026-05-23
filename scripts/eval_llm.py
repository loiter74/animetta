#!/usr/bin/env python3
"""LLM Evaluation Framework — compare providers on semantic similarity.

Usage:
    python scripts/eval_llm.py --prompts eval_prompts.txt --providers mock
    python scripts/eval_llm.py --prompts eval_prompts.txt --providers deepseek,openai --reference reference_answers.txt

Requirements:
    - sentence-transformers>=3.0 (optional, for similarity scoring)
    - scikit-learn (for cosine similarity)
"""

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

# Add src to path for imports (project root = parent of scripts/)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ──────────────────── CLI ────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare LLM providers on semantic similarity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python scripts/eval_llm.py --prompts eval_prompts.txt --providers mock
  python scripts/eval_llm.py --prompts eval_prompts.txt --providers deepseek,openai --reference ref.txt --output results.json""",
    )
    parser.add_argument("--prompts", type=str, required=True, help="Path to prompts file (one per line)")
    parser.add_argument("--providers", type=str, required=True, help="Comma-separated provider names (e.g. mock,deepseek)")
    parser.add_argument("--output", type=str, default="eval_results.json", help="Output JSON path (default: eval_results.json)")
    parser.add_argument("--reference", type=str, default=None, help="Optional reference answers file (one per line)")
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2", help="SentenceTransformer model name (default: all-MiniLM-L6-v2)")
    return parser.parse_args()


# ──────────────────── Prompt Loading ────────────────────

def load_prompts(path: str) -> list[str]:
    """Load prompts from file, one per line, skipping empty and comment lines."""
    prompts: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                prompts.append(stripped)
    return prompts


# ──────────────────── Parallel LLM Querying ────────────────────

async def query_providers(
    prompts: list[str],
    provider_names: list[str],
) -> list[dict[str, Any]]:
    """Send each prompt to all providers, recording response text and latency.

    Uses asyncio.gather for parallel execution within each prompt batch.
    Individual provider errors are caught and recorded — other providers continue.
    """
    from animetta import $$$

    results: list[dict[str, Any]] = []

    # Create one LLM instance per provider (reused across all prompts)
    providers: dict[str, Any] = {}
    for name in provider_names:
        try:
            providers[name] = LLMFactory.create(name)
            print(f"  Created provider: {name} → {type(providers[name]).__name__}")
        except Exception as e:
            print(f"  Warning: Failed to create provider '{name}': {e}")

    if not providers:
        print("Error: No providers could be created. Aborting.")
        return results

    async def query_one(provider_name: str, llm: Any, prompt: str) -> dict[str, Any]:
        """Query a single provider. Errors are recorded, not raised."""
        start = time.perf_counter()
        try:
            response = await llm.chat(prompt)
            latency_ms = (time.perf_counter() - start) * 1000
            return {
                "provider": provider_name,
                "prompt": prompt,
                "response": response,
                "latency_ms": round(latency_ms, 2),
                "error": None,
            }
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return {
                "provider": provider_name,
                "prompt": prompt,
                "response": "",
                "latency_ms": round(latency_ms, 2),
                "error": str(e),
            }

    # For each prompt, query all providers in parallel
    for i, prompt in enumerate(prompts):
        print(f"  [{i + 1}/{len(prompts)}] Processing prompt: {prompt[:60]}...")
        tasks = [query_one(name, llm, prompt) for name, llm in providers.items()]
        batch = await asyncio.gather(*tasks, return_exceptions=True)

        for r in batch:
            if isinstance(r, Exception):
                results.append({
                    "provider": "unknown",
                    "prompt": prompt,
                    "response": "",
                    "latency_ms": 0,
                    "error": str(r),
                })
            else:
                results.append(r)

    # Cleanup
    for llm in providers.values():
        try:
            await llm.close()
        except Exception:
            pass

    return results


# ──────────────────── Semantic Similarity Scoring ────────────────────

def compute_similarity(
    results: list[dict[str, Any]],
    references: list[str] | None,
    model_name: str = "all-MiniLM-L6-v2",
) -> list[dict[str, Any]]:
    """Compute cosine similarity between LLM responses and reference answers.

    Uses sentence-transformers to encode text into embeddings,
    then computes cosine similarity via sklearn.
    Score range: 0.0 (completely different) to 1.0 (identical meaning).

    If no reference answers are provided, similarity scoring is skipped
    and results are annotated with similarity=None.
    """
    if not references:
        print("Note: No reference answers provided — skipping similarity scoring.")
        for r in results:
            r["similarity"] = None
        return results

    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError as e:
        print(f"Warning: Missing dependencies for similarity scoring: {e}")
        print("Install with: pip install sentence-transformers>=3.0 scikit-learn")
        for r in results:
            r["similarity"] = None
        return results

    print(f"Loading embedding model: {model_name} ...")
    model = SentenceTransformer(model_name)

    # Map unique prompts to reference answers (by position)
    unique_prompts = list(dict.fromkeys(r["prompt"] for r in results))
    ref_map: dict[str, str] = {}
    for i, prompt_text in enumerate(unique_prompts):
        if i < len(references):
            ref_map[prompt_text] = references[i]

    print(f"Computing similarity for {len(results)} responses...")
    for r in results:
        if r.get("error"):
            r["similarity"] = None
            continue

        ref = ref_map.get(r["prompt"])
        if ref and r["response"]:
            emb_resp = model.encode(r["response"], normalize_embeddings=True)
            emb_ref = model.encode(ref, normalize_embeddings=True)
            sim = float(cosine_similarity([emb_resp], [emb_ref])[0][0])
            r["similarity"] = round(max(0.0, min(1.0, sim)), 4)
        else:
            r["similarity"] = None

    return results


# ──────────────────── Output Generation ────────────────────

def generate_output(results: list[dict[str, Any]], output_path: str) -> None:
    """Aggregate results per provider and write JSON + print Markdown table.

    Per-provider aggregates:
        - avg_similarity: mean cosine similarity across all prompts
        - avg_latency_ms: mean response latency in milliseconds
        - quality_per_sec: similarity / latency_seconds (composite metric)
    """
    by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in results:
        by_provider[r["provider"]].append(r)

    summary: dict[str, Any] = {}
    for provider, items in sorted(by_provider.items()):
        sims = [i["similarity"] for i in items if i.get("similarity") is not None]
        lats = [i["latency_ms"] for i in items if i.get("latency_ms", 0) > 0 and not i.get("error")]

        avg_sim = sum(sims) / len(sims) if sims else 0.0
        avg_lat_ms = sum(lats) / len(lats) if lats else 0.0
        avg_lat_s = avg_lat_ms / 1000.0
        quality_per_sec = avg_sim / avg_lat_s if avg_lat_s > 0 else 0.0
        errors = sum(1 for i in items if i.get("error"))

        summary[provider] = {
            "avg_similarity": round(avg_sim, 4),
            "avg_latency_ms": round(avg_lat_ms, 2),
            "quality_per_sec": round(quality_per_sec, 2),
            "num_prompts": len(items),
            "num_errors": errors,
            "responses": items,
        }

    output: dict[str, Any] = {
        "summary": summary,
        "total_prompts": len(set(r["prompt"] for r in results)),
        "total_providers": len(by_provider),
    }

    # Write JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults written to: {output_path}")

    # Print Markdown table to stdout
    print("\n## LLM Evaluation Results\n")
    print("| Provider | Avg Similarity | Avg Latency (s) | Quality/sec |")
    print("|----------|---------------|-----------------|-------------|")
    for provider, data in sorted(summary.items()):
        lat_s = data["avg_latency_ms"] / 1000.0
        print(f"| {provider} | {data['avg_similarity']:.2f} | {lat_s:.2f} | {data['quality_per_sec']:.2f} |")
    print()


# ──────────────────── Main ────────────────────

async def main() -> None:
    args = parse_args()

    prompts = load_prompts(args.prompts)
    print(f"Loaded {len(prompts)} prompts from {args.prompts}")

    provider_names = [p.strip() for p in args.providers.split(",") if p.strip()]
    if not provider_names:
        print("Error: No providers specified.")
        sys.exit(1)
    print(f"Providers: {', '.join(provider_names)}")

    references: list[str] | None = None
    if args.reference:
        references = load_prompts(args.reference)
        print(f"Loaded {len(references)} reference answers from {args.reference}")

    print("\nQuerying providers...")
    results = await query_providers(prompts, provider_names)
    print(f"Collected {len(results)} responses ({sum(1 for r in results if r.get('error'))} errors)")

    results = compute_similarity(results, references, args.model)

    generate_output(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
