"""
文本 Handler - 处理文本事件

处理 sentence 事件，发送文本到前端。
"""

from typing import TYPE_CHECKING, Optional
from loguru import logger

from .base import BaseHandler

if TYPE_CHECKING:
    from anima.core import OutputEvent


class TextHandler(BaseHandler):
    """
    文本 Handler

    处理 sentence 事件，发送文本到前端。

    event.data 格式: str (文本内容)
    event.metadata 格式: {"is_complete": bool} (可选)
    """

    # 类变量，用于减少日志频率
    _log_counter = 0
    _log_interval = 10  # 每10个片段打印一次日志

    async def handle(self, event: "OutputEvent") -> None:
        """处理文本事件"""
        # 使用统一的提取方法
        text, metadata = self.extract_event_data(event, expect_data_type=str)

        if text is None:
            return

        # 检查是否是完成标记
        is_complete = metadata.get("is_complete", False) if isinstance(metadata, dict) else False

        if is_complete:
            await self._handle_completion(event.seq)
            return

        # 普通文本
        if not text:
            return

        await self._handle_text(text, event.seq)

    async def _handle_completion(self, seq: int) -> None:
        """处理完成标记"""
        logger.info(f"[{self.name}] ✅ 发送完成标记 [seq={seq}]")

        await self.send({
            "type": "sentence",
            "text": "",  # 空文本表示完成
            "seq": seq,
        })

        # 重置计数器
        self._log_counter = 0

    async def _handle_text(self, text: str, seq: int) -> None:
        """处理普通文本"""
        self._log_counter += 1

        # 只在特定间隔打印DEBUG日志，减少日志量
        if self._log_counter % self._log_interval == 0:
            logger.debug(f"[{self.name}] 📤 发送文本片段 [seq={seq}] (第{self._log_counter}个片段)")
            logger.debug(f"[{self.name}] 片段内容: {text[:50]}...")

        await self.send({
            "type": "sentence",
            "text": text,
            "seq": seq,
        })
