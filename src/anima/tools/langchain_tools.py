"""
LangChain 内置工具集成

提供 LangChain 自带的工具的集成和加载。
"""

from typing import List, Any, Optional
from loguru import logger


def get_python_repl_tool() -> Any:
    """
    获取 Python 代码执行工具（安全版本）

    Returns:
        Python REPL 工具实例
    """
    try:
        from langchain_experimental.utilities import PythonREPL

        python_repl = PythonREPL()

        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field

        class PythonInput(BaseModel):
            code: str = Field(description="要执行的 Python 代码")

        async def python_exec(code: str) -> str:
            """安全执行 Python 代码并返回结果"""
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    python_repl.run,
                    code
                )
                return f"🐍 Python 执行结果：\n\n{result}"
            except Exception as e:
                return f"Python 执行错误: {str(e)}"

        return StructuredTool.from_coro(
            name="python_repl",
            description="安全执行 Python 代码并返回结果。适用于数学计算、数据处理、算法验证等。",
            func=python_exec,
            args_schema=PythonInput,
        )

    except ImportError:
        logger.warning("[LangChainTools] PythonREPL 未安装，请运行: pip install langchain-experimental")
        return None
    except Exception as e:
        logger.error(f"[LangChainTools] PythonREPL 加载失败: {e}")
        return None


# 工具注册表
_LANGCHAIN_TOOL_GETTERS = {
    "python_repl": get_python_repl_tool,
}


def load_langchain_tools(enabled_tools: Optional[List[str]] = None) -> List[Any]:
    """
    加载 LangChain 工具

    Args:
        enabled_tools: 要启用的工具名称列表（None 表示全部启用）

    Returns:
        工具列表
    """
    if enabled_tools is None:
        # 如果未指定，返回空列表（需要显式启用）
        return []

    tools = []

    for tool_name in enabled_tools:
        if tool_name in _LANGCHAIN_TOOL_GETTERS:
            getter = _LANGCHAIN_TOOL_GETTERS[tool_name]
            tool = getter()
            if tool:
                tools.append(tool)
                logger.info(f"[LangChainTools] 已加载工具: {tool_name}")
        else:
            logger.warning(f"[LangChainTools] 未知的工具: {tool_name}")

    logger.info(f"[LangChainTools] 共加载 {len(tools)} 个 LangChain 工具")
    return tools


def get_available_langchain_tools() -> List[str]:
    """
    获取可用的 LangChain 工具名称列表

    Returns:
        工具名称列表
    """
    return list(_LANGCHAIN_TOOL_GETTERS.keys())
