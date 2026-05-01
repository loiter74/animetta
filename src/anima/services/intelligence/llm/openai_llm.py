"""
OpenAI LLM implementation
Uses the openai SDK to call OpenAI GPT models
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
    OpenAI GPT model Agent implementation
    
    Uses the official openai SDK to call GPT-4, GPT-3.5, and other models
    Supports streaming output and custom base_url (compatible with other OpenAI API-compatible services)
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
        Initialize OpenAI LLM
        
        Args:
            api_key: OpenAI API Key
            model: Model name (gpt-4, gpt-4o, gpt-3.5-turbo, etc.)
            system_prompt: System prompt
            base_url: Custom API endpoint (optional)
            temperature: Temperature parameter
            max_tokens: Maximum number of tokens to generate
        """
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Conversation history
        self.history: List[Dict[str, str]] = []
        
        # Initialize async client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self.client = AsyncOpenAI(**client_kwargs)
        
        logger.info(f"OpenAILLM initialized: model={model}, base_url={base_url or 'default'}")

    @classmethod
    def from_config(cls, config: "LLMBaseConfig", system_prompt: str = "", **kwargs) -> "OpenAILLM":
        """
        Create an instance from a configuration object

        Supports:
        - OpenAILLMConfig (type: openai)
        - DeepSeekLLMConfig (type: deepseek) — OpenAI API compatible

        Args:
            config: LLM configuration object (OpenAILLMConfig or DeepSeekLLMConfig)
            system_prompt: System prompt
            **kwargs: Additional parameters (ignored)

        Returns:
            OpenAILLM instance
        """
        # Extract common fields from config (compatible with OpenAI / DeepSeek and other OpenAI API-compatible services)
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
        Build messages list

        Args:
            user_input: User input
            system_prompt: Dynamic system prompt (overrides self.system_prompt, used for RAG memory enhancement)

        Returns:
            List[Dict[str, str]]: Complete messages list
        """
        messages = []

        # Use the passed-in system_prompt (RAG enhanced), otherwise use the instance default
        effective_prompt = system_prompt if system_prompt is not None else self.system_prompt
        if effective_prompt:
            messages.append({
                "role": "system",
                "content": effective_prompt
            })
        
        # Add conversation history
        messages.extend(self.history)
        
        # Add current user input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages

    async def chat(self, user_input: str, **kwargs) -> str:
        """
        Chat with the OpenAI model

        Args:
            user_input: User input
            **kwargs: Supports system_prompt — dynamically overrides the system prompt

        Returns:
            str: Model response
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
            
            # Update history
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": assistant_message})
            
            logger.debug(f"OpenAI response: {assistant_message[:100]}...")
            return assistant_message
            
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise

    async def chat_stream(self, user_input: str, **kwargs) -> AsyncIterator[str]:
        """
        Streaming chat

        Args:
            user_input: User input
            **kwargs: Supports system_prompt — dynamically overrides the system prompt (RAG memory enhancement)

        Yields:
            str: Text chunk of the model response
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
            
            # Update history
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            logger.error(f"OpenAI streaming chat error: {e}")
            raise

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt"""
        self.system_prompt = prompt
        logger.debug(f"System prompt updated: {prompt[:50]}...")

    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.history.copy()

    def clear_history(self) -> None:
        """Clear conversation history"""
        self.history.clear()
        logger.debug("Conversation history cleared")

    async def close(self) -> None:
        """Clean up resources"""
        await self.client.close()
        logger.info("OpenAILLM resources released")
    
    def handle_interrupt(self, heard_response: str = "") -> None:
        """
        Handle user interruption
        
        Args:
            heard_response: Partial response heard by the user
        """
        if heard_response:
            # Save partial response to history
            if self.history and self.history[-1].get("role") == "user":
                # Get the last user input
                last_user_input = self.history[-1].get("content", "")
                # Add partial AI response
                self.history.append({
                    "role": "assistant",
                    "content": heard_response
                })
                # Add interruption marker
                self.history.append({
                    "role": "system",
                    "content": "[user interrupted the conversation]"
                })
        
        logger.info(f"Conversation interrupted, partial response saved: {heard_response[:50] if heard_response else '(empty)'}...")
    
    def set_memory_from_history(
        self, 
        conf_uid: str, 
        history_uid: str
    ) -> None:
        """
        Restore conversation memory from history records
         
        Args:
            conf_uid: Config UID
            history_uid: History UID
        """
        # TODO: Implement loading history from persistent storage
        # For now, just log it
        logger.info(f"Attempting to restore memory from history: conf_uid={conf_uid}, history_uid={history_uid}")

    # ================================================================
    # LangGraph tool calling interface
    # ================================================================

    def _convert_tools_to_openai(self, tools: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert a list of LangChain tools to OpenAI API format

        Args:
            tools: List of LangChain BaseTool objects

        Returns:
            Tool list in OpenAI API format
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
        Build an OpenAI API message list from LangChain messages

        Args:
            langchain_history: LangChain message history
            system_prompt: System prompt
            user_input: User input

        Returns:
            Message list in OpenAI API format
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
        Conversation with tool calls (LangGraph specific)

        Args:
            user_input: User input
            tools: List of LangChain tools
            langchain_history: LangChain message history
            system_prompt: System prompt

        Returns:
            Dict: Response containing content and tool_calls
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

                logger.info(f"[OpenAI] Tool calls: {[tc['name'] for tc in tool_calls]}")
                return {
                    "content": content or "Calling tool......",
                    "tool_calls": tool_calls,
                }

            logger.debug(f"[OpenAI] Response: {content[:100]}...")

            # Update conversation history
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": content})

            return {
                "content": content,
                "tool_calls": None,
            }

        except Exception as e:
            logger.error(f"[OpenAI] Tool call failed: {e}")
            raise
