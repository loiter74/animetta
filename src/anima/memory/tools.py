"""
Agent 工具接口.

提供两个核心工具供 LLM Agent 调用 (对应 OpenClaw 的 memory_search / memory_get):
- memory_search: 语义搜索记忆
- memory_get: 读取指定记忆文件

可以直接注册为 function calling 的 tool schema.
"""

from __future__ import annotations

import json
from typing import Any

from .memory_manager import MemoryManager


# ── Tool Schema (用于 function calling) ─────────────────

MEMORY_SEARCH_SCHEMA = {
    "name": "memory_search",
    "description": (
        "Semantically search MEMORY.md and daily logs (memory/*.md) "
        "for prior work, decisions, dates, people, preferences, or todos. "
        "Returns top snippets with file path and line numbers."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query text",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 10)",
                "default": 10,
            },
            "min_score": {
                "type": "number",
                "description": "Minimum relevance score threshold (default: 0.0)",
                "default": 0.0,
            },
        },
        "required": ["query"],
    },
}

MEMORY_GET_SCHEMA = {
    "name": "memory_get",
    "description": (
        "Read a specific memory file with optional line range. "
        "Use for targeted reads when you know the exact file and location."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": 'Relative path, e.g. "MEMORY.md" or "memory/2026-03-13.md"',
            },
            "start_line": {
                "type": "integer",
                "description": "Start line (1-based, optional)",
            },
            "end_line": {
                "type": "integer",
                "description": "End line (1-based, inclusive, optional)",
            },
        },
        "required": ["path"],
    },
}


def get_tool_schemas() -> list[dict]:
    """获取所有记忆工具的 schema, 可直接用于 function calling."""
    return [MEMORY_SEARCH_SCHEMA, MEMORY_GET_SCHEMA]


# ── Tool 执行器 ──────────────────────────────────────────

def execute_tool(
    manager: MemoryManager,
    tool_name: str,
    arguments: dict[str, Any],
) -> str:
    """
    执行记忆工具调用.

    Args:
        manager: MemoryManager 实例
        tool_name: 工具名称
        arguments: 参数字典

    Returns:
        JSON 格式的结果字符串
    """
    if tool_name == "memory_search":
        return _execute_search(manager, arguments)
    elif tool_name == "memory_get":
        return _execute_get(manager, arguments)
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def _execute_search(manager: MemoryManager, args: dict) -> str:
    query = args["query"]
    max_results = args.get("max_results", 10)
    min_score = args.get("min_score", 0.0)

    results = manager.search(query, max_results=max_results, min_score=min_score)

    return json.dumps(
        {
            "results": [
                {
                    "text": r.text,
                    "path": r.path,
                    "start_line": r.start_line,
                    "end_line": r.end_line,
                    "score": round(r.score, 4),
                    "source": r.source,
                }
                for r in results
            ],
            "total": len(results),
        },
        ensure_ascii=False,
        indent=2,
    )


def _execute_get(manager: MemoryManager, args: dict) -> str:
    path = args["path"]
    start_line = args.get("start_line")
    end_line = args.get("end_line")

    content = manager.get(path, start_line=start_line, end_line=end_line)

    return json.dumps(
        {
            "text": content,
            "path": path,
        },
        ensure_ascii=False,
    )
