#!/usr/bin/env python3
"""
ChatTTS 模型验证脚本
验证模型文件是否完整并测试加载
"""

import sys
from pathlib import Path


def verify_chattts_model(model_path="E:/anima_data/models/ChatTTS"):
    """验证 ChatTTS 模型"""

    print(f"Verifying ChatTTS model at: {model_path}")
    print("=" * 50)

    model_dir = Path(model_path)

    if not model_dir.exists():
        print(f"[ERROR] Model directory not found: {model_dir}")
        return False

    # 检查必要的模型文件
    required_files = {
        "asset/Decoder.pt": "Decoder model",
        "asset/Decoder.safetensors": "Decoder (safetensors format)",
        "asset/DVAE.pt": "DVAE model",
        "asset/GPT.pt": "GPT model",
        "asset/Embed.safetensors": "Embedding model",
        "asset/Vocos.pt": "Vocos model",
        "asset/tokenizer.pt": "Tokenizer",
    }

    print("\nChecking required files...")
    all_present = True
    for file_path, description in required_files.items():
        full_path = model_dir / file_path
        if full_path.exists():
            size_mb = full_path.stat().st_size / (1024 * 1024)
            print(f"[OK] {description:40s} ({size_mb:6.1f} MB)")
        else:
            print(f"[MISSING] {description:40s}")
            all_present = False

    print("\n" + "=" * 50)

    if all_present:
        print("[OK] All required model files present!")

        # 尝试加载模型
        print("\nAttempting to load model...")
        try:
            import ChatTTS
            import torch

            chat = ChatTTS.Chat()
            chat.load(
                source='custom',
                custom_path=str(model_dir),
                device='cuda' if torch.cuda.is_available() else 'cpu',
                compile=False,
            )

            print("[OK] Model loaded successfully!")
            print(f"[INFO] Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")

            # 释放模型
            del chat
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            return True

        except ImportError:
            print("[ERROR] ChatTTS not installed. Run: pip install ChatTTS")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            return False
    else:
        print("[ERROR] Model files incomplete. Please re-download.")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="验证 ChatTTS 模型")
    parser.add_argument("--model-path", default="E:/anima_data/models/ChatTTS")
    args = parser.parse_args()

    success = verify_chattts_model(args.model_path)
    sys.exit(0 if success else 1)
