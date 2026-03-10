"""
Socket.IO 服务端实现
基于 python-socketio 库，使用 ServiceContext 管理服务
参考 Open-LLM-VTuber 的实时对话逻辑

重构：使用 ConversationOrchestrator 整合对话逻辑
"""

import os
import sys
from pathlib import Path

# 修复模块导入路径：将 src 目录添加到 Python 路径
# 这样无论从哪个目录运行，都能正确导入 anima 模块
# 注意：必须在所有其他导入之前执行
current_dir = Path(__file__).resolve().parent
# anima 模块位于 src/anima，所以我们需要将 src 目录加入路径
src_dir = current_dir.parent  # C:\Users\30262\Project\Anima\src
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from loguru import logger

# 加载 .env 文件中的环境变量（必须在其他导入之前）
try:
    from dotenv import load_dotenv
    # 获取项目根目录（socketio_server.py 的上上级目录，因为 src/anima/socketio_server.py）
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
        logger.info(f"[OK] 已加载环境变量文件: {env_path}")
        # 立即验证关键环境变量
        glm_key = os.getenv("GLM_API_KEY")
        if glm_key:
            logger.info(f"[OK] GLM_API_KEY 已从 .env 加载: {glm_key[:20]}... (长度: {len(glm_key)})")
        else:
            logger.error("[WARNING] .env 文件已加载，但 GLM_API_KEY 仍未设置！")
    else:
        logger.warning(f".env 文件不存在: {env_path}，将使用系统环境变量")
except ImportError:
    # 如果没有安装 python-dotenv，跳过（依赖系统环境变量）
    logger.info("python-dotenv 未安装，使用系统环境变量")
    pass

# 最终验证关键环境变量
glm_key = os.getenv("GLM_API_KEY")
if glm_key:
    logger.info(f"[OK] GLM_API_KEY 在运行时可用: {glm_key[:20]}...")
else:
    logger.error("[WARNING] GLM_API_KEY 在运行时不可用，GLM将降级到MockLLM")

import socketio
import json
import time
import numpy as np
import uvicorn
from typing import Dict, Union, Optional

from anima.config import AppConfig
from anima.service_context import ServiceContext
from anima.services.conversation import (
    ConversationOrchestrator,
    SessionManager,
)
from anima.handlers import TextHandler
from anima.handlers.unified import UnifiedEventHandler
from anima.handlers.input_handler import InputHandler
from anima.events import EventPriority
from anima.utils.logger_manager import logger_manager
from anima.config.user_settings import UserSettings
from anima.config.live2d import get_live2d_config
from anima.avatar.prompts import EmotionPromptBuilder

# Adapter layer
from anima.adapters import (
    DesktopLive2DChatter,
    DesktopChatterConfig,
    AdapterRegistry,
)
from anima.state import AudioBufferManager

# Create Socket.IO server with ASGI mode (works with uvicorn)
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    cors_credentials=True,
    logger=False,  # Disable default logging (we handle our own)
    engineio_logger=False,  # Disable default engine.io logging
)

# Create ASGI app for Socket.IO
asgi_app = socketio.ASGIApp(sio)

logger.info(f"[Socket.IO] Server created with async_mode='asgi'")
logger.info(f"[Socket.IO] CORS enabled: origins=*")


# ============================================
# Socket.IO Event Handlers with Logging
# ============================================

@sio.on('connect')
async def on_connect(sid, environ, auth):
    logger.info(f"[Socket.IO] Client connected: sid={sid}")
    await sio.save_session(sid, {'connected_at': time.time()})
    logger.info(f"[Socket.IO] Session saved: {sid}")


@sio.on('disconnect')
async def on_disconnect(sid):
    logger.info(f"[Socket.IO] Client disconnected: sid={sid}")
    # Cleanup session resources
    await cleanup_context(sid)
    logger.info(f"[Socket.IO] Session cleaned up: {sid}")

# ============================================
# 全局状态管理
# ============================================

# 存储每个会话的 ServiceContext
# 键: session_id, 值: ServiceContext 实例
session_contexts: Dict[str, ServiceContext] = {}

# 存储每个会话的 ConversationOrchestrator
# 键: session_id, 值: ConversationOrchestrator 实例
orchestrators: Dict[str, ConversationOrchestrator] = {}

# 存储每个会话的 DesktopLive2DChatter adapter
# 键: session_id, 值: DesktopLive2DChatter 实例
adapters: Dict[str, DesktopLive2DChatter] = {}

# 全局配置（可被所有会话共享）
global_config: AppConfig = None

# 用户配置（持久化到 .user_settings.yaml）
user_settings = UserSettings(Path(__file__).parent.parent.parent)

# 应用用户配置的日志级别
initial_log_level = user_settings.get_log_level()
logger_manager.set_level(initial_log_level)
logger.info(f"应用用户日志级别配置: {initial_log_level}")

# ============================================
# Electron 桌面客户端支持
# ============================================

# 桌面客户端类型
DESKTOP_CLIENT_TYPES = ["live2d", "chat", "web"]

# 存储桌面客户端信息
# 键: session_id, 值: {client_type: str, connected: bool}
desktop_clients: Dict[str, dict] = {}

# Live2D 动作队列（延迟初始化）
_live2d_action_queue = None

def get_live2d_action_queue():
    """获取 Live2D 动作队列"""
    global _live2d_action_queue
    if _live2d_action_queue is None:
        from anima.services.live2d import Live2DActionQueue
        _live2d_action_queue = Live2DActionQueue()

        # 设置执行回调 - 将动作发送到 Live2D 客户端
        async def execute_action(action):
            await broadcast_to_desktop_clients("live2d", "live2d.action", {
                "action": action.action,
                "action_id": action.action_id
            })

        _live2d_action_queue.set_execute_callback(execute_action)
        logger.info("[Live2D] 动作队列已初始化")

    return _live2d_action_queue


async def broadcast_to_desktop_clients(client_type: str, event: str, data: dict):
    """
    广播消息到指定类型的桌面客户端

    Args:
        client_type: 客户端类型 ("live2d", "chat", "web")
        event: 事件名称
        data: 事件数据
    """
    for sid, client_info in list(desktop_clients.items()):
        if client_info.get("client_type") == client_type and client_info.get("connected"):
            await sio.emit(event, data, to=sid)


async def get_or_create_context(sid: str) -> ServiceContext:
    """
    获取或创建指定会话的 ServiceContext

    Args:
        sid: session id

    Returns:
        ServiceContext: 该会话的服务上下文
    """
    if sid not in session_contexts:
        print(f"\n[{sid}] [CREATE] 创建新的 ServiceContext")
        ctx = ServiceContext()
        ctx.session_id = sid

        # 设置发送消息的回调函数
        async def send_text_callback(message: str):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            await sio.emit(data.get('type', 'message'), data, to=sid)

        ctx.send_text = send_text_callback

        # 加载配置（使用全局配置或默认配置）
        print(f"[{sid}] [LOAD] 加载配置...")
        config = global_config or AppConfig.load()
        await ctx.load_from_config(config)

        session_contexts[sid] = ctx
        print(f"[{sid}] [OK] ServiceContext 创建完成")
        logger.info(f"为会话 {sid} 创建了新的 ServiceContext")
    else:
        # print(f"\n[{sid}] ♻️ 使用现有 ServiceContext")  # 注释掉以减少日志噪音
        pass

    return session_contexts[sid]


async def get_or_create_orchestrator(sid: str) -> ConversationOrchestrator:
    """
    获取或创建指定会话的 ConversationOrchestrator

    Args:
        sid: session id

    Returns:
        ConversationOrchestrator: 该会话的对话编排器
    """
    if sid not in orchestrators:
        logger.info(f"[{sid}] 创建新的 ConversationOrchestrator")
        ctx = await get_or_create_context(sid)
        
        # WebSocket 发送函数
        async def websocket_send(message: str):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            await sio.emit(data.get('type', 'message'), data, to=sid)
        
        # 加载 Live2D 配置
        live2d_config = get_live2d_config()

        # 创建编排器（管线步骤在编排器内部自动组装）
        orchestrator = ConversationOrchestrator(
            asr_engine=ctx.asr_engine,
            tts_engine=ctx.tts_engine,
            agent=ctx.llm_engine,
            websocket_send=websocket_send,
            session_id=sid,
            live2d_config=live2d_config if live2d_config.enabled else None,
            memory_system=ctx.memory_system,
            local_llm=ctx.local_llm_engine,  # 添加本地LLM（无persona）
        )

        # 创建并注册 TextHandler（使用 orchestrator 的 websocket_send，已通过 adapter 包装）
        text_handler = TextHandler(websocket_send=orchestrator.websocket_send)
        logger.info(f"[{sid}] 创建 TextHandler 实例: ID={id(text_handler)}")
        orchestrator.register_handler("sentence", text_handler, priority=EventPriority.NORMAL)
        logger.info(f"[{sid}] TextHandler 已注册到 sentence 事件")

        # 创建并注册 UnifiedEventHandler（处理音频 + 表情事件）
        if live2d_config.enabled:
            unified_handler = UnifiedEventHandler(
                websocket_send=orchestrator.websocket_send,
                analyzer_type="llm_tag_analyzer",  # 使用 LLM 标签分析器
                strategy_type="position_based",     # 使用基于位置的时间轴策略
                sample_rate=50  # 50 Hz
            )
            orchestrator.register_handler(
                "audio_with_expression",
                unified_handler,
                priority=EventPriority.NORMAL
            )
            logger.info(f"[{sid}] UnifiedEventHandler 已注册到 audio_with_expression 事件")

        # 启动编排器（将 EventRouter 连接到 EventBus）
        orchestrator.start()

        # 创建并注册 InputHandler（处理 INPUT_TEXT/INPUT_AUDIO 事件）
        input_handler = InputHandler(
            event_bus=orchestrator.event_bus,
            orchestrator_registry=lambda session_id: orchestrators.get(session_id),
            asr_service=ctx.asr_service,
        )
        await input_handler.start()
        logger.info(f"[{sid}] InputHandler 已启动，订阅 INPUT_TEXT/INPUT_AUDIO 事件")

        orchestrators[sid] = orchestrator
        logger.info(f"为会话 {sid} 创建了新的 ConversationOrchestrator，已注册 {orchestrator.get_handler_count()} 个 Handler")
    
    return orchestrators[sid]


async def cleanup_context(sid: str) -> None:
    """
    清理指定会话的所有资源

    Args:
        sid: session id
    """
    # 停止并清理 adapter
    if sid in adapters:
        try:
            await adapters[sid].stop()
            logger.debug(f"[{sid}] Adapter 已停止")
        except Exception as e:
            logger.error(f"[{sid}] 停止 Adapter 时出错: {e}")
        del adapters[sid]

    # 停止编排器（清理 EventRouter 中的所有订阅）
    if sid in orchestrators:
        orchestrator = orchestrators[sid]
        orchestrator.stop()
        del orchestrators[sid]

    # 清理上下文
    if sid in session_contexts:
        ctx = session_contexts[sid]
        await ctx.close()
        del session_contexts[sid]
        logger.info(f"已清理会话 {sid} 的所有资源")


async def get_or_create_adapter(sid: str) -> DesktopLive2DChatter:
    """
    获取或创建指定会话的 DesktopLive2DChatter adapter

    EventBus 架构：
    - Adapter 只依赖 EventBus，不直接依赖 Orchestrator
    - 输入：Adapter → EventBus.emit(INPUT_TEXT/INPUT_AUDIO) → InputHandler → Orchestrator
    - 输出：Orchestrator → EventBus → Adapter.send() → 客户端

    Args:
        sid: session id

    Returns:
        DesktopLive2DChatter: 该会话的 adapter 实例
    """
    if sid not in adapters:
        logger.info(f"[{sid}] 创建新的 DesktopLive2DChatter adapter (EventBus 架构)")

        # 获取上下文和编排器（用于获取 EventBus 和 VAD）
        ctx = await get_or_create_context(sid)
        orchestrator = await get_or_create_orchestrator(sid)

        # 创建发送回调函数
        async def send_callback(data: dict):
            """发送数据到客户端"""
            event_type = data.get('type', 'message')
            await sio.emit(event_type, data, to=sid)

        # 创建 adapter 配置
        config = DesktopChatterConfig(
            sample_rate=16000,
            channels=1,
            vad_enabled=ctx.vad_engine is not None,
            vad_timeout_seconds=15.0,
            auto_interrupt=True,
        )

        # 创建 adapter（只依赖 EventBus，不直接依赖 Orchestrator）
        adapter = DesktopLive2DChatter(
            event_bus=orchestrator.event_bus,
            channel_id=sid,
            vad_engine=ctx.vad_engine,
            config=config,
            send_callback=send_callback,
            session_id=sid,
        )

        # 启动 adapter
        await adapter.start()

        adapters[sid] = adapter
        logger.info(f"[{sid}] DesktopLive2DChatter adapter 已创建并启动 (EventBus 模式)")

    return adapters[sid]


# ============================================
# 连接事件处理
# ============================================

@sio.event
async def connect(sid, environ):
    """
    客户端连接时触发
    支持 Web 和 Electron 桌面客户端
    """
    # 检测客户端类型
    client_type = environ.get("HTTP_USER_AGENT", "")
    is_electron = "electron" in client_type.lower()

    print(f"\n{'='*60}")
    print(f"[OK] 客户端已连接: {sid}")
    print(f"     类型: {'Electron' if is_electron else 'Web'}")
    print(f"{'='*60}\n")
    logger.info(f"客户端已连接: {sid} (类型: {'Electron' if is_electron else 'Web'})")

    # 发送欢迎消息
    await sio.emit('connection-established', {
        'message': '连接成功',
        'sid': sid,
        'server_time': asyncio.get_event_loop().time()
    }, to=sid)

    # 对于 Web 客户端，发送启动麦克风信号
    if not is_electron:
        await sio.emit('control', {
            'type': 'control',
            'text': 'start-mic'
        }, to=sid)
        print(f"[OK] 已发送 start-mic 信号给客户端 {sid}")


@sio.event
async def disconnect(sid):
    """
    客户端断开时触发
    """
    logger.info(f"客户端已断开: {sid}")
    
    # 清理该会话的所有资源
    await cleanup_context(sid)


# ============================================
# 业务事件处理
# ============================================

@sio.event
async def text_input(sid, data):
    """
    处理文本输入
    使用 DesktopLive2DChatter adapter 处理对话
    """
    text = data.get('text', '')
    logger.info(f"[{sid}] 收到文本输入: {text}")

    if not text:
        return

    try:
        adapter = await get_or_create_adapter(sid)
        await adapter.handle_text_input(
            text=text,
            from_name=data.get('from_name', 'User'),
            metadata=data.get('metadata', {}),
        )

    except Exception as e:
        logger.error(f"[{sid}] 处理文本输入时出错: {e}")
        await sio.emit('error', {
            'type': 'error',
            'message': str(e)
        }, to=sid)


@sio.event
async def mic_audio_data(sid, data):
    """
    处理音频数据流（非 VAD 模式）
    使用 DesktopLive2DChatter adapter 累积音频数据
    """
    audio = data.get('audio', [])

    if audio:
        adapter = await get_or_create_adapter(sid)
        # 使用 adapter 的 handle_audio_chunk 方法（会自动处理无 VAD 的情况）
        await adapter.handle_audio_chunk(audio)
        logger.debug(f"[{sid}] 累积音频: {len(audio)} 个采样点")


@sio.event
async def raw_audio_data(sid, data):
    """
    处理原始音频数据用于 VAD 检测
    使用 DesktopLive2DChatter adapter 处理
    """
    audio_chunk = data.get('audio', [])

    if not audio_chunk:
        logger.debug(f"[{sid}] 收到空音频数据")
        return

    try:
        adapter = await get_or_create_adapter(sid)
        await adapter.handle_audio_chunk(audio_chunk)

    except Exception as e:
        logger.error(f"[{sid}] VAD 处理出错: {e}", exc_info=True)


@sio.event
async def mic_audio_end(sid, data):
    """
    用户说完话，触发完整对话流程
    使用 DesktopLive2DChatter adapter 处理
    """
    logger.info(f"[{sid}] 音频输入结束")

    try:
        adapter = await get_or_create_adapter(sid)
        await adapter.handle_audio_end(
            metadata=data.get('metadata', {}),
            from_name=data.get('from_name', 'User'),
        )

    except Exception as e:
        logger.error(f"[{sid}] 处理音频时出错: {e}")
        await sio.emit('error', {
            'type': 'error',
            'message': str(e)
        }, to=sid)


@sio.event
async def interrupt_signal(sid, data):
    """
    打断信号
    取消当前正在进行的对话和 TTS
    使用 DesktopLive2DChatter adapter 处理
    """
    # 获取用户听到的部分回复
    heard_response = data.get('text', '')
    logger.info(f"[{sid}] 收到打断信号，已听到的回复: {heard_response[:50] if heard_response else '(空)'}...")

    try:
        adapter = await get_or_create_adapter(sid)
        await adapter.handle_interrupt(heard_text=heard_response)

    except Exception as e:
        logger.error(f"[{sid}] 处理打断信号时出错: {e}")

    await sio.emit('control', {
        'type': 'control',
        'text': 'interrupted'
    }, to=sid)


@sio.event
async def fetch_history_list(sid, data):
    """
    获取聊天历史列表
    """
    logger.info(f"[{sid}] 请求聊天历史列表")
    
    # TODO: 从持久化存储获取历史列表
    histories = [
        {'uid': 'history_001', 'preview': '你好...'},
        {'uid': 'history_002', 'preview': '今天天气...'},
    ]
    
    await sio.emit('history-list', {
        'type': 'history-list',
        'histories': histories
    }, to=sid)


@sio.event
async def fetch_history(sid, data):
    """
    获取特定历史记录
    """
    history_uid = data.get('history_uid')
    logger.info(f"[{sid}] 请求历史记录: {history_uid}")
    
    # TODO: 从持久化存储获取历史记录
    messages = [
        {'role': 'user', 'content': '你好'},
        {'role': 'assistant', 'content': '你好！有什么可以帮助你的吗？'},
    ]
    
    await sio.emit('history-data', {
        'type': 'history-data',
        'messages': messages
    }, to=sid)


@sio.event
async def switch_config(sid, data):
    """
    切换配置
    """
    config_name = data.get('file', 'default')
    logger.info(f"[{sid}] 切换配置: {config_name}")
    
    try:
        # 清理旧的编排器（保留上下文）
        if sid in orchestrators:
            del orchestrators[sid]
        
        # TODO: 加载新配置
        # new_config = load_config(config_name)
        # await ctx.handle_config_switch(new_config)
        
        await sio.emit('config-switched', {
            'type': 'config-switched',
            'message': f'已切换到配置: {config_name}'
        }, to=sid)
        
    except Exception as e:
        logger.error(f"[{sid}] 切换配置时出错: {e}")
        await sio.emit('error', {
            'type': 'error',
            'message': str(e)
        }, to=sid)


@sio.event
async def clear_history(sid, data):
    """
    清空对话历史
    """
    logger.info(f"[{sid}] 清空对话历史")
    
    ctx = await get_or_create_context(sid)
    if ctx.llm_engine:
        ctx.llm_engine.clear_history()
        logger.info(f"[{sid}] 对话历史已清空")
        
        await sio.emit('history-cleared', {
            'type': 'history-cleared'
        }, to=sid)


@sio.event
async def create_new_history(sid, data):
    """
    创建新的对话历史
    """
    logger.info(f"[{sid}] 创建新对话历史")

    # TODO: 创建新的历史记录

    await sio.emit('new-history-created', {
        'type': 'new-history-created',
        'history_uid': 'new_history_001'
    }, to=sid)


@sio.event
async def set_log_level(sid, data):
    """
    设置后端日志级别

    Args:
        data: { level: str } - 日志级别 (DEBUG/INFO/WARNING/ERROR)
    """
    level = data.get('level', 'INFO').upper()
    logger.info(f"[{sid}] 请求设置日志级别为: {level}")

    # 设置日志级别
    success = logger_manager.set_level(level)

    if success:
        # 持久化到用户配置文件
        user_settings.set_log_level(level)

    # 确认响应
    await sio.emit('log_level_changed', {
        'type': 'log_level_changed',
        'success': success,
        'level': logger_manager.get_level(),
        'message': f'日志级别已设置为 {logger_manager.get_level()}' if success else '设置失败'
    }, to=sid)


# ============================================
# 心跳检测
# ============================================

@sio.event
async def heartbeat(sid, data):
    """心跳检测"""
    await sio.emit('heartbeat-ack', {}, to=sid)


# ============================================
# Electron 桌面客户端事件处理
# ============================================

@sio.event
async def desktop_register(sid, data):
    """
    Electron 桌面客户端注册

    Args:
        data: {client_type: "live2d" | "chat"}
    """
    client_type = data.get('client_type', 'web')

    if client_type not in DESKTOP_CLIENT_TYPES:
        await sio.emit('error', {
            'type': 'error',
            'message': f'Unknown client type: {client_type}'
        }, to=sid)
        return

    desktop_clients[sid] = {
        'client_type': client_type,
        'connected': True
    }

    logger.info(f"[Desktop] {client_type} 客户端已注册: {sid}")

    await sio.emit('desktop.registered', {
        'client_id': sid,
        'client_type': client_type
    }, to=sid)


@sio.event
async def desktop_live2d_action(sid, data):
    """
    处理来自 Electron 的 Live2D 动作请求

    Args:
        data: {action: {...}, action_id: str}
    """
    from anima.services.live2d import ActionMessage, QueuePolicy

    action_data = data.get('action', {})
    action_id = data.get('action_id', '')
    queue_policy = data.get('queue_policy', 'append')
    duration = data.get('duration', 0.5)

    # 创建动作消息
    action = ActionMessage(
        action_id=action_id,
        action=action_data,
        duration_sec=duration,
        queue_policy=queue_policy
    )

    # 入队到动作队列
    queue = get_live2d_action_queue()
    result = await queue.enqueue(action)

    logger.info(f"[Desktop] Live2D 动作已入队: {action_id}, 结果: {result}")

    await sio.emit('desktop.action_queued', result, to=sid)


@sio.event
async def desktop_chat_message(sid, data):
    """
    处理来自 Electron Chat 窗口的聊天消息
    使用 DesktopLive2DChatter adapter 处理

    Args:
        data: {text: str, timestamp: float}
    """
    text = data.get('text', '')
    logger.info(f"[Desktop][Chat] 收到消息: {text[:50]}...")

    try:
        adapter = await get_or_create_adapter(sid)
        await adapter.handle_text_input(
            text=text,
            from_name='User',
            metadata={},
        )

    except Exception as e:
        logger.error(f"[{sid}] 处理桌面聊天消息时出错: {e}")
        await sio.emit('error', {
            'type': 'error',
            'message': str(e)
        }, to=sid)


@sio.event
async def desktop_voice_start(sid, data):
    """开始语音输入"""
    logger.info(f"[Desktop][Chat] 语音输入开始")
    # 可以启动 VAD 或通知客户端开始录音
    await sio.emit('desktop.voice_started', {}, to=sid)


@sio.event
async def desktop_voice_stop(sid, data):
    """停止语音输入"""
    logger.info(f"[Desktop][Chat] 语音输入停止")
    # 处理录制的音频
    await sio.emit('desktop.voice_stopped', {}, to=sid)


# ============================================
# 优雅关闭
# ============================================

import signal
import asyncio


async def cleanup_all_resources():
    """清理所有资源"""
    logger.info("开始清理所有资源...")

    # 清理所有 adapters
    for sid, adapter in list(adapters.items()):
        try:
            await adapter.stop()
            logger.debug(f"[{sid}] Adapter 已停止")
        except Exception as e:
            logger.error(f"[{sid}] 停止 Adapter 时出错: {e}")
    adapters.clear()

    # 清理所有编排器
    for sid, orchestrator in list(orchestrators.items()):
        try:
            orchestrator.stop()
            logger.debug(f"[{sid}] 编排器已停止")
        except Exception as e:
            logger.error(f"[{sid}] 停止编排器时出错: {e}")
    orchestrators.clear()

    # 清理所有会话上下文
    for sid, ctx in list(session_contexts.items()):
        try:
            await ctx.close()
            logger.debug(f"[{sid}] 上下文已关闭")
        except Exception as e:
            logger.error(f"[{sid}] 关闭上下文时出错: {e}")
    session_contexts.clear()

    logger.info("所有资源已清理完成")


def signal_handler(signum, frame):
    """信号处理器"""
    signal_name = signal.Signals(signum).name
    logger.info(f"收到信号 {signal_name}，准备优雅关闭...")
    # uvicorn 会处理优雅关闭
    import sys
    sys.exit(0)


def setup_signal_handlers():
    """设置信号处理器"""
    # Windows 和 Unix 都支持的信号
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # taskkill (无 /F)
    
    # Windows 特有的信号
    if hasattr(signal, 'CTRL_BREAK_EVENT'):
        try:
            signal.signal(signal.CTRL_BREAK_EVENT, signal_handler)
        except (ValueError, OSError):
            pass
    
    if hasattr(signal, 'CTRL_C_EVENT'):
        try:
            signal.signal(signal.CTRL_C_EVENT, signal_handler)
        except (ValueError, OSError):
            pass
    
    logger.debug("信号处理器已设置")


# ============================================
# 启动入口
# ============================================

def init_config(config_path: str = None) -> None:
    """
    初始化全局配置
    
    Args:
        config_path: YAML 配置文件路径（可选）
    """
    global global_config
    
    if config_path:
        global_config = AppConfig.from_yaml(config_path)
    else:
        # 默认从 config/config.yaml 加载
        global_config = AppConfig.load()
    
    logger.info(f"配置加载完成: {global_config.system.host}:{global_config.system.port}")


def run_server():
    """运行服务器 using uvicorn (ASGI mode)"""
    import uvicorn
    import atexit

    # 初始化配置
    init_config(None)

    # 设置信号处理器
    setup_signal_handlers()

    # 注册退出时的清理函数
    def cleanup_on_exit():
        logger.info("服务器关闭中...")
        try:
            # 在同步上下文中调用异步清理函数
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(cleanup_all_resources())
            loop.close()
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")
        logger.info("服务器已关闭")

    atexit.register(cleanup_on_exit)

    logger.info("=" * 50)
    logger.info("启动 Socket.IO 服务器...")
    logger.info(f"Host: {global_config.system.host}")
    logger.info(f"Port: {global_config.system.port}")
    logger.info(f"Socket.IO async_mode: asgi (uvicorn)")
    logger.info("=" * 50)
    logger.info(f"访问 http://{global_config.system.host}:{global_config.system.port} 测试")
    logger.info(f"WebSocket URL: ws://{global_config.system.host}:{global_config.system.port}/socket.io/")

    # Run uvicorn server
    uvicorn.run(
        "anima.socketio_server:asgi_app",
        host=global_config.system.host,
        port=global_config.system.port,
        log_level="info"
    )

if __name__ == '__main__':
    run_server()
