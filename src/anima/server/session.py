"""
会话管理
管理客户端会话的生命周期和资源
支持 Adapter 架构和 EventBus
"""

from typing import Dict, Optional, Callable, Any
from loguru import logger

from anima.service_context import ServiceContext
from anima.services.conversation import ConversationOrchestrator
from anima.adapters import DesktopLive2DChatter, DesktopChatterConfig
from anima.handlers import HandlerRegistry


class SessionManager:
    """
    会话管理器

    负责：
    1. 管理所有客户端会话的 ServiceContext
    2. 管理所有会话的 ConversationOrchestrator
    3. 管理所有会话的 DesktopLive2DChatter Adapter
    4. 创建和销毁会话资源
    """

    def __init__(self):
        # 存储每个会话的 ServiceContext
        # 键: session_id, 值: ServiceContext 实例
        self.contexts: Dict[str, ServiceContext] = {}

        # 存储每个会话的 ConversationOrchestrator
        # 键: session_id, 值: ConversationOrchestrator 实例
        self.orchestrators: Dict[str, ConversationOrchestrator] = {}

        # 存储每个会话的 DesktopLive2DChatter adapter
        # 键: session_id, 值: DesktopLive2DChatter 实例
        self.adapters: Dict[str, DesktopLive2DChatter] = {}

        # 存储每个会话的 handlers（用于清理）
        # 键: session_id, 值: Dict[str, BaseHandler]
        self.handlers: Dict[str, Dict[str, Any]] = {}

    # ========================================
    # Context 管理
    # ========================================

    async def get_or_create_context(
        self,
        sid: str,
        config,
        websocket_send: Callable
    ) -> ServiceContext:
        """
        获取或创建指定会话的 ServiceContext

        Args:
            sid: session id
            config: 应用配置
            websocket_send: WebSocket 发送函数

        Returns:
            ServiceContext: 该会话的服务上下文
        """
        if sid not in self.contexts:
            logger.info(f"[{sid}] 创建新的 ServiceContext")
            ctx = ServiceContext()
            ctx.session_id = sid
            ctx.send_text = websocket_send

            await ctx.load_from_config(config)
            self.contexts[sid] = ctx
            logger.info(f"为会话 {sid} 创建了新的 ServiceContext")

        return self.contexts[sid]

    def get_context(self, sid: str) -> Optional[ServiceContext]:
        """获取会话上下文"""
        return self.contexts.get(sid)

    # ========================================
    # Orchestrator 管理
    # ========================================

    async def get_or_create_orchestrator(
        self,
        sid: str,
        ctx: ServiceContext,
        websocket_send: Callable,
        live2d_config
    ) -> ConversationOrchestrator:
        """
        获取或创建指定会话的 ConversationOrchestrator

        Args:
            sid: session id
            ctx: ServiceContext
            websocket_send: WebSocket 发送函数
            live2d_config: Live2D 配置

        Returns:
            ConversationOrchestrator: 该会话的对话编排器
        """
        if sid not in self.orchestrators:
            logger.info(f"[{sid}] 创建新的 ConversationOrchestrator")

            # 包装 websocket_send
            from anima.handlers.adapters.socket import SocketEventAdapter
            adapter = SocketEventAdapter(websocket_send)
            wrapped_send = adapter.send

            # 创建编排器
            orchestrator = ConversationOrchestrator(
                asr_engine=ctx.asr_engine,
                tts_engine=ctx.tts_engine,
                agent=ctx.llm_engine,
                websocket_send=wrapped_send,
                session_id=sid,
                live2d_config=live2d_config if live2d_config and live2d_config.enabled else None,
                memory_system=ctx.memory_system,
                local_llm=ctx.local_llm_engine,
            )

            # 启动编排器
            orchestrator.start()

            # 使用 HandlerRegistry 注册所有 handlers
            handlers = await HandlerRegistry.register_all(
                orchestrator=orchestrator,
                websocket_send=orchestrator.websocket_send,
                live2d_config=live2d_config,
                orchestrator_registry=lambda session_id: self.orchestrators.get(session_id),
                asr_service=ctx.asr_engine,
            )
            self.handlers[sid] = handlers
            logger.info(f"[{sid}] 已通过 HandlerRegistry 注册 {len(handlers)} 个 Handler")

            self.orchestrators[sid] = orchestrator
            logger.info(f"为会话 {sid} 创建了新的 ConversationOrchestrator")

        return self.orchestrators[sid]

    def get_orchestrator(self, sid: str) -> Optional[ConversationOrchestrator]:
        """获取会话编排器"""
        return self.orchestrators.get(sid)

    # ========================================
    # Adapter 管理 (EventBus 架构)
    # ========================================

    async def get_or_create_adapter(
        self,
        sid: str,
        ctx: ServiceContext,
        orchestrator: ConversationOrchestrator,
        send_callback: Callable[[Dict[str, Any]], None]
    ) -> DesktopLive2DChatter:
        """
        获取或创建指定会话的 DesktopLive2DChatter adapter

        EventBus 架构：
        - Adapter 只依赖 EventBus，不直接依赖 Orchestrator
        - 输入：Adapter → EventBus.emit(INPUT_TEXT/INPUT_AUDIO) → InputHandler → Orchestrator
        - 输出：Orchestrator → EventBus → Adapter.send() → 客户端

        Args:
            sid: session id
            ctx: ServiceContext
            orchestrator: ConversationOrchestrator
            send_callback: 发送数据到客户端的回调函数

        Returns:
            DesktopLive2DChatter: 该会话的 adapter 实例
        """
        if sid not in self.adapters:
            logger.info(f"[{sid}] 创建新的 DesktopLive2DChatter adapter (EventBus 架构)")

            # 创建 adapter 配置
            config = DesktopChatterConfig(
                sample_rate=16000,
                channels=1,
                vad_enabled=ctx.vad_engine is not None,
                vad_timeout_seconds=15.0,
                auto_interrupt=True,
            )

            # 创建 adapter（只依赖 EventBus，不直接依赖 Orchestrator）
            adapter = DesktopLive2DChatter(
                event_bus=orchestrator.event_bus,
                channel_id=sid,
                vad_engine=ctx.vad_engine,
                config=config,
                send_callback=send_callback,
                session_id=sid,
            )

            # 启动 adapter
            await adapter.start()

            self.adapters[sid] = adapter
            logger.info(f"[{sid}] DesktopLive2DChatter adapter 已创建并启动 (EventBus 模式)")

        return self.adapters[sid]

    def get_adapter(self, sid: str) -> Optional[DesktopLive2DChatter]:
        """获取会话 adapter"""
        return self.adapters.get(sid)

    # ========================================
    # 清理方法
    # ========================================

    async def cleanup_session(self, sid: str) -> None:
        """
        清理指定会话的所有资源

        Args:
            sid: session id
        """
        # 停止并清理 handlers
        if sid in self.handlers:
            handlers = self.handlers[sid]
            for name, handler in handlers.items():
                if hasattr(handler, 'stop'):
                    try:
                        await handler.stop()
                        logger.debug(f"[{sid}] Handler {name} 已停止")
                    except Exception as e:
                        logger.error(f"[{sid}] 停止 Handler {name} 时出错: {e}")
            del self.handlers[sid]

        # 停止并清理 adapter
        if sid in self.adapters:
            try:
                await self.adapters[sid].stop()
                logger.debug(f"[{sid}] Adapter 已停止")
            except Exception as e:
                logger.error(f"[{sid}] 停止 Adapter 时出错: {e}")
            del self.adapters[sid]

        # 停止编排器
        if sid in self.orchestrators:
            orchestrator = self.orchestrators[sid]
            orchestrator.stop()
            del self.orchestrators[sid]

        # 清理上下文
        if sid in self.contexts:
            ctx = self.contexts[sid]
            await ctx.close()
            del self.contexts[sid]
            logger.info(f"已清理会话 {sid} 的所有资源")

    async def cleanup_all(self) -> None:
        """清理所有会话"""
        logger.info("清理所有会话...")

        # 停止所有 handlers
        for sid, handlers in list(self.handlers.items()):
            for name, handler in handlers.items():
                if hasattr(handler, 'stop'):
                    try:
                        await handler.stop()
                        logger.debug(f"[{sid}] Handler {name} 已停止")
                    except Exception as e:
                        logger.error(f"[{sid}] 停止 Handler {name} 时出错: {e}")
        self.handlers.clear()

        # 清理所有 adapters
        for sid, adapter in list(self.adapters.items()):
            try:
                await adapter.stop()
                logger.debug(f"[{sid}] Adapter 已停止")
            except Exception as e:
                logger.error(f"[{sid}] 停止 Adapter 时出错: {e}")
        self.adapters.clear()

        # 停止所有编排器
        for sid, orchestrator in list(self.orchestrators.items()):
            try:
                orchestrator.stop()
                logger.debug(f"[{sid}] 编排器已停止")
            except Exception as e:
                logger.error(f"[{sid}] 停止编排器时出错: {e}")
        self.orchestrators.clear()

        # 关闭所有上下文
        for sid, ctx in list(self.contexts.items()):
            try:
                await ctx.close()
                logger.debug(f"[{sid}] 上下文已关闭")
            except Exception as e:
                logger.error(f"[{sid}] 关闭上下文时出错: {e}")
        self.contexts.clear()

        logger.info("所有会话已清理")

    @property
    def session_count(self) -> int:
        """获取活跃会话数"""
        return len(self.contexts)
