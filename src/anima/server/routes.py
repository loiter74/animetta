"""
WebSocket 路由定义
定义所有 Socket.IO 事件处理器
"""

import json
import numpy as np
from loguru import logger
from typing import Dict, Any, Optional


class AudioBufferManager:
    """音频缓冲区管理器"""

    def __init__(self):
        self.buffers: Dict[str, list] = {}

    def append(self, sid: str, audio_data) -> int:
        """追加音频数据"""
        if sid not in self.buffers:
            self.buffers[sid] = []

        if isinstance(audio_data, list):
            self.buffers[sid].extend(audio_data)
        else:
            self.buffers[sid].append(audio_data)

        return len(self.buffers[sid])

    def pop(self, sid: str) -> Optional[np.ndarray]:
        """获取并清空缓冲区"""
        if sid not in self.buffers:
            return None

        data = self.buffers.pop(sid)
        if not data:
            return None

        return np.array(data, dtype=np.float32)

    def remove(self, sid: str) -> None:
        """移除缓冲区"""
        self.buffers.pop(sid, None)


class RouteHandlers:
    """
    路由处理器集合

    包含所有 Socket.IO 事件处理逻辑
    """

    def __init__(self, sio, session_manager, audio_buffer_manager=None):
        """
        初始化路由处理器

        Args:
            sio: Socket.IO 服务器实例
            session_manager: 会话管理器
            audio_buffer_manager: 音频缓冲区管理器
        """
        self.sio = sio
        self.session_manager = session_manager
        self.audio_buffer_manager = audio_buffer_manager or AudioBufferManager()
        self.vad_active_sessions: Dict[str, dict] = {}
        self.vad_timeout_seconds = 15

    async def on_connect(self, sid, environ):
        """客户端连接事件"""
        logger.info(f"客户端已连接: {sid}")

        await self.sio.emit('connection-established', {
            'message': '连接成功',
            'sid': sid
        }, to=sid)

        await self.sio.emit('control', {
            'type': 'control',
            'text': 'start-mic'
        }, to=sid)

    async def on_disconnect(self, sid):
        """客户端断开事件"""
        logger.info(f"客户端已断开: {sid}")
        await self.session_manager.cleanup_session(sid)
        self.audio_buffer_manager.remove(sid)

    async def on_text_input(self, sid, data):
        """处理文本输入"""
        text = data.get('text', '')
        logger.info(f"[{sid}] 收到文本输入: {text}")

        if not text:
            return

        try:
            # 获取配置和上下文
            from anima.config import AppConfig
            config = AppConfig.load()

            ctx = await self.session_manager.get_or_create_context(
                sid,
                config,
                self._make_send_callback(sid)
            )

            from anima.config.live2d import get_live2d_config
            live2d_config = get_live2d_config()

            orchestrator = await self.session_manager.get_or_create_orchestrator(
                sid,
                ctx,
                self._make_send_callback(sid),
                live2d_config
            )

            result = await orchestrator.process_input(
                raw_input=text,
                metadata=data.get('metadata', {}),
                from_name=data.get('from_name', 'User'),
            )

            if result.error:
                logger.error(f"[{sid}] 处理出错: {result.error}")
                await self.sio.emit('error', {
                    'type': 'error',
                    'message': result.error
                }, to=sid)

        except Exception as e:
            logger.error(f"[{sid}] 处理文本输入时出错: {e}")
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e)
            }, to=sid)

    async def on_mic_audio_data(self, sid, data):
        """处理音频数据流"""
        audio = data.get('audio', [])
        if audio:
            sample_count = self.audio_buffer_manager.append(sid, audio)
            logger.debug(f"[{sid}] 累积音频: {len(audio)} 个采样点, 总计: {sample_count}")

    async def on_raw_audio_data(self, sid, data):
        """处理原始音频数据用于 VAD 检测"""
        audio_chunk = data.get('audio', [])
        if not audio_chunk:
            return

        # 静态计数器
        if not hasattr(self, '_audio_counter'):
            self._audio_counter = {}
        if sid not in self._audio_counter:
            self._audio_counter[sid] = 0
        self._audio_counter[sid] += 1

        count = self._audio_counter[sid]

        try:
            from anima.config import AppConfig
            config = AppConfig.load()
            ctx = await self.session_manager.get_or_create_context(
                sid,
                config,
                self._make_send_callback(sid)
            )

            if ctx.vad_engine is None:
                self.audio_buffer_manager.append(sid, audio_chunk)
                return

            result = ctx.vad_engine.detect_speech(audio_chunk)

            # 超时保护
            import time
            current_time = time.time()

            if result.state.value == 'ACTIVE':
                if sid not in self.vad_active_sessions:
                    self.vad_active_sessions[sid] = {'active_time': current_time, 'chunk_count': 0}
                self.vad_active_sessions[sid]['chunk_count'] += 1

                active_duration = current_time - self.vad_active_sessions[sid]['active_time']
                if active_duration > self.vad_timeout_seconds:
                    logger.warning(f"[{sid}] VAD 持续活跃超过 {self.vad_timeout_seconds} 秒，强制触发语音结束")
                    await self._force_process_audio(sid, ctx)

            elif result.state.value == 'IDLE' and sid in self.vad_active_sessions:
                del self.vad_active_sessions[sid]

            if result.is_speech_start:
                logger.info(f"[{sid}] VAD 检测到语音开始")
                orchestrator = self.session_manager.get_orchestrator(sid)
                if orchestrator and orchestrator.is_processing:
                    logger.info(f"[{sid}] 检测到新语音，自动打断当前回复")
                    orchestrator.interrupt()
                    await self.sio.emit('control', {
                        'type': 'control',
                        'text': 'interrupt'
                    }, to=sid)

            elif result.is_speech_end and len(result.audio_data) > 1024:
                logger.info(f"[{sid}] VAD 检测到语音结束")

                if sid in self.vad_active_sessions:
                    del self.vad_active_sessions[sid]

                audio_data = np.frombuffer(result.audio_data, dtype=np.int16).astype(np.float32) / 32767.0
                self.audio_buffer_manager.append(sid, audio_data.tolist())

                await self.sio.emit('control', {
                    'type': 'control',
                    'text': 'mic-audio-end'
                }, to=sid)

                await self._process_audio_input(sid)

        except Exception as e:
            logger.error(f"[{sid}] VAD 处理出错: {e}")

    async def on_mic_audio_end(self, sid, data):
        """音频输入结束事件"""
        logger.info(f"[{sid}] 音频输入结束")
        await self._process_audio_input(sid)

    async def on_interrupt_signal(self, sid, data):
        """打断信号"""
        heard_response = data.get('text', '')
        logger.info(f"[{sid}] 收到打断信号")

        orchestrator = self.session_manager.get_orchestrator(sid)
        if orchestrator:
            orchestrator.interrupt()

        ctx = self.session_manager.get_context(sid)
        if ctx:
            ctx.is_speaking = False

        await self.sio.emit('control', {
            'type': 'control',
            'text': 'interrupted'
        }, to=sid)

    async def on_heartbeat(self, sid, data):
        """心跳检测"""
        await self.sio.emit('heartbeat-ack', {}, to=sid)

    async def on_clear_history(self, sid, data):
        """清空对话历史"""
        logger.info(f"[{sid}] 清空对话历史")

        ctx = self.session_manager.get_context(sid)
        if ctx and ctx.llm_engine:
            ctx.llm_engine.clear_history()
            logger.info(f"[{sid}] 对话历史已清空")

            await self.sio.emit('history-cleared', {
                'type': 'history-cleared'
            }, to=sid)

    async def on_set_log_level(self, sid, data):
        """设置日志级别"""
        from anima.utils.logger_manager import logger_manager
        from anima.config.user_settings import UserSettings
        from pathlib import Path

        level = data.get('level', 'INFO').upper()
        logger.info(f"[{sid}] 请求设置日志级别为: {level}")

        success = logger_manager.set_level(level)

        if success:
            user_settings = UserSettings(Path(__file__).parent.parent.parent.parent.parent)
            user_settings.set_log_level(level)

        await self.sio.emit('log_level_changed', {
            'type': 'log_level_changed',
            'success': success,
            'level': logger_manager.get_level(),
            'message': f'日志级别已设置为 {logger_manager.get_level()}' if success else '设置失败'
        }, to=sid)

    def _make_send_callback(self, sid):
        """创建 WebSocket 发送回调"""
        async def send_text_callback(message: str):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            await self.sio.emit(data.get('type', 'message'), data, to=sid)
        return send_text_callback

    async def _process_audio_input(self, sid):
        """处理音频输入"""
        try:
            audio_data = self.audio_buffer_manager.pop(sid)

            if audio_data is None or len(audio_data) == 0:
                await self.sio.emit('control', {
                    'type': 'control',
                    'text': 'no-audio-data'
                }, to=sid)
                return

            audio_duration = len(audio_data) / 16000
            logger.info(f"[{sid}] 开始处理音频，时长: {audio_duration:.2f}秒")

            await self.sio.emit('control', {
                'type': 'control',
                'text': 'conversation-start'
            }, to=sid)

            from anima.config import AppConfig
            from anima.config.live2d import get_live2d_config

            config = AppConfig.load()
            ctx = await self.session_manager.get_or_create_context(
                sid,
                config,
                self._make_send_callback(sid)
            )

            live2d_config = get_live2d_config()
            orchestrator = await self.session_manager.get_or_create_orchestrator(
                sid,
                ctx,
                self._make_send_callback(sid),
                live2d_config
            )

            result = await orchestrator.process_input(
                raw_input=audio_data,
                metadata={},
                from_name='User',
            )

            if result.error:
                logger.error(f"[{sid}] 处理出错: {result.error}")
                await self.sio.emit('error', {
                    'type': 'error',
                    'message': result.error
                }, to=sid)

            await self.sio.emit('control', {
                'type': 'control',
                'text': 'conversation-end'
            }, to=sid)

        except Exception as e:
            logger.error(f"[{sid}] _process_audio_input 出错: {e}")
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e)
            }, to=sid)

    async def _force_process_audio(self, sid, ctx):
        """强制处理音频（超时时）"""
        if hasattr(ctx.vad_engine, 'state_machine') and ctx.vad_engine.state_machine.bytes:
            audio_data_bytes = bytes(ctx.vad_engine.state_machine.bytes)

            if len(audio_data_bytes) > 1024:
                logger.info(f"[{sid}] 超时强制触发ASR，音频长度: {len(audio_data_bytes)} 字节")

                audio_float = np.frombuffer(audio_data_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                self.audio_buffer_manager.append(sid, audio_float.tolist())

                ctx.vad_engine.reset()

                await self.sio.emit('control', {
                    'type': 'control',
                    'text': 'mic-audio-end'
                }, to=sid)

                await self._process_audio_input(sid)


def register_routes(sio, session_manager):
    """
    注册所有路由到 Socket.IO 服务器

    Args:
        sio: Socket.IO 服务器实例
        session_manager: 会话管理器

    Returns:
        RouteHandlers: 路由处理器实例
    """
    handlers = RouteHandlers(sio, session_manager)

    sio.on('connect', handlers.on_connect)
    sio.on('disconnect', handlers.on_disconnect)
    sio.on('text_input', handlers.on_text_input)
    sio.on('mic_audio_data', handlers.on_mic_audio_data)
    sio.on('raw_audio_data', handlers.on_raw_audio_data)
    sio.on('mic_audio_end', handlers.on_mic_audio_end)
    sio.on('interrupt_signal', handlers.on_interrupt_signal)
    sio.on('heartbeat', handlers.on_heartbeat)
    sio.on('clear_history', handlers.on_clear_history)
    sio.on('set_log_level', handlers.on_set_log_level)

    return handlers
