"""
ChatTTS 实现 - 开源对话式语音合成
模型存放在本地磁盘，启动时加载到显存
"""

from typing import Union, Optional
from pathlib import Path
import tempfile
import io
import numpy as np

from loguru import logger

from ..interface import TTSInterface
from ....config.core.registry import ProviderRegistry
from ....config.providers.tts.chattts import ChatTTSConfig


@ProviderRegistry.register_service("tts", "chattts")
class ChatTTSTTS(TTSInterface):
    """
    ChatTTS 实现
    专为对话场景设计的语音合成，支持中英文
    模型从本地磁盘加载到 GPU 显存推理
    """

    SAMPLE_RATE = 24000

    def __init__(
        self,
        model_path: str = "E:/models/ChatTTS",
        device: str = "cuda",
        compile: bool = False,
        speaker_seed: Optional[int] = 42,
        temperature: float = 0.3,
        top_p: float = 0.7,
        top_k: int = 20,
    ):
        """
        初始化 ChatTTS

        Args:
            model_path: 模型文件路径（如 E:/models/ChatTTS）
            device: 推理设备 cuda / cpu
            compile: 是否启用 torch.compile（Windows 建议 False）
            speaker_seed: 说话人音色种子，固定后声音一致
            temperature: 生成温度
            top_p: nucleus sampling
            top_k: top-k sampling
        """
        self.model_path = model_path
        self.device = device
        self.compile = compile
        self.speaker_seed = speaker_seed
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k

        self._chat = None
        self._speaker_embedding = None

    def _ensure_loaded(self):
        """懒加载：首次调用时将模型从磁盘加载到显存"""
        if self._chat is not None:
            return

        try:
            import ChatTTS
            import torch
        except ImportError as e:
            logger.error("未安装 ChatTTS，请运行: pip install ChatTTS")
            raise ImportError(
                "ChatTTS 未安装，请运行: pip install ChatTTS"
            ) from e

        logger.info(f"正在从 {self.model_path} 加载 ChatTTS 模型到 {self.device}...")

        self._chat = ChatTTS.Chat()
        self._chat.load(
            source='custom',
            custom_path=self.model_path,
            device=self.device,
            compile=self.compile,
        )

        # 固定说话人音色，确保每次生成的声音一致
        if self.speaker_seed is not None:
            import torch
            torch.manual_seed(self.speaker_seed)
            self._speaker_embedding = self._chat.sample_random_speaker()
            logger.info(f"已固定说话人音色 (seed={self.speaker_seed})")

        logger.info("ChatTTS 模型加载完成")

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        清洗文本，只保留 ChatTTS 能处理的字符
        ChatTTS 对标点非常敏感，只支持很有限的标点符号
        """
        import re

        # 移除 emoji（修复正则表达式范围错误）
        # 注意：范围必须是递增的，否则会匹配所有字符
        emoji_ranges = [
            '\U0001F600-\U0001F64F',  # Emoticons
            '\U0001F300-\U0001F5FF',  # Symbols & Pictographs
            '\U0001F680-\U0001F6FF',  # Transport & Map
            '\U0001F1E0-\U0001F1FF',  # Flags (Regional Indicator Symbols)
            '\U00002702-\U000027B0',  # Dingbats
            '\U000024C2-\U000025FF',  # Enclosed characters (修复范围)
            '\U00002300-\U000023FF',  # Miscellaneous Technical
            '\U00002B50-\U00002BFF',  # Misc Symbols and Arrows
            '\U0000FE00-\U0000FE0F',  # Variation Selectors
            '\U0001F900-\U0001F9FF',  # Supplemental Symbols and Pictographs
            '\U0001FA00-\U0001FA6F',  # Chess Symbols
            '\U0001FA70-\U0001FAFF',  # Symbols and Pictographs Extended-A
        ]
        emoji_pattern = re.compile('[' + ''.join(emoji_ranges) + ']+', flags=re.UNICODE)
        text = emoji_pattern.sub('', text)

        # 句末标点 -> 逗号
        for char in ['。', '！', '？', '!', '?', '；', ';']:
            text = text.replace(char, '，')

        # 移除所有其他标点（使用字符循环避免正则表达式编码问题）
        punctuation_to_remove = '：:「」『』""''""（）()[]【】《》~——…·•'
        for char in punctuation_to_remove:
            text = text.replace(char, '')

        # 去掉多余逗号，只修剪首尾的逗号
        while '，，' in text:
            text = text.replace('，，', '，')
        # 删除首尾的逗号（全角和半角）
        text = text.strip('，')
        text = text.strip(',')

        # 去掉多余空白
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _build_params(self):
        """构建推理参数"""
        import ChatTTS

        params = ChatTTS.Chat.InferCodeParams(
            temperature=self.temperature,
            top_P=self.top_p,
            top_K=self.top_k,
            spk_emb=self._speaker_embedding,
        )
        return params

    def _wav_to_bytes(self, wav_array: np.ndarray) -> bytes:
        """将 numpy 音频数组转为 WAV 格式字节流"""
        import struct

        # 归一化并转 int16
        if wav_array.dtype != np.int16:
            # 裁剪到 [-1, 1] 防止溢出
            wav_array = np.clip(wav_array, -1.0, 1.0)
            wav_array = (wav_array * 32767).astype(np.int16)

        # 构造 WAV 文件头
        num_samples = len(wav_array)
        data_size = num_samples * 2  # int16 = 2 bytes
        channels = 1
        sample_width = 2
        byte_rate = self.SAMPLE_RATE * channels * sample_width
        block_align = channels * sample_width

        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + data_size,
            b'WAVE',
            b'fmt ',
            16,               # fmt chunk size
            1,                # PCM format
            channels,
            self.SAMPLE_RATE,
            byte_rate,
            block_align,
            sample_width * 8, # bits per sample
            b'data',
            data_size,
        )

        return header + wav_array.tobytes()

    async def synthesize(
        self,
        text: str,
        output_path: Optional[Union[str, Path]] = None,
        voice: Optional[str] = None,
        **kwargs
    ) -> Union[bytes, str]:
        """
        将文本合成为语音

        Args:
            text: 要合成的文本
            output_path: 输出文件路径（可选）
            voice: 预留参数，ChatTTS 通过 speaker_seed 控制音色
            **kwargs: 额外参数

        Returns:
            Union[bytes, str]: 如果指定了 output_path，返回文件路径字符串
                               否则返回 WAV 音频字节数据
        """
        # 确保模型已加载
        self._ensure_loaded()

        # 清洗文本：全角标点、emoji 等 ChatTTS 不支持的字符
        cleaned_text = self._clean_text(text)
        if not cleaned_text:
            logger.warning(f"ChatTTS 文本清洗后为空，原文: {text}")
            silence = np.zeros(self.SAMPLE_RATE, dtype=np.float32)
            audio_bytes = self._wav_to_bytes(silence)
            temp_file = tempfile.mktemp(suffix=".wav")
            with open(temp_file, "wb") as f:
                f.write(audio_bytes)
            return temp_file

        logger.debug(f"ChatTTS 清洗后文本: {cleaned_text}")

        try:
            params = self._build_params()

            # ChatTTS.infer 是同步阻塞的，放到线程池避免阻塞事件循环
            import asyncio
            loop = asyncio.get_event_loop()
            wavs = await loop.run_in_executor(
                None,
                lambda: self._chat.infer(
                    [cleaned_text],
                    params_infer_code=params,
                )
            )

            # 检查返回结果是否有效
            if wavs is None or len(wavs) == 0 or wavs[0] is None:
                logger.warning("ChatTTS 返回空结果，使用静音替代")
                silence = np.zeros(self.SAMPLE_RATE, dtype=np.float32)
                audio_bytes = self._wav_to_bytes(silence)
                temp_file = tempfile.mktemp(suffix=".wav")
                with open(temp_file, "wb") as f:
                    f.write(audio_bytes)
                return temp_file

            # wavs[0] 是 numpy array
            wav_array = wavs[0]
            if wav_array.ndim > 1:
                wav_array = wav_array.flatten()

            if len(wav_array) == 0:
                logger.warning("ChatTTS 生成了空音频，使用静音替代")
                silence = np.zeros(self.SAMPLE_RATE, dtype=np.float32)
                audio_bytes = self._wav_to_bytes(silence)
                temp_file = tempfile.mktemp(suffix=".wav")
                with open(temp_file, "wb") as f:
                    f.write(audio_bytes)
                return temp_file

            audio_bytes = self._wav_to_bytes(wav_array)

            if output_path is not None:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
                logger.debug(
                    f"ChatTTS 合成完成: {len(text)} 字符 -> {output_path}"
                )
                return str(output_path)
            else:
                # 写入临时文件并返回路径（与 EdgeTTS 行为一致）
                temp_file = tempfile.mktemp(suffix=".wav")
                with open(temp_file, "wb") as f:
                    f.write(audio_bytes)
                logger.debug(
                    f"ChatTTS 合成完成: {len(text)} 字符 -> {temp_file}"
                )
                return temp_file

        except Exception as e:
            error_msg = str(e)
            if "narrow()" in error_msg:
                logger.warning(f"ChatTTS narrow() 错误（已知问题），文本: {cleaned_text}")
                silence = np.zeros(self.SAMPLE_RATE, dtype=np.float32)
                audio_bytes = self._wav_to_bytes(silence)
                if output_path is not None:
                    output_path = Path(output_path)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(audio_bytes)
                    return str(output_path)
                temp_file = tempfile.mktemp(suffix=".wav")
                with open(temp_file, "wb") as f:
                    f.write(audio_bytes)
                return temp_file
            logger.error(f"ChatTTS 合成失败: {e}")
            raise

    async def close(self) -> None:
        """释放显存资源"""
        if self._chat is not None:
            # 释放模型引用，让 GC 回收显存
            self._chat = None
            self._speaker_embedding = None

            # 主动清理 CUDA 缓存
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

            logger.info("ChatTTS 资源已释放，显存已清理")

    @classmethod
    def from_config(cls, config: ChatTTSConfig) -> "ChatTTSTTS":
        """从配置创建实例"""
        return cls(
            model_path=config.model_path,
            device=config.device,
            compile=config.compile,
            speaker_seed=config.speaker_seed,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
        )
