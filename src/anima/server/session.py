"""
会话管理
管理客户端会话的生命周期和资源
"""

from typing import Dict, Optional
from loguru import logger

from anima.service_context import ServiceContext
from anima.services.conversation import ConversationOrchestrator


class SessionManager:
    """
    会话管理器

    负责：
    1. 管理所有客户端会话
    2. 创建和销毁会话
    3. 获取或创建会话上下文
    """

    def __init__(self):
        # 存储每个会话的 ServiceContext
        self.contexts: Dict[str, ServiceContext] = {}

        # 存储每个会话的 ConversationOrchestrator
        self.orchestrators: Dict[str, ConversationOrchestrator] = {}

    async def get_or_create_context(
        self,
        sid: str,
        config,
        websocket_send
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

    async def get_or_create_orchestrator(
        self,
        sid: str,
        ctx: ServiceContext,
        websocket_send,
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

            # 注册 Handler
            from anima.handlers import TextHandler
            from anima.handlers.unified import UnifiedEventHandler
            from anima.events import EventPriority

            text_handler = TextHandler(websocket_send=orchestrator.websocket_send)
            orchestrator.register_handler("sentence", text_handler, priority=EventPriority.NORMAL)

            if live2d_config and live2d_config.enabled:
                unified_handler = UnifiedEventHandler(
                    websocket_send=orchestrator.websocket_send,
                    analyzer_type="llm_tag_analyzer",
                    strategy_type="position_based",
                    sample_rate=50
                )
                orchestrator.register_handler(
                    "audio_with_expression",
                    unified_handler,
                    priority=EventPriority.NORMAL
                )

            # 启动编排器
            orchestrator.start()
            self.orchestrators[sid] = orchestrator
            logger.info(f"为会话 {sid} 创建了新的 ConversationOrchestrator")

        return self.orchestrators[sid]

    async def cleanup_session(self, sid: str) -> None:
        """
        清理指定会话的所有资源

        Args:
            sid: session id
        """
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

    def get_context(self, sid: str) -> Optional[ServiceContext]:
        """获取会话上下文"""
        return self.contexts.get(sid)

    def get_orchestrator(self, sid: str) -> Optional[ConversationOrchestrator]:
        """获取会话编排器"""
        return self.orchestrators.get(sid)

    async def cleanup_all(self) -> None:
        """清理所有会话"""
        logger.info("清理所有会话...")

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
