from __future__ import annotations

"""Unified entry point for bilibili-api-python.

All bilibili_api imports go through a single lazy-import mechanism.
If the library is not installed, all functions return empty results with a warning.
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


_LAZY_CACHE: dict[str, Any] = {}
_IMPORT_ERROR: Exception | None = None


def _import_bilibili_api(*modules: str) -> dict[str, Any]:
    """Lazy-import bilibili_api submodules. Caches results after first call.

    Args:
        *modules: Module names to import (e.g., 'live', 'hot', 'comment', 'search', 'sync').

    Returns:
        Dict mapping module name → module object.
    """
    global _IMPORT_ERROR, _LAZY_CACHE
    if _IMPORT_ERROR is not None:
        raise _IMPORT_ERROR

    result: dict[str, Any] = {}
    try:
        import bilibili_api  # noqa: F401
        for name in modules:
            if name not in _LAZY_CACHE:
                _LAZY_CACHE[name] = __import__(f"bilibili_api.{name}", fromlist=[name])
            result[name] = _LAZY_CACHE[name]
    except ImportError as e:
        _IMPORT_ERROR = e
        raise

    return result


async def fetch_live_danmaku(
    room_id: int,
    limit: int = 100,
    timeout: float = 15.0,
) -> list[str]:
    """Fetch historical danmaku from a Bilibili live room.

    Replaces duplicate implementations in:
    - MemeCollector._fetch_historical_danmaku()
    - InteractionLearner._collect_danmaku()

    Args:
        room_id: Bilibili live room ID.
        limit: Maximum number of danmaku texts to return.
        timeout: Per-request timeout in seconds.

    Returns:
        List of danmaku text strings. Empty list on error.
    """
    try:
        modules = _import_bilibili_api("live", "sync")
    except ImportError:
        logger.warning("[bilibili.api] bilibili-api-python not installed, skipping live danmaku fetch")
        return []

    try:
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: modules["sync"].sync(modules["live"].get_danmaku(
                    room_id=room_id,
                    page_index=1,
                )),
            ),
            timeout=timeout,
        )

        texts: list[str] = []
        if result and "data" in result:
            data = result.get("data", {})
            danmaku_list = data.get("list", data.get("danmaku", []))
            if isinstance(danmaku_list, list):
                for d in danmaku_list[:limit]:
                    if isinstance(d, dict):
                        content = d.get("text", d.get("content", d.get("msg", "")))
                    else:
                        content = str(d)
                    if content:
                        texts.append(str(content)[:200])

        return texts

    except TimeoutError:
        logger.warning("[bilibili.api] Live danmaku fetch timed out for room %d (%.1fs)", room_id, timeout)
        return []
    except Exception as e:
        logger.debug("[bilibili.api] Live danmaku fetch failed for room %d: %s", room_id, e)
        return []


async def fetch_trending_videos(
    max_videos: int = 50,
    search_keyword: str = "",
) -> list[dict]:
    """Fetch trending videos from Bilibili hot API, with search fallback.

    Returns raw video dicts from the API response.

    Args:
        max_videos: Maximum number of videos to return.
        search_keyword: Fallback search keyword if hot API returns nothing.

    Returns:
        List of raw video dicts from bilibili_api.
    """
    try:
        modules = _import_bilibili_api("hot", "sync")
    except ImportError:
        logger.warning("[bilibili.api] bilibili-api-python not installed, skipping trending videos")
        return []

    videos: list[dict] = []
    loop = asyncio.get_event_loop()

    # Try hot topics first
    try:
        hot_result = await loop.run_in_executor(
            None,
            lambda: modules["sync"].sync(modules["hot"].get_hot_videos()),
        )
        if hot_result and "list" in hot_result:
            items = hot_result.get("list", [])
            for item in items[:max_videos]:
                videos.append(item)
    except Exception as e:
        logger.warning("[bilibili.api] Hot videos API failed: %s", e)

    # Fallback to search
    if not videos and search_keyword:
        try:
            modules_search = _import_bilibili_api("search", "sync")
            result = await loop.run_in_executor(
                None,
                lambda: modules_search["sync"].sync(modules_search["search"].search(
                    keyword=search_keyword,
                    page=1,
                )),
            )
            if result and "result" in result:
                items = result.get("result", [])
                for item in items[:max_videos]:
                    videos.append(item)
        except Exception as e:
            logger.warning("[bilibili.api] Search API fallback failed: %s", e)

    return videos


async def fetch_comments(
    bvid: str,
    max_count: int = 50,
    min_likes: int = 2,
    timeout: float = 15.0,
) -> list[dict]:
    """Fetch top comments for a Bilibili video.

    Args:
        bvid: Bilibili video BV ID.
        max_count: Maximum number of comments to return.
        min_likes: Minimum likes threshold for comment inclusion.
        timeout: Per-request timeout in seconds.

    Returns:
        List of raw comment dicts.
    """
    try:
        modules = _import_bilibili_api("comment", "sync")
    except ImportError:
        logger.warning("[bilibili.api] bilibili-api-python not installed, skipping comments")
        return []

    try:
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: modules["sync"].sync(modules["comment"].get_comments(
                    oid=bvid,
                    type_=modules["comment"].CommentResourceType.VIDEO,
                    order=modules["comment"].OrderType.LIKE,
                    page_index=1,
                )),
            ),
            timeout=timeout,
        )

        if not result or "replies" not in result:
            return []

        comments: list[dict] = []
        for reply in result.get("replies", [])[:max_count]:
            try:
                content = reply.get("content", {})
                message = content.get("message", "") if isinstance(content, dict) else str(content)
                likes = reply.get("like", 0)
                if likes >= min_likes and message:
                    comments.append({
                        "content": message,
                        "likes": likes,
                        "replies": reply.get("rcount", 0),
                        "publish_time": str(reply.get("ctime", "")),
                    })
            except Exception:
                continue

        return comments

    except TimeoutError:
        logger.warning("[bilibili.api] Comment fetch timed out for BV %s (%.1fs)", bvid, timeout)
        return []
    except Exception as e:
        logger.debug("[bilibili.api] Comment fetch failed for %s: %s", bvid, e)
        return []
