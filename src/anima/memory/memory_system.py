"""
记忆系统协调器

基于 OpenClaw 架构的新版记忆系统：
- Markdown 文件是唯一事实来源 (MEMORY.md + daily logs)
- 混合检索: 向量语义搜索 (70%) + BM25 关键词搜索 (30%)
- 滑动窗口分块: ~400 token/块, 80 token 重叠
- 增量索引: 基于文件哈希检测变更
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from .memory_turn import MemoryTurn
from .config import MemoryConfig
from .memory_manager import MemoryManager
from .models import SearchResult


class MemorySystem:
    """
    记忆系统统一入口

    职责：
    1. 包装 MemoryManager，提供与旧接口兼容的 API
    2. 管理短期记忆（内存）+ 长期记忆（Markdown + SQLite + Chroma）
    3. 提供混合检索能力

    Example:
        >>> memory = MemorySystem({
        ...     "workspace_dir": "~/.anima/workspace",
        ...     "short_term_max_turns": 20,
        ... })
        >>> turn = MemoryTurn(...)
        >>> await memory.store_turn(turn)
        >>> results = await memory.retrieve_context(
        ...     query="你好",
        ...     session_id="session_123"
        ... )
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化记忆系统

        Args:
            config: 配置字典
                - workspace_dir: 工作目录（存储 MEMORY.md 和 daily logs）
                - db_path: SQLite 数据库路径（可选）
                - chroma_path: Chroma 向量库路径（可选）
                - short_term_max_turns: 短期记忆容量
                - embedding_model: embedding 模型名称
        """
        # 短期记忆（内存中的会话缓存）
        self._short_term_max_turns = config.get("short_term_max_turns", 20)
        self._session_cache: Dict[str, List[MemoryTurn]] = {}

        # 构建 MemoryConfig
        workspace = config.get("workspace_dir", "~/.anima/workspace")
        memory_config = MemoryConfig(
            workspace_dir=workspace,
            db_path=config.get("db_path"),
            chroma_path=config.get("chroma_path"),
        )

        # 设置 embedding 模型
        if "embedding_model" in config:
            from .config import EmbeddingConfig
            memory_config.embedding = EmbeddingConfig(model_name=config["embedding_model"])

        # 初始化 MemoryManager
        try:
            self.manager = MemoryManager(config=memory_config)
            logger.info(f"[MemorySystem] 初始化成功，workspace: {memory_config.workspace_dir}")
        except Exception as e:
            logger.warning(f"[MemorySystem] MemoryManager 初始化失败，降级为纯内存模式: {e}")
            self.manager = None

    async def store_turn(self, turn: MemoryTurn) -> None:
        """
        存储对话轮次

        流程：
        1. 存储到短期记忆（内存缓存）
        2. 写入长期记忆（Markdown 文件）
        3. 触发增量索引

        Args:
            turn: 对话轮次数据
        """
        # 1. 存储到短期记忆
        session_id = turn.session_id
        if session_id not in self._session_cache:
            self._session_cache[session_id] = []

        cache = self._session_cache[session_id]
        cache.append(turn)

        # 保持短期记忆容量限制
        if len(cache) > self._short_term_max_turns:
            cache.pop(0)

        # 2. 写入长期记忆
        if self.manager:
            try:
                # 格式化对话为 Markdown（不含时间戳，由 write_daily_log 添加）
                content = f"""**User**: {turn.user_input}
**AI**: {turn.agent_response}
"""
                if turn.emotions:
                    # emotions 可能是字典列表 [{"emotion": "happy", "position": 6}] 或字符串列表 ["happy"]
                    if turn.emotions and isinstance(turn.emotions[0], dict):
                        emotion_names = [e.get("emotion", str(e)) for e in turn.emotions]
                    else:
                        emotion_names = [str(e) for e in turn.emotions]
                    content += f"*Emotions: {', '.join(emotion_names)}*\n"

                # 写入每日日志
                self.manager.write_daily_log(content)

                # 如果重要性高，也写入 MEMORY.md
                if turn.importance >= 0.7:
                    memory_entry = f"- [{turn.timestamp.strftime('%Y-%m-%d')}] {turn.user_input[:50]}...\n"
                    self.manager.write_memory(memory_entry)

            except Exception as e:
                logger.warning(f"[MemorySystem] 长期记忆写入失败: {e}")

    async def retrieve_context(
        self,
        query: str,
        session_id: str,
        max_turns: int = 5
    ) -> List[MemoryTurn]:
        """
        检索相关记忆

        策略：多路召回
        1. 短期记忆：最近 N 轮
        2. 混合搜索：向量语义 + BM25 关键词

        Args:
            query: 查询文本
            session_id: 会话 ID
            max_turns: 短期记忆返回数量

        Returns:
            相关记忆列表
        """
        results = []

        # 1. 短期记忆：最近 N 轮
        cache = self._session_cache.get(session_id, [])
        recent = cache[-max_turns:] if cache else []
        results.extend(recent)

        # 2. 混合搜索长期记忆
        if self.manager:
            try:
                search_results = self.manager.search(
                    query=query,
                    max_results=5
                )

                # 转换 SearchResult 为 MemoryTurn
                for sr in search_results:
                    # 解析 Markdown 格式的对话
                    user_input, agent_response = self._parse_markdown_dialog(sr.text)

                    if user_input or agent_response:
                        memory_turn = MemoryTurn(
                            turn_id=f"search_{sr.path}_{sr.start_line}",
                            session_id=session_id,
                            timestamp=datetime.now(),
                            user_input=user_input,
                            agent_response=agent_response,
                            emotions=[],
                            metadata={
                                "path": sr.path,
                                "score": sr.score,
                                "source": sr.source,
                            },
                            importance=sr.score
                        )
                        results.append(memory_turn)

                logger.debug(f"[MemorySystem] 混合搜索返回 {len(search_results)} 条结果")

            except Exception as e:
                logger.warning(f"[MemorySystem] 混合搜索失败: {e}")

        # 3. 去重（按 turn_id）
        seen = set()
        unique_results = []
        for turn in results:
            if turn.turn_id not in seen:
                seen.add(turn.turn_id)
                unique_results.append(turn)

        return unique_results

    def _parse_markdown_dialog(self, text: str) -> tuple:
        """解析 Markdown 格式的对话"""
        user_input = ""
        agent_response = ""

        lines = text.split("\n")
        for line in lines:
            if line.startswith("**User**:"):
                user_input = line[9:].strip()
            elif line.startswith("**AI**:"):
                agent_response = line[6:].strip()
            elif line.startswith("User: "):
                user_input = line[6:].strip()
            elif line.startswith("AI: "):
                agent_response = line[4:].strip()

        return user_input, agent_response

    async def get_user_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[MemoryTurn]:
        """
        获取用户历史记录

        Args:
            session_id: 会话 ID
            limit: 返回记录数量

        Returns:
            历史对话列表（按时间倒序）
        """
        # 从短期记忆获取
        cache = self._session_cache.get(session_id, [])
        return list(reversed(cache[-limit:]))

    async def clear_session(self, session_id: str) -> None:
        """
        清除会话（短期记忆）

        Args:
            session_id: 会话 ID
        """
        if session_id in self._session_cache:
            del self._session_cache[session_id]

    def write_memory(self, content: str, append: bool = True) -> None:
        """
        写入长期记忆 (MEMORY.md)

        Args:
            content: 要写入的内容
            append: True=追加, False=覆盖
        """
        if self.manager:
            self.manager.write_memory(content, append=append)

    def write_daily_log(self, content: str) -> None:
        """
        写入每日日志

        Args:
            content: 日志内容
        """
        if self.manager:
            self.manager.write_daily_log(content)

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        直接搜索记忆（不转换为 MemoryTurn）

        Args:
            query: 查询文本
            max_results: 返回结果数量

        Returns:
            SearchResult 列表
        """
        if self.manager:
            return self.manager.search(query, max_results=max_results)
        return []

    def load_session_context(self) -> str:
        """
        加载会话启动时的记忆上下文

        Returns:
            组合后的记忆上下文文本
        """
        if self.manager:
            return self.manager.load_session_context()
        return ""

    def should_flush(self, current_tokens: int, context_window: int) -> bool:
        """
        判断是否需要触发记忆 flush

        Args:
            current_tokens: 当前会话消耗的 token 数
            context_window: 模型上下文窗口大小

        Returns:
            True 表示应该触发 flush
        """
        if self.manager:
            return self.manager.should_flush(current_tokens, context_window)
        return False

    def sync(self) -> None:
        """全量同步索引"""
        if self.manager:
            self.manager.sync()

    def close(self) -> None:
        """关闭记忆系统"""
        if self.manager:
            self.manager.close()
        self._session_cache.clear()
