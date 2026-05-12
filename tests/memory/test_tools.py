"""Tests for memory tool schemas and execute_tool."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.anima.memory.tools import (
    MEMORY_GET_SCHEMA,
    MEMORY_SEARCH_SCHEMA,
    execute_tool,
    get_tool_schemas,
)


class TestToolSchemas:
    """Tool schema structure and content."""

    def test_get_tool_schemas_returns_two(self):
        schemas = get_tool_schemas()
        assert len(schemas) == 2
        names = {s["name"] for s in schemas}
        assert names == {"memory_search", "memory_get"}

    def test_memory_search_schema_structure(self):
        assert MEMORY_SEARCH_SCHEMA["name"] == "memory_search"
        assert "description" in MEMORY_SEARCH_SCHEMA
        params = MEMORY_SEARCH_SCHEMA["parameters"]
        assert params["type"] == "object"
        assert "query" in params["properties"]
        assert params["required"] == ["query"]

    def test_memory_search_schema_properties(self):
        props = MEMORY_SEARCH_SCHEMA["parameters"]["properties"]
        assert props["query"]["type"] == "string"
        assert props["max_results"]["type"] == "integer"
        assert props["max_results"]["default"] == 10
        assert props["min_score"]["type"] == "number"
        assert props["min_score"]["default"] == 0.0

    def test_memory_get_schema_structure(self):
        assert MEMORY_GET_SCHEMA["name"] == "memory_get"
        params = MEMORY_GET_SCHEMA["parameters"]
        assert params["type"] == "object"
        assert "path" in params["properties"]
        assert params["required"] == ["path"]

    def test_memory_get_schema_properties(self):
        props = MEMORY_GET_SCHEMA["parameters"]["properties"]
        assert props["path"]["type"] == "string"
        assert props["start_line"]["type"] == "integer"
        assert props["end_line"]["type"] == "integer"


class TestExecuteTool:
    """Tool execution via execute_tool()."""

    def test_memory_search_calls_manager_search(self):
        mock_manager = MagicMock()
        mock_manager.search.return_value = []

        result = execute_tool(mock_manager, "memory_search", {"query": "hello"})

        mock_manager.search.assert_called_once_with(
            "hello", max_results=10, min_score=0.0
        )
        parsed = json.loads(result)
        assert parsed["results"] == []
        assert parsed["total"] == 0

    def test_memory_search_with_custom_params(self):
        mock_manager = MagicMock()
        mock_manager.search.return_value = []

        execute_tool(
            mock_manager,
            "memory_search",
            {"query": "test", "max_results": 5, "min_score": 0.3},
        )

        mock_manager.search.assert_called_once_with(
            "test", max_results=5, min_score=0.3
        )

    def test_memory_get_calls_manager_get(self):
        mock_manager = MagicMock()
        mock_manager.get.return_value = "file content"

        result = execute_tool(mock_manager, "memory_get", {"path": "MEMORY.md"})

        mock_manager.get.assert_called_once_with(
            "MEMORY.md", start_line=None, end_line=None
        )
        parsed = json.loads(result)
        assert parsed["text"] == "file content"

    def test_memory_get_with_line_range(self):
        mock_manager = MagicMock()
        mock_manager.get.return_value = "line 5\nline 6"

        execute_tool(
            mock_manager,
            "memory_get",
            {"path": "daily.md", "start_line": 5, "end_line": 6},
        )

        mock_manager.get.assert_called_once_with("daily.md", start_line=5, end_line=6)

    def test_unknown_tool_returns_error(self):
        mock_manager = MagicMock()
        result = execute_tool(mock_manager, "unknown_tool", {})
        parsed = json.loads(result)
        assert "error" in parsed

    def test_search_results_serialization(self):
        mock_manager = MagicMock()
        from src.anima.memory.models.base import SearchResult

        mock_manager.search.return_value = [
            SearchResult(
                text="found it",
                path="wiki/entities/test.md",
                start_line=1,
                end_line=3,
                score=0.85,
                source="wiki",
            )
        ]

        result = execute_tool(mock_manager, "memory_search", {"query": "test"})
        parsed = json.loads(result)
        assert parsed["total"] == 1
        r = parsed["results"][0]
        assert r["text"] == "found it"
        assert r["score"] == 0.85
        assert r["source"] == "wiki"
