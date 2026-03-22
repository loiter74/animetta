"""LangGraph 状态图构建器"""

from typing import Dict, Any, Optional, Literal, List
from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import asr_node, llm_node, tts_node, emotion_node, output_node, tool_node


def route_input(state: AgentState) -> Literal["asr", "llm"]:
    """根据输入类型决定起始节点"""
    input_type = state.get("input_type", "text")
    if input_type == "audio" and state.get("raw_audio"):
        logger.debug(f"[路由] 音频输入 -> ASR 节点")
        return "asr"
    logger.debug(f"[路由] 文本输入 -> LLM 节点")
    return "llm"


def should_use_tools(state: AgentState) -> Literal["tools", "tts"]:
    """检查 LLM 是否请求了工具调用"""
    tool_calls = state.get("tool_calls")
    if tool_calls:
        logger.debug(f"[路由] LLM 请求工具调用 -> 工具节点")
        return "tools"
    logger.debug(f"[路由] LLM 直接回复 -> TTS 节点")
    return "tts"


def build_graph(
    checkpointer: Optional[Any] = None,
    enable_tools: bool = False,
    tools: Optional[List[Any]] = None,
    tools_map: Optional[Dict[str, Any]] = None,
) -> StateGraph:
    """
    构建 LangGraph 状态图

    图结构:
        [START]
           |
           +--(音频输入)--> [asr_node]
           |                  |
           +--(文本输入)------+-> [llm_node]
                                     |
                            +--------+--------+
                            |                 |
                      (有工具调用)      (直接回复)
                            |                 |
                        [tool_node]      [tts_node]
                            |                 |
                            +-------+---------+
                                    |
                               [emotion_node]
                                    |
                               [output_node]
                                    |
                                  [END]
    """
    logger.info("[LangGraph] 开始构建状态图...")

    if enable_tools:
        logger.info(f"[LangGraph] 工具调用已启用，加载 {len(tools or [])} 个工具")

    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("asr", asr_node)
    graph.add_node("llm", llm_node)
    graph.add_node("tts", tts_node)
    graph.add_node("emotion", emotion_node)
    graph.add_node("output", output_node)

    if enable_tools:
        graph.add_node("tools", tool_node)
        logger.info("[LangGraph] 工具节点已注册")

    # 设置入口点
    graph.set_conditional_entry_point(route_input, {"asr": "asr", "llm": "llm"})

    # 添加边
    graph.add_edge("asr", "llm")

    if enable_tools:
        graph.add_conditional_edges("llm", should_use_tools, {"tools": "tools", "tts": "tts"})
        graph.add_edge("tools", "llm")
        logger.info("[LangGraph] 工具循环已配置: llm -> tools -> llm")
    else:
        graph.add_edge("llm", "tts")

    graph.add_edge("tts", "emotion")
    graph.add_edge("emotion", "output")
    graph.add_edge("output", END)

    logger.info("[LangGraph] 状态图构建完成")

    compiled_graph = graph.compile(checkpointer=checkpointer)
    logger.info("[LangGraph] 状态图编译完成")
    return compiled_graph


def create_default_graph(
    enable_memory: bool = True,
    enable_tools: bool = False,
    tools: Optional[List[Any]] = None,
    tools_map: Optional[Dict[str, Any]] = None,
) -> StateGraph:
    """
    创建默认配置的状态图

    Args:
        enable_memory: 是否启用内存检查点
        enable_tools: 是否启用工具调用
        tools: 工具列表
        tools_map: 工具映射
    """
    checkpointer = None

    if enable_memory:
        checkpointer = MemorySaver()
        logger.info("[LangGraph] 内存检查点已启用")

    if enable_tools and not tools:
        logger.warning("[LangGraph] 启用工具但未提供工具列表，工具节点将无法工作")

    return build_graph(
        checkpointer=checkpointer,
        enable_tools=enable_tools,
        tools=tools,
        tools_map=tools_map,
    )


def visualize_graph(graph: StateGraph, output_path: str = "graph.png") -> None:
    """可视化状态图（需要安装 graphviz）"""
    try:
        from IPython.display import Image, display

        img_data = graph.get_graph().draw_mermaid_png()

        with open(output_path, "wb") as f:
            f.write(img_data)

        logger.info(f"[LangGraph] 图已保存到: {output_path}")

    except ImportError:
        logger.warning("[LangGraph] 无法可视化: 缺少 graphviz 或 IPython")
    except Exception as e:
        logger.error(f"[LangGraph] 可视化失败: {e}")


def print_graph_structure(graph: StateGraph) -> None:
    """打印图结构（用于调试）"""
    logger.info("[LangGraph] 图结构:")
    logger.info(str(graph.get_graph().print_ascii()))
