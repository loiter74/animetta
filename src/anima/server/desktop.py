"""
桌面客户端支持
管理 Electron 桌面客户端的注册和广播
"""

from typing import Dict, Set
from loguru import logger

# 桌面客户端类型
DESKTOP_CLIENT_TYPES = {"live2d", "chat", "web"}


class DesktopClientManager:
    """
    桌面客户端管理器

    负责：
    1. 管理桌面客户端的注册
    2. 广播消息到指定类型的客户端
    3. 客户端状态追踪
    """

    def __init__(self):
        # 存储桌面客户端信息
        # 键: session_id, 值: {client_type: str, connected: bool}
        self.clients: Dict[str, dict] = {}

    def register(
        self,
        sid: str,
        client_type: str = "web"
    ) -> bool:
        """
        注册桌面客户端

        Args:
            sid: session id
            client_type: 客户端类型 ("live2d", "chat", "web")

        Returns:
            bool: 是否注册成功
        """
        if client_type not in DESKTOP_CLIENT_TYPES:
            logger.warning(f"[Desktop] 未知的客户端类型: {client_type}")
            return False

        self.clients[sid] = {
            'client_type': client_type,
            'connected': True
        }

        logger.info(f"[Desktop] {client_type} 客户端已注册: {sid}")
        return True

    def unregister(self, sid: str) -> None:
        """
        注销桌面客户端

        Args:
            sid: session id
        """
        if sid in self.clients:
            client_type = self.clients[sid].get('client_type', 'unknown')
            del self.clients[sid]
            logger.info(f"[Desktop] {client_type} 客户端已注销: {sid}")

    def get_client_type(self, sid: str) -> str:
        """获取客户端类型"""
        if sid in self.clients:
            return self.clients[sid].get('client_type', 'web')
        return 'web'

    def is_connected(self, sid: str) -> bool:
        """检查客户端是否已连接"""
        if sid in self.clients:
            return self.clients[sid].get('connected', False)
        return False

    def set_connected(self, sid: str, connected: bool) -> None:
        """设置客户端连接状态"""
        if sid in self.clients:
            self.clients[sid]['connected'] = connected

    def get_clients_by_type(self, client_type: str) -> Set[str]:
        """
        获取指定类型的所有客户端

        Args:
            client_type: 客户端类型

        Returns:
            Set[str]: 客户端 session id 集合
        """
        return {
            sid for sid, info in self.clients.items()
            if info.get('client_type') == client_type and info.get('connected')
        }

    @property
    def client_count(self) -> int:
        """获取已注册的客户端数量"""
        return len(self.clients)
