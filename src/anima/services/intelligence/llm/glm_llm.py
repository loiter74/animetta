"""
GLM (智谱AI) LLM 实现
使用 zhipuai SDK 调用智谱 AI 的 GLM 模型
"""

from typing import AsyncIterator, List, Dict, Any, Optional, TYPE_CHECKING
from loguru import logger
from zhipuai import ZhipuAI
import asyncio

from .interface import LLMInterface
from anima.config.core.registry import ProviderRegistry
from anima.config import GLMLLMConfig
from .glm_message_converter import GLMMessageConverter, GLMToolConverter

if TYPE_CHECKING:
    from anima.config.providers.llm.base import LLMBaseConfig


@ProviderRegistry.register_service("llm", "glm")
class GLMLLM(LLMInterface):
    """GLM (智谱 AI) LLM 实现"""

    def __init__(self, config: GLMLLMConfig):
        self.config = config
        self.client = None
        self._conversation_history: List[Dict[str, Any]] = []
        self._call_count = 0

    @classmethod
    def from_config(cls, config: GLMLLMConfig, **kwargs):
        return cls(config=config)

    async def _ensure_client(self):
        if self.client is None:
            self.client = ZhipuAI(api_key=self.config.api_key)
            logger.info(f"[GLM] ZhipuAI 客户端已初始化")

    async def chat_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Any]] = None,
    ) -> AsyncIterator[str]:
        await self._ensure_client()

        messages = self._build_messages(prompt, system_prompt, include_history=True)
        glm_tools = self._convert_tools_if_needed(tools)

        logger.debug(f"[GLM] 发送消息，历史记录数: {len(self._conversation_history)}, 工具数: {len(glm_tools) if glm_tools else 0}")

        try:
            def _create_stream():
                return self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    tools=glm_tools,
                    stream=True,
                    temperature=self.config.temperature,
                )

            response = await asyncio.to_thread(_create_stream)
            full_response = ""

            for chunk in response:
                content = self._extract_chunk_content(chunk)
                if content:
                    full_response += content
                    yield content

            self._update_history(prompt, full_response)

        except Exception as e:
            logger.error(f"[GLM] 聊天失败: {e}")
            raise

    async def chat(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Any]] = None,
    ) -> str:
        await self._ensure_client()

        messages = self._build_messages(user_input, system_prompt, include_history=True)
        glm_tools = self._convert_tools_if_needed(tools)

        try:
            def _create_completion():
                return self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    tools=glm_tools,
                    stream=False,
                    temperature=self.config.temperature,
                )

            response = await asyncio.to_thread(_create_completion)
            full_response = response.choices[0].message.content

            self._update_history(user_input, full_response)
            return full_response

        except Exception as e:
            logger.error(f"[GLM] 聊天失败: {e}")
            raise

    async def chat_with_tools(
        self,
        user_input: str,
        tools: List[Any],
        langchain_history: List[Any],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """带工具调用的对话（LangGraph 专用）"""
        await self._ensure_client()

        logger.debug(f"[GLM] chat_with_tools 调用: tools={len(tools)}, user_input={user_input[:50]}")

        glm_tools = GLMToolConverter.convert_tools(tools)
        messages = self._build_langchain_messages(langchain_history, system_prompt, user_input)

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

            response = await asyncio.to_thread(_create_completion)
            return GLMToolConverter.parse_tool_response(response.choices[0].message)

        except Exception as e:
            logger.error(f"[GLM] 工具调用失败: {e}")
            raise

    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str],
        include_history: bool = True
    ) -> List[Dict[str, Any]]:
        """构建消息列表"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if include_history:
            for msg in self._conversation_history:
                messages.append(msg.copy() if isinstance(msg, dict) else msg)

        messages.append({"role": "user", "content": prompt})
        return messages

    def _build_langchain_messages(
        self,
        langchain_history: List[Any],
        system_prompt: Optional[str],
        user_input: str
    ) -> List[Dict[str, Any]]:
        """从 LangChain 历史构建 GLM 消息"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        for msg in langchain_history:
            glm_msg = GLMMessageConverter.convert_to_glm(msg)
            messages.append(glm_msg)
            logger.debug(f"[GLM] 转换历史消息: {type(msg).__name__} -> {glm_msg.get('role')}")

        messages.append({"role": "user", "content": user_input})
        return messages

    def _convert_tools_if_needed(self, tools: Optional[List[Any]]) -> Optional[List[Dict]]:
        """如果历史中有工具调用，转换工具格式"""
        if not tools:
            return None

        has_tool_calls = any(
            msg.get("role") == "assistant" and "tool_calls" in msg
            for msg in self._conversation_history
        )

        if has_tool_calls:
            return GLMToolConverter.convert_tools(tools)
        return None

    def _extract_chunk_content(self, chunk: Any) -> str:
        """从流式响应块中提取内容"""
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content:
                return delta.content
        elif hasattr(chunk, 'content') and chunk.content:
            return chunk.content
        return ""

    def _update_history(self, user_input: str, response: str):
        """更新对话历史"""
        self._conversation_history.append({"role": "user", "content": user_input})
        self._conversation_history.append({"role": "assistant", "content": response})

        self._call_count += 1

        if self._call_count % 100 == 0 and len(self._conversation_history) > 100:
            self._conversation_history = self._conversation_history[-50:]

    def clear_history(self):
        self._conversation_history = []
        logger.debug("[GLM] 对话历史已清空")

    def set_system_prompt(self, prompt: str) -> None:
        self._conversation_history = [msg for msg in self._conversation_history if msg.get("role") != "system"]
        if prompt:
            self._conversation_history.insert(0, {"role": "system", "content": prompt})
        logger.debug(f"[GLM] 系统提示词已更新: {prompt[:50]}...")

    def get_history(self) -> List[Dict[str, Any]]:
        return self._conversation_history.copy()

    def handle_interrupt(self, heard_response: str = "") -> None:
        if heard_response and self._conversation_history:
            if self._conversation_history[-1].get("role") == "user":
                self._conversation_history.append({"role": "assistant", "content": heard_response})
                self._conversation_history.append({"role": "system", "content": "[用户打断了对话]"})
        logger.info(f"[GLM] 对话被打断，已保存部分回复: {heard_response[:50] if heard_response else '(空)'}...")

    @property
    def max_tokens(self) -> Optional[int]:
        return self.config.max_tokens

    def set_max_tokens(self, max_tokens: int):
        self.config.max_tokens = max_tokens

    def supports_tool_calls(self) -> bool:
        return self.config.model.startswith("glm-4")

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        logger.info(f"[GLM] 尝试从历史恢复记忆: conf_uid={conf_uid}, history_uid={history_uid}")

    async def close(self):
        self.client = None
        logger.info("[GLM] 连接已关闭")
