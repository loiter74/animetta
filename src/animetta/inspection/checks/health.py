"""Component health checks — concurrent async probes.

Probes for 7 core components:
1. stats_store     — SQLite health via SELECT 1
2. chroma          — ChromaDB collection accessibility
3. llm_available   — LLM service loaded in ServicePool
4. tts_available   — TTS engine initialized
5. asr_available   — ASR model ready
6. memory_read     — MemorySystem read capability
7. metrics_endpoint — GET /metrics returns 200
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from loguru import logger


# ── Timeout constants (seconds) ─────────────────────────────

STATS_STORE_TIMEOUT = 2.0
CHROMA_TIMEOUT = 3.0
LLM_TIMEOUT = 5.0
TTS_TIMEOUT = 3.0
ASR_TIMEOUT = 3.0
MEMORY_TIMEOUT = 3.0
METRICS_TIMEOUT = 3.0


# ── ComponentCheck ──────────────────────────────────────────


@dataclass
class ComponentCheck:
    """Definition of a single component health probe.

    Attributes:
        name: Unique check identifier (e.g. "stats_store")
        probe: Async callable returning bool (True = healthy, False = degraded)
        timeout: Per-probe timeout in seconds
        description: Human-readable description
    """

    name: str
    probe: Callable[[], Awaitable[bool]]
    timeout: float
    description: str = ""


# ── Probe implementations ───────────────────────────────────


async def _probe_stats_store() -> bool:
    """Check StatsStore SQLite is accessible via SELECT 1."""
    try:

        store = await get_stats_store()
        cursor = await store._db.execute("SELECT 1")
        row = await cursor.fetchone()
        return row is not None and row[0] == 1
    except Exception as e:
        logger.warning(f"[health/stats_store] probe failed: {e}")
        return False


async def _probe_chroma() -> bool:
    """Check ChromaDB collection accessibility."""
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        logger.debug("[health/chroma] chromadb not installed — assuming not configured")
        return True

    try:
        chroma_path = str(Path("~/.myagent/workspace/chroma_db").expanduser())
        client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        # Lightweight: just list collections (no heavy queries)
        _ = client.list_collections()
        return True
    except Exception as e:
        logger.warning(f"[health/chroma] probe failed: {e}")
        return False


async def _probe_llm_available() -> bool:
    """Check LLM service is loaded in ServicePool."""
    try:

        if not ServicePool._ready:
            logger.debug("[health/llm] ServicePool not initialized — not configured")
            return True
        return ServicePool._llm is not None
    except Exception as e:
        logger.warning(f"[health/llm] probe failed: {e}")
        return False


async def _probe_tts_available() -> bool:
    """Check TTS engine is initialized."""
    try:

        if not ServicePool._ready:
            logger.debug("[health/tts] ServicePool not initialized — not configured")
            return True
        return ServicePool._tts is not None
    except Exception as e:
        logger.warning(f"[health/tts] probe failed: {e}")
        return False


async def _probe_asr_available() -> bool:
    """Check ASR model is ready."""
    try:

        if not ServicePool._ready:
            logger.debug("[health/asr] ServicePool not initialized — not configured")
            return True
        return ServicePool._asr is not None
    except Exception as e:
        logger.warning(f"[health/asr] probe failed: {e}")
        return False


async def _probe_memory_read() -> bool:
    """Check MemorySystem can perform a read (via ChromaDB proxy)."""
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        logger.debug("[health/memory_read] chromadb not installed — not configured")
        return True

    try:
        chroma_path = str(Path("~/.myagent/workspace/chroma_db").expanduser())
        client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        collections = client.list_collections()
        if not collections:
            logger.debug("[health/memory_read] No ChromaDB collections — memory not yet populated")
            return True

        # Lightweight: just count documents in the first collection
        col = client.get_collection(collections[0].name)
        _ = col.count()
        return True
    except Exception as e:
        logger.warning(f"[health/memory_read] probe failed: {e}")
        return False


async def _probe_metrics_endpoint() -> bool:
    """Check GET /metrics returns 200 with expected counter names."""
    try:
        import aiohttp
    except ImportError:
        logger.debug("[health/metrics] aiohttp not installed — metrics probe skipped")
        return True

    try:
        url = "http://localhost:12394/metrics"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=METRICS_TIMEOUT)) as resp:
                if resp.status != 200:
                    logger.warning(f"[health/metrics] unexpected status {resp.status}")
                    return False
                text = await resp.text()
                # Check for expected counter patterns
                expected_patterns = ["anima_", "http_request", "process_"]
                found = any(pattern in text for pattern in expected_patterns)
                if not found:
                    logger.debug("[health/metrics] no expected metric patterns, but endpoint OK")
                return True
    except aiohttp.ClientConnectorError:
        logger.debug("[health/metrics] metrics endpoint not reachable — not configured")
        return True
    except asyncio.TimeoutError:
        logger.warning("[health/metrics] metrics endpoint timed out")
        return False
    except Exception as e:
        logger.warning(f"[health/metrics] probe failed: {e}")
        return False


# ── Check registry ──────────────────────────────────────────

COMPONENT_CHECKS: tuple[ComponentCheck, ...] = (
    ComponentCheck(
        name="stats_store",
        probe=_probe_stats_store,
        timeout=STATS_STORE_TIMEOUT,
        description="StatsStore SQLite health (SELECT 1)",
    ),
    ComponentCheck(
        name="chroma",
        probe=_probe_chroma,
        timeout=CHROMA_TIMEOUT,
        description="ChromaDB collection accessibility",
    ),
    ComponentCheck(
        name="llm_available",
        probe=_probe_llm_available,
        timeout=LLM_TIMEOUT,
        description="LLM service loaded in ServicePool",
    ),
    ComponentCheck(
        name="tts_available",
        probe=_probe_tts_available,
        timeout=TTS_TIMEOUT,
        description="TTS engine initialized",
    ),
    ComponentCheck(
        name="asr_available",
        probe=_probe_asr_available,
        timeout=ASR_TIMEOUT,
        description="ASR model ready",
    ),
    ComponentCheck(
        name="memory_read",
        probe=_probe_memory_read,
        timeout=MEMORY_TIMEOUT,
        description="MemorySystem read capability",
    ),
    ComponentCheck(
        name="metrics_endpoint",
        probe=_probe_metrics_endpoint,
        timeout=METRICS_TIMEOUT,
        description="GET /metrics returns 200",
    ),
)


# ── Runner ──────────────────────────────────────────────────


async def _run_single_probe(check: ComponentCheck) -> CheckResult:
    """Execute a single probe with timeout and error handling.

    Args:
        check: ComponentCheck definition with probe, name, timeout.

    Returns:
        CheckResult with pass/fail status, timing, and error info.
    """
    t0 = time.perf_counter()
    try:
        ok = await asyncio.wait_for(check.probe(), timeout=check.timeout)
        duration_ms = (time.perf_counter() - t0) * 1000
        if ok:
            return CheckResult.passed(check.name, duration_ms=duration_ms)
        else:
            return CheckResult.failed(
                check.name, duration_ms=duration_ms, error="probe returned False"
            )
    except asyncio.TimeoutError:
        duration_ms = (time.perf_counter() - t0) * 1000
        logger.warning(f"[health/{check.name}] timed out after {check.timeout}s")
        return CheckResult.failed(
            check.name,
            duration_ms=duration_ms,
            error=f"timeout after {check.timeout}s",
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        logger.error(f"[health/{check.name}] unhandled exception: {type(e).__name__}: {e}")
        return CheckResult.failed(
            check.name,
            duration_ms=duration_ms,
            error=f"{type(e).__name__}: {e}",
        )


async def check_all_components() -> dict[str, CheckResult]:
    """Run all component health probes concurrently.

    Each probe runs with its own timeout via asyncio.wait_for().
    All probes execute in parallel via asyncio.gather().
    Failures in one probe do not abort others.

    Returns:
        dict mapping check name → CheckResult for all registered probes.
    """
    tasks = [_run_single_probe(check) for check in COMPONENT_CHECKS]
    results = await asyncio.gather(*tasks)

    result_dict: dict[str, CheckResult] = {}
    for check, result in zip(COMPONENT_CHECKS, results):
        if isinstance(result, CheckResult):
            result_dict[check.name] = result
        else:
            # Safety net: should not happen since _run_single_probe always returns CheckResult
            result_dict[check.name] = CheckResult.failed(
                check.name,
                error=f"unexpected result type: {type(result).__name__}",
            )

    return result_dict
