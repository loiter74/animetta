"""
VibeVoice TTS 实现 - Microsoft 开源长文本多说话人语音合成

双模架构:
- Remote 模式: 通过 httpx 调用本地 VibeVoice HTTP 推理服务 (推荐)
- Local 模式: 通过 subprocess 调用本地模型推理 (备选)

本地 RTX 5090D 建议用 Remote 模式 + 常驻 FastAPI 推理服务。
"""

from typing import Union, Optional, AsyncGenerator
from pathlib import Path
import os
import tempfile
import asyncio
from io import BytesIO

from loguru import logger

from .interface import TTSInterface
from anima.config.core.registry import ProviderRegistry
from anima.config.providers.tts.vibe_voice import VibeVoiceTTSConfig


@ProviderRegistry.register_service("tts", "vibe_voice")
class VibeVoiceTTS(TTSInterface):
    """
    VibeVoice TTS 实现

    支持 remote（HTTP API）和 local（subprocess 推理）两种部署模式。
    遵循 GLM TTS 的远程 API 调用模式，并扩展了本地推理支持。

    Remote 模式:
        通过 httpx.AsyncClient POST 到 {base_url}/tts
        请求体: {"text": str, "voice": str, "language": str, "num_speakers": int}
        响应: audio/wav bytes

    Local 模式:
        通过 asyncio.create_subprocess_exec 调 vibe_infer.py
        临时文件传递输出音频
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "vibe-voice-1.5b",
        voice: str = "default",
        base_url: str = "http://localhost:8765",
        mode: str = "remote",
        model_size: str = "1.5b",
        model_path: Optional[str] = None,
        device: str = "cuda:0",
        num_speakers: int = 1,
        language: str = "zh",
    ):
        """
        初始化 VibeVoice TTS

        Args:
            api_key: API Key（remote 模式需要）
            model: 模型名称标识
            voice: 默认音色
            base_url: 推理服务地址（remote 模式）
            mode: 部署模式 "remote" / "local"
            model_size: 模型大小 "1.5b" / "7b"（local 模式）
            model_path: 模型权重路径（local 模式，默认 HuggingFace）
            device: 推理设备（local 模式）
            num_speakers: 说话人数 1-4
            language: 语言
        """
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.base_url = base_url.rstrip("/")
        self.mode = mode
        self.model_size = model_size
        self.model_path = model_path
        self.device = device
        self.num_speakers = num_speakers
        self.language = language
        self._client = None

    def _get_client(self):
        """懒加载 HTTP 客户端（remote 模式使用）"""
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=180.0,  # 长文本合成可能较久
                    headers={
                        "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                        "Content-Type": "application/json",
                    },
                )
                logger.info(
                    f"VibeVoice HTTP 客户端初始化 (base_url={self.base_url})"
                )
            except ImportError as e:
                logger.error("未安装 httpx，请运行: pip install httpx")
                raise ImportError("httpx 未安装，请运行: pip install httpx") from e
        return self._client

    @classmethod
    def from_config(cls, config: VibeVoiceTTSConfig, **kwargs) -> "VibeVoiceTTS":
        """从配置对象创建实例（支持 ProviderRegistry.create_service 路径）"""
        return cls(
            api_key=config.api_key,
            model=getattr(config, "model", "vibe-voice-1.5b"),
            voice=config.voice,
            base_url=getattr(config, "base_url", "http://localhost:8765"),
            mode=config.mode,
            model_size=config.model_size,
            model_path=config.model_path,
            device=config.device,
            num_speakers=config.num_speakers,
            language=config.language,
        )

    async def synthesize(
        self,
        text: str,
        output_path: Optional[Union[str, Path]] = None,
        voice: Optional[str] = None,
        **kwargs,
    ) -> Union[bytes, str]:
        """
        将文本合成为语音

        Args:
            text: 要合成的文本
            output_path: 输出文件路径（可选）
            voice: 音色（可选，覆盖默认值）
            **kwargs: 额外参数（可覆盖 num_speakers, language 等）

        Returns:
            Union[bytes, str]: 如果指定了 output_path，返回文件路径字符串
                               否则返回音频字节数据
        """
        if not text or not text.strip():
            logger.warning("VibeVoice TTS 收到空文本，跳过合成")
            return b"" if output_path is None else str(output_path)

        logger.debug(
            f"VibeVoice TTS 合成: text_len={len(text)}, "
            f"mode={self.mode}, voice={voice or self.voice}"
        )

        try:
            if self.mode == "remote":
                return await self._synthesize_remote(
                    text=text,
                    output_path=output_path,
                    voice=voice or self.voice,
                    num_speakers=kwargs.get("num_speakers", self.num_speakers),
                    language=kwargs.get("language", self.language),
                )
            else:
                return await self._synthesize_local(
                    text=text,
                    output_path=output_path,
                    voice=voice or self.voice,
                )
        except Exception as e:
            logger.error(f"VibeVoice TTS 合成失败: {e}")
            raise

    async def _synthesize_remote(
        self,
        text: str,
        output_path: Optional[Union[str, Path]],
        voice: str,
        num_speakers: int,
        language: str,
    ) -> Union[bytes, str]:
        """通过 HTTP API 合成语音"""
        import httpx

        client = self._get_client()

        payload = {
            "text": text,
            "voice": voice,
            "language": language,
            "num_speakers": num_speakers,
        }

        try:
            response = await client.post("/tts", json=payload)
            response.raise_for_status()

            audio_data = response.content

            if not audio_data:
                raise RuntimeError("VibeVoice 服务返回空音频数据")

            logger.debug(
                f"VibeVoice remote 合成成功: {len(audio_data)} bytes, "
                f"voice={voice}, speakers={num_speakers}"
            )

            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                logger.info(f"VibeVoice 音频已保存到: {output_path}")
                return str(output_path)
            return audio_data

        except httpx.ConnectError as e:
            raise ConnectionError(
                f"无法连接到 VibeVoice 服务 ({self.base_url})。"
                f"请确保推理服务已启动。"
            ) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"VibeVoice 服务返回错误: {e.response.status_code} "
                f"{e.response.text}"
            ) from e

    async def _synthesize_local(
        self,
        text: str,
        output_path: Optional[Union[str, Path]],
        voice: str,
    ) -> Union[bytes, str]:
        """通过 subprocess 本地推理合成语音"""
        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_file = Path(tempfile.mktemp(suffix=".wav"))

        # 构建推理命令
        infer_script = self._find_infer_script()
        cmd = [
            "python", infer_script,
            "--text", text,
            "--output", str(out_file),
            "--device", self.device,
        ]
        if self.model_path:
            cmd.extend(["--model", self.model_path])
        if self.model_size:
            cmd.extend(["--model-size", self.model_size])

        logger.debug(f"VibeVoice local 推理: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "未知错误"
                raise RuntimeError(
                    f"VibeVoice 本地推理失败 (exit={process.returncode}): {error_msg}"
                )

            if not out_file.exists() or out_file.stat().st_size == 0:
                raise RuntimeError("VibeVoice 本地推理未生成音频文件")

            logger.debug(
                f"VibeVoice local 合成成功: {out_file.stat().st_size} bytes"
            )

            if output_path:
                return str(out_file)
            else:
                audio_data = out_file.read_bytes()
                out_file.unlink(missing_ok=True)  # 清理临时文件
                return audio_data

        except FileNotFoundError as e:
            raise RuntimeError(
                f"找不到 VibeVoice 推理脚本。请确保模型已下载并配置 model_path。"
            ) from e

    def _find_infer_script(self) -> str:
        """查找 VibeVoice 推理脚本路径"""
        candidates = [
            os.path.expanduser("~/VibeVoice/demo/tts_1p5b_inference.py"),
            os.path.expanduser("~/VibeVoice/demo/vibevoice_realtime_demo.py"),
        ]
        if self.model_path:
            parents = Path(self.model_path).parents
            for p in parents:
                demo_dir = p / "demo"
                if (demo_dir / "tts_1p5b_inference.py").exists():
                    return str(demo_dir / "tts_1p5b_inference.py")

        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate

        # 默认返回，让调用方处理 FileNotFoundError
        return "vibe_infer.py"

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[bytes, None]:
        """
        流式合成语音（Remote 模式支持流式响应）

        Yields:
            bytes: 音频数据块
        """
        import httpx

        if self.mode != "remote":
            # Local 模式不支持流式，fallback 到完整合成
            audio = await self._synthesize_local(
                text=text,
                output_path=None,
                voice=voice or self.voice,
            )
            yield audio
            return

        client = self._get_client()
        payload = {
            "text": text,
            "voice": voice or self.voice,
            "language": kwargs.get("language", self.language),
            "num_speakers": kwargs.get("num_speakers", self.num_speakers),
            "stream": True,
        }

        try:
            async with client.stream("POST", "/tts/stream", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
        except Exception as e:
            logger.error(f"VibeVoice 流式合成失败: {e}")
            raise

    async def close(self) -> None:
        """清理资源"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("VibeVoice HTTP 客户端已关闭")
