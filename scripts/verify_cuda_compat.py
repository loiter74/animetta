"""
CUDA Compatibility Verification Script for RTX 50-series (Blackwell) GPUs

Checks whether PyTorch + CUDA setup supports RTX 5090D / 5080 / 5070.
Run: python scripts/verify_cuda_compat.py
"""

import sys
import platform


def check(condition: bool, message: str, fix: str = "") -> bool:
    """Print pass/fail with optional fix guidance."""
    if condition:
        print(f"  [PASS] {message}")
        return True
    else:
        print(f"  [FAIL] {message}")
        if fix:
            print(f"         Fix: {fix}")
        return False


def main() -> int:
    print("=" * 60)
    print("  CUDA / PyTorch Compatibility Checker")
    print("  (RTX 50-series / Blackwell / sm_120)")
    print("=" * 60)
    print()

    passed = 0
    failed = 0

    def c(cond, msg, fix=""):
        nonlocal passed, failed
        if check(cond, msg, fix):
            passed += 1
        else:
            failed += 1

    # --- Python ---
    py_version = sys.version_info
    c(
        py_version >= (3, 10),
        f"Python {py_version.major}.{py_version.minor}.{py_version.micro} (≥ 3.10)",
    )

    # --- Platform ---
    system = platform.system()
    c(system in ("Linux", "Windows"), f"OS: {system}")

    if system == "Linux":
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version --format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            c(True, f"nvidia-smi detected: {result.stdout.strip()}")
        else:
            c(False, "nvidia-smi not available", "Install NVIDIA drivers with WSL2 support")

    # --- PyTorch ---
    try:
        import torch
    except ImportError:
        c(False, "PyTorch not installed", "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128")
        print(f"\n  {passed} passed, {failed} failed")
        return 1 if failed > 0 else 0

    c(True, f"PyTorch {torch.__version__}")

    # --- CUDA availability ---
    cuda_avail = torch.cuda.is_available()
    c(cuda_avail, "torch.cuda.is_available()",
      "Install cu128 PyTorch: pip install torch ... --index-url https://download.pytorch.org/whl/cu128")

    if cuda_avail:
        # --- CUDA version ---
        cuda_ver = torch.version.cuda
        c(
            tuple(int(x) for x in cuda_ver.split(".")) >= (12, 8),
            f"CUDA {cuda_ver} (≥ 12.8)",
            "Install CUDA 12.8+ toolkit and reinstall PyTorch with cu128 index"
        )

        # --- GPU name ---
        gpu_name = torch.cuda.get_device_name(0)
        c(True, f"GPU: {gpu_name}")

        # --- Compute capability ---
        capability = torch.cuda.get_device_capability(0)
        major, minor = capability
        is_blackwell = major >= 12
        c(
            is_blackwell,
            f"Compute Capability: sm_{major}{minor} (Blackwell)" if is_blackwell else f"Compute Capability: sm_{major}{minor}",
            "If this is a 50-series GPU but capability < 12.0, update your NVIDIA driver to ≥ 565.90"
        )

        # --- Arch list (critical check) ---
        arch_list = torch.cuda.get_arch_list()
        expected_arch = f"sm_{major}{minor}"
        has_arch = any(expected_arch in arch for arch in arch_list)
        c(
            has_arch,
            f"Arch list contains {expected_arch}",
            f"PyTorch build does not support sm_{major}{minor}. "
            "Reinstall with: pip install torch torchvision torchaudio --force-reinstall "
            "--index-url https://download.pytorch.org/whl/cu128"
        )

        # --- Actual CUDA kernel execution test ---
        try:
            x = torch.randn(1000, 1000, device="cuda")
            y = torch.randn(1000, 1000, device="cuda")
            z = x @ y
            c(
                z.shape == (1000, 1000),
                "CUDA matmul test: tensor(1000,1000) @ tensor(1000,1000) = " + str(z.shape),
                "CUDA kernel execution failed — wrong PyTorch build for this GPU"
            )
            del x, y, z
            torch.cuda.empty_cache()
        except Exception as e:
            c(False, f"CUDA kernel execution test FAILED: {e}",
              "Wrong PyTorch build for this GPU. Use cu128 index.")

    print()
    print("-" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("-" * 60)

    if failed == 0:
        print("  [OK] Your setup is fully compatible with RTX 50-series GPUs.")
        print("  You can proceed with GPT-SoVITS and Anima setup.")
    else:
        print(f"  [{failed} issue(s) found] Review the fixes above.")
        print("  Key command: pip install torch torchvision torchaudio")
        print("    --index-url https://download.pytorch.org/whl/cu128")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
