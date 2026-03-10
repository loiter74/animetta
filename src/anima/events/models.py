"""
事件类型定义
定义 EventBus 中使用的事件类型
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class EventType(str, Enum):
    """事件类型枚举"""
    # === 输出事件（现有） ===
    SENTENCE = "sentence"           # 文本句子
    AUDIO = "audio"                 # 音频数据
    TOOL_CALL = "tool_call"         # 工具调用
    CONTROL = "control"             # 控制信号
    IMAGE = "image"                 # 图片
    GAME_CONTROL = "game_control"   # 游戏控制
    ERROR = "error"                 # 错误
    EXPRESSION = "expression"       # Live2D 表情（旧版，基于状态）
    AUDIO_WITH_EXPRESSION = "audio_with_expression"  # 音频 + 表情统一事件（新版，基于情感）

    # === 输入事件（新增 - Adapter Layer） ===
    INPUT_TEXT = "input_text"       # 文本输入
    INPUT_AUDIO = "input_audio"     # 音频输入
    INPUT_IMAGE = "input_image"     # 图片输入

    # === 通道事件（新增 - Adapter Layer） ===
    CHANNEL_CONNECT = "channel_connect"         # 通道连接
    CHANNEL_DISCONNECT = "channel_disconnect"   # 通道断开

    # === MCP 工具事件（新增 - MCP Layer） ===
    TOOL_EXECUTE = "tool_execute"       # 请求执行工具
    TOOL_RESULT = "tool_result"         # 工具执行结果


class ControlSignal(str, Enum):
    """控制信号枚举"""
    # 对话生命周期
    CONVERSATION_START = "conversation-start"
    CONVERSATION_END = "conversation-end"

    # ASR 相关
    ASR_START = "asr-start"
    SYNTH_COMPLETE = "backend-synth-complete"

    # 打断相关
    INTERRUPT = "interrupt"
    INTERRUPTED = "interrupted"

    # 麦克风控制
    START_MIC = "start-mic"
    STOP_MIC = "stop-mic"
    MIC_AUDIO_END = "mic-audio-end"

    # 错误/警告
    NO_AUDIO_DATA = "no-audio-data"
    ERROR = "error"


@dataclass
class OutputEvent:
    """
    输出事件

    统一的输出事件类型，由 Pipeline 产出，分发到各个 Handler 处理
    """
    # 事件类型
    type: str

    # 事件数据（根据 type 不同而不同）
    data: Any

    # 序号（用于排序）
    seq: int = 0

    # 额外元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "type": self.type,
            "data": self.data,
            "seq": self.seq,
            "metadata": self.metadata,
        }


@dataclass
class SinkMessage:
    """
    输出槽消息

    由 Handler 产出，发送到 WebSocket
    """
    # 消息类型
    type: str

    # 消息内容（将被 JSON 序列化）
    content: Dict[str, Any]

    # 序号（用于排序）
    seq: int = 0

    # 优先级（数字越小优先级越高）
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为发送格式"""
        result = {"type": self.type}
        result.update(self.content)
        return result


# ============================================================================
# Adapter Layer Types (新增)
# ============================================================================

@dataclass
class ChannelMessage:
    """
    通道消息

    用于 INPUT_* 事件，携带来自不同通道的输入数据
    """
    # 通道实例 ID（唯一标识一个通道连接）
    channel_id: str

    # 通道类型（socketio / rest / cli / discord 等）
    channel_type: str

    # 会话 ID（关联到 ConversationOrchestrator）
    session_id: str

    # 消息内容（根据事件类型不同：str / bytes / numpy array）
    content: Any

    # 用户 ID（可选，用于多用户场景）
    user_id: Optional[str] = None

    # 用户显示名称
    user_name: Optional[str] = None

    # 额外元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "channel_id": self.channel_id,
            "channel_type": self.channel_type,
            "session_id": self.session_id,
            "content": self.content,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "metadata": self.metadata,
        }


@dataclass
class ChannelInfo:
    """
    通道信息

    用于 CHANNEL_CONNECT / CHANNEL_DISCONNECT 事件
    """
    # 通道实例 ID
    channel_id: str

    # 通道类型
    channel_type: str

    # 会话 ID
    session_id: str

    # 通道能力
    capabilities: Dict[str, bool] = field(default_factory=lambda: {
        "text": True,
        "audio": False,
        "image": False,
        "streaming": False,
    })

    # 客户端信息
    client_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "channel_type": self.channel_type,
            "session_id": self.session_id,
            "capabilities": self.capabilities,
            "client_info": self.client_info,
        }


# ============================================================================
# MCP Layer Types (新增)
# ============================================================================

class ToolPermission(str, Enum):
    """工具权限级别"""
    AUTO = "auto"           # 自动允许（安全工具）
    SESSION = "session"     # 会话内允许一次
    ASK = "ask"             # 每次都询问用户
    DENY = "deny"           # 拒绝执行


@dataclass
class ToolCallRequest:
    """
    工具调用请求

    用于 TOOL_EXECUTE 事件，由 LLM 发起工具调用
    """
    # 工具调用 ID（唯一标识一次调用）
    tool_call_id: str

    # 工具名称
    tool_name: str

    # 调用参数
    arguments: Dict[str, Any]

    # 来源通道 ID（可选，用于回复）
    channel_id: Optional[str] = None

    # 会话 ID
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "channel_id": self.channel_id,
            "session_id": self.session_id,
        }


@dataclass
class ToolCallResult:
    """
    工具调用结果

    用于 TOOL_RESULT 事件，返回工具执行结果
    """
    # 对应的工具调用 ID
    tool_call_id: str

    # 是否成功
    success: bool

    # 执行结果（成功时）或错误信息（失败时）
    result: Any

    # 错误信息（可选）
    error: Optional[str] = None

    # 执行时间（毫秒）
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ToolSchema:
    """
    工具 Schema

    兼容 OpenAI / Anthropic 的工具定义格式
    """
    # 工具名称
    name: str

    # 工具描述
    description: str

    # 参数 JSON Schema
    parameters: Dict[str, Any]

    # 必需参数列表
    required: List[str] = field(default_factory=list)

    def to_openai_format(self) -> Dict[str, Any]:
        """转换为 OpenAI 工具格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """转换为 Anthropic 工具格式"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }
