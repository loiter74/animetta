"""
ConversationSummarizer — produces structured daily abstracts from raw conversation turns.

Workflow:
1. Group MemoryTurn list by date
2. Call LLM (or fallback to rules) to produce a daily summary
3. Write AI-generated abstract to wiki source page (wiki/sources/YYYY-MM-DD.md)
4. Return LearningLog list for downstream storage
"""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.turns import MemoryTurn

logger = logging.getLogger(__name__)


@dataclass
class LearningLog:
    id: str = ""
    session_id: str = ""
    summary_type: str = ""
    content: str = ""
    source_ids: str = ""
    created_at: Optional[datetime] = None


SUMMARIZE_SYSTEM_PROMPT = """你是一个对话总结助手。请根据以下对话记录，生成一份结构化的每日摘要。

要求:
1. 用简洁自然的语言总结当天核心内容
2. 包含以下部分:
   - **核心话题**: 当天讨论了哪些主要话题
   - **用户状态**: 用户的情绪、需求、关注点
   - **重要互动**: 值得注意的对话或关键信息
3. 控制在 200 字以内
4. 只输出摘要本身，不要额外解释"""

SUMMARIZE_USER_PROMPT = """以下是 {session_id} 在 {date} 的对话记录:

{turns_text}

请生成一份结构化的每日摘要:"""


def _format_turns(turns: List[MemoryTurn]) -> str:
    lines: List[str] = []
    for t in turns:
        time = t.timestamp.strftime("%H:%M")
        emo = f" [{', '.join(t.emotions)}]" if t.emotions else ""
        lines.append(f"[{time}]{emo}")
        lines.append(f"  用户: {t.user_input}")
        lines.append(f"  AI: {t.agent_response}")
        lines.append("")
    return "\n".join(lines)


def _count_messages(turns: List[MemoryTurn]) -> Dict[str, int]:
    return {
        "total": len(turns),
        "user": len([t for t in turns if t.user_input.strip()]),
        "ai": len([t for t in turns if t.agent_response.strip()]),
    }


def _now_iso() -> str:
    return datetime.now().isoformat()


class ConversationSummarizer:
    """
    Produces structured daily summaries from conversation turns.

    Uses LLM when available; falls back to rule-based extraction.
    Writes results as LearningLog entries and optionally to wiki source pages.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self._llm_client = llm_client
        self._config = config or {}

    # ── Public API ────────────────────────────────────────────

    async def summarize(
        self,
        turns: List[MemoryTurn],
        session_id: str,
    ) -> List[LearningLog]:
        """
        Summarize conversation turns for a session, grouped by date.

        Args:
            turns: Conversation turns to summarize.
            session_id: Session identifier.

        Returns:
            List of LearningLog entries, one per date.
        """
        grouped = self._group_by_date(turns)
        results: List[LearningLog] = []

        for date_key, date_turns in sorted(grouped.items()):
            log = await self._summarize_date_group(date_turns, date_key, session_id)
            results.append(log)

        return results

    async def summarize_batch(
        self,
        all_turns_by_session: Dict[str, List[MemoryTurn]],
    ) -> List[LearningLog]:
        """
        Summarize conversations across multiple sessions.

        Args:
            all_turns_by_session: Session ID → list of turns.

        Returns:
            Flattened list of LearningLog entries.
        """
        all_logs: List[LearningLog] = []
        for session_id, turns in all_turns_by_session.items():
            logs = await self.summarize(turns, session_id)
            all_logs.extend(logs)
        return all_logs

    # ── Date grouping ─────────────────────────────────────────

    @staticmethod
    def _group_by_date(turns: List[MemoryTurn]) -> Dict[str, List[MemoryTurn]]:
        grouped: Dict[str, List[MemoryTurn]] = {}
        for t in turns:
            key = t.timestamp.strftime("%Y-%m-%d")
            grouped.setdefault(key, []).append(t)
        return grouped

    # ── Core summarization ────────────────────────────────────

    async def _summarize_date_group(
        self,
        turns: List[MemoryTurn],
        date_key: str,
        session_id: str,
    ) -> LearningLog:
        if self._llm_client:
            try:
                summary = await self._summarize_with_llm(turns, date_key, session_id)
            except Exception as e:
                logger.warning(f"[Summarizer] LLM failed, fallback to rules: {e}")
                summary = self._summarize_with_rules(turns, date_key)
        else:
            summary = self._summarize_with_rules(turns, date_key)

        self._write_wiki_source(date_key, summary)

        turn_ids = [t.turn_id for t in turns]
        return LearningLog(
            id=str(uuid.uuid4()),
            session_id=session_id,
            summary_type="conversation",
            content=summary,
            source_ids=json.dumps(turn_ids, ensure_ascii=False),
            created_at=datetime.now(),
        )

    async def _summarize_with_llm(
        self,
        turns: List[MemoryTurn],
        date_key: str,
        session_id: str,
    ) -> str:
        turns_text = _format_turns(turns)
        user_prompt = SUMMARIZE_USER_PROMPT.format(
            session_id=session_id,
            date=date_key,
            turns_text=turns_text,
        )

        if hasattr(self._llm_client, "chat"):
            response = await self._llm_client.chat(
                messages=[
                    {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.get("content", "") if isinstance(response, dict) else str(response)
            return content.strip()

        if hasattr(self._llm_client, "ainvoke"):
            from langchain_core.messages import HumanMessage, SystemMessage
            resp = await self._llm_client.ainvoke([
                SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ])
            return resp.content.strip()

        logger.warning("[Summarizer] LLM client has neither .chat nor .ainvoke")
        return self._summarize_with_rules(turns, date_key)

    def _summarize_with_rules(
        self,
        turns: List[MemoryTurn],
        date_key: str,
    ) -> str:
        stats = _count_messages(turns)

        topics: List[str] = []
        for t in turns:
            text = t.user_input.strip()
            if text and len(text) > 3:
                topics.append(text[:40])

        topic_summary = "\n".join(f"- {tp}..." for tp in topics[:5])
        if len(topics) > 5:
            topic_summary += f"\n- ...及其他 {len(topics) - 5} 个话题"

        return (
            f"## 对话摘要 {date_key}\n\n"
            f"**AI生成摘要**\n\n"
            f"### 核心话题\n{topic_summary}\n\n"
            f"### 对话统计\n"
            f"- 总轮数: {stats['total']}\n"
            f"- 用户消息: {stats['user']}\n"
            f"- AI回复: {stats['ai']}\n\n"
            f"*摘要由规则引擎自动生成*\n"
        )

    # ── Wiki source page writing ──────────────────────────────

    def _write_wiki_source(self, date_key: str, summary: str) -> None:
        workspace_dir = self._config.get("workspace_dir")
        if not workspace_dir:
            return

        ws = Path(workspace_dir)
        wiki_dir = ws / "wiki"
        sources_dir = wiki_dir / "sources"
        sources_dir.mkdir(parents=True, exist_ok=True)

        source_path = sources_dir / f"{date_key}.md"

        abstract_section = (
            f"\n## AI生成摘要\n\n"
            f"{summary}\n\n"
            f"---\n"
            f"*摘要生成时间: {_now_iso()}*\n"
        )

        if source_path.exists():
            existing = source_path.read_text(encoding="utf-8")
            existing = self._replace_or_append_abstract(existing, abstract_section)
            source_path.write_text(existing, encoding="utf-8")
            logger.info(f"[Summarizer] updated abstract in sources/{date_key}.md")
        else:
            frontmatter = (
                "---\n"
                f"type: source\n"
                f"created: {_now_iso()}\n"
                f"updated: {_now_iso()}\n"
                "tags:\n"
                f"  - {date_key}\n"
                "  - daily\n"
                "  - ai-abstract\n"
                f"raw_source: raw/{date_key}.md\n"
                "---\n\n"
            )
            content = (
                f"# 对话摘要 {date_key}\n\n"
                f"**原始日志**: [raw/{date_key}.md](../../raw/{date_key}.md)\n\n"
                f"{abstract_section.strip()}\n"
            )
            source_path.write_text(frontmatter + content, encoding="utf-8")
            logger.info(f"[Summarizer] created sources/{date_key}.md with abstract")

    @staticmethod
    def _replace_or_append_abstract(existing: str, new_abstract: str) -> str:
        import re as _re
        pattern = r"\n## AI生成摘要\n.*?(?=\n## |\n---|\Z)"
        if _re.search(pattern, existing, flags=_re.DOTALL):
            return _re.sub(pattern, new_abstract.rstrip("\n"), existing, count=1, flags=_re.DOTALL)
        return existing.rstrip("\n") + "\n" + new_abstract
