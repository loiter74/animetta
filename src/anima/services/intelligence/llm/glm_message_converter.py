"""
GLM 消息格式转换器
处理 LangChain 消息与 GLM API 格式之间的转换
"""

import json
from typing import Any, Dict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage


class GLMMessageConverter:
    """LangChain 消息到 GLM API 格式的转换器"""

    @staticmethod
    def convert_to_glm(msg: Any) -> Dict[str, Any]:
        """
        将 LangChain 消息转换为 GLM API 格式

        Args:
            msg: LangChain 消息对象

        Returns:
            Dict: GLM API 格式的消息
        """
        if isinstance(msg, SystemMessage):
            return GLMMessageConverter._convert_system(msg)
        elif isinstance(msg, HumanMessage):
            return GLMMessageConverter._convert_human(msg)
        elif isinstance(msg, AIMessage):
            return GLMMessageConverter._convert_ai(msg)
        elif isinstance(msg, ToolMessage):
            return GLMMessageConverter._convert_tool(msg)
        else:
            return GLMMessageConverter._convert_fallback(msg)

    @staticmethod
    def _convert_system(msg: SystemMessage) -> Dict[str, Any]:
        return {"role": "system", "content": msg.content}

    @staticmethod
    def _convert_human(msg: HumanMessage) -> Dict[str, Any]:
        return {"role": "user", "content": msg.content}

    @staticmethod
    def _convert_ai(msg: AIMessage) -> Dict[str, Any]:
        glm_msg = {"role": "assistant", "content": msg.content or ""}

        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            glm_msg["tool_calls"] = [
                GLMMessageConverter._convert_tool_call(tc)
                for tc in msg.tool_calls
            ]

        return glm_msg

    @staticmethod
    def _convert_tool_call(tc: Any) -> Dict[str, Any]:
        """转换单个工具调用"""
        if isinstance(tc, dict):
            tc_id = tc.get("id", "")
            tc_name = tc.get("name", "")
            tc_args = tc.get("args", {})
        else:
            tc_id = getattr(tc, 'id', '')
            tc_name = getattr(tc, 'name', '')
            tc_args = getattr(tc, 'args', {})

        arguments_str = tc_args if isinstance(tc_args, str) else json.dumps(tc_args, ensure_ascii=False)

        return {
            "id": tc_id,
            "type": "function",
            "function": {
                "name": tc_name,
                "arguments": arguments_str,
            }
        }

    @staticmethod
    def _convert_tool(msg: ToolMessage) -> Dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": msg.tool_call_id,
            "content": msg.content,
        }

    @staticmethod
    def _convert_fallback(msg: Any) -> Dict[str, Any]:
        content = str(msg.content) if hasattr(msg, 'content') else str(msg)
        return {"role": "user", "content": content}


class GLMToolConverter:
    """LangChain 工具到 GLM API 格式的转换器"""

    @staticmethod
    def convert_tools(tool_list: list[Any]) -> list[Dict[str, Any]]:
        """
        将 LangChain 工具列表转换为 GLM 格式

        Args:
            tool_list: LangChain BaseTool 对象列表

        Returns:
            List[Dict]: GLM API 格式的工具列表
        """
        glm_tools = []

        for tool in tool_list:
            parameters = GLMToolConverter._get_tool_parameters(tool)

            glm_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters,
                }
            })

        return glm_tools

    @staticmethod
    def _get_tool_parameters(tool: Any) -> Dict[str, Any]:
        """获取工具参数 schema"""
        if hasattr(tool, 'args_schema') and tool.args_schema:
            return tool.args_schema.schema()
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    @staticmethod
    def parse_tool_response(message: Any) -> Dict[str, Any]:
        """
        解析 GLM API 响应中的工具调用

        Args:
            message: GLM API 返回的消息对象

        Returns:
            Dict: 包含 content 和 tool_calls 的字典
        """
        content = message.content or ""
        tool_calls = []

        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tc in message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)

                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": args,
                })

        return {
            "content": content or "正在调用工具...",
            "tool_calls": tool_calls if tool_calls else None,
        }
