"""
Adapter Registry - 适配器注册表

管理所有已注册的适配器实例。

职责：
1. 注册/注销适配器
2. 按 channel_id / session_id 查找适配器
3. 批量启动/停止适配器
"""

from typing import Dict, List, Optional, Type
from loguru import logger

from .base import ChannelAdapter


class AdapterRegistry:
    """
    适配器注册表

    单例模式，管理所有活跃的适配器实例。
    """

    _instance: Optional["AdapterRegistry"] = None

    def __new__(cls) -> "AdapterRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._adapters: Dict[str, ChannelAdapter] = {}
            cls._instance._session_map: Dict[str, str] = {}  # session_id -> channel_id
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AdapterRegistry":
        """获取单例实例"""
        return cls()

    def register(self, adapter: ChannelAdapter) -> None:
        """
        注册适配器

        Args:
            adapter: 适配器实例
        """
        if adapter.channel_id in self._adapters:
            logger.warning(f"Adapter {adapter.channel_id} already registered, replacing")

        self._adapters[adapter.channel_id] = adapter
        self._session_map[adapter.session_id] = adapter.channel_id

        logger.info(
            f"[AdapterRegistry] Registered adapter: "
            f"channel_id={adapter.channel_id}, "
            f"type={adapter.channel_type}, "
            f"session_id={adapter.session_id}"
        )

    def unregister(self, channel_id: str) -> Optional[ChannelAdapter]:
        """
        注销适配器

        Args:
            channel_id: 通道 ID

        Returns:
            被注销的适配器，如果不存在则返回 None
        """
        adapter = self._adapters.pop(channel_id, None)
        if adapter:
            # 清理 session 映射
            self._session_map = {
                k: v for k, v in self._session_map.items()
                if v != channel_id
            }
            logger.info(f"[AdapterRegistry] Unregistered adapter: {channel_id}")
        return adapter

    def get(self, channel_id: str) -> Optional[ChannelAdapter]:
        """
        获取适配器

        Args:
            channel_id: 通道 ID

        Returns:
            适配器实例，如果不存在则返回 None
        """
        return self._adapters.get(channel_id)

    def get_by_session(self, session_id: str) -> Optional[ChannelAdapter]:
        """
        通过 session_id 获取适配器

        Args:
            session_id: 会话 ID

        Returns:
            适配器实例，如果不存在则返回 None
        """
        channel_id = self._session_map.get(session_id)
        if channel_id:
            return self._adapters.get(channel_id)
        return None

    def get_all(self) -> List[ChannelAdapter]:
        """获取所有适配器"""
        return list(self._adapters.values())

    def get_by_type(self, channel_type: str) -> List[ChannelAdapter]:
        """
        获取指定类型的所有适配器

        Args:
            channel_type: 通道类型 (如 "socketio", "rest")

        Returns:
            匹配的适配器列表
        """
        return [
            adapter for adapter in self._adapters.values()
            if adapter.channel_type == channel_type
        ]

    async def start_all(self) -> None:
        """启动所有适配器"""
        for adapter in self._adapters.values():
            try:
                await adapter.start()
            except Exception as e:
                logger.error(f"Failed to start adapter {adapter.channel_id}: {e}")

    async def stop_all(self) -> None:
        """停止所有适配器"""
        for adapter in self._adapters.values():
            try:
                await adapter.stop()
            except Exception as e:
                logger.error(f"Failed to stop adapter {adapter.channel_id}: {e}")

    def count(self) -> int:
        """获取适配器数量"""
        return len(self._adapters)

    def clear(self) -> None:
        """清空所有适配器"""
        self._adapters.clear()
        self._session_map.clear()
        logger.info("[AdapterRegistry] Cleared all adapters")
