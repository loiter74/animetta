#!/usr/bin/env python3
"""
Standalone Bilibili meme collector test script.
Runs BilibiliMemeCollector + MemeCognitiveAnalyzer pipeline.
Uses DeepSeek API for both meme identification and cognitive analysis.

Usage:
    PYTHONPATH=src python scripts/test_meme_collector.py

Env vars needed (from .env):
    DEEPSEEK_API_KEY
    DEEPSEEK_BASE_URL (default: https://api.deepseek.com)
"""

import asyncio
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()


class SimpleLLMClient:
    """Minimal async LLM client using OpenAI SDK (DeepSeek-compatible)."""

    def __init__(self):
        from openai import AsyncOpenAI
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set in .env")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    async def chat(self, messages, **kwargs):
        """Simple chat interface compatible with collector/analyzer expectations."""
        response_format = kwargs.get("response_format")
        extra = {}
        if response_format and response_format.get("type") == "json_object":
            extra["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=2000,
            **extra,
        )
        content = response.choices[0].message.content
        return {"content": content}

    async def chat_messages(self, messages, **kwargs):
        """Alias for chat() — compatible with BilibiliMemeCollector interface."""
        return await self.chat(messages, **kwargs)


async def main():
    print("=" * 60)
    print("  Anima Bilibili Meme Collector — Test Run")
    print("=" * 60)
    print()

    # 1. Create LLM client
    try:
        llm = SimpleLLMClient()
        print(f"[OK] LLM client created (model: {llm.model})")
    except Exception as e:
        print(f"[WARN] LLM not available: {e}")
        print("[INFO] Running in heuristic mode (no AI analysis)")
        llm = None

    # 2. Create collector
    from animetta import $$$
    collector = BilibiliMemeCollector(
        llm_client=llm,
        config={
            "max_videos": 10,
            "max_comments_per_video": 10,
            "min_comment_likes": 3,
            "request_delay": 1.5,
            "search_keyword": "",  # empty = trending
        },
    )

    # 3. Collect meme candidates from B站
    print("\n[1/3] Collecting trending meme candidates from Bilibili...")
    candidates = await collector.collect()

    if not candidates:
        print("[RESULT] No meme candidates found. (API might be rate-limited or no trending data)")
        return

    print(f"[RESULT] Found {len(candidates)} raw meme candidates:")
    for i, c in enumerate(candidates, 1):
        print(f"  {i}. {c.text}")
        if c.context_hint:
            print(f"     Context: {c.context_hint}")
        if c.tags:
            print(f"     Tags: {', '.join(c.tags)}")

    # 4. Cognitive analysis (if LLM available)
    if llm:
        print(f"\n[2/3] Running cognitive analysis on {len(candidates)} candidates...")
        from animetta import $$$
        analyzer = MemeCognitiveAnalyzer(llm_client=llm, meme_pool=None)

        analyses = []
        for candidate in candidates[:3]:  # Limit to 3 for cost
            analysis = await analyzer.analyze(
                text=candidate.text,
                context_hint=candidate.context_hint,
                source="bilibili",
                tags=candidate.tags,
                source_url=(
                    f"https://www.bilibili.com/video/{candidate.source_videos[0]}"
                    if candidate.source_videos else ""
                ),
            )
            analyses.append((candidate, analysis))

        print("\n[3/3] Cognitive analysis results:")
        for candidate, analysis in analyses:
            print(f"\n  ── {candidate.text} ──")
            if analysis:
                print(f"  Humor Mechanism: {analysis.humor_mechanism}")
                print(f"  Emotional Tone:  {analysis.emotional_tone}")
                print(f"  Persona Fit:     {analysis.persona_fit_score:.2f}")
                print(f"  Trigger:         {analysis.context_trigger}")
                print(f"  Usage Example:   {analysis.usage_example}")
            else:
                print("  [Analysis failed — degraded]")
    else:
        print("\n[2/3] Skipped cognitive analysis (no LLM)")
        print("[3/3] Skipped")

    # 5. Summary
    print(f"\n{'=' * 60}")
    print(f"  Collection complete: {len(candidates)} candidates collected")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
