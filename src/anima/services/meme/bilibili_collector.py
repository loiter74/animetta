"""BilibiliMemeCollector — 从 B 站热门视频采集梗候选.

Uses bilibili-api-python to fetch trending videos and comments,
then uses LLM to identify emerging meme (梗) patterns.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CollectedVideo:
    """Raw video data collected from B站."""
    bvid: str
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    view_count: int = 0
    danmaku_count: int = 0
    reply_count: int = 0

    def to_dict(self) -> dict:
        return {
            "bvid": self.bvid,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "view_count": self.view_count,
            "danmaku_count": self.danmaku_count,
            "reply_count": self.reply_count,
        }


@dataclass
class CollectedComment:
    """Raw comment data collected from B站."""
    content: str
    likes: int = 0
    replies: int = 0
    publish_time: str = ""

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "likes": self.likes,
            "replies": self.replies,
            "publish_time": self.publish_time,
        }


@dataclass
class MemeCandidateRaw:
    """Raw meme candidate identified from B站 content before cognitive analysis."""
    text: str
    context_hint: str = ""
    frequency: int = 1
    source_videos: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "context_hint": self.context_hint,
            "frequency": self.frequency,
            "source_videos": self.source_videos,
            "tags": self.tags,
        }


# ── LLM Prompt for meme candidate identification ─────────────────────

MEME_IDENTIFY_SYSTEM_PROMPT = """你是一个中文互联网梗（meme）分析专家。从B站热门视频的标题、标签和评论中识别新兴的网络梗。

梗的特征：
- 在多个视频或评论中重复出现的特定短语、句式或概念
- 具有幽默、反讽、荒诞或自指等特征
- 通常由某个视频引发，在评论区被大量复制和改编

分析要求：
- 识别重复出现的特定短语（非通用词汇）
- 判断是否具有梗的结构特征（双关、反讽、谐音、荒诞、反差等）
- 不要将普通的流行语或日常用语误判为梗

返回 JSON 数组（不要 markdown 包裹）：
[
  {
    "text": "梗的文本",
    "context_hint": "梗的使用场景（如：吐槽某事时、表达无奈时）",
    "frequency": 出现频次估计,
    "tags": ["双关", "自指"],
    "description": "梗的简要说明"
  }
]"""

MEME_IDENTIFY_USER_PROMPT = """分析以下B站热门内容，识别其中出现的新兴梗：

{video_data}

请识别重复出现的梗模式，返回 JSON 数组。"""


class BilibiliMemeCollector:
    """从 B 站热门视频采集梗候选。

    采集流程：
    1. 使用 bilibili-api-python 搜索热门视频
    2. 提取标题、标签、高赞评论
    3. LLM 分析识别梗候选模式
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            llm_client: LLM client with .chat(messages, **kwargs) method.
            config: Optional config dict. Keys:
                - max_videos: max videos to collect (default 20)
                - max_comments_per_video: max comments per video (default 20)
                - min_comment_likes: minimum likes for comment inclusion (default 3)
                - request_delay: delay between API requests in seconds (default 1.0)
                - search_keyword: keyword for trending search (default "")
        """
        self._llm = llm_client
        self._config = config or {}
        self._max_videos = self._config.get("max_videos", 20)
        self._max_comments_per_video = self._config.get("max_comments_per_video", 20)
        self._min_comment_likes = self._config.get("min_comment_likes", 3)
        self._request_delay = self._config.get("request_delay", 1.0)
        self._search_keyword = self._config.get("search_keyword", "")

    # ── Public API ──────────────────────────────────────────────────────

    async def collect(self) -> List[MemeCandidateRaw]:
        """Run the full collection pipeline: videos → comments → meme identification.

        Returns:
            List of MemeCandidateRaw identified from trending content.
        """
        logger.info(
            "[BilibiliMemeCollector] Starting collection "
            "(max_videos=%d, max_comments=%d)",
            self._max_videos,
            self._max_comments_per_video,
        )

        try:
            videos = await self._fetch_trending_videos()
            if not videos:
                logger.info("[BilibiliMemeCollector] No trending videos found")
                return []

            logger.info("[BilibiliMemeCollector] Fetched %d videos", len(videos))

            # Collect comments for each video
            all_comments: Dict[str, List[CollectedComment]] = {}
            for video in videos:
                try:
                    await asyncio.sleep(self._request_delay)
                    comments = await self._fetch_comments(video.bvid)
                    if comments:
                        all_comments[video.bvid] = comments
                except Exception as e:
                    logger.warning(
                        "[BilibiliMemeCollector] Failed to fetch comments for %s: %s",
                        video.bvid, e,
                    )

            # Identify meme candidates via LLM
            candidates = await self._identify_meme_candidates(videos, all_comments)
            logger.info("[BilibiliMemeCollector] Identified %d meme candidates", len(candidates))
            return candidates

        except Exception as e:
            logger.error("[BilibiliMemeCollector] Collection failed: %s", e, exc_info=True)
            return []

    # ── Video collection ────────────────────────────────────────────────

    async def _fetch_trending_videos(self) -> List[CollectedVideo]:
        """Fetch trending videos from B站 using hot/ranking APIs."""
        try:
            from bilibili_api import hot, sync
        except ImportError:
            logger.error(
                "[BilibiliMemeCollector] bilibili-api-python not installed. "
                "Run: pip install bilibili-api-python"
            )
            return []

        videos: List[CollectedVideo] = []

        try:
            loop = asyncio.get_event_loop()

            # Try hot topics first (no auth needed for basic listing)
            try:
                hot_result = await loop.run_in_executor(
                    None,
                    lambda: sync(hot.get_hot_videos()),
                )
                if hot_result and "list" in hot_result:
                    items = hot_result.get("list", [])
                    for item in items[:self._max_videos]:
                        try:
                            video = CollectedVideo(
                                bvid=item.get("bvid", ""),
                                title=item.get("title", ""),
                                description=item.get("desc", "")[:200],
                                tags=self._parse_tags(item.get("tag", "")),
                                view_count=item.get("stat", {}).get("view", 0) if isinstance(item.get("stat"), dict) else 0,
                                danmaku_count=item.get("stat", {}).get("danmaku", 0) if isinstance(item.get("stat"), dict) else 0,
                                reply_count=item.get("stat", {}).get("reply", 0) if isinstance(item.get("stat"), dict) else 0,
                            )
                            if video.bvid:
                                videos.append(video)
                        except Exception as e:
                            logger.debug("[BilibiliMemeCollector] Skipped video item: %s", e)
                            continue
            except Exception as e:
                logger.debug("[BilibiliMemeCollector] Hot videos API failed: %s", e)

            # Fallback: use search with keyword
            if not videos and self._search_keyword:
                from bilibili_api import search as bilibili_search
                result = await loop.run_in_executor(
                    None,
                    lambda: sync(bilibili_search.search(
                        keyword=self._search_keyword,
                        page=1,
                    )),
                )
                if result and "result" in result:
                    items = result.get("result", [])
                    for item in items[:self._max_videos]:
                        try:
                            video = CollectedVideo(
                                bvid=item.get("bvid", ""),
                                title=item.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
                                description=item.get("description", "")[:200],
                                tags=self._parse_tags(item.get("tag", "")),
                                view_count=item.get("play", 0),
                                danmaku_count=item.get("video_review", 0),
                                reply_count=item.get("review", 0),
                            )
                            if video.bvid:
                                videos.append(video)
                        except Exception as e:
                            logger.debug("[BilibiliMemeCollector] Skipped search item: %s", e)
                            continue

        except Exception as e:
            logger.warning("[BilibiliMemeCollector] Video fetch failed: %s", e)

        return videos

    @staticmethod
    def _parse_tags(tag_str: str) -> List[str]:
        """Parse comma-separated tag string into list."""
        if not tag_str:
            return []
        return [t.strip() for t in tag_str.split(",") if t.strip()]

    # ── Comment collection ──────────────────────────────────────────────

    async def _fetch_comments(self, bvid: str) -> List[CollectedComment]:
        """Fetch top comments for a video."""
        try:
            from bilibili_api import comment, sync
        except ImportError:
            return []

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: sync(comment.get_comments(
                    oid=bvid,
                    type_=comment.CommentResourceType.VIDEO,
                    order=comment.OrderType.LIKE,
                    page_index=1,
                )),
            )

            if not result or "replies" not in result:
                return []

            comments: List[CollectedComment] = []
            for reply in result.get("replies", [])[:self._max_comments_per_video]:
                try:
                    content = reply.get("content", {})
                    message = content.get("message", "") if isinstance(content, dict) else str(content)
                    likes = reply.get("like", 0)

                    if likes >= self._min_comment_likes and message:
                        comments.append(CollectedComment(
                            content=message,
                            likes=likes,
                            replies=reply.get("rcount", 0),
                            publish_time=str(reply.get("ctime", "")),
                        ))
                except Exception as e:
                    logger.debug("[BilibiliMemeCollector] Skipped comment: %s", e)
                    continue

            return comments

        except Exception as e:
            logger.debug("[BilibiliMemeCollector] Comment fetch failed for %s: %s", bvid, e)
            return []

    # ── Meme identification ─────────────────────────────────────────────

    async def _identify_meme_candidates(
        self,
        videos: List[CollectedVideo],
        comments: Dict[str, List[CollectedComment]],
    ) -> List[MemeCandidateRaw]:
        """Use LLM to identify meme patterns from collected data."""
        if not self._llm:
            logger.info("[BilibiliMemeCollector] No LLM client, using heuristic identification")
            return self._heuristic_identify(videos, comments)

        # Build context for LLM
        video_lines: List[str] = []
        for v in videos:
            video_lines.append(
                f"视频: {v.title}\n"
                f"标签: {', '.join(v.tags) if v.tags else '无'}\n"
                f"播放: {v.view_count}, 弹幕: {v.danmaku_count}"
            )

        comment_lines: List[str] = []
        for bvid, clist in comments.items():
            for c in clist[:10]:  # Limit comments to avoid token overflow
                comment_lines.append(f"[{bvid}] 👍{c.likes}: {c.content}")

        video_text = "\n\n".join(video_lines[:20])
        comment_text = "\n".join(comment_lines[:50])

        combined = f"=== 热门视频 ===\n\n{video_text}\n\n=== 高赞评论 ===\n\n{comment_text}"

        try:
            result = await self._llm.chat(
                messages=[
                    {"role": "system", "content": MEME_IDENTIFY_SYSTEM_PROMPT},
                    {"role": "user", "content": MEME_IDENTIFY_USER_PROMPT.format(video_data=combined)},
                ],
                response_format={"type": "json_object"},
            )

            content = result.get("content", "") if isinstance(result, dict) else str(result)
            parsed = self._parse_llm_json(content)
            return self._build_candidates(parsed, videos)

        except Exception as e:
            logger.warning("[BilibiliMemeCollector] LLM identification failed: %s", e)
            return self._heuristic_identify(videos, comments)

    def _heuristic_identify(
        self,
        videos: List[CollectedVideo],
        comments: Dict[str, List[CollectedComment]],
    ) -> List[MemeCandidateRaw]:
        """Fallback: identify meme candidates from high-frequency phrases in titles/comments."""
        # Simple heuristic: look for repeated phrases across video titles
        candidates: List[MemeCandidateRaw] = []
        title_phrases: Dict[str, int] = {}

        for v in videos:
            # Extract interesting phrases from titles
            title = v.title
            for tag in v.tags:
                if len(tag) >= 2:
                    title_phrases[tag] = title_phrases.get(tag, 0) + 1

        for phrase, count in title_phrases.items():
            if count >= 2 and len(phrase) <= 15:
                candidates.append(MemeCandidateRaw(
                    text=phrase,
                    context_hint=f"来自B站热门视频标签，出现 {count} 次",
                    frequency=count,
                    tags=["bilibili", "trending"],
                ))

        return candidates[:5]

    @staticmethod
    def _parse_llm_json(raw: str) -> List[Dict[str, Any]]:
        """Parse LLM JSON response into list of dicts."""
        text = raw.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                # Try common wrapper keys
                for key in ("memes", "candidates", "results", "items"):
                    if key in data:
                        return data[key]
                return [data]
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("[BilibiliMemeCollector] JSON parse failed: %s", e)
        return []

    @staticmethod
    def _build_candidates(
        parsed: List[Dict[str, Any]],
        videos: List[CollectedVideo],
    ) -> List[MemeCandidateRaw]:
        """Build MemeCandidateRaw from parsed LLM output."""
        candidates: List[MemeCandidateRaw] = []
        source_bvids = [v.bvid for v in videos[:3]] if videos else []

        for item in parsed:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            candidates.append(MemeCandidateRaw(
                text=text,
                context_hint=item.get("context_hint", ""),
                frequency=item.get("frequency", 1),
                source_videos=list(source_bvids),
                tags=item.get("tags", []),
            ))

        return candidates
