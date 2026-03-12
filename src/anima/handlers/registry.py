"""
Handler 注册中心

统一管理所有 Handler 的创建和注册。

使用示例:
    from anima.handlers import HandlerRegistry

    # 创建并注册所有 handlers
    handlers = await HandlerRegistry.register_all(
        orchestrator=orchestrator,
        websocket_send=websocket_send,
        live2d_config=live2d_config,
        orchestrator_registry=get_orchestrator,
        asr_service=asr_engine,
    )

    # 或者单独创建 handler
    text_handler = HandlerRegistry.create_text_handler(websocket_send)
    orchestrator.register_handler("sentence", text_handler)
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional, Callable

from loguru import logger

from .base import BaseHandler
from .text import TextHandler
from .unified import UnifiedEventHandler
from .input_handler import InputHandler

if TYPE_CHECKING:
    from anima.events import EventBus, EventPriority
    from anima.services.conversation import ConversationOrchestrator
    from anima.services.asr import ASRInterface
    from anima.core import WebSocketSend


@dataclass
class HandlerConfig:
    """Handler 配置"""
    event_type: str           # 事件类型
    handler_class: type       # Handler 类
    priority: int             # 优先级
    enabled: bool = True      # 是否启用
    requires_live2d: bool = False  # 是否需要 Live2D 配置


class HandlerRegistry:
    """
    Handler 注册中心

    职责:
    1. 统一管理所有 Handler 的配置
    2. 提供 Handler 工厂方法
    3. 批量注册 Handler 到 Orchestrator

    所有 Handler 的创建和注册都应该通过此类进行，
    确保配置一致性和可维护性。
    """

    # ========================================
    # Handler 配置表
    # ========================================

    HANDLER_CONFIGS: Dict[str, HandlerConfig] = {
        # 文本输出 Handler（总是启用）
        "text": HandlerConfig(
            event_type="sentence",
            handler_class=TextHandler,
            priority=10,  # EventPriority.NORMAL
            enabled=True,
            requires_live2d=False,
        ),

        # 音频 + 表情 Handler（需要 Live2D）
        "unified": HandlerConfig(
            event_type="audio_with_expression",
            handler_class=UnifiedEventHandler,
            priority=10,  # EventPriority.NORMAL
            enabled=True,
            requires_live2d=True,
        ),
    }

    # ========================================
    # 工厂方法
    # ========================================

    @classmethod
    def create_text_handler(
        cls,
        websocket_send: "WebSocketSend",
    ) -> TextHandler:
        """
        创建文本 Handler

        Args:
            websocket_send: WebSocket 发送函数

        Returns:
            TextHandler 实例
        """
        return TextHandler(websocket_send=websocket_send)

    @classmethod
    def create_unified_handler(
        cls,
        websocket_send: "WebSocketSend",
        analyzer_type: str = "llm_tag_analyzer",
        analyzer_config: Optional[Dict[str, Any]] = None,
        strategy_type: str = "position_based",
        strategy_config: Optional[Dict[str, Any]] = None,
        sample_rate: int = 50,
    ) -> UnifiedEventHandler:
        """
        创建统一事件 Handler

        Args:
            websocket_send: WebSocket 发送函数
            analyzer_type: 情绪分析器类型
            analyzer_config: 情绪分析器配置
            strategy_type: 时间轴策略类型
            strategy_config: 时间轴策略配置
            sample_rate: 音量包络采样率

        Returns:
            UnifiedEventHandler 实例
        """
        return UnifiedEventHandler(
            websocket_send=websocket_send,
            analyzer_type=analyzer_type,
            analyzer_config=analyzer_config,
            strategy_type=strategy_type,
            strategy_config=strategy_config,
            sample_rate=sample_rate,
        )

    @classmethod
    def create_input_handler(
        cls,
        event_bus: "EventBus",
        orchestrator_registry: Callable[[str], Optional["ConversationOrchestrator"]],
        asr_service: Optional["ASRInterface"] = None,
    ) -> InputHandler:
        """
        创建输入事件 Handler

        Args:
            event_bus: 事件总线
            orchestrator_registry: 获取 Orchestrator 的函数
            asr_service: ASR 服务

        Returns:
            InputHandler 实例
        """
        return InputHandler(
            event_bus=event_bus,
            orchestrator_registry=orchestrator_registry,
            asr_service=asr_service,
        )

    # ========================================
    # 批量注册
    # ========================================

    @classmethod
    async def register_all(
        cls,
        orchestrator: "ConversationOrchestrator",
        websocket_send: "WebSocketSend",
        live2d_config: Optional[Any] = None,
        orchestrator_registry: Optional[Callable[[str], Optional["ConversationOrchestrator"]]] = None,
        asr_service: Optional["ASRInterface"] = None,
    ) -> Dict[str, BaseHandler]:
        """
        注册所有 Handler 到 Orchestrator

        Args:
            orchestrator: 对话编排器
            websocket_send: WebSocket 发送函数
            live2d_config: Live2D 配置（可选）
            orchestrator_registry: 获取 Orchestrator 的函数（用于 InputHandler）
            asr_service: ASR 服务（可选）

        Returns:
            Dict[str, BaseHandler]: 已创建的 Handler 字典 {name: handler}
        """
        from anima.events import EventPriority

        handlers = {}
        session_id = orchestrator.session_id

        # 1. 注册文本 Handler（总是启用）
        config = cls.HANDLER_CONFIGS["text"]
        text_handler = cls.create_text_handler(websocket_send)
        orchestrator.register_handler(
            config.event_type,
            text_handler,
            priority=config.priority,
        )
        handlers["text"] = text_handler
        logger.info(f"[{session_id}] 已注册 Handler: sentence -> TextHandler")

        # 2. 注册统一事件 Handler（需要 Live2D）
        if live2d_config and live2d_config.enabled:
            config = cls.HANDLER_CONFIGS["unified"]
            unified_handler = cls.create_unified_handler(
                websocket_send=websocket_send,
                analyzer_type="llm_tag_analyzer",
                strategy_type="position_based",
                sample_rate=50,
            )
            orchestrator.register_handler(
                config.event_type,
                unified_handler,
                priority=config.priority,
            )
            handlers["unified"] = unified_handler
            logger.info(f"[{session_id}] 已注册 Handler: audio_with_expression -> UnifiedEventHandler")

        # 3. 创建并启动 InputHandler（用于处理 INPUT_TEXT/INPUT_AUDIO 事件）
        if orchestrator_registry:
            input_handler = cls.create_input_handler(
                event_bus=orchestrator.event_bus,
                orchestrator_registry=orchestrator_registry,
                asr_service=asr_service,
            )
            await input_handler.start()
            handlers["input"] = input_handler
            logger.info(f"[{session_id}] 已启动 Handler: InputHandler (订阅 INPUT_TEXT/INPUT_AUDIO)")

        return handlers

    @classmethod
    def get_handler_configs(cls) -> Dict[str, HandlerConfig]:
        """获取所有 Handler 配置"""
        return cls.HANDLER_CONFIGS.copy()

    @classmethod
    def get_enabled_handlers(cls, live2d_enabled: bool = False) -> Dict[str, HandlerConfig]:
        """
        获取启用的 Handler 配置

        Args:
            live2d_enabled: 是否启用 Live2D

        Returns:
            Dict[str, HandlerConfig]: 启用的 Handler 配置
        """
        return {
            name: config
            for name, config in cls.HANDLER_CONFIGS.items()
            if config.enabled and (not config.requires_live2d or live2d_enabled)
        }
