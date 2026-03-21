"""
音频处理器服务接口

负责：
1. 接收音频数据流
2. 使用 VAD 进行语音活动检测
3. 累积有效语音片段
4. 触发 ASR 转录和 LLM 对话
"""

from abc import ABC, abstractmethod
from typing import List, Callable, Optional, Any
from typing import Dict


class AudioProcessorInterface(ABC):
    """音频处理器接口"""

    @abstractmethod
    async def process_chunk(self, audio_data: List[float]) -> None:
        """
        处理音频数据块

        Args:
            audio_data: 音频数据（float32 列表）
        """
        pass

    @abstractmethod
    async def process_end(self) -> None:
        """处理音频输入结束"""
        pass

    @abstractmethod
    def reset(self) -> None:
        """重置处理器状态"""
        pass

    @abstractmethod
    def is_speaking(self) -> bool:
        """是否正在检测到语音"""
        pass
