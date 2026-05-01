"""
OpenAI LLM 实现
使用 openai SDK 调用 OpenAI GPT 模型
"""

import json
from typing import AsyncIterator, List, Dict, Any, Optional, TYPE_CHECKING
from loguru import logger
from openai import AsyncOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from .interface import LLMInterface
from anima.config.core.registry import ProviderRegistry
from anima.config import OpenAILLMConfig, DeepSeekLLMConfig

if TYPE_CHECKING:
    from anima.config.providers.llm.base import LLMBaseConfig


@ProviderRegistry.register_service("llm", "openai")
@ProviderRegistry.register_service("llm", "deepseek")
class OpenAILLM(LLMInterface):
    """
    OpenAI GPT 模型 Agent 实现
    
    使用官方 openai SDK 调用 GPT-4、GPT-3.5 等模型
    支持流式输出和自定义 base_url（兼容其他 OpenAI API 兼容服务）
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        system_prompt: str = "",
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ):
        """
        初始化 OpenAI LLM
        
        Args:
            api_key: OpenAI API Key
            model: 模型名称 (gpt-4, gpt-4o, gpt-3.5-turbo 等)
            system_prompt: 系统提示词
            base_url: 自定义 API 端点（可选）
            temperature: 温度参数
            max_tokens: 最大生成 token 数
        """
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # 对话历史
        self.history: List[Dict[str, str]] = []
        
        # 初始化异步客户端
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self.client = AsyncOpenAI(**client_kwargs)
        
        logger.info(f"OpenAILLM 初始化完成: model={model}, base_url={base_url or 'default'}")

    @classmethod
    def from_config(cls, config: "LLMBaseConfig", system_prompt: str = "", **kwargs) -> "OpenAILLM":
        """
        从配置对象创建实例

        支持:
        - OpenAILLMConfig (type: openai)
        - DeepSeekLLMConfig (type: deepseek) — OpenAI API 兼容

        Args:
            config: LLM 配置对象 (OpenAILLMConfig 或 DeepSeekLLMConfig)
            system_prompt: 系统提示词
            **kwargs: 额外参数（忽略）

        Returns:
            OpenAILLM 实例
        """
        # 从配置中提取公共字段（兼容 OpenAI / DeepSeek 等 OpenAI API 兼容服务）
        api_key = getattr(config, 'api_key', '')
        model = getattr(config, 'model', 'gpt-4o-mini')
        base_url = getattr(config, 'base_url', None)
        temperature = getattr(config, 'temperature', 0.7)
        max_tokens = getattr(config, 'max_tokens', 1000)

        return cls(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _build_messages(self, user_input: str, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        """
        构建消息列表

        Args:
            user_input: 用户输入
            system_prompt: 动态系统提示词（覆盖 self.system_prompt，用于 RAG 记忆增强）

        Returns:
            List[Dict[str, str]]: 完整的消息列表
        """
        messages = []

        # 使用传入的 system_prompt（RAG 增强），否则用实例的默认提示词
        effective_prompt = system_prompt if system_prompt is not None else self.system_prompt
        if effective_prompt:
            messages.append({
                "role": "system",
                "content": effective_prompt
            })
        
        # 添加历史对话
        messages.extend(self.history)
        
        # 添加当前用户输入
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages

    async def chat(self, user_input: str, **kwargs) -> str:
        """
        与 OpenAI 模型进行对话

        Args:
            user_input: 用户输入
            **kwargs: 支持 system_prompt — 动态覆盖系统提示词

        Returns:
            str: 模型回复
        """
        system_prompt = kwargs.get("system_prompt")
        messages = self._build_messages(user_input, system_prompt=system_prompt)
        
        try:
            response = await self.client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            
            assistant_message = response.choices[0].message.content
            
            # 更新历史
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": assistant_message})
            
            logger.debug(f"OpenAI 回复: {assistant_message[:100]}...")
            return assistant_message
            
        except Exception as e:
            logger.error(f"OpenAI 对话异常: {e}")
            raise

    async def chat_stream(self, user_input: str, **kwargs) -> AsyncIterator[str]:
        """
        流式对话

        Args:
            user_input: 用户输入
            **kwargs: 支持 system_prompt — 动态覆盖系统提示词（RAG 记忆增强）

        Yields:
            str: 模型回复的文本片段
        """
        system_prompt = kwargs.get("system_prompt")
        messages = self._build_messages(user_input, system_prompt=system_prompt)
        
        full_response = ""
        
        try:
            response = await self.client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            # 更新历史
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            logger.error(f"OpenAI 流式对话异常: {e}")
            raise

    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示词"""
        self.system_prompt = prompt
        logger.debug(f"系统提示词已更新: {prompt[:50]}...")

    def get_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.history.copy()

    def clear_history(self) -> None:
        """清空对话历史"""
        self.history.clear()
        logger.debug("对话历史已清空")

    async def close(self) -> None:
        """清理资源"""
        await self.client.close()
        logger.info("OpenAILLM 资源已释放")
    
    def handle_interrupt(self, heard_response: str = "") -> None:
        """
        处理用户打断
        
        Args:
            heard_response: 用户听到的部分回复
        """
        if heard_response:
            # 保存部分回复到历史
            if self.history and self.history[-1].get("role") == "user":
                # 获取最后一个用户输入
                last_user_input = self.history[-1].get("content", "")
                # 添加部分 AI 回复
                self.history.append({
                    "role": "assistant",
                    "content": heard_response
                })
                # 添加打断标记
                self.history.append({
                    "role": "system",
                    "content": "[用户打断了对话]"
                })
        
        logger.info(f"对话被打断，已保存部分回复: {heard_response[:50] if heard_response else '(空)'}...")
    
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
        # 这里暂时只记录日志
        logger.info(f"尝试从历史恢复记忆: conf_uid={conf_uid}, history_uid={history_uid}")

    # ================================================================
    # LangGraph 工具调用接口
    # ================================================================

    def _convert_tools_to_openai(self, tools: List[Any]) -> List[Dict[str, Any]]:
        """
        将 LangChain 工具列表转换为 OpenAI API 格式

        Args:
            tools: LangChain BaseTool 对象列表

        Returns:
            OpenAI API 格式的工具列表
        """
        openai_tools = []
        for tool in tools:
            parameters = {"type": "object", "properties": {}}
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    parameters = tool.args_schema.schema()
                except Exception:
                    parameters = {"type": "object", "properties": {}}

            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters,
                }
            })
        return openai_tools

    def _build_langchain_messages(
        self,
        langchain_history: List[Any],
        system_prompt: Optional[str],
        user_input: str,
    ) -> List[Dict[str, Any]]:
        """
        从 LangChain 消息构建 OpenAI API 消息列表

        Args:
            langchain_history: LangChain 消息历史
            system_prompt: 系统提示词
            user_input: 用户输入

        Returns:
            OpenAI API 格式的消息列表
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        for msg in langchain_history:
            if isinstance(msg, SystemMessage):
                messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                ai_msg = {"role": "assistant", "content": msg.content or ""}
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    ai_msg["tool_calls"] = [
                        {
                            "id": tc.get("id", "") if isinstance(tc, dict) else getattr(tc, 'id', ''),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", "") if isinstance(tc, dict) else getattr(tc, 'name', ''),
                                "arguments": json.dumps(
                                    tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, 'args', {}),
                                    ensure_ascii=False,
                                ),
                            },
                        }
                        for tc in (msg.tool_calls if hasattr(msg, 'tool_calls') else [])
                    ]
                messages.append(ai_msg)
            elif isinstance(msg, ToolMessage):
                messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content,
                })

        messages.append({"role": "user", "content": user_input})
        return messages

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
            tools: LangChain 工具列表
            langchain_history: LangChain 消息历史
            system_prompt: 系统提示词

        Returns:
            Dict: 包含 content 和 tool_calls 的响应
        """
        openai_tools = self._convert_tools_to_openai(tools)
        messages = self._build_langchain_messages(langchain_history, system_prompt, user_input)

        logger.debug(f"[OpenAI] chat_with_tools: tools={len(openai_tools)}, input={user_input[:50]}")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=openai_tools if openai_tools else None,
                tool_choice="auto" if openai_tools else None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=False,
            )

            message = response.choices[0].message
            content = message.content or ""

            tool_calls = []
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tc in message.tool_calls:
                    args = tc.function.arguments
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}

                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "args": args,
                    })

                logger.info(f"[OpenAI] 工具调用: {[tc['name'] for tc in tool_calls]}")
                return {
                    "content": content or "正在调用工具...",
                    "tool_calls": tool_calls,
                }

            logger.debug(f"[OpenAI] 回复: {content[:100]}...")

            # 更新对话历史
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": content})

            return {
                "content": content,
                "tool_calls": None,
            }

        except Exception as e:
            logger.error(f"[OpenAI] 工具调用失败: {e}")
            raise
