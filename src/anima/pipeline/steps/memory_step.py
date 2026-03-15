"""
Memory Step
记忆检索步骤 - 从记忆系统中检索相关上下文
"""

from typing import Optional, List, TYPE_CHECKING
from loguru import logger

from ..base import PipelineStep
from ...core.context import PipelineContext

if TYPE_CHECKING:
    from anima.memory import MemorySystem


class MemoryStep(PipelineStep):
    """
    记忆检索步骤

    从记忆系统中检索与当前输入相关的历史记忆，
    并将格式化后的记忆上下文存入 ctx.memory_context
    """

    name = "memory"

    def __init__(
        self,
        memory_system: Optional["MemorySystem"] = None,
        session_id: str = "default",
        max_turns: int = 3,
    ):
        """
        初始化记忆步骤

        Args:
            memory_system: 记忆系统实例（可选）
            session_id: 会话 ID
            max_turns: 检索的最大轮次数
        """
        super().__init__()
        self.memory_system = memory_system
        self.session_id = session_id
        self.max_turns = max_turns

        logger.debug(f"[MemoryStep] 初始化完成 (session_id={session_id})")

    async def process(self, context: PipelineContext) -> None:
        """
        处理 Pipeline 上下文，检索相关记忆

        Args:
            context: Pipeline 上下文
        """
        # 检查是否应跳过记忆检索
        if context.should_skip_memory():
            logger.debug("[MemoryStep] 跳过记忆检索 (skip_memory=True)")
            return

        # 检查是否有记忆系统
        if not self.memory_system:
            logger.debug("[MemoryStep] 记忆系统未初始化，跳过")
            return

        # 检查是否有有效的输入文本
        if not context.text:
            logger.debug("[MemoryStep] 文本为空，跳过记忆检索")
            return

        try:
            logger.info(f"[MemoryStep] 🔍 检索相关记忆 (query={context.text[:50]}...)")

            # 检索相关记忆
            related_memories = await self.memory_system.retrieve_context(
                query=context.text,
                session_id=self.session_id,
                max_turns=self.max_turns
            )

            if related_memories:
                logger.info(f"[MemoryStep] 📚 检索到 {len(related_memories)} 条相关记忆")

                # 格式化记忆为上下文
                memory_context = self._format_memory_context(related_memories)

                # 存入 context
                context.memory_context = memory_context

                logger.debug(f"[MemoryStep] 记忆上下文已注入 ({len(memory_context)} 字符)")
            else:
                logger.debug("[MemoryStep] 未检索到相关记忆")

        except Exception as e:
            logger.warning(f"[MemoryStep] 记忆检索失败: {e}")
            # 失败时不清空 memory_context，保持原样

    def _format_memory_context(self, memories: List) -> str:
        """
        格式化记忆为上下文字符串

        Args:
            memories: MemoryTurn 列表

        Returns:
            str: 格式化的记忆上下文
        """
        if not memories:
            return ""

        lines = []
        for i, mem in enumerate(memories, 1):
            # 截断过长的内容
            user_input = mem.user_input[:100] + "..." if len(mem.user_input) > 100 else mem.user_input
            agent_response = mem.agent_response[:100] + "..." if len(mem.agent_response) > 100 else mem.agent_response

            lines.append(f"{i}. 用户: {user_input}")
            lines.append(f"   AI: {agent_response}")

        return "\n".join(lines)
