"""
会话管理
管理客户端会话的生命周期和资源
使用 LangGraph 编排器
"""

from typing import Dict, Optional, Callable, Any
from loguru import logger
from pathlib import Path

from ...core.service_context import ServiceContext


class SessionManager:
    """
    会话管理器

    负责：
    1. 管理所有客户端会话的 ServiceContext
    2. 管理所有会话的 LangGraphOrchestrator
    3. 创建和销毁会话资源
    """

    def __init__(self):
        # 存储每个会话的 ServiceContext
        # 键: session_id, 值: ServiceContext 实例
        self.contexts: Dict[str, ServiceContext] = {}

        # 存储每个会话的编排器
        # 键: session_id, 值: LangGraphOrchestrator 实例
        self.orchestrators: Dict[str, Any] = {}

        # 存储每个会话的音频处理器
        # 键: session_id, 值: AudioProcessor 实例
        self.audio_processors: Dict[str, Any] = {}

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
        live2d_config,
        socketio=None,
    ):
        """
        获取或创建指定会话的 LangGraph 编排器

        Args:
            sid: session id
            ctx: ServiceContext
            websocket_send: WebSocket 发送函数
            live2d_config: Live2D 配置

        Returns:
            LangGraphOrchestrator: 编排器实例
        """
        if sid not in self.orchestrators:
            logger.info(f"[{sid}] 创建新的 LangGraphOrchestrator")

            # 从配置加载工具设置
            tools_config = await self._load_tools_config()

            # 创建 LangGraph Orchestrator
            from ..graph.orchestrator import LangGraphOrchestratorFactory

            # 详细调试日志
            logger.info(f"[{sid}] tools_config 完整返回值: {tools_config}")
            logger.info(f"[{sid}] tools_config.get('enable_tools', False): {tools_config.get('enable_tools', False)}")

            # 确保 enable_tools 正确传递
            enable_tools = tools_config.get("enable_tools", False)
            logger.info(f"[{sid}] 工具配置状态: enable_tools={enable_tools}, 类型={type(enable_tools)}")

            orchestrator = await LangGraphOrchestratorFactory.create(
                session_id=sid,
                service_context=ctx,
                socketio=socketio,  # Socket.IO 实例用于发送消息
                emotion_analyzer=ctx.emotion_analyzer if hasattr(ctx, 'emotion_analyzer') else None,
                enable_tools=enable_tools,
                enable_memory=True,
                tools_config=tools_config.get("config", tools_config),
            )

            logger.info(f"[{sid}] LangGraphOrchestrator 已创建")
            self.orchestrators[sid] = orchestrator
            logger.info(f"为会话 {sid} 创建了新的 LangGraphOrchestrator")

        return self.orchestrators[sid]

    async def _load_tools_config(self) -> Dict[str, Any]:
        """加载工具配置"""
        try:
            import yaml
            # 修复路径：从 src/anima/server/session.py 到项目根目录的 config/tools.yaml
            # __file__ = .../src/anima/server/session.py
            # 需要：.../config/tools.yaml
            # 所以需要向上 4 级到项目根目录
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "tools.yaml"

            logger.info(f"[_load_tools_config] 配置文件路径: {config_path}")
            logger.info(f"[_load_tools_config] 文件是否存在: {config_path.exists()}")

            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    tools_config = yaml.safe_load(f)

                    # 详细调试日志
                    logger.info(f"[_load_tools_config] 原始 YAML 解析结果类型: {type(tools_config)}")
                    logger.info(f"[_load_tools_config] YAML 顶级键: {list(tools_config.keys()) if isinstance(tools_config, dict) else 'NOT A DICT'}")

                    # 检查是否显式启用工具 - 修复配置路径
                    tool_settings = tools_config.get("tool_settings", {})
                    logger.info(f"[_load_tools_config] tool_settings 内容: {tool_settings}")
                    logger.info(f"[_load_tools_config] tool_settings 类型: {type(tool_settings)}")

                    enable_tools = tool_settings.get("enable_tools", False)
                    logger.info(f"[_load_tools_config] enable_tools 原始值: {enable_tools}")
                    logger.info(f"[_load_tools_config] enable_tools 类型: {type(enable_tools)}")

                    logger.info(f"[_load_tools_config] 工具调用 {'已启用' if enable_tools else '未启用'}")

                    result = {
                        "enable_tools": enable_tools,
                        "config": tools_config,
                    }
                    logger.info(f"[_load_tools_config] 返回结果 enable_tools: {result['enable_tools']}")
                    return result
            else:
                logger.info(f"工具配置文件不存在: {config_path}")
                return {"enable_tools": False, "config": {}}

        except Exception as e:
            logger.error(f"[_load_tools_config] 加载工具配置失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"enable_tools": False, "config": {}}

    def get_orchestrator(self, sid: str) -> Optional[Any]:
        """获取会话编排器"""
        return self.orchestrators.get(sid)

    # ========================================
    # 清理方法
    # ========================================

    async def cleanup_session(self, sid: str) -> None:
        """
        清理指定会话的所有资源

        Args:
            sid: session id
        """
        # 停止编排器
        if sid in self.orchestrators:
            orchestrator = self.orchestrators[sid]
            if hasattr(orchestrator, 'stop'):
                await orchestrator.stop()
            del self.orchestrators[sid]

        # 清理音频处理器
        if sid in self.audio_processors:
            processor = self.audio_processors[sid]
            if hasattr(processor, 'reset'):
                processor.reset()
            del self.audio_processors[sid]

        # 清理上下文
        if sid in self.contexts:
            ctx = self.contexts[sid]
            await ctx.close()
            del self.contexts[sid]
            logger.info(f"已清理会话 {sid} 的所有资源")

    async def cleanup_all(self) -> None:
        """清理所有会话"""
        logger.info("清理所有会话...")

        # 停止所有编排器
        for sid, orchestrator in list(self.orchestrators.items()):
            try:
                if hasattr(orchestrator, 'stop'):
                    await orchestrator.stop()
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
        # 清理所有音频处理器
        for sid, processor in list(self.audio_processors.items()):
            try:
                if hasattr(processor, 'reset'):
                    processor.reset()
                logger.debug(f"[{sid}] AudioProcessor 已重置")
            except Exception as e:
                logger.error(f"[{sid}] 重置 AudioProcessor 时出错: {e}")
        self.audio_processors.clear()

        self.contexts.clear()

        logger.info("所有会话已清理")


    def get_audio_processor(self, sid: str) -> Optional[Any]:
        """获取会话的音频处理器"""
        return self.audio_processors.get(sid)

    async def get_or_create_audio_processor(
        self,
        sid: str,
        ctx: ServiceContext,
    ):
        """
        获取或创建音频处理器

        Args:
            sid: session id
            ctx: ServiceContext

        Returns:
            AudioProcessor: 音频处理器实例
        """
        if sid not in self.audio_processors:
            from ..services.audio.implementations.simple_vad_processor import SimpleVADProcessor

            async def on_speech_end(audio_data):
                # 语音结束时，调用 orchestrator 处理音频
                orchestrator = self.get_orchestrator(sid)
                if orchestrator:
                    import numpy as np
                    # 转换为 bytes
                    audio_bytes = (np.array(audio_data, dtype=np.float32) * 32768).astype(np.int16).tobytes()
                    await orchestrator.process_audio(audio_bytes)

            processor = SimpleVADProcessor(
                session_id=sid,
                vad_engine=ctx.vad_engine,
                on_speech_end=on_speech_end,
            )

            self.audio_processors[sid] = processor
            logger.info(f"[{sid}] AudioProcessor 已创建")

        return self.audio_processors[sid]


    @property
    def session_count(self) -> int:
        """获取活跃会话数"""
        return len(self.contexts)
