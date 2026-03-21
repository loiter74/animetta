"""
LangGraph 状态图模块

将 Anima 从自定义 EventBus 架构迁移到 LangGraph 状态图架构，
引入 Tool Use / Agent 能力，支持 MCP 协议。

架构迁移计划:
- Phase 1: 定义 LangGraph 状态和图结构
- Phase 2: 实现核心节点（ASR, LLM, TTS, Emotion, Output）
- Phase 3: 集成 Tool Use（工具调用）
- Phase 4: 集成 MCP 协议
"""

from .state import AgentState, create_initial_state
from .builder import build_graph, create_default_graph
from .orchestrator import LangGraphOrchestrator, LangGraphOrchestratorFactory

__all__ = [
    "AgentState",
    "create_initial_state",
    "build_graph",
    "create_default_graph",
    "LangGraphOrchestrator",
    "LangGraphOrchestratorFactory",
]
