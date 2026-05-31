"""BilibiliMemeCollector — 从 B 站热门视频采集梗候选.

Uses bilibili-api-python to fetch trending videos and comments,
then uses LLM to identify emerging meme (梗) patterns.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Chinese stopwords for heuristic filtering
_STOPWORDS = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "这个", "那个", "什么", "怎么", "如何", "可以", "没有", "还是",
    "但是", "因为", "所以", "如果", "虽然", "而且", "或者", "不是", "就是",
    "我们", "你们", "他们", "它们", "自己", "起来", "这些", "那些",
})

# Chinese punctuation for title splitting
_TITLE_SEPARATORS = re.compile(r"[,，、。！？：；""''（）!?:\\;\"'\\(\\)\\s]|·|●|◆|【|】|《|》|—+")


@dataclass
class CollectedVideo:
    """Raw video data collected from B站."""
    bvid: str
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
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
    source_videos: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "context_hint": self.context_hint,
            "frequency": self.frequency,
            "source_videos": self.source_videos,
            "tags": self.tags,
        }


# ── LLM Prompt for meme candidate identification ─────────────────────

MEME_IDENTIFY_SYSTEM_PROMPT = """你是一个中文互联网梗（meme）分析专家。从B站热门视频的标题、标签、评论和弹幕中识别新兴的网络梗。

梗的特征：
- 在多个视频或评论中重复出现的特定短语、句式或概念
- 具有幽默、反讽、荒诞或自指等特征
- 通常由某个视频引发，在评论区被大量复制和改编
- **在弹幕中高频重复出现的短语**（弹幕是梗的重要发酵地）

分析要求：
- 识别重复出现的特定短语（非通用词汇）
- 判断是否具有梗的结构特征（双关、反讽、谐音、荒诞、反差等）
- **优先关注弹幕高频短语中具有梗特征的表达**
- **跨视频交叉验证**：如果某个短语在多个视频的弹幕/评论中出现，优先识别
- 区分"通用流行语"和"特定场景梗"
- 不要将普通的流行语或日常用语误判为梗

返回 JSON 数组（不要 markdown 包裹）：
[
  {
    "text": "梗的文本",
    "context_hint": "梗的使用场景（如：吐槽某事时、表达无奈时）",
    "frequency": 出现频次估计,
    "tags": ["双关", "自指", "弹幕高频"],
    "description": "梗的简要说明"
  }
]"""

MEME_IDENTIFY_USER_PROMPT = """分析以下B站热门内容，识别其中出现的新兴梗：

{video_data}

{danmaku_section}

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
        llm_client: Any | None = None,
        config: dict[str, Any] | None = None,
        danmaku_buffer: Any | None = None,
    ):
        """
        Args:
            llm_client: LLM client with .chat(messages, **kwargs) method.
            config: Optional config dict. Keys:
                - max_videos: max videos to collect (default 50)
                - max_comments_per_video: max comments per video (default 50)
                - min_comment_likes: minimum likes for comment inclusion (default 2)
                - request_delay: delay between API requests in seconds (default 0.3)
                - search_keyword: keyword for trending search (default "")
                - request_timeout: overall timeout in seconds (default 120)
                - comment_timeout: per-comment timeout in seconds (default 15)
                - room_id: Bilibili live room ID for danmaku collection (default 0)
                - concurrency: max parallel requests for comment fetching (default 5)
            danmaku_buffer: Optional DanmakuBuffer instance for real-time danmaku.
        """
        self._llm = llm_client
        self._config = config or {}
        self._max_videos = self._config.get("max_videos", 50)
        self._max_comments_per_video = self._config.get("max_comments_per_video", 50)
        self._min_comment_likes = self._config.get("min_comment_likes", 2)
        self._request_delay = self._config.get("request_delay", 0.3)
        self._search_keyword = self._config.get("search_keyword", "")
        self._request_timeout = self._config.get("request_timeout", 120)
        self._comment_timeout = self._config.get("comment_timeout", 15)
        self._room_id = self._config.get("room_id", 0)
        self._concurrency = self._config.get("concurrency", 5)
        self._danmaku_buffer = danmaku_buffer

    # ── Public API ──────────────────────────────────────────────────────

    async def collect(self) -> list[MemeCandidateRaw]:
        """Run the full collection pipeline: videos → comments → meme identification.

        Returns:
            List of MemeCandidateRaw identified from trending content.
        """
        logger.info(
            "[BilibiliMemeCollector] Starting collection "
            "(max_videos=%d, max_comments=%d, timeout=%ds)",
            self._max_videos,
            self._max_comments_per_video,
            self._request_timeout,
        )

        try:
            return await asyncio.wait_for(
                self._collect_impl(),
                timeout=self._request_timeout,
            )
        except TimeoutError:
            logger.warning(
                "[BilibiliMemeCollector] Collection timed out after %ds — "
                "returning partial results",
                self._request_timeout,
            )
            return []
        except Exception as e:
            logger.error("[BilibiliMemeCollector] Collection failed: %s", e, exc_info=True)
            return []

    async def _collect_impl(self) -> list[MemeCandidateRaw]:
        """Internal collection implementation (wrapped with timeout by collect())."""
        try:
            # Phase 1: Fetch trending videos (existing path)
            videos_task = asyncio.create_task(self._fetch_trending_videos())

            # Phase 2: Fetch danmaku phrases (new path — runs in parallel with videos)
            danmaku_task = asyncio.create_task(self._fetch_danmaku_phrases())

            videos = await videos_task
            danmaku_phrases = await danmaku_task

            if not videos:
                logger.info("[BilibiliMemeCollector] No trending videos found")
                # If we have danmaku phrases but no videos, still do heuristic
                if danmaku_phrases:
                    logger.info(
                        "[BilibiliMemeCollector] %d danmaku phrases collected, "
                        "running heuristic-only identification",
                        len(danmaku_phrases),
                    )
                    return self._heuristic_danmaku_only(danmaku_phrases)
                return []

            logger.info("[BilibiliMemeCollector] Fetched %d videos", len(videos))
            if danmaku_phrases:
                logger.info(
                    "[BilibiliMemeCollector] Collected %d danmaku hot phrases",
                    len(danmaku_phrases),
                )

            # Phase 3: Collect comments in parallel with semaphore control
            all_comments: dict[str, list[CollectedComment]] = {}
            semaphore = asyncio.Semaphore(self._concurrency)

            async def fetch_one(video: CollectedVideo) -> tuple[str, list[CollectedComment]]:
                async with semaphore:
                    await asyncio.sleep(self._request_delay)
                    comments = await self._fetch_comments(video.bvid)
                    return video.bvid, comments

            results = await asyncio.gather(
                *[fetch_one(v) for v in videos],
                return_exceptions=True,
            )

            for r in results:
                if isinstance(r, BaseException):
                    logger.warning("[BilibiliMemeCollector] Comment fetch error: %s", r)
                    continue
                bvid, comments = r
                if comments:
                    all_comments[bvid] = comments

            logger.info(
                "[BilibiliMemeCollector] Collected comments for %d/%d videos",
                len(all_comments), len(videos),
            )

            # Phase 4: Identify meme candidates via LLM (includes danmaku context)
            candidates = await self._identify_meme_candidates(
                videos, all_comments, danmaku_phrases,
            )
            logger.info(
                "[BilibiliMemeCollector] Identified %d meme candidates",
                len(candidates),
            )
            return candidates

        except Exception as e:
            logger.error("[BilibiliMemeCollector] Collection failed: %s", e, exc_info=True)
            return []

    # ── Video collection ────────────────────────────────────────────────

    async def _fetch_trending_videos(self) -> list[CollectedVideo]:
        """Fetch trending videos from B站 using hot/ranking APIs."""
        try:
            from bilibili_api import hot, sync
        except ImportError:
            logger.error(
                "[BilibiliMemeCollector] bilibili-api-python not installed. "
                "Run: pip install bilibili-api-python"
            )
            return []

        videos: list[CollectedVideo] = []

        try:
            loop = asyncio.get_event_loop()

            # Try hot topics first (no auth needed for basic listing)
            try:
                logger.info("[BilibiliMemeCollector] Calling hot.get_hot_videos()...")
                hot_result = await loop.run_in_executor(
                    None,
                    lambda: sync(hot.get_hot_videos()),
                )
                if hot_result is None:
                    logger.warning("[BilibiliMemeCollector] hot.get_hot_videos() returned None")
                elif "list" not in hot_result:
                    logger.warning(
                        "[BilibiliMemeCollector] hot.get_hot_videos() returned unexpected keys: %s",
                        list(hot_result.keys())[:5],
                    )
                else:
                    items = hot_result.get("list", [])
                    logger.info(
                        "[BilibiliMemeCollector] hot.get_hot_videos() returned %d items",
                        len(items),
                    )
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
                logger.warning(
                    "[BilibiliMemeCollector] Hot videos API failed: %s",
                    e, exc_info=True,
                )

            logger.info(
                "[BilibiliMemeCollector] Videos after hot API: %d (search_keyword=%s)",
                len(videos), self._search_keyword,
            )

            # Fallback: use search with keyword
            if not videos and self._search_keyword:
                from bilibili_api import search as bilibili_search
                logger.info(
                    "[BilibiliMemeCollector] Falling back to search keyword='%s'",
                    self._search_keyword,
                )
                try:
                    result = await loop.run_in_executor(
                        None,
                        lambda: sync(bilibili_search.search(
                            keyword=self._search_keyword,
                            page=1,
                        )),
                    )
                    if result and "result" in result:
                        items = result.get("result", [])
                        logger.info(
                            "[BilibiliMemeCollector] Search returned %d items",
                            len(items),
                        )
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
                    else:
                        logger.warning(
                            "[BilibiliMemeCollector] Search returned no results or unexpected format"
                        )
                except Exception as e:
                    logger.warning(
                        "[BilibiliMemeCollector] Search API failed: %s",
                        e, exc_info=True,
                    )

        except Exception as e:
            logger.warning(
                "[BilibiliMemeCollector] Video fetch outer try failed: %s",
                e, exc_info=True,
            )

        logger.info(
            "[BilibiliMemeCollector] _fetch_trending_videos returning %d videos",
            len(videos),
        )
        return videos

    @staticmethod
    def _parse_tags(tag_str: str) -> list[str]:
        """Parse comma-separated tag string into list."""
        if not tag_str:
            return []
        return [t.strip() for t in tag_str.split(",") if t.strip()]

    # ── Comment collection ──────────────────────────────────────────────

    async def _fetch_comments(self, bvid: str) -> list[CollectedComment]:
        """Fetch top comments for a video."""
        try:
            from bilibili_api import comment, sync
        except ImportError:
            return []

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: sync(comment.get_comments(
                        oid=bvid,
                        type_=comment.CommentResourceType.VIDEO,
                        order=comment.OrderType.LIKE,
                        page_index=1,
                    )),
                ),
                timeout=self._comment_timeout,
            )

            if not result or "replies" not in result:
                return []

            comments: list[CollectedComment] = []
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

        except TimeoutError:
            logger.warning(
                "[BilibiliMemeCollector] Comment fetch timed out for %s (%ds)",
                bvid, self._comment_timeout,
            )
            return []
        except Exception as e:
            logger.debug("[BilibiliMemeCollector] Comment fetch failed for %s: %s", bvid, e)
            return []

    # ── Danmaku collection (new) ─────────────────────────────────────────

    async def _fetch_danmaku_phrases(self) -> list[str]:
        """Collect hot danmaku phrases from DanmakuBuffer and historical API.

        Two sources:
        1. Real-time buffer (DanmakuBuffer.get_hot_phrases)
        2. Historical danmaku API (live.get_danmaku)

        Returns:
            List of hot danmaku phrase texts, deduplicated.
        """
        phrases: list[str] = []
        seen: set = set()

        # Source 1: Real-time buffer
        if self._danmaku_buffer:
            try:
                hot = self._danmaku_buffer.get_hot_phrases(
                    min_freq=3, window_minutes=30,
                )
                for p in hot:
                    text = p.text.strip()
                    if text and text not in seen:
                        phrases.append(text)
                        seen.add(text)
                if hot:
                    logger.info(
                        "[BilibiliMemeCollector] Got %d hot phrases from DanmakuBuffer",
                        len(hot),
                    )
            except Exception as e:
                logger.warning(
                    "[BilibiliMemeCollector] DanmakuBuffer query failed: %s", e,
                )

        # Source 2: Historical danmaku API
        if self._room_id:
            try:
                historical = await self._fetch_historical_danmaku(self._room_id)
                for text in historical:
                    if text and text not in seen:
                        phrases.append(text)
                        seen.add(text)
                if historical:
                    logger.info(
                        "[BilibiliMemeCollector] Got %d historical danmaku texts",
                        len(historical),
                    )
            except Exception as e:
                logger.warning(
                    "[BilibiliMemeCollector] Historical danmaku fetch failed: %s", e,
                )

        return phrases

    async def _fetch_historical_danmaku(self, room_id: int) -> list[str]:
        """Fetch historical danmaku from a Bilibili live room via API.

        Args:
            room_id: Bilibili live room ID.

        Returns:
            List of danmaku text strings (limited to ~100 samples).
        """
        try:
            from bilibili_api import live, sync
        except ImportError:
            logger.warning(
                "[BilibiliMemeCollector] bilibili-api-python not installed, "
                "skipping historical danmaku",
            )
            return []

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: sync(live.get_danmaku(
                        room_id=room_id,
                        page_index=1,
                    )),
                ),
                timeout=self._comment_timeout,
            )

            texts: list[str] = []
            if result and "data" in result:
                data = result.get("data", {})
                danmaku_list = data.get("list", data.get("danmaku", []))
                if isinstance(danmaku_list, list):
                    for d in danmaku_list[:100]:
                        if isinstance(d, dict):
                            content = d.get("text", d.get("content", d.get("msg", "")))
                        else:
                            content = str(d)
                        if content and len(content.strip()) >= 2:
                            texts.append(str(content)[:200])

            return texts

        except TimeoutError:
            logger.warning(
                "[BilibiliMemeCollector] Historical danmaku timed out for room %d",
                room_id,
            )
            return []
        except Exception as e:
            logger.debug(
                "[BilibiliMemeCollector] Historical danmaku fetch failed: %s", e,
            )
            return []

    # ── Meme identification ─────────────────────────────────────────────

    async def _identify_meme_candidates(
        self,
        videos: list[CollectedVideo],
        comments: dict[str, list[CollectedComment]],
        danmaku_phrases: list[str] | None = None,
    ) -> list[MemeCandidateRaw]:
        """Use LLM to identify meme patterns from collected data.

        Args:
            videos: Collected trending videos.
            comments: Collected comments per video.
            danmaku_phrases: Optional hot danmaku phrases from buffer/history.

        Returns:
            List of MemeCandidateRaw identified by LLM or heuristic fallback.
        """
        if not self._llm:
            logger.info("[BilibiliMemeCollector] No LLM client, using heuristic identification")
            return self._heuristic_identify(videos, comments, danmaku_phrases)

        # Build context for LLM
        video_lines: list[str] = []
        for v in videos:
            video_lines.append(
                f"视频: {v.title}\n"
                f"标签: {', '.join(v.tags) if v.tags else '无'}\n"
                f"播放: {v.view_count}, 弹幕: {v.danmaku_count}"
            )

        comment_lines: list[str] = []
        for bvid, clist in comments.items():
            for c in clist[:10]:  # Limit comments to avoid token overflow
                comment_lines.append(f"[{bvid}] 👍{c.likes}: {c.content}")

        video_text = "\n\n".join(video_lines[:20])
        comment_text = "\n".join(comment_lines[:50])

        combined = f"=== 热门视频 ===\n\n{video_text}\n\n=== 高赞评论 ===\n\n{comment_text}"

        # Build danmaku section if available
        danmaku_section = ""
        if danmaku_phrases:
            danmaku_lines = "\n".join(f"  - {p}" for p in danmaku_phrases[:30])
            danmaku_section = f"=== 弹幕高频短语 ===\n\n{danmaku_lines}"

        # Try chat_messages first (new interface), fall back to chat (legacy)
        llm_method = None
        if hasattr(self._llm, 'chat_messages'):
            llm_method = 'chat_messages'
        elif hasattr(self._llm, 'chat'):
            llm_method = 'chat'
            logger.info("[BilibiliMemeCollector] LLM lacks chat_messages, using chat() fallback")

        if not llm_method:
            logger.warning(
                "[BilibiliMemeCollector] LLM has neither chat_messages nor chat(), "
                "using heuristic"
            )
            return self._heuristic_identify(videos, comments, danmaku_phrases)

        try:
            if llm_method == 'chat_messages':
                result = await self._llm.chat_messages(
                    messages=[
                        {"role": "system", "content": MEME_IDENTIFY_SYSTEM_PROMPT},
                        {"role": "user", "content": MEME_IDENTIFY_USER_PROMPT.format(
                            video_data=combined,
                            danmaku_section=danmaku_section,
                        )},
                    ],
                    response_format={"type": "json_object"},
                )
            else:
                # Legacy chat() interface — build single user message
                user_text = MEME_IDENTIFY_SYSTEM_PROMPT + "\n\n" + MEME_IDENTIFY_USER_PROMPT.format(
                    video_data=combined,
                    danmaku_section=danmaku_section,
                )
                result = await self._llm.chat(
                    messages=[{"role": "user", "content": user_text}],
                    response_format={"type": "json_object"},
                )

            content = result.get("content", "") if isinstance(result, dict) else str(result)
            parsed = self._parse_llm_json(content)
            return self._build_candidates(parsed, videos)

        except Exception as e:
            logger.warning("[BilibiliMemeCollector] LLM identification failed: %s", e)
            return self._heuristic_identify(videos, comments, danmaku_phrases)

    def _heuristic_identify(
        self,
        videos: list[CollectedVideo],
        comments: dict[str, list[CollectedComment]],
        danmaku_phrases: list[str] | None = None,
    ) -> list[MemeCandidateRaw]:
        """Fallback: identify meme candidates from high-frequency phrases.

        Four strategies combined:
        1. Repeated tags across videos
        2. Meaningful phrases from video titles
        3. High-frequency n-grams from top comments
        4. Hot danmaku phrases (new)
        """
        candidates: list[MemeCandidateRaw] = []
        seen_texts: set = set()

        # ── Strategy 1: Repeated tags ──
        tag_counts: dict[str, int] = {}
        for v in videos:
            for tag in v.tags:
                t = tag.strip()
                if len(t) >= 2 and t not in _STOPWORDS:
                    tag_counts[t] = tag_counts.get(t, 0) + 1
        for phrase, count in tag_counts.items():
            if count >= 2 and len(phrase) <= 15 and phrase not in seen_texts:
                seen_texts.add(phrase)
                candidates.append(MemeCandidateRaw(
                    text=phrase,
                    context_hint=f"出现在 {count} 个热门视频标签中",
                    frequency=count,
                    tags=["bilibili", "trending", "tag"],
                ))

        # ── Strategy 2: Extract meaningful phrases from titles ──
        title_phrases: Counter = Counter()
        for v in videos:
            for phrase in self._extract_title_phrases(v.title):
                if phrase not in _STOPWORDS and len(phrase) >= 2:
                    title_phrases[phrase] += 1
        for phrase, count in title_phrases.most_common(10):
            if count >= 2 and phrase not in seen_texts:
                seen_texts.add(phrase)
                candidates.append(MemeCandidateRaw(
                    text=phrase,
                    context_hint=f"出现在 {count} 个视频标题中的热门短语",
                    frequency=count,
                    tags=["bilibili", "trending", "title"],
                ))

        # ── Strategy 3: Extract n-grams from top comments ──
        all_comments_text: list[str] = []
        for clist in comments.values():
            for c in clist[:5]:
                all_comments_text.append(c.content)
        comment_ngrams = self._extract_comment_ngrams(all_comments_text)
        for phrase, count in comment_ngrams.most_common(10):
            if count >= 2 and phrase not in seen_texts:
                seen_texts.add(phrase)
                candidates.append(MemeCandidateRaw(
                    text=phrase,
                    context_hint=f"在热门评论中出现 {count} 次",
                    frequency=count,
                    tags=["bilibili", "trending", "comment"],
                ))

        # ── Strategy 4: Hot danmaku phrases (new) ──
        if danmaku_phrases:
            # Use semantic extraction if available, else simple frequency
            try:
                semantic = self._extract_semantic_phrases(danmaku_phrases, top_k=20)
                for phrase, count in semantic:
                    if phrase not in seen_texts and phrase not in _STOPWORDS:
                        seen_texts.add(phrase)
                        candidates.append(MemeCandidateRaw(
                            text=phrase,
                            context_hint=f"弹幕高频短语，出现 {count} 次以上",
                            frequency=count,
                            tags=["bilibili", "danmaku", "hot"],
                        ))
            except ImportError:
                # jieba not available — use simple frequency
                from collections import Counter as _Counter
                freq = _Counter(danmaku_phrases)
                for phrase, count in freq.most_common(15):
                    if (phrase not in seen_texts and phrase not in _STOPWORDS
                            and len(phrase) >= 2):
                        seen_texts.add(phrase)
                        candidates.append(MemeCandidateRaw(
                            text=phrase,
                            context_hint=f"弹幕中出现 {count} 次",
                            frequency=count,
                            tags=["bilibili", "danmaku", "hot"],
                        ))

        logger.info(
            "[BilibiliMemeCollector] Heuristic identify: %d candidates from "
            "%d videos, %d comments, %d danmaku phrases",
            len(candidates), len(videos),
            sum(len(c) for c in comments.values()),
            len(danmaku_phrases) if danmaku_phrases else 0,
        )
        return candidates[:15]

    def _heuristic_danmaku_only(
        self,
        danmaku_phrases: list[str],
    ) -> list[MemeCandidateRaw]:
        """Fallback when only danmaku data is available (no videos)."""
        candidates: list[MemeCandidateRaw] = []
        seen: set = set()

        try:
            semantic = self._extract_semantic_phrases(danmaku_phrases, top_k=15)
            for phrase, count in semantic:
                if phrase not in seen and phrase not in _STOPWORDS and len(phrase) >= 2:
                    seen.add(phrase)
                    candidates.append(MemeCandidateRaw(
                        text=phrase,
                        context_hint="弹幕高频短语",
                        frequency=count,
                        tags=["bilibili", "danmaku", "hot"],
                    ))
        except ImportError:
            from collections import Counter as _Counter
            freq = _Counter(danmaku_phrases)
            for phrase, count in freq.most_common(10):
                if (phrase not in seen and phrase not in _STOPWORDS
                        and len(phrase) >= 2):
                    seen.add(phrase)
                    candidates.append(MemeCandidateRaw(
                        text=phrase,
                        context_hint="弹幕高频短语",
                        frequency=count,
                        tags=["bilibili", "danmaku", "hot"],
                    ))

        return candidates[:10]

    @staticmethod
    def _extract_semantic_phrases(
        texts: list[str],
        top_k: int = 20,
    ) -> list[tuple[str, int]]:
        """Extract meaningful phrases using jieba segmentation + TF-IDF filtering.

        Uses jieba for Chinese word segmentation, extracts 2-4 word n-grams,
        and applies TF-IDF to filter stopwords.

        Falls back to simple character n-grams if jieba is not installed.
        """
        try:
            import jieba
        except ImportError:
            # Fallback: use character 2-gram like old method
            logger.warning(
                "[BilibiliMemeCollector] jieba not installed, "
                "falling back to char n-grams for semantic extraction"
            )
            from collections import Counter as _Counter
            fallback: _Counter = _Counter()
            for text in texts:
                chars = list(text.strip())
                for n in range(2, min(5, len(chars) + 1)):
                    for i in range(len(chars) - n + 1):
                        phrase = "".join(chars[i:i + n])
                        if phrase.strip() and not phrase.isdigit():
                            fallback[phrase] += 1
            return fallback.most_common(top_k)

        from collections import Counter
        from math import log

        # Jieba-based semantic extraction
        total_docs = len(texts)
        if total_docs == 0:
            return []

        # Tokenize all texts
        tokenized = [list(jieba.cut(t)) for t in texts]

        # Extract 2-4 word n-grams
        ngram_counter: Counter = Counter()
        doc_frequency: Counter = Counter()

        for tokens in tokenized:
            seen_in_doc = set()
            for i in range(len(tokens)):
                for j in range(i + 1, min(i + 4, len(tokens) + 1)):
                    phrase = "".join(tokens[i:j])
                    if len(phrase) < 2 or len(phrase) > 15:
                        continue
                    if phrase.isdigit():
                        continue
                    ngram_counter[phrase] += 1
                    seen_in_doc.add(phrase)
            for phrase in seen_in_doc:
                doc_frequency[phrase] += 1

        # TF-IDF scoring: score = count * log(total_docs / (1 + doc_freq))
        scored = []
        for phrase, count in ngram_counter.items():
            if count < 2:  # Must appear at least twice
                continue
            if phrase in _STOPWORDS:
                continue
            df = doc_frequency.get(phrase, 1)
            # Boost phrases that appear across multiple documents
            idf = log((total_docs + 1) / (df + 1)) + 1
            score = count * idf
            scored.append((phrase, int(score)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _extract_title_phrases(self, title: str) -> list[str]:
        """Split title into candidate phrases using punctuation and common patterns."""
        if not title:
            return []
        # Split by punctuation
        parts = _TITLE_SEPARATORS.split(title)
        phrases: list[str] = []
        for part in parts:
            part = part.strip()
            # Keep 2-15 char segments that aren't pure numbers
            if 2 <= len(part) <= 15 and not part.isdigit():
                phrases.append(part)
                # Also extract 2-4 char sub-phrases for longer segments
                if len(part) > 4:
                    for i in range(len(part) - 1):
                        sub = part[i:i+2]
                        if sub not in _STOPWORDS:
                            phrases.append(sub)
        return phrases

    @staticmethod
    def _extract_comment_ngrams(comments: list[str]) -> Counter:
        """Extract meaningful bigrams and trigrams from comment text."""
        ngram_counts: Counter = Counter()
        for text in comments:
            if not text:
                continue
            # Simple tokenization: split by whitespace/punctuation for Chinese text
            chars = list(text.strip())
            # Bigrams
            for i in range(len(chars) - 1):
                bigram = chars[i] + chars[i+1]
                if bigram not in _STOPWORDS and not bigram.isdigit() and len(bigram.strip()) == 2:
                    ngram_counts[bigram] += 1
        return ngram_counts

    @staticmethod
    def _parse_llm_json(raw: str) -> list[dict[str, Any]]:
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
        parsed: list[dict[str, Any]],
        videos: list[CollectedVideo],
    ) -> list[MemeCandidateRaw]:
        """Build MemeCandidateRaw from parsed LLM output."""
        candidates: list[MemeCandidateRaw] = []
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
