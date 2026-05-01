"""
VibeVoice 1.5B TTS FastAPI Server
==================================
本地推理服务，监听 localhost:8765，暴露 POST /tts 接口。
供 Anima 的 VibeVoiceTTS (remote 模式) 调用。

用法:
    python scripts/vibe_voice_server.py --port 8765

依赖:
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
    pip install fastapi uvicorn[standard] soundfile numpy scipy

模型:
    需先下载 microsoft/VibeVoice-1.5B 到本地目录。
    huggingface-cli download microsoft/VibeVoice-1.5B --local-dir E:/anima_data/models/VibeVoice
"""

import io
import wave
import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 全局对象（服务启动时加载）
# ---------------------------------------------------------------------------
model = None
processor = None
device = "cuda"
SAMPLE_RATE = 24000

# ---------------------------------------------------------------------------
# 请求体 Schema
# ---------------------------------------------------------------------------
class TTSRequest(BaseModel):
    text: str = Field(..., description="要合成的文本")
    voice: Optional[str] = Field(None, description="音色参考 WAV 路径（留空用默认）")
    num_speakers: Optional[int] = Field(1, ge=1, le=4, description="说话人数 1-4")
    cfg_scale: Optional[float] = Field(3.0, ge=1.0, le=10.0, description="CFG guidance scale")
    ddpm_steps: Optional[int] = Field(20, ge=5, le=50, description="扩散推理步数")

# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(title="VibeVoice TTS Server", version="1.0.0", docs_url="/docs")


@app.on_event("startup")
async def startup():
    """启动时加载模型"""
    global model, processor

    model_path = os.environ.get("VIBEVOICE_MODEL_PATH", "")
    if not model_path or not os.path.isdir(model_path):
        raise RuntimeError(
            f"模型目录不存在: {model_path}\n"
            f"请设置环境变量 VIBEVOICE_MODEL_PATH 或使用 --model 参数。\n"
            f"下载模型: huggingface-cli download microsoft/VibeVoice-1.5B "
            f"--local-dir <路径>"
        )

    print(f"[VibeVoice] 加载 processor 从: {model_path}")
    from vibevoice.processor import VibeVoiceProcessor
    processor = VibeVoiceProcessor.from_pretrained(model_path)

    print(f"[VibeVoice] 加载模型到 {device} ...")
    try:
        from vibevoice import VibeVoiceForConditionalGenerationInference
        model = VibeVoiceForConditionalGenerationInference.from_pretrained_hf(
            model_path,
            device=device,
            torch_dtype=torch.bfloat16,
        )
    except Exception as e:
        print(f"[VibeVoice] HF 加载失败 ({e}), 尝试直接加载...")
        from vibevoice.modular import VibeVoiceForConditionalGenerationInference
        model = VibeVoiceForConditionalGenerationInference.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map=device,
            attn_implementation="sdpa",  # Windows fallback
        )

    model.eval()
    model.set_ddpm_inference_steps(20)
    print(f"[VibeVoice] 模型加载完成 ({model_path})")


@app.post("/tts")
async def tts_endpoint(req: TTSRequest):
    """合成语音，返回 WAV 音频"""
    global model, processor

    if model is None or processor is None:
        raise HTTPException(status_code=503, detail="模型未加载")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空")

    # 自动添加 Speaker 前缀（VibeVoice 要求）
    if not text.startswith("Speaker"):
        text = f"Speaker 0: {text}"

    print(f"[VibeVoice] 合成: text_len={len(text)}, speakers={req.num_speakers}")

    # 加载音色参考
    voice_samples = None
    if req.voice and os.path.isfile(req.voice):
        try:
            import torchaudio
            waveform, sr = torchaudio.load(req.voice)
            if sr != SAMPLE_RATE:
                waveform = torchaudio.functional.resample(waveform, sr, SAMPLE_RATE)
            if waveform.shape[0] > 1:
                waveform = waveform.mean(0, keepdim=True)
            voice_samples = [waveform.squeeze(0).numpy()]
            print(f"[VibeVoice] 使用音色参考: {req.voice}")
        except Exception as e:
            print(f"[VibeVoice] 音色加载失败 (将用默认): {e}")

    model.set_ddpm_inference_steps(req.ddpm_steps)

    inputs = processor(
        text=text,
        voice_samples=voice_samples,
        return_tensors="pt",
    ).to(device)

    try:
        with torch.no_grad():
            output = model.generate(
                **inputs,
                tokenizer=processor.tokenizer,
                cfg_scale=req.cfg_scale,
                return_speech=True,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {e}")

    if not output.speech_outputs or output.speech_outputs[0] is None:
        raise HTTPException(status_code=500, detail="未生成音频")

    audio = output.speech_outputs[0].cpu().float().numpy()
    duration = len(audio) / SAMPLE_RATE
    print(f"[VibeVoice] 合成完成: {duration:.1f}s")

    # 编码为 WAV
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(SAMPLE_RATE)
        audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
        wf.writeframes(audio_int16.tobytes())

    return Response(
        content=buf.getvalue(),
        media_type="audio/wav",
        headers={"X-Duration-Secs": f"{duration:.2f}"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": model is not None, "device": device}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VibeVoice 1.5B TTS Server")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8765, help="端口")
    parser.add_argument(
        "--model",
        default="E:/anima_data/models/VibeVoice/VibeVoice-1.5B",
        help="模型权重路径",
    )
    parser.add_argument("--device", default="cuda", help="推理设备 cuda / cpu")
    args = parser.parse_args()

    os.environ["VIBEVOICE_MODEL_PATH"] = args.model
    device = args.device

    print(f"[VibeVoice] 启动服务: {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
