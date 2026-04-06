"""
可观测性集成 - LangSmith + LangFuse

职责:
1. 加载 config/observability.yaml 配置
2. 初始化 LangSmith (通过环境变量, LangGraph 原生集成)
3. 初始化 LangFuse CallbackHandler
4. 提供合并的 callbacks 列表注入 LangGraph config
"""

import os
from typing import Any, Dict, List, Optional
from loguru import logger
from pathlib import Path

import yaml


class ObservabilityManager:
    """可观测性管理器 - 单例"""

    _instance: Optional["ObservabilityManager"] = None

    def __new__(cls) -> "ObservabilityManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._langfuse_handler: Optional[Any] = None
        self._langfuse_client: Optional[Any] = None
        self._langsmith_enabled: bool = False
        self._langfuse_enabled: bool = False
        self._config: Dict[str, Any] = {}

    def initialize(self, config_path: Optional[str] = None) -> None:
        """
        初始化可观测性

        Args:
            config_path: 配置文件路径, 默认 config/observability.yaml
        """
        if self._initialized:
            return

        # 加载配置
        self._config = self._load_config(config_path)

        # 初始化 LangSmith (环境变量)
        self._init_langsmith()

        # 初始化 LangFuse (CallbackHandler)
        self._init_langfuse()

        self._initialized = True
        self._log_status()

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载配置文件"""
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent.parent.parent.parent
                / "config" / "observability.yaml"
            )

        config_path = Path(config_path)
        if not config_path.exists():
            logger.info("[Observability] 未找到配置文件, 使用默认配置 (全部关闭)")
            return {"langsmith": {"enabled": False}, "langfuse": {"enabled": False}}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"[Observability] 配置已加载: {config_path}")
            return config
        except Exception as e:
            logger.warning(f"[Observability] 配置加载失败: {e}")
            return {"langsmith": {"enabled": False}, "langfuse": {"enabled": False}}

    def _init_langsmith(self) -> None:
        """初始化 LangSmith - 通过环境变量, LangGraph 自动采集"""
        cfg = self._config.get("langsmith", {})
        if not cfg.get("enabled", False):
            return

        os.environ["LANGCHAIN_TRACING_V2"] = "true"

        if cfg.get("api_key"):
            os.environ["LANGCHAIN_API_KEY"] = cfg["api_key"]
        if cfg.get("project"):
            os.environ["LANGCHAIN_PROJECT"] = cfg["project"]
        if cfg.get("endpoint"):
            os.environ["LANGCHAIN_ENDPOINT"] = cfg["endpoint"]

        self._langsmith_enabled = True
        logger.info("[Observability] LangSmith 已启用")

    def _init_langfuse(self) -> None:
        """初始化 LangFuse - 通过 CallbackHandler 采集

        Langfuse v4: CallbackHandler 只接受 public_key,
        secret_key/host 通过环境变量自动读取:
          LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
        """
        cfg = self._config.get("langfuse", {})
        if not cfg.get("enabled", False):
            return

        try:
            from langfuse.langchain import CallbackHandler
        except ImportError:
            logger.warning("[Observability] langfuse 未安装或版本过低, 请运行: pip install langfuse>=4.0.0")
            return

        # 设置环境变量（如果 YAML 配置中有值，写入环境变量供 Langfuse SDK 读取）
        if cfg.get("secret_key") and not os.environ.get("LANGFUSE_SECRET_KEY"):
            os.environ["LANGFUSE_SECRET_KEY"] = cfg["secret_key"]
        if cfg.get("host") and not os.environ.get("LANGFUSE_HOST"):
            os.environ["LANGFUSE_HOST"] = cfg["host"]

        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", cfg.get("public_key"))
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY", cfg.get("secret_key"))

        if not public_key or not secret_key:
            logger.warning("[Observability] LangFuse 缺少 public_key/secret_key, 已跳过")
            return

        host = os.environ.get("LANGFUSE_HOST", cfg.get("host", "https://cloud.langfuse.com"))

        try:
            # Langfuse v4: 必须先创建 Langfuse 客户端，再创建 CallbackHandler（不传 public_key）
            from langfuse import Langfuse
            self._langfuse_client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
            self._langfuse_handler = CallbackHandler()
            self._langfuse_enabled = True
            logger.info(f"[Observability] LangFuse 已启用 - host: {host}")
        except Exception as e:
            logger.error(f"[Observability] LangFuse 初始化失败: {e}")

    def _log_status(self) -> None:
        """输出当前状态"""
        parts = []
        if self._langsmith_enabled:
            parts.append("LangSmith=ON")
        if self._langfuse_enabled:
            parts.append("LangFuse=ON")
        if not parts:
            parts.append("全部关闭")
        logger.info(f"[Observability] 状态: {', '.join(parts)}")

    @property
    def callbacks(self) -> List[Any]:
        """返回 LangGraph/LangChain 回调列表"""
        if self._langfuse_handler:
            return [self._langfuse_handler]
        return []

    @property
    def langsmith_enabled(self) -> bool:
        return self._langsmith_enabled

    @property
    def langfuse_enabled(self) -> bool:
        return self._langfuse_enabled

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "langsmith_enabled": self._langsmith_enabled,
            "langfuse_enabled": self._langfuse_enabled,
        }


def get_observability() -> ObservabilityManager:
    """获取全局可观测性管理器"""
    return ObservabilityManager()
