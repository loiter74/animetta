#!/usr/bin/env python3
"""
ChatTTS 模型下载脚本
将 ChatTTS 模型下载到 E:/anima_data/models/ChatTTS
"""

import os
import sys
from pathlib import Path


def download_chattts_model():
    """下载 ChatTTS 模型到指定目录"""

    model_dir = Path("E:/anima_data/models/ChatTTS")
    model_dir.mkdir(parents=True, exist_ok=True)

    print(f"Target directory: {model_dir}")
    print("=" * 50)

    # 检查 huggingface_hub
    try:
        from huggingface_hub import snapshot_download
        print("[OK] huggingface_hub installed")
    except ImportError:
        print("[INFO] Installing huggingface_hub...")
        os.system("pip install huggingface_hub")
        from huggingface_hub import snapshot_download

    # ChatTTS 模型信息
    repo_id = "2Noise/ChatTTS"

    print(f"\nStarting download ChatTTS model...")
    print(f"Repo: {repo_id}")
    print(f"Target: {model_dir}")
    print(f"Size: ~3-4 GB")
    print("\nThis may take a few minutes, please wait...")
    print("=" * 50)

    try:
        # 下载模型
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
        )

        print("\n" + "=" * 50)
        print("[OK] ChatTTS model download completed!")
        print(f"Model path: {model_dir}")

        # 验证下载
        config_file = model_dir / "config.json"
        if config_file.exists():
            print("[OK] Model files verified")
        else:
            print("[WARN] config.json not found, download may be incomplete")

        return True

    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        print("\nPossible reasons:")
        print("  1. Network connection issue")
        print("  2. HuggingFace access restricted")
        print("  3. Insufficient disk space")
        print("\nSuggestions:")
        print("  - Check network connection")
        print("  - Set proxy: set HF_ENDPOINT=https://hf-mirror.com")
        print("  - Use VPN")
        return False


if __name__ == "__main__":
    success = download_chattts_model()
    sys.exit(0 if success else 1)
