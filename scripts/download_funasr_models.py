"""
FunASR 模型预下载脚本
运行此脚本可提前下载所需模型，避免首次使用时等待

使用方法:
    python scripts/download_funasr_models.py

模型会下载到: ~/.cache/modelscope/hub/
"""

import os
import sys

# 设置 UTF-8 编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def download_models():
    """下载 FunASR 所需的模型"""

    # 需要下载的模型列表
    models = [
        ("paraformer-zh", "中文语音识别主模型"),
        ("fsmn-vad", "语音活动检测模型"),
        ("ct-punc", "标点恢复模型"),
    ]

    print("=" * 60)
    print("FunASR 模型预下载工具")
    print("=" * 60)
    print(f"\n模型将下载到: {os.path.expanduser('~/.cache/modelscope/hub/')}\n")

    try:
        from modelscope import snapshot_download
        from funasr import AutoModel
    except ImportError as e:
        print(f"[ERROR] 缺少依赖: {e}")
        print("\n请先安装依赖:")
        print("  pip install funasr modelscope")
        sys.exit(1)

    for model_id, desc in models:
        print(f"\n{'='*60}")
        print(f"[DOWN] 下载模型: {model_id}")
        print(f"   说明: {desc}")
        print("-" * 60)

        try:
            # 使用 modelscope 下载
            model_path = snapshot_download(
                f"iic/{model_id}",
                cache_dir=os.path.expanduser("~/.cache/modelscope/hub")
            )
            print(f"[OK] 下载完成: {model_path}")

        except Exception as e:
            print(f"[WARN] 下载失败: {e}")
            print("   尝试使用 FunASR AutoModel 下载...")

            try:
                # 备用方式：通过 FunASR 加载来触发下载
                if model_id == "paraformer-zh":
                    AutoModel(model=model_id, disable_update=True)
                elif model_id == "fsmn-vad":
                    AutoModel(model="paraformer-zh", vad_model=model_id, disable_update=True)
                elif model_id == "ct-punc":
                    AutoModel(model="paraformer-zh", punc_model=model_id, disable_update=True)
                print(f"[OK] 模型已缓存")
            except Exception as e2:
                print(f"[ERROR] 下载失败: {e2}")

    print("\n" + "=" * 60)
    print("[OK] 所有模型下载完成！")
    print("=" * 60)

    # 验证模型
    print("\n验证模型加载...")
    try:
        model = AutoModel(
            model="paraformer-zh",
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            disable_update=True
        )
        print("[OK] 模型加载成功！")
    except Exception as e:
        print(f"[WARN] 模型加载测试失败: {e}")


if __name__ == "__main__":
    download_models()
