"""
LangGraph Orchestrator

负责：
1. 管理 LangGraph 状态图的生命周期
2. 提供与现有系统兼容的接口
3. 处理状态图的执行和结果返回
4. Phase 3: 支持工具调用（Tool Use）

使用示例:
    orchestrator = LangGraphOrchestrator(
        service_context=service_context,
        socketio=sio,
        emotion_analyzer=emotion_analyzer,
        enable_tools=True,
        tools_config=tools_config,
    )

    # 文本输入
    await orchestrator.process_text(text="你好")

    # 音频输入
    await orchestrator.process_audio(audio_data=b"...")
"""

import asyncio
from typing import Optional, Any, Dict, List, Union
from loguru import logger
from pathlib import Path

from .state import AgentState, create_initial_state
from .builder import create_default_graph
from .config_store import ConfigStore
from .interrupt_handler import get_interrupt_handler


class LangGraphOrchestrator:
    """
    LangGraph 编排器

    封装 LangGraph 状态图的执行逻辑，提供与现有系统兼容的接口。
    """

    def __init__(
        self,
        service_context: Any,
        socketio: Any,
        emotion_analyzer: Optional[Any] = None,
        enable_tools: bool = False,
        enable_memory: bool = True,
        tools_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化编排器

        Args:
            service_context: 服务上下文（ServiceContext）
            socketio: Socket.IO 实例
            emotion_analyzer: 情感分析器（可选）
            enable_tools: 是否启用工具调用
            enable_memory: 是否启用内存检查点
            tools_config: 工具配置（可选）
        """
        self.service_context = service_context
        self.socketio = socketio
        self.emotion_analyzer = emotion_analyzer
        self.enable_tools = enable_tools
        self.enable_memory = enable_memory
        self.tools_config = tools_config or {}

        # 会话 ID
        self.session_id = getattr(service_context, "session_id", "unknown")

        # 工具相关
        self.tools: List[Any] = []
        self.tools_map: Dict[str, Any] = {}
        self.chat_model: Optional[Any] = None

        # 构建配置
        self.config = {
            "configurable": {
                "service_context": service_context,
                "socketio": socketio,
                "emotion_analyzer": emotion_analyzer,
            }
        }

        # 创建状态图
        self.graph = None
        self._is_running = False

        # 将配置存储到全局存储中（供节点访问）
        ConfigStore.set(self.session_id, "service_context", service_context)
        ConfigStore.set(self.session_id, "socketio", socketio)
        ConfigStore.set(self.session_id, "emotion_analyzer", emotion_analyzer)

        logger.info(f"[{self.session_id}] [LangGraph] 编排器初始化完成")

    async def start(self) -> None:
        """启动编排器，构建状态图"""
        if self._is_running:
            logger.warning(f"[{self.session_id}] [LangGraph] 编排器已在运行")
            return

        logger.info(f"[{self.session_id}] [LangGraph] 正在构建状态图...")
        logger.info(f"[{self.session_id}] [LangGraph] self.enable_tools={self.enable_tools}, 类型={type(self.enable_tools)}")

        try:
            # 加载工具（如果启用）
            if self.enable_tools:
                logger.info(f"[{self.session_id}] [LangGraph] 工具已启用，开始加载...")
                await self._load_tools()
            else:
                logger.warning(f"[{self.session_id}] [LangGraph] 工具未启用，跳过工具加载")

            # 创建状态图（禁用检查点以避免序列化问题）
            self.graph = create_default_graph(
                enable_memory=False,  # 禁用检查点
                enable_tools=self.enable_tools,
                tools=self.tools if self.enable_tools else None,
                tools_map=self.tools_map if self.enable_tools else None,
            )

            self._is_running = True
            logger.info(f"[{self.session_id}] [LangGraph] 状态图已启动")

        except Exception as e:
            logger.error(f"[{self.session_id}] [LangGraph] 启动失败: {e}")
            raise

    async def _load_tools(self) -> None:
        """加载工具和创建 ChatModel"""
        try:
            logger.info(f"[{self.session_id}] [LangGraph] _load_tools() 开始执行")
            logger.info(f"[{self.session_id}] [LangGraph] self.enable_tools={self.enable_tools}")

            # 加载工具配置
            from anima.tools.base import load_tools_from_config

            self.tools, self.tools_map = load_tools_from_config(self.tools_config)
            logger.info(f"[{self.session_id}] [LangGraph] 已加载 {len(self.tools)} 个工具")

            # 创建 LangChain ChatModel
            self.chat_model = await self._create_chat_model()

            # 更新配置
            self.config["configurable"].update({
                "tools": self.tools,
                "tools_map": self.tools_map,
                "chat_model": self.chat_model,
                "enable_tools": True,
            })

            # 存储到 ConfigStore（供节点访问）
            ConfigStore.set(self.session_id, "enable_tools", True)
            ConfigStore.set(self.session_id, "chat_model", self.chat_model)
            ConfigStore.set(self.session_id, "tools_map", self.tools_map)

            logger.info(f"[{self.session_id}] [LangGraph] 工具配置已存储到 ConfigStore")
            logger.info(f"[{self.session_id}] [LangGraph] ConfigStore.enable_tools={ConfigStore.get(self.session_id, 'enable_tools')}")

        except Exception as e:
            logger.error(f"[{self.session_id}] [LangGraph] 工具加载失败: {e}")
            # 禁用工具
            self.enable_tools = False
            ConfigStore.set(self.session_id, "enable_tools", False)

    async def _create_chat_model(self) -> Any:
        """
        创建 LangChain ChatModel

        将现有的 LLM 服务包装为 LangChain 兼容的 ChatModel。
        """
        try:
            from anima.services.llm.langchain_adapter import create_chat_model_from_service

            chat_model = create_chat_model_from_service(
                llm_service=self.service_context.llm_engine,
                enable_tooling=True,  # 启用工具支持
            )

            # 绑定工具
            if self.tools:
                chat_model = chat_model.bind_tools(self.tools)
                logger.info(f"[{self.session_id}] [LangGraph] ChatModel 已绑定 {len(self.tools)} 个工具")

            return chat_model

        except Exception as e:
            logger.error(f"[{self.session_id}] [LangGraph] ChatModel 创建失败: {e}")
            return None

    async def stop(self) -> None:
        """停止编排器"""
        if not self._is_running:
            return

        # 清理 MCP 连接（如果有）
        if hasattr(self, '_mcp_manager'):
            await self._mcp_manager.close_all()

        self._is_running = False

        # 清理配置存储
        ConfigStore.remove(self.session_id)

        logger.info(f"[{self.session_id}] [LangGraph] 编排器已停止")

    async def process_text(
        self,
        text: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        channel_id: Optional[str] = None,
        **metadata,
    ) -> Dict[str, Any]:
        """
        处理文本输入

        Args:
            text: 用户输入文本
            user_id: 用户 ID
            user_name: 用户名称
            channel_id: 通道 ID
            **metadata: 额外元数据

        Returns:
            处理结果字典
        """
        if not self._is_running:
            logger.error(f"[{self.session_id}] [LangGraph] 编排器未启动")
            return {"error": "编排器未启动"}

        logger.info(f"[{self.session_id}] [LangGraph] 处理文本输入: {text[:50]}...")

        # 新对话开始前清除打断信号
        interrupt_handler = get_interrupt_handler()
        interrupt_handler.clear_interrupt(self.session_id)

        try:
            # 创建初始状态
            initial_state = create_initial_state(
                session_id=self.session_id,
                input_type="text",
                user_text=text,
                persona=self._get_persona_dict(),
                system_prompt=self._get_system_prompt(),
                channel_id=channel_id,
                user_id=user_id,
                user_name=user_name,
            )
            initial_state["metadata"] = metadata

            # 将配置注入到 initial_state 中，作为备用方案
            initial_state["_config"] = self.config

            # 执行状态图
            final_state = await self._run_graph(initial_state)

            # 清理返回值，移除不可序列化的对象
            return {
                "response_text": final_state.get("response_text", ""),
                "response_chunks": final_state.get("response_chunks", []),
                "tts_audio": final_state.get("tts_audio"),
                "emotion": final_state.get("emotion"),
                "error": final_state.get("error"),
            }

        except Exception as e:
            logger.error(f"[{self.session_id}] [LangGraph] 处理文本失败: {e}")
            return {"error": str(e), "response_text": "", "response_chunks": []}

    async def process_audio(
        self,
        audio_data: bytes,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        channel_id: Optional[str] = None,
        **metadata,
    ) -> Dict[str, Any]:
        """
        处理音频输入

        Args:
            audio_data: 音频数据
            user_id: 用户 ID
            user_name: 用户名称
            channel_id: 通道 ID
            **metadata: 额外元数据

        Returns:
            处理结果字典
        """
        if not self._is_running:
            logger.error(f"[{self.session_id}] [LangGraph] 编排器未启动")
            return {"error": "编排器未启动"}

        logger.info(f"[{self.session_id}] [LangGraph] 处理音频输入: {len(audio_data)} bytes")

        # 新对话开始前清除打断信号
        interrupt_handler = get_interrupt_handler()
        interrupt_handler.clear_interrupt(self.session_id)

        try:
            # 创建初始状态
            initial_state = create_initial_state(
                session_id=self.session_id,
                input_type="audio",
                raw_audio=audio_data,
                persona=self._get_persona_dict(),
                system_prompt=self._get_system_prompt(),
                channel_id=channel_id,
                user_id=user_id,
                user_name=user_name,
            )
            initial_state["metadata"] = metadata

            # 将配置注入到 initial_state 中，作为备用方案
            initial_state["_config"] = self.config

            # 执行状态图
            final_state = await self._run_graph(initial_state)

            # 清理返回值，移除不可序列化的对象
            return {
                "response_text": final_state.get("response_text", ""),
                "response_chunks": final_state.get("response_chunks", []),
                "tts_audio": final_state.get("tts_audio"),
                "emotion": final_state.get("emotion"),
                "error": final_state.get("error"),
            }

        except Exception as e:
            logger.error(f"[{self.session_id}] [LangGraph] 处理音频失败: {e}")
            return {"error": str(e), "response_text": "", "response_chunks": []}

    async def _run_graph(self, initial_state: AgentState) -> Dict[str, Any]:
        """
        运行状态图

        Args:
            initial_state: 初始状态

        Returns:
            最终状态字典
        """
        # 使用 thread_id 区分不同会话
        thread_id = self.session_id

        # 构建传递给 LangGraph 的配置
        invoke_config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        # 调用状态图
        final_state = await self.graph.ainvoke(
            initial_state,
            config=invoke_config,
        )

        return final_state

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
        """检查编排器是否在运行"""
        return self._is_running


class LangGraphOrchestratorFactory:
    """
    LangGraph 编排器工厂

    用于创建和管理 LangGraphOrchestrator 实例。
    """

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
        """
        创建编排器实例

        Args:
            session_id: 会话 ID
            service_context: 服务上下文
            socketio: Socket.IO 实例
            emotion_analyzer: 情感分析器
            enable_tools: 是否启用工具调用
            enable_memory: 是否启用内存检查点
            tools_config: 工具配置

        Returns:
            LangGraphOrchestrator: 编排器实例
        """
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
        """
        获取编排器实例

        Args:
            session_id: 会话 ID

        Returns:
            LangGraphOrchestrator or None
        """
        return cls._instances.get(session_id)

    @classmethod
    async def remove(cls, session_id: str) -> None:
        """
        移除编排器实例

        Args:
            session_id: 会话 ID
        """
        orchestrator = cls._instances.pop(session_id, None)
        if orchestrator:
            await orchestrator.stop()

    @classmethod
    async def clear_all(cls) -> None:
        """清除所有编排器实例"""
        for session_id, orchestrator in cls._instances.items():
            await orchestrator.stop()
        cls._instances.clear()
