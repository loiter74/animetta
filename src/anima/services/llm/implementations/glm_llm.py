"""
GLM (智谱AI) LLM 实现
使用 zhipuai SDK 调用智谱 AI 的 GLM 模型
"""

from typing import AsyncIterator, List, Dict, Any, Optional, TYPE_CHECKING
from loguru import logger
from zhipuai import ZhipuAI
import asyncio
import json

from ..interface import LLMInterface
from anima.config.core.registry import ProviderRegistry
from anima.config import GLMLLMConfig

if TYPE_CHECKING:
    from anima.config.providers.llm.base import LLMBaseConfig


@ProviderRegistry.register_service("llm", "glm")
class GLMLLM(LLMInterface):
    """GLM (智谱 AI) LLM 实现"""

    def __init__(
        self,
        config: GLMLLMConfig,
    ):
        self.config = config
        self.client = None
        self._conversation_history: List[Dict[str, Any]] = []
        self._call_count = 0

    @classmethod
    def from_config(cls, config: GLMLLMConfig, **kwargs):
        """从配置创建实例"""
        return cls(config=config)

    async def _ensure_client(self):
        """确保客户端已初始化"""
        if self.client is None:
            try:
                self.client = ZhipuAI(api_key=self.config.api_key)
                logger.info(f"[GLM] ZhipuAI 客户端已初始化")
            except Exception as e:
                logger.error(f"[GLM] ZhipuAI 客户端初始化失败: {e}")
                raise

    async def chat_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Any]] = None,
    ) -> AsyncIterator[str]:
        """
        流式聊天接口

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            tools: 工具列表（如果对话历史中有工具调用）

        Yields:
            str: 流式文本块
        """
        await self._ensure_client()

        # 构建消息列表
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 添加对话历史
        for msg in self._conversation_history:
            messages.append(msg)

        # 添加当前用户消息
        messages.append({"role": "user", "content": prompt})

        # 检查是否需要传递工具（如果历史中有 tool_calls）
        has_tool_calls_in_history = any(
            msg.get("role") == "assistant" and "tool_calls" in msg
            for msg in self._conversation_history
        )

        glm_tools = None
        if has_tool_calls_in_history and tools:
            glm_tools = []
            for tool in tools:
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    parameters = tool.args_schema.schema()
                else:
                    parameters = {"type": "object", "properties": {}, "required": []}
                glm_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": parameters,
                    }
                })

        logger.debug(f"[GLM] 发送消息，历史记录数: {len(self._conversation_history)}, 工具数: {len(glm_tools) if glm_tools else 0}")

        try:
            def _create_stream():
                return self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    tools=glm_tools if glm_tools else None,
                    stream=True,
                    temperature=self.config.temperature,
                )

            response = await asyncio.to_thread(_create_stream)

            full_response = ""

            for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        full_response += content
                        yield content
                elif hasattr(chunk, 'content') and chunk.content:
                    full_response += chunk.content
                    yield chunk.content

            self._conversation_history.append({"role": "user", "content": prompt})
            self._conversation_history.append({"role": "assistant", "content": full_response})

            self._call_count += 1

            if self._call_count % 100 == 0 and len(self._conversation_history) > 100:
                self._conversation_history = self._conversation_history[-50:]

        except Exception as e:
            logger.error(f"[GLM] 聊天失败: {e}")
            raise

    def clear_history(self):
        """清空对话历史"""
        self._conversation_history = []
        logger.debug("[GLM] 对话历史已清空")

    @property
    def max_tokens(self) -> Optional[int]:
        """获取最大 token 数"""
        return self.config.max_tokens

    def set_max_tokens(self, max_tokens: int):
        """设置最大 token 数"""
        self.config.max_tokens = max_tokens

    async def chat(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Any]] = None,
    ) -> str:
        """
        非流式对话

        Args:
            user_input: 用户输入
            system_prompt: 系统提示词
            tools: 工具列表（如果对话历史中有工具调用）

        Returns:
            str: LLM 回复
        """
        await self._ensure_client()

        # 构建消息列表
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 添加对话历史
        for msg in self._conversation_history:
            # 复制消息，避免修改原始数据
            messages.append(msg.copy() if isinstance(msg, dict) else msg)

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_input})

        # 检查是否需要传递工具（如果历史中有 tool_calls）
        has_tool_calls_in_history = any(
            msg.get("role") == "assistant" and "tool_calls" in msg
            for msg in self._conversation_history
        )

        # 如果历史中有工具调用，且没有传入工具，尝试从工具调用中推断
        glm_tools = None
        if has_tool_calls_in_history and tools:
            glm_tools = []
            for tool in tools:
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    parameters = tool.args_schema.schema()
                else:
                    parameters = {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    }
                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": parameters,
                    }
                }
                glm_tools.append(tool_schema)

        try:
            def _create_completion():
                return self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    tools=glm_tools if glm_tools else None,
                    stream=False,
                    temperature=self.config.temperature,
                )

            # 在线程池中运行同步 API
            response = await asyncio.to_thread(_create_completion)

            # 获取回复
            full_response = response.choices[0].message.content if hasattr(response, 'choices') else str(response)

            # 保存对话历史
            self._conversation_history.append({"role": "user", "content": user_input})
            self._conversation_history.append({"role": "assistant", "content": full_response})

            self._call_count += 1

            # 定期清理历史记录
            if self._call_count % 100 == 0 and len(self._conversation_history) > 100:
                self._conversation_history = self._conversation_history[-50:]

            return full_response

        except Exception as e:
            logger.error(f"[GLM] 聊天失败: {e}")
            raise

    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示词（存储在对话历史的开头）"""
        # 移除旧的系统提示词
        self._conversation_history = [msg for msg in self._conversation_history if msg.get("role") != "system"]
        # 添加新的系统提示词
        if prompt:
            self._conversation_history.insert(0, {"role": "system", "content": prompt})
        logger.debug(f"[GLM] 系统提示词已更新: {prompt[:50]}...")

    def get_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self._conversation_history.copy()

    def handle_interrupt(self, heard_response: str = "") -> None:
        """
        处理用户打断

        Args:
            heard_response: 用户听到的部分回复
        """
        if heard_response:
            # 保存部分回复到历史
            if self._conversation_history and self._conversation_history[-1].get("role") == "user":
                # 添加部分 AI 回复
                self._conversation_history.append({
                    "role": "assistant",
                    "content": heard_response
                })
                # 添加打断标记
                self._conversation_history.append({
                    "role": "system",
                    "content": "[用户打断了对话]"
                })

        logger.info(f"[GLM] 对话被打断，已保存部分回复: {heard_response[:50] if heard_response else '(空)'}...")

    def supports_tool_calls(self) -> bool:
        """检查是否支持工具调用"""
        # GLM-4 系列模型支持工具调用
        return self.config.model.startswith("glm-4")

    def _convert_langchain_message_to_glm(self, msg: Any) -> Dict[str, Any]:
        """
        将 LangChain 消息转换为 GLM API 格式

        Args:
            msg: LangChain 消息对象

        Returns:
            Dict: GLM API 格式的消息
        """
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

        if isinstance(msg, SystemMessage):
            return {"role": "system", "content": msg.content}

        elif isinstance(msg, HumanMessage):
            return {"role": "user", "content": msg.content}

        elif isinstance(msg, AIMessage):
            glm_msg = {"role": "assistant", "content": msg.content or ""}

            # 转换 tool_calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_calls_for_glm = []
                for tc in msg.tool_calls:
                    # tc 可能是字典或对象
                    if isinstance(tc, dict):
                        tc_id = tc.get("id", "")
                        tc_name = tc.get("name", "")
                        tc_args = tc.get("args", {})
                    else:
                        tc_id = getattr(tc, 'id', '')
                        tc_name = getattr(tc, 'name', '')
                        tc_args = getattr(tc, 'args', {})

                    # arguments 必须是 JSON 字符串
                    arguments_str = tc_args if isinstance(tc_args, str) else json.dumps(tc_args, ensure_ascii=False)

                    tool_calls_for_glm.append({
                        "id": tc_id,
                        "type": "function",
                        "function": {
                            "name": tc_name,
                            "arguments": arguments_str,
                        }
                    })

                glm_msg["tool_calls"] = tool_calls_for_glm

            return glm_msg

        elif isinstance(msg, ToolMessage):
            # GLM API: tool 消息格式
            return {
                "role": "tool",
                "tool_call_id": msg.tool_call_id,
                "content": msg.content,
            }

        else:
            # 未知类型，尝试作为用户消息处理
            return {"role": "user", "content": str(msg.content) if hasattr(msg, 'content') else str(msg)}

    async def chat_with_tools(
        self,
        user_input: str,
        tools: List[Any],
        langchain_history: List[Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        带工具调用的对话（LangGraph 专用）

        Args:
            user_input: 用户输入
            tools: 工具列表（LangChain BaseTool 对象）
            system_prompt: 系统提示词
            langchain_history: LangChain 格式的历史消息（包含 ToolMessage）

        Returns:
            Dict: 包含 content 和 tool_calls 的字典
        """
        await self._ensure_client()

        logger.debug(f"[GLM] chat_with_tools 调用: tools={len(tools)}, user_input={user_input[:50]}")

        # 将 LangChain 工具转换为 GLM 格式
        glm_tools = []
        for tool in tools:
            # 获取参数 schema
            if hasattr(tool, 'args_schema') and tool.args_schema:
                parameters = tool.args_schema.schema()
            else:
                # 默认参数 schema（即使没有参数也需要正确格式）
                parameters = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }

            glm_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters,
                }
            })

        # 构建消息列表
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 转换 LangChain 历史消息为 GLM 格式
        for msg in langchain_history:
            glm_msg = self._convert_langchain_message_to_glm(msg)
            messages.append(glm_msg)
            logger.debug(f"[GLM] 转换历史消息: {type(msg).__name__} -> {glm_msg.get('role')}")

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_input})

        logger.debug(f"[GLM] 发送消息（工具模式），工具数: {len(glm_tools)}, 历史数: {len(messages)}")

        try:
            def _create_completion():
                return self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    tools=glm_tools,
                    tool_choice="auto",
                    stream=False,
                    temperature=self.config.temperature,
                )

            # 在线程池中运行同步 API
            response = await asyncio.to_thread(_create_completion)

            # 解析响应
            message = response.choices[0].message
            content = message.content or ""

            # 检查是否有工具调用
            tool_calls = []

            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments,
                    })

                logger.info(f"[GLM] LLM 请求 {len(tool_calls)} 个工具调用")

            if tool_calls:
                return {
                    "content": content or "正在调用工具...",
                    "tool_calls": tool_calls,
                }
            else:
                return {
                    "content": content,
                    "tool_calls": None,
                }

        except Exception as e:
            logger.error(f"[GLM] 工具调用失败: {e}")
            raise

    def set_memory_from_history(
        self,
        conf_uid: str,
        history_uid: str
    ) -> None:
        """
        从历史记录恢复对话记忆

        Args:
            conf_uid: 配置 UID
            history_uid: 历史 UID
        """
        # TODO: 实现从持久化存储加载历史
        logger.info(f"[GLM] 尝试从历史恢复记忆: conf_uid={conf_uid}, history_uid={history_uid}")

    async def close(self):
        """关闭连接"""
        self.client = None
        logger.info("[GLM] 连接已关闭")
