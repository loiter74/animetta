"""
VibeVoice 一键安装脚本
======================
在 Windows 上部署 VibeVoice 1.5B TTS 模型 + FastAPI 推理服务。

用法:
    python scripts/setup_vibevoice.py

步骤:
    1. 克隆 davidamacey/VibeVoice (社区 fork，恢复了 TTS-1.5B 推理代码)
    2. 创建虚拟环境并安装依赖
    3. 从 HuggingFace 下载模型权重 (~6GB)
    4. 启动推理服务

注意:
    - 需安装 Git for Windows: https://git-scm.com/
    - 需安装 CUDA 12.x: https://developer.nvidia.com/cuda-downloads
    - RTX 5090D 建议搭配 CUDA 12.8
    - 如果在国内无法直连 HuggingFace，脚本会自动使用 hf-mirror.com
"""

import os
import sys
import subprocess
import argparse
import time
import urllib.request
from pathlib import Path

REPO_URL = "https://github.com/davidamacey/VibeVoice.git"
MODEL_REPO = "microsoft/VibeVoice-1.5B"
HF_ENDPOINT = "https://huggingface.co"  # 默认，会自动检测镜像


def check_network_speed(url: str, timeout: int = 5) -> tuple:
    """测试网络连通性和速度，返回 (reachable: bool, speed_bytes_per_sec: float)"""
    try:
        start = time.time()
        urllib.request.urlopen(url, timeout=timeout)
        elapsed = time.time() - start
        return True, 1.0 / max(elapsed, 0.001)
    except Exception:
        return False, 0.0


def auto_detect_hf_endpoint() -> str:
    """自动检测 HuggingFace 可用镜像"""
    endpoints = [
        ("https://huggingface.co", "官方"),
        ("https://hf-mirror.com", "国内镜像"),
    ]
    best_url = "https://huggingface.co"
    best_speed = 0.0

    print("\n检测 HuggingFace 网络连接...")
    for url, name in endpoints:
        ok, speed = check_network_speed(url)
        status = f"{'✅' if ok else '❌'} {speed:.1f} req/s"
        print(f"  {name}: {url} [{status}]")
        if ok and speed > best_speed:
            best_speed = speed
            best_url = url

    if best_url != "https://huggingface.co":
        print(f"  → 使用镜像: {best_url}")
    return best_url


def run(cmd: str, cwd: str = None, check: bool = True):
    """运行 shell 命令并打印输出"""
    print(f"\n$ {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=False, text=True
    )
    if check and result.returncode != 0:
        print(f"✗ 命令失败 (exit={result.returncode})")
        sys.exit(result.returncode)
    return result


    # 自动检测网络，选择镜像
    global HF_ENDPOINT
    HF_ENDPOINT = auto_detect_hf_endpoint()


def main():
    parser = argparse.ArgumentParser(description="VibeVoice 一键安装")
    parser.add_argument(
        "--install-dir",
        default=str(Path.home() / "VibeVoice"),
        help="安装目录 (默认 ~/VibeVoice)",
    )
    parser.add_argument(
        "--model-dir",
        default="E:/animetta_data/models/VibeVoice",
        help="模型权重目录 (默认 E:/animetta_data/models/VibeVoice)",
    )
    parser.add_argument(
        "--skip-clone", action="store_true", help="跳过 git clone（目录已存在时）"
    )
    parser.add_argument(
        "--skip-download", action="store_true", help="跳过模型下载"
    )
    parser.add_argument(
        "--skip-install", action="store_true", help="跳过依赖安装"
    )
    parser.add_argument(
        "--start-server", action="store_true", help="安装完成后启动推理服务"
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="推理服务端口 (默认 8765)"
    )
    parser.add_argument(
        "--device", default="cuda", help="推理设备 (默认 cuda)"
    )
    args = parser.parse_args()

    install_dir = Path(args.install_dir)
    model_dir = Path(args.model_dir)

    print("=" * 60)
    print("  VibeVoice 1.5B 一键安装")
    print("=" * 60)
    print(f"  安装目录:     {install_dir}")
    print(f"  模型目录:     {model_dir}")
    print(f"  推理设备:     {args.device}")
    print(f"  服务端口:     {args.port}")
    print("=" * 60)

    # ---- 1. 克隆仓库 ----
    if not args.skip_clone:
        if install_dir.exists():
            print(f"\n[1/5] 目录已存在: {install_dir}")
            ans = input("  是否重新克隆? (y/n, 默认 n): ").strip().lower()
            if ans == "y":
                run(f"rmdir /s /q \"{install_dir}\"" if sys.platform == "win32" else f"rm -rf {install_dir}")
                run(f"git clone {REPO_URL} \"{install_dir}\"")
            else:
                print("  跳过克隆")
        else:
            print(f"\n[1/5] 克隆仓库: {REPO_URL}")
            run(f"git clone {REPO_URL} \"{install_dir}\"")
    else:
        print("\n[1/5] 跳过克隆")

    # ---- 2. 创建虚拟环境 ----
    venv_dir = install_dir / ".venv"
    python_path = venv_dir / "Scripts" / "python.exe"
    pip_path = venv_dir / "Scripts" / "pip.exe"

    if not args.skip_install:
        if not venv_dir.exists():
            print(f"\n[2/5] 创建虚拟环境: {venv_dir}")
            run(f"python -m venv \"{venv_dir}\"")
        else:
            print(f"\n[2/5] 虚拟环境已存在: {venv_dir}")

        # ---- 3. 安装依赖 ----
        print(f"\n[3/5] 安装 PyTorch (CUDA)...")
        run(f"\"{pip_path}\" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128")

        print(f"\n[3/5] 安装 VibeVoice 依赖...")
        run(f"\"{pip_path}\" install -e \"{install_dir}\"")

        print(f"\n[3/5] 安装 Web 服务依赖...")
        run(f"\"{pip_path}\" install fastapi uvicorn[standard] soundfile")
    else:
        print("\n[2/5] 跳过虚拟环境")
        print("\n[3/5] 跳过依赖安装")

    # ---- 4. 下载模型 ----
    if not args.skip_download:
        model_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n[4/5] 下载模型 {MODEL_REPO}")
        print(f"  目标: {model_dir} (~6GB, 可能需要几分钟...)")
        run(f"\"{pip_path}\" install huggingface-hub")
        run(
            f"\"{python_path}\" -m huggingface_hub.commands.download"
            f" --resume-download {MODEL_REPO}"
            f" --local-dir \"{model_dir}\""
        )
        print(f"  模型下载完成 ✅")
    else:
        print("\n[4/5] 跳过模型下载")

    # ---- 5. 启动服务 ----
    if args.start_server:
        print(f"\n[5/5] 启动 VibeVoice 推理服务 (端口 {args.port})...")
        print(f"  Python: {python_path}")
        print(f"  模型:   {model_dir}")
        print(f"  设备:   {args.device}")
        print(f"\n  按 Ctrl+C 停止服务\n")

        server_script = Path(__file__).resolve().parent / "vibe_voice_server.py"
        run(
            f"\"{python_path}\" \"{server_script}\""
            f" --model \"{model_dir}\""
            f" --port {args.port}"
            f" --device {args.device}"
        )
    else:
        print(f"\n[5/5] 跳过启动。")
        print(f"\n  手动启动:")
        print(f"    \"{python_path}\" scripts/vibe_voice_server.py"
              f" --model \"{model_dir}\" --port {args.port}")

    print("\n" + "=" * 60)
    print("  安装完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
