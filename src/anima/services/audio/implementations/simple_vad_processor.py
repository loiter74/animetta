"""
简化版 VAD 处理器 - 直接使用概率值
"""
import time
import numpy as np
from typing import List, Optional, Callable
from loguru import logger

from ....services.vad import VADInterface


class SimpleVADProcessor:
    """简化版 VAD 处理器"""
    
    def __init__(
        self,
        session_id: str,
        vad_engine: VADInterface,
        on_speech_end: Optional[Callable] = None,
        threshold: float = 0.5,
        min_speech_duration: float = 0.5,
        min_silence_duration: float = 0.8,
        sample_rate: int = 16000,
    ):
        self.session_id = session_id
        self.vad_engine = vad_engine
        self.on_speech_end = on_speech_end
        self.threshold = threshold
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration
        self.sample_rate = sample_rate
        
        # 音频缓冲
        self._audio_buffer: List[float] = []
        
        # 状态
        self._is_speech = False
        self._speech_start_time = None
        self._silence_start_time = None
        self._total_chunks = 0
        
        # 获取 Silero VAD 模型的原始概率
        self._silero_model = None
        if hasattr(vad_engine, 'model'):
            self._silero_model = vad_engine.model
    
    def _get_speech_prob(self, audio_data: List[float]) -> float:
        """获取原始语音概率"""
        if self._silero_model is None:
            return 0.0
        
        try:
            import torch
            # 转换为 tensor
            chunk_tensor = torch.from_numpy(np.array(audio_data, dtype=np.float32))
            
            # Silero VAD 模型需要 (batch, samples) 格式
            if chunk_tensor.ndim == 1:
                chunk_tensor = chunk_tensor.unsqueeze(0)
            
            with torch.no_grad():
                prob = self._silero_model(chunk_tensor, self.sample_rate).item()
            return prob
        except Exception as e:
            logger.error(f"Error getting speech prob: {e}")
            return 0.0
    
    async def process_chunk(self, audio_data: List[float]) -> None:
        """处理音频数据块"""
        if not audio_data:
            return
        
        self._total_chunks += 1
        
        # 每 500 个块输出一次
        if self._total_chunks % 500 == 0:
            logger.info(f"[{self.session_id}] Audio chunks: {self._total_chunks}")
        
        # 获取语音概率
        prob = self._get_speech_prob(audio_data)
        is_speech_frame = prob > self.threshold
        
        current_time = time.time()
        
        # 累积音频
        self._audio_buffer.extend(audio_data)
        
        if is_speech_frame:
            # 检测到语音
            if not self._is_speech:
                self._is_speech = True
                self._speech_start_time = current_time
                self._silence_start_time = None
                logger.info(f"[{self.session_id}] 🎤 Speech started")
            
            self._silence_start_time = None
        else:
            # 检测到静音
            if self._is_speech:
                if self._silence_start_time is None:
                    self._silence_start_time = current_time
                
                silence_duration = current_time - self._silence_start_time
                speech_duration = current_time - self._speech_start_time if self._speech_start_time else 0
                
                # 条件：语音足够长 + 静音足够长
                if speech_duration >= self.min_speech_duration and silence_duration >= self.min_silence_duration:
                    logger.info(
                        f"[{self.session_id}] 🎤 Speech ended: "
                        f"speech={speech_duration:.2f}s, silence={silence_duration:.2f}s, prob={prob:.3f}"
                    )
                    
                    if self.on_speech_end:
                        await self.on_speech_end(list(self._audio_buffer))
                    
                    # 重置
                    self._is_speech = False
                    self._speech_start_time = None
                    self._silence_start_time = None
                    self._audio_buffer.clear()
    
    async def process_end(self) -> None:
        """手动结束"""
        if self._is_speech and self._audio_buffer:
            logger.info(f"[{self.session_id}] 手动结束语音输入")
            
            if self.on_speech_end:
                await self.on_speech_end(list(self._audio_buffer))
            
            self._is_speech = False
            self._audio_buffer.clear()
    
    def reset(self) -> None:
        """重置"""
        self._audio_buffer.clear()
        self._is_speech = False
        self._speech_start_time = None
        self._silence_start_time = None
