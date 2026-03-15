"""
FunASR Paraformer ASR 实现 - 阿里开源语音识别
GitHub: https://github.com/modelscope/FunASR

特点：
- 中文识别准确率比 Whisper 更高
- 支持实时流式识别
- 可选配 VAD、标点恢复、说话人分离
- 支持热词功能

常用模型：
- paraformer-zh: 中文离线语音识别（推荐）
- paraformer-zh-streaming: 中文流式语音识别
- paraformer-en: 英文语音识别
"""

from typing import Union, Optional, List
from pathlib import Path
import numpy as np
from loguru import logger

from ..interface import ASRInterface
from ....config.core.registry import ProviderRegistry


@ProviderRegistry.register_service("asr", "funasr")
class FunASRASR(ASRInterface):
    """
    FunASR Paraformer ASR 实现
    使用阿里开源的 Paraformer 模型，中文识别效果优于 Whisper
    """

    # 支持的模型列表
    MODELS = {
        "paraformer-zh": "中文离线语音识别（推荐）",
        "paraformer-zh-streaming": "中文流式语音识别",
        "paraformer-en": "英文语音识别",
        "paraformer-8k-zh": "中文 8k 采样率",
        "paraformer-large-zh": "中文大模型",
        "paraformer-large-en": "英文大模型",
    }

    def __init__(
        self,
        model: str = "paraformer-zh",
        language: str = "zh",
        device: str = "cuda",
        ncpu: int = 4,
        vad_model: Optional[str] = "fsmn-vad",
        punc_model: Optional[str] = "ct-punc",
        spk_model: Optional[str] = None,
        chunk_size: List[int] = None,
        hotword: Optional[str] = None,
        model_hub: str = "ms",
        disable_update: bool = True,
    ):
        """
        初始化 FunASR Paraformer ASR

        Args:
            model: 模型名称（默认 paraformer-zh）
            language: 语言代码（zh=中文, en=英文）
            device: 运行设备（cpu/cuda）
            ncpu: CPU 线程数
            vad_model: VAD 模型名称，None 禁用
            punc_model: 标点恢复模型名称，None 禁用
            spk_model: 说话人识别模型名称，None 禁用
            chunk_size: 流式识别块大小
            hotword: 热词文件路径或字符串
            model_hub: 模型下载源（ms=ModelScope, hf=HuggingFace）
            disable_update: 禁用模型自动更新检查
        """
        self.model_name = model
        self.language = language
        self.device = device
        self.ncpu = ncpu
        self.vad_model = vad_model
        self.punc_model = punc_model
        self.spk_model = spk_model
        self.chunk_size = chunk_size or [0, 10, 5]
        self.hotword = hotword
        self.model_hub = model_hub
        self.disable_update = disable_update
        self._model = None

        logger.info(f"FunASR Paraformer ASR 初始化配置:")
        logger.info(f"  模型: {model}")
        logger.info(f"  语言: {language}")
        logger.info(f"  设备: {device}")
        logger.info(f"  VAD 模型: {vad_model}")
        logger.info(f"  标点模型: {punc_model}")
        logger.info(f"  说话人模型: {spk_model}")

    def _get_model(self):
        """懒加载模型"""
        if self._model is None:
            try:
                from funasr import AutoModel

                # 构建模型参数
                model_kwargs = {
                    "model": self.model_name,
                    "device": self.device,
                    "ncpu": self.ncpu,
                    "model_hub": self.model_hub,
                    "disable_update": self.disable_update,
                }

                # 添加可选的辅助模型
                if self.vad_model:
                    model_kwargs["vad_model"] = self.vad_model
                if self.punc_model:
                    model_kwargs["punc_model"] = self.punc_model
                if self.spk_model:
                    model_kwargs["spk_model"] = self.spk_model

                logger.info(f"正在加载 FunASR 模型: {self.model_name}...")
                self._model = AutoModel(**model_kwargs)
                logger.info(f"✅ FunASR 模型加载完成")

            except ImportError:
                logger.error("funasr 未安装，请运行: pip install funasr modelscope")
                raise ImportError(
                    "funasr 未安装，请运行: pip install funasr modelscope"
                )
            except Exception as e:
                logger.error(f"加载 FunASR 模型失败: {e}")
                raise

        return self._model

    async def transcribe(
        self,
        audio_data: Union[bytes, str, Path, list, np.ndarray],
        **kwargs
    ) -> str:
        """
        将音频数据转录为文本

        Args:
            audio_data: 音频数据，可以是:
                - bytes: WAV/MP3 等格式的字节数据
                - str/Path: 音频文件路径
                - list/numpy array: PCM 音频数据 (float32, range [-1.0, 1.0])

        Returns:
            str: 识别出的文本
        """
        import asyncio
        import tempfile

        model = self._get_model()

        # FunASR 需要文件路径作为输入
        if isinstance(audio_data, np.ndarray):
            # 将 numpy 数组写入临时 WAV 文件
            audio_path = await self._save_temp_wav(audio_data)
        elif isinstance(audio_data, list):
            audio_np = np.array(audio_data, dtype=np.float32)
            audio_path = await self._save_temp_wav(audio_np)
        elif isinstance(audio_data, (str, Path)):
            audio_path = str(audio_data)
        elif isinstance(audio_data, bytes):
            # 从 bytes 保存临时文件
            audio_path = await self._save_bytes_to_temp(audio_data)
        else:
            raise ValueError(f"不支持的音频数据类型: {type(audio_data)}")

        logger.debug(f"FunASR 处理音频: {audio_path}")

        # 在线程池中运行转录（CPU/GPU 密集型操作）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._transcribe_sync,
            audio_path
        )

        logger.info(f"FunASR 识别结果: {result}")
        return result

    def _transcribe_sync(self, audio_path: str) -> str:
        """同步转录方法"""
        model = self._get_model()

        # 构建生成参数
        gen_kwargs = {}
        if self.hotword:
            gen_kwargs["hotword"] = self.hotword

        # 执行转录
        result = model.generate(input=audio_path, **gen_kwargs)

        # 提取文本
        if not result:
            return ""

        # result 是一个列表，每个元素对应一个输入
        first_result = result[0]
        if isinstance(first_result, dict):
            text = first_result.get("text", "")
        else:
            text = str(first_result)

        return text.strip()

    async def _save_temp_wav(self, audio_np: np.ndarray) -> str:
        """将 numpy 数组保存为临时 WAV 文件"""
        import wave
        import tempfile

        # 确保是 float32 格式
        if audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)

        # 限制范围到 [-1.0, 1.0]
        audio_np = np.clip(audio_np, -1.0, 1.0)

        # 转换为 16-bit PCM
        audio_int16 = (audio_np * 32767).astype(np.int16)

        # 写入临时 WAV 文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        with wave.open(tmp_path, 'wb') as wf:
            wf.setnchannels(1)  # 单声道
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(16000)  # 16kHz
            wf.writeframes(audio_int16.tobytes())

        logger.debug(f"保存临时 WAV 文件: {tmp_path}")
        return tmp_path

    async def _save_bytes_to_temp(self, audio_bytes: bytes) -> str:
        """将字节保存为临时文件"""
        import tempfile

        # 尝试判断格式
        suffix = ".wav"
        if audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
            suffix = ".mp3"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            return tmp_file.name

    async def transcribe_stream(
        self,
        audio_data: Union[bytes, str, Path, list, np.ndarray],
        **kwargs
    ):
        """
        流式识别音频，生成器返回文本块

        Args:
            audio_data: 音频数据

        Yields:
            str: 识别的文本块
        """
        # 对于流式模型，可以使用 chunk 模式
        result = await self.transcribe(audio_data, **kwargs)

        # 按句子分割返回
        import re
        sentences = re.split(r'[。！？.!?]', result)

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                yield sentence

    async def close(self) -> None:
        """清理资源"""
        self._model = None
        logger.debug("FunASR ASR 资源已释放")

    @classmethod
    def from_config(cls, config, **kwargs):
        """从配置创建实例"""
        return cls(
            model=config.get("model", "paraformer-zh"),
            language=config.get("language", "zh"),
            device=config.get("device", "cuda"),
            ncpu=config.get("ncpu", 4),
            vad_model=config.get("vad_model", "fsmn-vad"),
            punc_model=config.get("punc_model", "ct-punc"),
            spk_model=config.get("spk_model"),
            chunk_size=config.get("chunk_size", [0, 10, 5]),
            hotword=config.get("hotword"),
            model_hub=config.get("model_hub", "ms"),
            disable_update=config.get("disable_update", True),
        )

    async def preload(self) -> None:
        """
        预加载模型（启动时调用，避免首次使用时延迟）
        """
        import asyncio

        logger.info(f"FunASR 预加载模型: {self.model_name}...")

        # 在线程池中加载模型（避免阻塞）
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._get_model)

        logger.info(f"FunASR 模型预加载完成: {self.model_name}")
