"""
全局配置存储

用于在 LangGraph 节点中访问服务上下文。
由于 LangGraph 的 config 传递限制，使用全局存储作为备选方案。
"""

from typing import Dict, Any, Optional


class ConfigStore:
    """
    全局配置存储

    用于存储每个会话的服务上下文和配置信息。
    """

    _store: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def set(cls, session_id: str, key: str, value: Any) -> None:
        """设置配置"""
        if session_id not in cls._store:
            cls._store[session_id] = {}
        cls._store[session_id][key] = value

    @classmethod
    def get(cls, session_id: str, key: str, default: Any = None) -> Any:
        """获取配置"""
        if session_id not in cls._store:
            return default
        return cls._store[session_id].get(key, default)

    @classmethod
    def get_all(cls, session_id: str) -> Dict[str, Any]:
        """获取会话的所有配置"""
        return cls._store.get(session_id, {})

    @classmethod
    def remove(cls, session_id: str) -> None:
        """移除会话配置"""
        cls._store.pop(session_id, None)

    @classmethod
    def clear_all(cls) -> None:
        """清空所有配置"""
        cls._store.clear()


# 便捷函数
def get_service_context(session_id: str) -> Optional[Any]:
    """获取会话的 service_context"""
    return ConfigStore.get(session_id, "service_context")


def get_socketio(session_id: str) -> Optional[Any]:
    """获取会话的 socketio"""
    return ConfigStore.get(session_id, "socketio")


def get_emotion_analyzer(session_id: str) -> Optional[Any]:
    """获取会话的 emotion_analyzer"""
    return ConfigStore.get(session_id, "emotion_analyzer")


def get_config_value(session_id: str, key: str, default: Any = None) -> Any:
    """
    获取会话的配置值

    Args:
        session_id: 会话 ID
        key: 配置键
        default: 默认值

    Returns:
        配置值
    """
    return ConfigStore.get(session_id, key, default)
