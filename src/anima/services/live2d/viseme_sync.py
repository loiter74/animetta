"""
Viseme Lip Sync Engine
基于 Viseme 的口型同步引擎，移植自 open-yachiyo

使用频谱分析推断 viseme 权重，实现更自然的口型同步
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class VisemeConfig:
    """Viseme 配置"""
    # 频带配置 (Hz)
    bands: Dict[str, Tuple[int, int]] = None

    # Viseme 权重配置
    weights: Dict[str, List[float]] = None

    # 平滑配置
    attack: float = 0.02  # 攻击时间 (秒)
    release: float = 0.1  # 释放时间 (秒)
    smoothing: float = 0.3  # 平滑系数

    def __post_init__(self):
        if self.bands is None:
            self.bands = {
                'low': (120, 360),      # 低频
                'lowMid': (360, 900),   # 中低频
                'mid': (900, 1800),     # 中频
                'highMid': (1800, 3200), # 中高频
                'high': (3200, 5200)    # 高频
            }

        if self.weights is None:
            # 5 个 visemes: a, i, u, e, o
            # 每个权重对应一个频带
            self.weights = {
                'a': [0.5, 0.3, 0.1, 0.0, 0.0],
                'i': [0.1, 0.3, 0.4, 0.2, 0.0],
                'u': [0.2, 0.1, 0.3, 0.3, 0.1],
                'e': [0.1, 0.2, 0.4, 0.2, 0.1],
                'o': [0.3, 0.1, 0.2, 0.2, 0.2]
            }


class VisemeLipSync:
    """
    Viseme 口型同步引擎

    功能：
    1. 音频频谱分析
    2. Viseme 权重推断
    3. 平滑过渡处理
    4. 输出 Live2D 口型参数
    """

    def __init__(self, config: VisemeConfig = None, sample_rate: int = 24000):
        self.config = config or VisemeConfig()
        self.sample_rate = sample_rate

        # 状态
        self._current_weights: np.ndarray = np.zeros(5)
        self._target_weights: np.ndarray = np.zeros(5)

        # 窗口大小
        self.window_size = 1024

    def extract_band_energy(
        self,
        frequency_buffer: np.ndarray,
        sample_rate: int,
        min_freq: int,
        max_freq: int
    ) -> float:
        """
        提取指定频带的能量

        Args:
            frequency_buffer: 频率数据
            sample_rate: 采样率
            min_freq: 最小频率
            max_freq: 最大频率

        Returns:
            频带能量
        """
        # 计算频率索引
        min_idx = int(min_freq * len(frequency_buffer) / (sample_rate / 2))
        max_idx = int(max_freq * len(frequency_buffer) / (sample_rate / 2))

        # 边界检查
        min_idx = max(0, min_idx)
        max_idx = min(len(frequency_buffer), max_idx)

        # 计算能量
        if max_idx > min_idx:
            band_energy = np.mean(np.abs(frequency_buffer[min_idx:max_idx]))
        else:
            band_energy = 0.0

        return float(band_energy)

    def extract_viseme_features(
        self,
        audio_data: np.ndarray,
        voice_energy: float
    ) -> List[float]:
        """
        提取 Viseme 特征

        Args:
            audio_data: 音频数据
            voice_energy: 语音能量

        Returns:
            频带能量列表 [low, lowMid, mid, highMid, high]
        """
        # FFT
        if len(audio_data) < self.window_size:
            # 填充到窗口大小
            padded = np.zeros(self.window_size)
            padded[:len(audio_data)] = audio_data
            audio_data = padded

        # 应用窗函数
        window = np.hanning(len(audio_data))
        windowed = audio_data * window

        # FFT
        fft_result = np.fft.rfft(windowed)
        magnitude = np.abs(fft_result)

        # 提取各频带能量
        features = []
        for band_name in ['low', 'lowMid', 'mid', 'highMid', 'high']:
            min_freq, max_freq = self.config.bands[band_name]
            energy = self.extract_band_energy(
                magnitude,
                self.sample_rate,
                min_freq,
                max_freq
            )
            features.append(energy)

        return features

    def infer_viseme_weights(self, features: List[float]) -> np.ndarray:
        """
        推断 Viseme 权重

        Args:
            features: 频带特征

        Returns:
            Viseme 权重 [a, i, u, e, o]
        """
        features_array = np.array(features)

        # 归一化
        total = np.sum(features_array)
        if total > 0:
            normalized = features_array / total
        else:
            normalized = np.zeros_like(features_array)

        # 计算每个 viseme 的权重
        weights = []
        for viseme in ['a', 'i', 'u', 'e', 'o']:
            viseme_weight = np.dot(normalized, self.config.weights[viseme])
            weights.append(viseme_weight)

        return np.array(weights)

    def apply_smoothing(self, target_weights: np.ndarray) -> np.ndarray:
        """
        应用平滑过渡

        Args:
            target_weights: 目标权重

        Returns:
            平滑后的权重
        """
        # 计算平滑系数
        alpha = self.config.smoothing

        # 应用指数平滑
        smoothed = alpha * target_weights + (1 - alpha) * self._current_weights

        self._current_weights = smoothed
        return smoothed

    def process_audio(
        self,
        audio_data: np.ndarray,
        voice_energy: float = 1.0
    ) -> Dict[str, float]:
        """
        处理音频并返回口型参数

        Args:
            audio_data: 音频数据
            voice_energy: 语音能量 (0-1)

        Returns:
            口型参数字典
        """
        # 提取特征
        features = self.extract_viseme_features(audio_data, voice_energy)

        # 推断 viseme 权重
        target_weights = self.infer_viseme_weights(features)

        # 应用平滑
        smoothed_weights = self.apply_smoothing(target_weights)

        # 转换为 Live2D 参数
        return self._weights_to_params(smoothed_weights, voice_energy)

    def _weights_to_params(
        self,
        weights: np.ndarray,
        voice_energy: float
    ) -> Dict[str, float]:
        """
        将 viseme 权重转换为 Live2D 参数

        Args:
            weights: Viseme 权重 [a, i, u, e, o]
            voice_energy: 语音能量

        Returns:
            Live2D 参数
        """
        # 计算口型开合度
        # a: 大开, i: 横开, u: 圆唇, e: 扁唇, o: 突唇

        a, i, u, e, o = weights

        # 主要参数
        mouth_open = (a * 0.8 + o * 0.4 + u * 0.2) * voice_energy
        mouth_form = (i * 0.5 + e * 0.3) * voice_energy

        return {
            'ParamMouthOpen': mouth_open,
            'ParamMouthForm': mouth_form
        }

    def reset(self):
        """重置状态"""
        self._current_weights = np.zeros(5)
        self._target_weights = np.zeros(5)


class SimpleLipSync:
    """
    简单口型同步（基于 RMS）

    作为 Viseme 模式的后备方案
    """

    def __init__(self, sensitivity: float = 2.5, smoothing: float = 0.3):
        self.sensitivity = sensitivity
        self.smoothing = smoothing
        self._current_value = 0.0

    def process_audio(self, audio_data: np.ndarray) -> float:
        """
        处理音频并返回口型开合度

        Args:
            audio_data: 音频数据

        Returns:
            口型开合度 (0-1)
        """
        # 计算 RMS
        rms = np.sqrt(np.mean(audio_data ** 2))

        # 应用灵敏度
        target_value = min(1.0, rms * self.sensitivity)

        # 平滑
        self._current_value = (
            self.smoothing * target_value +
            (1 - self.smoothing) * self._current_value
        )

        return self._current_value

    def reset(self):
        """重置状态"""
        self._current_value = 0.0


# ==================== 工厂函数 ====================

def create_lip_sync_engine(
    mode: str = "viseme",
    sample_rate: int = 24000,
    **kwargs
) -> Any:
    """
    创建口型同步引擎

    Args:
        mode: 模式 ("viseme" 或 "simple")
        sample_rate: 采样率
        **kwargs: 其他配置

    Returns:
        口型同步引擎实例
    """
    if mode == "viseme":
        config = VisemeConfig(**kwargs)
        return VisemeLipSync(config, sample_rate)
    elif mode == "simple":
        return SimpleLipSync(**kwargs)
    else:
        raise ValueError(f"未知的口型同步模式: {mode}")
