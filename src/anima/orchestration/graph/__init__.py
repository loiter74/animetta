"""
LangGraph 节点模块

实现各个处理节点，每个节点负责：
1. 读取状态中的特定字段
2. 调用现有服务（services/ 中的实现）
3. 将结果写回状态

节点原则:
- 不重写业务逻辑，全部复用现有服务
- 只负责状态流转和服务调用
- 异常处理：失败时设置 state["error"]
"""

from .asr_node import asr_node
from .llm_node import llm_node
from .tts_node import tts_node
from .emotion_node import emotion_node
from .output_node import output_node
from .tool_node import tool_node

__all__ = [
    "asr_node",
    "llm_node",
    "tts_node",
    "emotion_node",
    "output_node",
    "tool_node",
]
