"""
LangChain ChatModel 适配器

将现有的 LLM 服务包装为 LangChain 的 BaseChatModel，
使其支持 bind_tools() 等高级功能。

注意：实际工具调用由 llm_node.py 直接处理，此适配器仅用于基础对话。
"""

from typing import Any, Dict, List, Optional, Iterator, AsyncIterator, Sequence, TypeVar, Union
from loguru import logger

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.tools import BaseTool

# Pydantic v1/v2 兼容性处理
try:
    from pydantic import Field
except ImportError:
    from pydantic.v1 import Field

# 导入现有 LLM 接口
from ..llm.interface import LLMInterface


GenericChatModel = TypeVar("GenericChatModel", bound="LLMChatModelAdapter")


class LLMChatModelAdapter(BaseChatModel):
    """
    LangChain ChatModel 适配器

    包装现有的 LLMInterface 实现，使其兼容 LangChain 的 BaseChatModel 协议。
    注意：此适配器不处理工具调用，工具调用由 llm_node.py 直接处理。
    """

    llm_service: LLMInterface = Field(description="现有的 LLM 服务实例")

    # 支持的工具列表（用于 bind_tools）
    bound_tools: Sequence[BaseTool] = Field(default_factory=list, description="绑定的工具列表")

    # LangChain 必需字段
    @property
    def _llm_type(self) -> str:
        """返回 LLM 类型标识"""
        return f"anima_llm_adapter_{self.llm_service.__class__.__name__}"

    @property
    def lc_secrets(self) -> Dict[str, str]:
        """隐藏敏感信息"""
        return {}

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        同步生成（委托给异步版本）

        注意: 现有的 LLM 服务是异步的，这里通过 asyncio 转换
        """
        import asyncio
        return asyncio.run(self._agenerate(messages, stop, run_manager, **kwargs))

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        异步生成响应

        Args:
            messages: 消息列表
            stop: 停止词
            run_manager: 回调管理器
            **kwargs: 额外参数

        Returns:
            ChatResult: 生成结果
        """
        # 提取用户输入（最后一条 HumanMessage）
        user_input = ""
        system_prompt = ""

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt = msg.content
            elif isinstance(msg, HumanMessage):
                user_input = msg.content

        if not user_input:
            logger.warning("[LLM适配器] 未找到用户输入")
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content="抱歉，我没有收到您的消息。"))]
            )

        # 设置系统提示词
        if system_prompt:
            self.llm_service.set_system_prompt(system_prompt)

        # 调用现有 LLM 服务的流式接口
        chunks = []
        full_response = ""

        try:
            async for chunk in self.llm_service.chat_stream(user_input):
                chunks.append(chunk)
                full_response += chunk

                # 通知回调（支持流式输出）
                if run_manager:
                    await run_manager.on_llm_new_token(chunk)

        except Exception as e:
            logger.error(f"[LLM适配器] 生成失败: {e}")
            full_response = f"生成回复时出错: {str(e)}"

        # 构建 AI 消息
        ai_message = AIMessage(content=full_response)

        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], type, BaseTool]],
        **kwargs: Any,
    ) -> "LLMChatModelAdapter":
        """
        绑定工具（占位方法，实际工具调用由 llm_node.py 处理）
        """
        logger.info(f"[LLM适配器 bind_tools] 调用，tools 数量: {len(tools)}")

        # 直接设置 bound_tools
        self.bound_tools = list(tools)

        logger.info(f"[LLM适配器 bind_tools] 已设置 {len(self.bound_tools)} 个工具")
        for i, tool in enumerate(self.bound_tools):
            logger.debug(f"[LLM适配器 bind_tools] tool[{i}]: {tool.name}")

        return self


def create_chat_model_from_service(
    llm_service: LLMInterface,
    enable_tooling: bool = False,
) -> BaseChatModel:
    """
    从现有的 LLM 服务创建 LangChain ChatModel

    Args:
        llm_service: 现有的 LLM 服务实例
        enable_tooling: 是否启用工具调用支持（占位参数，实际由 llm_node.py 处理）

    Returns:
        BaseChatModel: LangChain ChatModel 实例
    """
    return LLMChatModelAdapter(llm_service=llm_service)
