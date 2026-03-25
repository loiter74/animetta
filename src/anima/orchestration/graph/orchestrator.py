"""
LangGraph Orchestrator

负责：
1. 管理 LangGraph 状态图的生命周期
2. 提供与现有系统兼容的接口
3. 处理状态图的执行和结果返回
"""

import asyncio
from typing import Optional, Any, Dict
from loguru import logger

from .state import AgentState, create_initial_state
from .builder import create_default_graph
from .interrupt_handler import get_interrupt_handler
from .tool_manager import ToolManager


class LangGraphOrchestrator:
    """LangGraph 编排器"""

    def __init__(
        self,
        service_context: Any,
        socketio: Any,
        emotion_analyzer: Optional[Any] = None,
        enable_tools: bool = False,
        enable_memory: bool = True,
        tools_config: Optional[Dict[str, Any]] = None,
    ):
        self.service_context = service_context
        self.socketio = socketio
        self.emotion_analyzer = emotion_analyzer
        self.enable_tools = enable_tools
        self.enable_memory = enable_memory
        self.tools_config = tools_config or {}

        self.session_id = getattr(service_context, "session_id", "unknown")

        self.graph = None
        self._is_running = False

        # 初始化工具管理器
        self.tool_manager: Optional[ToolManager] = None

        # 构建 LangGraph 配置（通过 config 参数传递给节点）
        self._langgraph_config = {
            "configurable": {
                "service_context": service_context,
                "socketio": socketio,
                "emotion_analyzer": emotion_analyzer,
                "thread_id": self.session_id,
            }
        }

        logger.info(f"[{self.session_id}] [LangGraph] 编排器初始化完成")

    async def start(self) -> None:
        """启动编排器"""
        if self._is_running:
            logger.warning(f"[{self.session_id}] [LangGraph] 编排器已在运行")
            return

        logger.info(f"[{self.session_id}] [LangGraph] 正在构建状态图...")
        logger.info(f"[{self.session_id}] [LangGraph] self.enable_tools={self.enable_tools}")

        try:
            # 加载工具
            if self.enable_tools:
                logger.info(f"[{self.session_id}] [LangGraph] 工具已启用，开始加载...")
                await self._load_tools()
            else:
                logger.warning(f"[{self.session_id}] [LangGraph] 工具未启用")

            # 创建状态图
            self.graph = create_default_graph(
                enable_memory=False,
                enable_tools=self.enable_tools,
                tools=self.tool_manager.tools if self.tool_manager else None,
                tools_map=self.tool_manager.tools_map if self.tool_manager else None,
            )

            self._is_running = True
            logger.info(f"[{self.session_id}] [LangGraph] 状态图已启动")

        except Exception as e:
            logger.error(f"[{self.session_id}] [LangGraph] 启动失败: {e}")
            raise

    async def _load_tools(self) -> None:
        """加载工具"""
        self.tool_manager = ToolManager(self.session_id, self.service_context)
        success = await self.tool_manager.load_tools(self.tools_config)

        if success:
            # 更新 LangGraph 配置
            self._langgraph_config["configurable"].update(self.tool_manager.get_config())
            logger.info(f"[{self.session_id}] [LangGraph] 工具配置已添加到 LangGraph config")
        else:
            self.enable_tools = False
            logger.warning(f"[{self.session_id}] [LangGraph] 工具加载失败，工具调用已禁用")

    async def stop(self) -> None:
        """停止编排器"""
        if not self._is_running:
            return

        if self.tool_manager:
            await self.tool_manager.cleanup()

        self._is_running = False
        logger.info(f"[{self.session_id}] [LangGraph] 编排器已停止")

    async def process_text(
        self,
        text: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        channel_id: Optional[str] = None,
        **metadata,
    ) -> Dict[str, Any]:
        """处理文本输入"""
        if not self._is_running:
            return {"error": "编排器未启动"}

        logger.info(f"[{self.session_id}] [LangGraph] 处理文本输入: {text[:50]}...")

        # 清除打断信号
        get_interrupt_handler().clear_interrupt(self.session_id)

        try:
            initial_state = self._create_initial_state(
                input_type="text",
                user_text=text,
                channel_id=channel_id,
                user_id=user_id,
                user_name=user_name,
                metadata=metadata,
            )

            final_state = await self._run_graph(initial_state)
            return self._clean_result(final_state)

        except Exception as e:
            logger.error(f"[{self.session_id}] [LangGraph] 处理文本失败: {e}")
            return {"error": str(e), "response_text": ""}

    async def process_audio(
        self,
        audio_data: bytes,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        channel_id: Optional[str] = None,
        **metadata,
    ) -> Dict[str, Any]:
        """处理音频输入"""
        if not self._is_running:
            return {"error": "编排器未启动"}

        logger.info(f"[{self.session_id}] [LangGraph] 处理音频输入: {len(audio_data)} bytes")

        get_interrupt_handler().clear_interrupt(self.session_id)

        try:
            initial_state = self._create_initial_state(
                input_type="audio",
                raw_audio=audio_data,
                channel_id=channel_id,
                user_id=user_id,
                user_name=user_name,
                metadata=metadata,
            )

            final_state = await self._run_graph(initial_state)
            return self._clean_result(final_state)

        except Exception as e:
            logger.error(f"[{self.session_id}] [LangGraph] 处理音频失败: {e}")
            return {"error": str(e), "response_text": ""}

    def _create_initial_state(
        self,
        input_type: str,
        user_text: str = "",
        raw_audio: Optional[bytes] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AgentState:
        """创建初始状态"""
        initial_state = create_initial_state(
            session_id=self.session_id,
            input_type=input_type,
            user_text=user_text,
            raw_audio=raw_audio,
            persona=self._get_persona_dict(),
            system_prompt=self._get_system_prompt(),
            channel_id=channel_id,
            user_id=user_id,
            user_name=user_name,
        )

        if metadata:
            initial_state["metadata"] = metadata

        return initial_state

    async def _run_graph(self, initial_state: AgentState) -> Dict[str, Any]:
        """运行状态图，通过 LangGraph config 传递服务上下文"""
        return await self.graph.ainvoke(initial_state, config=self._langgraph_config)

    def _clean_result(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """清理返回值"""
        return {
            "response_text": final_state.get("response_text", ""),
            "response_chunks": final_state.get("response_chunks", []),
            "tts_audio": final_state.get("tts_audio"),
            "emotion": final_state.get("emotion"),
            "error": final_state.get("error"),
        }

    def _get_persona_dict(self) -> Optional[Dict[str, Any]]:
        """获取人设配置字典"""
        if self.service_context and hasattr(self.service_context, "config"):
            persona = self.service_context.config.get_persona()
            if persona:
                return {
                    "name": persona.name,
                    "role": persona.role,
                    "identity": persona.identity,
                    "personality": persona.personality.dict() if hasattr(persona.personality, "dict") else {},
                    "behavior": persona.behavior.dict() if hasattr(persona.behavior, "dict") else {},
                    "speaking_style": persona.speaking_style,
                }
        return {}

    def _get_system_prompt(self) -> Optional[str]:
        """获取系统提示词"""
        if self.service_context and hasattr(self.service_context, "config"):
            return self.service_context.config.get_system_prompt()
        return None

    def is_running(self) -> bool:
        return self._is_running


class LangGraphOrchestratorFactory:
    """LangGraph 编排器工厂"""

    _instances: Dict[str, LangGraphOrchestrator] = {}

    @classmethod
    async def create(
        cls,
        session_id: str,
        service_context: Any,
        socketio: Any,
        emotion_analyzer: Optional[Any] = None,
        enable_tools: bool = False,
        enable_memory: bool = True,
        tools_config: Optional[Dict[str, Any]] = None,
    ) -> LangGraphOrchestrator:
        """创建编排器实例"""
        orchestrator = LangGraphOrchestrator(
            service_context=service_context,
            socketio=socketio,
            emotion_analyzer=emotion_analyzer,
            enable_tools=enable_tools,
            enable_memory=enable_memory,
            tools_config=tools_config,
        )

        await orchestrator.start()
        cls._instances[session_id] = orchestrator
        return orchestrator

    @classmethod
    def get(cls, session_id: str) -> Optional[LangGraphOrchestrator]:
        return cls._instances.get(session_id)

    @classmethod
    async def remove(cls, session_id: str) -> None:
        orchestrator = cls._instances.pop(session_id, None)
        if orchestrator:
            await orchestrator.stop()

    @classmethod
    async def clear_all(cls) -> None:
        for session_id, orchestrator in cls._instances.items():
            await orchestrator.stop()
        cls._instances.clear()
