"""
Silero VAD 实现
参考 Open-LLM-VTuber 的 VADEngine 和 StateMachine 实现
"""

from collections import deque
from typing import Union
import numpy as np
from loguru import logger

from ..interface import VADInterface, VADState, VADResult
from ....config.core.registry import ProviderRegistry


@ProviderRegistry.register_service("vad", "silero")
class SileroVAD(VADInterface):
    """
    基于 Silero 的语音活动检测实现

    使用状态机检测语音的开始和结束：
    - IDLE -> ACTIVE: 检测到语音开始
    - ACTIVE -> INACTIVE: 检测到语音暂停
    - INACTIVE -> ACTIVE: 语音继续
    - INACTIVE -> IDLE: 语音完全结束，输出累积的音频
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        prob_threshold: float = 0.4,
        db_threshold: int = 60,
        required_hits: int = 3,
        required_misses: int = 24,
        smoothing_window: int = 5,
    ):
        # 保存配置参数
        self.sample_rate = sample_rate
        self.prob_threshold = prob_threshold
        self.db_threshold = db_threshold
        self.required_hits = required_hits
        self.required_misses = required_misses
        self.smoothing_window = smoothing_window

        # 窗口大小：16kHz 时为 512 采样点 (约 32ms)
        self.window_size_samples = 512 if sample_rate == 16000 else 256

        # 加载模型
        self.model = self._load_vad_model()

        # 状态机
        self.state_machine = SileroStateMachine(self)

        # 诊断日志标志（防止重复日志）
        self._vad_logged = False
        self._vad_int16_logged = False
        self._vad_normalized_logged = False

        logger.info(f"✅ Silero VAD 初始化完成")
        logger.info(f"   - 采样率: {sample_rate} Hz")
        logger.info(f"   - 概率阈值: {prob_threshold}")
        logger.info(f"   - 分贝阈值: {db_threshold}")
        logger.info(f"   - 开始命中次数: {required_hits}")
        logger.info(f"   - 结束未命中次数: {required_misses}")

    @classmethod
    def from_config(cls, config, **kwargs):
        """从配置创建实例"""
        return cls(
            sample_rate=config.sample_rate,
            prob_threshold=config.prob_threshold,
            db_threshold=config.db_threshold,
            required_hits=config.required_hits,
            required_misses=config.required_misses,
            smoothing_window=config.smoothing_window,
        )

    def _load_vad_model(self):
        """加载 Silero VAD 模型"""
        try:
            from silero_vad import load_silero_vad
            logger.info("正在加载 Silero-VAD 模型...")
            model = load_silero_vad()
            logger.info("Silero-VAD 模型加载完成")
            return model
        except ImportError:
            logger.warning("silero-vad 未安装，请运行: pip install silero-vad")
            raise
        except Exception as e:
            logger.error(f"加载 Silero-VAD 模型失败: {e}")
            raise

    def detect_speech(self, audio_data: Union[list, np.ndarray]) -> VADResult:
        """
        检测音频数据中的语音活动

        处理流程：
        1. 将音频分块（每块 512 采样点）
        2. 对每块计算语音概率
        3. 通过状态机判断语音开始/结束

        Args:
            audio_data: 音频数据（float32 列表或 numpy 数组，范围 [-1.0, 1.0] 或 int16 PCM）

        Returns:
            VADResult: 检测结果
        """
        import torch

        # 转换为 numpy 数组并智能归一化
        audio_np = np.array(audio_data, dtype=np.float32)

        # 🔥 诊断：记录原始音频数据范围（只记录第一个块，避免刷屏）
        if not hasattr(self, '_vad_logged'):
            if len(audio_np) > 0:
                orig_min = float(np.min(audio_np))
                orig_max = float(np.max(audio_np))
                orig_abs_max = float(np.max(np.abs(audio_np)))
            self._vad_logged = True
        elif len(audio_np) > 0:
            orig_min = float(np.min(audio_np))
            orig_max = float(np.max(audio_np))
            orig_abs_max = float(np.max(np.abs(audio_np)))
        else:
            orig_min = orig_max = orig_abs_max = 0.0

        # 检测是否为 int16 PCM 数据（值范围超出 [-1.0, 1.0]）
        is_int16 = False
        if len(audio_np) > 0 and np.max(np.abs(audio_np)) > 1.0:
            # int16 PCM 数据，归一化到 [-1.0, 1.0]
            if not hasattr(self, '_vad_int16_logged'):
                logger.info(f"[VAD] ✅ 检测到 int16 PCM 数据格式，将自动归一化")
                self._vad_int16_logged = True
            audio_np = audio_np / 32767.0
            is_int16 = True

        # 打印归一化后的信号幅度（只打印一次）
        if not hasattr(self, '_vad_normalized_logged'):
            norm_min = float(np.min(audio_np)) if len(audio_np) > 0 else 0
            norm_max = float(np.max(audio_np)) if len(audio_np) > 0 else 0
            norm_rms = float(np.sqrt(np.mean(audio_np**2))) if len(audio_np) > 0 else 0
            logger.info(f"[VAD] 📊 归一化后信号范围: [{norm_min:.4f}, {norm_max:.4f}], RMS: {norm_rms:.4f}")
            logger.info(f"[VAD] 💡 提示：Silero VAD 在 RMS > 0.01 时工作良好，当前 RMS: {norm_rms:.4f}")
            self._vad_normalized_logged = True

        # 🔥 关键修复：记录所有事件，返回最后一个重要事件
        # 不要在遇到第一个事件时就返回，要处理完所有块
        speech_start_event = None
        speech_end_event = None

        # 分块处理
        for i in range(0, len(audio_np), self.window_size_samples):
            chunk_np = audio_np[i: i + self.window_size_samples]

            # 🔥 修复：不要跳过不完整的块，也要处理
            if len(chunk_np) < self.window_size_samples:
                # 最后一块可能不完整，填充零
                padded_chunk = np.zeros(self.window_size_samples, dtype=np.float32)
                padded_chunk[:len(chunk_np)] = chunk_np
                chunk_np = padded_chunk

            # 转换为 torch 张量
            chunk_tensor = torch.Tensor(chunk_np)

            # 计算语音概率
            with torch.no_grad():
                speech_prob = self.model(chunk_tensor, self.sample_rate).item()

            # 通过状态机处理
            result = self.state_machine.process(speech_prob, chunk_np)

            # 记录事件，但不立即返回
            if result is not None:
                if result.is_speech_start:
                    speech_start_event = result
                elif result.is_speech_end:
                    speech_end_event = result

        # 返回优先级最高的事件：语音结束 > 语音开始 > 普通状态
        if speech_end_event is not None:
            # 只在 DEBUG 级别记录，避免刷屏
            logger.debug(f"[VAD] 语音结束，音频长度: {len(speech_end_event.audio_data)} 字节")
            return speech_end_event
        elif speech_start_event is not None:
            return speech_start_event

        # 没有特殊事件，返回当前状态
        return VADResult(
            audio_data=b"",
            is_speech_start=False,
            is_speech_end=False,
            state=self.state_machine.state
        )

    def reset(self) -> None:
        """重置状态机"""
        self.state_machine = SileroStateMachine(self)
        logger.debug("VAD 状态机已重置")

    def get_current_state(self) -> VADState:
        """获取当前状态"""
        return self.state_machine.state

    async def close(self) -> None:
        """清理资源"""
        self.reset()
        logger.info("Silero VAD 资源已释放")


class SileroStateMachine:
    """
    Silero VAD 状态机

    状态转换：
    IDLE -> ACTIVE: 连续命中 required_hits 次
    ACTIVE -> INACTIVE: 连续未命中 required_misses 次
    INACTIVE -> ACTIVE: 连续命中 required_hits 次
    INACTIVE -> IDLE: 连续未命中 required_misses 次（输出音频）
    """

    def __init__(self, vad_instance):
        self.state = VADState.IDLE
        self.vad = vad_instance  # 保存 SileroVAD 实例的引用

        # 计数器
        self.hit_count = 0
        self.miss_count = 0

        # 累积的音频数据
        self.probs = []
        self.dbs = []
        self.bytes = bytearray()

        # 平滑窗口
        self.prob_window = deque(maxlen=vad_instance.smoothing_window)
        self.db_window = deque(maxlen=vad_instance.smoothing_window)

        # 预缓冲（保存语音开始前的一些音频）
        self.pre_buffer = deque(maxlen=20)

        # 诊断计数器
        self._chunk_count = 0

        # INACTIVE 状态超时机制（秒）
        self._inactive_start_time = None
        self._inactive_timeout = 1.0  # INACTIVE 状态超过1秒就强制结束

    @staticmethod
    def calculate_db(audio_data: np.ndarray) -> float:
        """计算音频的分贝值"""
        # 避免空数组或全零数组导致的 sqrt 警告
        if audio_data is None or len(audio_data) == 0:
            return -np.inf
        mean_square = np.mean(np.square(audio_data))
        if mean_square <= 0:
            return -np.inf
        rms = np.sqrt(mean_square)
        return 20 * np.log10(rms + 1e-7)

    def get_smoothed_values(self, prob: float, db: float) -> tuple:
        """获取平滑后的概率和分贝值"""
        self.prob_window.append(prob)
        self.db_window.append(db)
        return np.mean(self.prob_window), np.mean(self.db_window)

    def update(self, chunk_bytes: bytes, prob: float, db: float) -> None:
        """更新累积数据"""
        self.probs.append(prob)
        self.dbs.append(db)
        self.bytes.extend(chunk_bytes)

    def reset_buffers(self) -> None:
        """重置缓冲区"""
        self.probs.clear()
        self.dbs.clear()
        self.bytes.clear()

    def process(self, prob: float, float_chunk_np: np.ndarray) -> Union[VADResult, None]:
        """
        处理音频块

        Args:
            prob: 语音概率
            float_chunk_np: float32 音频块

        Returns:
            VADResult 或 None（无特殊事件时）
        """
        # 转换为 int16 字节
        int_chunk_np = (float_chunk_np * 32767).astype(np.int16)
        chunk_bytes = int_chunk_np.tobytes()

        # 计算分贝值
        db = self.calculate_db(int_chunk_np)

        # 平滑处理
        smoothed_prob, smoothed_db = self.get_smoothed_values(prob, db)

        # 🔥 诊断日志：判断是否为语音
        # 只使用 prob 判断，不使用 db（因为 db 可能为 -inf）
        is_speech = smoothed_prob >= self.vad.prob_threshold
        # is_speech = (
        #     smoothed_prob >= self.vad.prob_threshold and
        #     smoothed_db >= self.vad.db_threshold
        # )

        # 每5个块打印一次诊断信息（更频繁）
        self._chunk_count += 1

        # 诊断日志：每 100 个块打印一次（约 3 秒）
        if self._chunk_count % 100 == 1:
            logger.debug(f"[VAD] #{self._chunk_count}: state={self.state.value}, prob={smoothed_prob:.3f}/{self.vad.prob_threshold:.3f}, speech={is_speech}")

        # 状态机处理
        if self.state == VADState.IDLE:
            # 空闲状态：等待语音开始
            self.pre_buffer.append(chunk_bytes)

            if is_speech:
                self.hit_count += 1
                if self.hit_count >= self.vad.required_hits:
                    # 检测到语音开始
                    self.state = VADState.ACTIVE
                    self.update(chunk_bytes, smoothed_prob, smoothed_db)
                    self.hit_count = 0
                    logger.debug(f"[VAD] 语音开始")
                    return VADResult(
                        audio_data=b"",
                        is_speech_start=True,
                        is_speech_end=False,
                        state=VADState.ACTIVE
                    )
            else:
                self.hit_count = 0

        elif self.state == VADState.ACTIVE:
            # 活跃状态：正在说话
            self.update(chunk_bytes, smoothed_prob, smoothed_db)

            if is_speech:
                self.miss_count = 0
            else:
                self.miss_count += 1
                # 注释掉频繁的DEBUG日志
                # if self._chunk_count % 100 == 1 or self.miss_count % 10 == 1:
                #     logger.debug(f"[VAD State Machine] ACTIVE: miss_count={self.miss_count}/{self.vad.required_misses}")
                if self.miss_count >= self.vad.required_misses:
                    # 检测到语音暂停
                    self.state = VADState.INACTIVE
                    self.miss_count = 0
                    self._inactive_start_time = None  # 重置超时计时
                    logger.debug(f"[VAD] 语音暂停 (ACTIVE→INACTIVE)")

        elif self.state == VADState.INACTIVE:
            # 暂停状态：等待语音继续或结束
            self.update(chunk_bytes, smoothed_prob, smoothed_db)

            # 🔥 超时检查：如果 INACTIVE 状态持续超过超时时间，强制结束
            import time
            if self._inactive_start_time is None:
                self._inactive_start_time = time.time()

            inactive_duration = time.time() - self._inactive_start_time
            if inactive_duration > self._inactive_timeout:
                # 超时强制结束
                logger.debug(f"[VAD] INACTIVE 超时 ({inactive_duration:.2f}s)，强制结束")
                self.state = VADState.IDLE
                self._inactive_start_time = None
                self.miss_count = 0

                # 合并预缓冲和主缓冲区的音频
                pre_bytes = b"".join(self.pre_buffer)
                audio_data = pre_bytes + bytes(self.bytes)

                self.reset_buffers()
                self.pre_buffer.clear()

                # 检查音频长度是否足够（至少0.5秒，约8000字节）
                if len(audio_data) > 8000:
                    logger.debug(f"[VAD] 语音结束 (超时), 音频: {len(audio_data)} 字节")
                    return VADResult(
                        audio_data=audio_data,
                        is_speech_start=False,
                        is_speech_end=True,
                        state=VADState.IDLE
                    )
                else:
                    logger.debug(f"[VAD] 音频太短 ({len(audio_data)} 字节)，丢弃")
                    return None

            if is_speech:
                self.hit_count += 1
                if self.hit_count >= self.vad.required_hits:
                    # 语音继续
                    self.state = VADState.ACTIVE
                    self.hit_count = 0
                    self.miss_count = 0
                    self._inactive_start_time = None
                    logger.debug(f"[VAD] 语音继续 (INACTIVE→ACTIVE)")
            else:
                self.hit_count = 0
                self.miss_count += 1
                # 注释掉频繁的DEBUG日志
                # if self._chunk_count % 100 == 1 or self.miss_count % 10 == 1:
                #     logger.debug(f"[VAD State Machine] INACTIVE: miss_count={self.miss_count}/{self.vad.required_misses}, duration={inactive_duration:.2f}s")
                if self.miss_count >= self.vad.required_misses:
                    # 语音完全结束
                    self.state = VADState.IDLE
                    self.miss_count = 0
                    self._inactive_start_time = None

                    # 合并预缓冲和主缓冲区的音频
                    pre_bytes = b"".join(self.pre_buffer)
                    audio_data = pre_bytes + bytes(self.bytes)

                    self.reset_buffers()
                    self.pre_buffer.clear()

                    # 检查音频长度是否足够（至少0.5秒，约8000字节）
                    if len(audio_data) > 8000:
                        logger.debug(f"[VAD] 语音结束 (INACTIVE→IDLE), 音频: {len(audio_data)} 字节")
                        return VADResult(
                            audio_data=audio_data,
                            is_speech_start=False,
                            is_speech_end=True,
                            state=VADState.IDLE
                        )
                    else:
                        logger.debug(f"[VAD] 音频太短 ({len(audio_data)} 字节)，丢弃")

        return None
