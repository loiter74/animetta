#!/usr/bin/env python3
"""
处理 Anima 图标素材：去白底 → 添加 Alpha → 缩放 → 输出 PNG

使用方式:
    python scripts/process_icons.py                         # 处理所有图标
    python scripts/process_icons.py --path path/to/dir       # 处理指定目录
    python scripts/process_icons.py --threshold 245          # 自定义白底阈值
    python scripts/process_icons.py --size 64                # 自定义输出尺寸
"""

import os
import sys
import argparse
from pathlib import Path

from PIL import Image


def remove_white_background(img: Image.Image, threshold: int = 240) -> Image.Image:
    """
    将 RGB 图片的白色/浅灰背景转为透明。

    Args:
        img: RGB 模式 PIL Image
        threshold: 被视为"白色"的阈值 (0-255)，越大越严格

    Returns:
        RGBA 模式 PIL Image，白色背景已透明
    """
    if img.mode == "RGBA":
        return img

    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            # 如果 RGB 都高于阈值→全透明；否则在边界附近做渐变过渡
            if r >= threshold and g >= threshold and b >= threshold:
                # 完全白→全透明
                pixels[x, y] = (r, g, b, 0)
            else:
                # 计算距离阈值的差值，做边缘 feather
                distance = min(r, g, b)  # 取最小通道值作为"非白程度"
                if distance >= threshold - 30 and r >= threshold - 15 and g >= threshold - 15 and b >= threshold - 15:
                    # 过渡区域：根据非白程度渐变 alpha
                    alpha = max(0, min(255, int((threshold - distance) * 8)))
                    pixels[x, y] = (r, g, b, alpha)

    return img


def process_image(
    input_path: str,
    output_path: str,
    threshold: int = 240,
    target_size: int = 64,
    resize: bool = True,
) -> bool:
    """
    处理单个图片：去白底 → RGBA → 缩放 → 保存 PNG

    Returns:
        True 如果处理成功
    """
    try:
        img = Image.open(input_path)
    except Exception as e:
        print(f"  [SKIP] 无法打开 {input_path}: {e}")
        return False

    original_mode = img.mode
    original_format = img.format

    # Step 1: 去白底
    if img.mode != "RGBA":
        img = remove_white_background(img, threshold)

    # Step 2: 缩放
    if resize and target_size and (img.width > target_size or img.height > target_size):
        img = img.resize((target_size, target_size), Image.LANCZOS)

    # Step 3: 保存
    img.save(output_path, "PNG")

    print(
        f"  [OK] {os.path.basename(input_path):30s}"
        f"  {original_format:5s}→PNG"
        f"  {img.width:4d}x{img.height:<4d}"
    )
    return True


def process_directory(
    directory: str,
    threshold: int = 240,
    target_size: int = 64,
    resize: bool = True,
    pattern: str = "*.png",
) -> int:
    """
    批量处理目录下所有图片。

    Returns:
        成功处理的文件数
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"[ERROR] 目录不存在: {directory}")
        return 0

    success = 0
    for img_path in sorted(dir_path.glob(pattern)):
        if process_image(str(img_path), str(img_path), threshold, target_size, resize):
            success += 1

    return success


def process_icons_recursive(
    base_dir: str,
    threshold: int = 240,
    target_size: int = 64,
) -> int:
    """
    递归处理 icons/ 目录下所有子目录中的图标。
    每找到一个 PNG/JPEG 就原地替换。

    Returns:
        成功处理的文件数
    """
    base = Path(base_dir)
    if not base.exists():
        print(f"[ERROR] 目录不存在: {base_dir}")
        return 0

    total = 0
    for subdir in sorted(base.iterdir()):
        if not subdir.is_dir():
            continue
        print(f"\n  → {subdir.name}/")
        count = process_directory(str(subdir), threshold, target_size)
        total += count

    return total


def main():
    parser = argparse.ArgumentParser(
        description="Anima 图标处理工具：去白底 + 缩放 + 转 PNG"
    )
    parser.add_argument(
        "--path",
        default=None,
        help="处理单个文件或目录（默认处理所有图标和素材）",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=240,
        help="白色阈值 (0-255)，默认 240",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=64,
        help="目标尺寸（像素），默认 64",
    )
    parser.add_argument(
        "--no-resize",
        action="store_true",
        help="不缩放图片",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent

    if args.path:
        # 处理指定路径
        path = Path(args.path)
        if path.is_file():
            ext = path.suffix.lower()
            out_path = path.with_suffix(".png") if ext != ".png" else path
            process_image(
                str(path),
                str(out_path),
                args.threshold,
                args.size,
                not args.no_resize,
            )
        elif path.is_dir():
            count = process_directory(
                str(path),
                args.threshold,
                args.size,
                not args.no_resize,
            )
            print(f"\n处理完成: {count} 个文件")
        return

    # 默认处理流程
    print("=" * 50)
    print("Anima 图标处理工具")
    print("=" * 50)
    print(f"\n白色阈值: {args.threshold}")
    print(f"目标尺寸: {args.size if not args.no_resize else '不缩放'}")

    # 1. 处理 service icons
    icons_dir = project_root / "frontend" / "public" / "icons"
    if icons_dir.exists():
        print(f"\n[1/3] 处理服务图标 ({icons_dir})")
        count = process_icons_recursive(str(icons_dir), args.threshold, args.size)
        print(f"\n[1/3] 完成: {count} 个图标已处理")

    # 2. 检查 avatar / loading / error
    print(f"\n[2/3] 检查其他素材")
    other_assets = [
        ("avatar", project_root / "frontend" / "public" / "avatar" / "avatar.png"),
        ("loading", project_root / "frontend" / "public" / "loading" / "loading.png"),
        ("error", project_root / "frontend" / "public" / "error" / "error.png"),
        ("favicon", project_root / "frontend" / "public" / "favicon.png"),
    ]

    for name, path in other_assets:
        if not path.exists():
            print(f"  [SKIP] {name}: 文件不存在")
            continue
        img = Image.open(str(path))
        if img.mode != "RGBA":
            print(f"  [FIX]  {name}: {img.format} {img.mode} → 添加 Alpha")
            process_image(
                str(path), str(path), args.threshold, args.size, not args.no_resize
            )
        else:
            print(f"  [OK]  {name}: 已经是 RGBA")

    # 3. 检查背景图（只报告，不修改，除非有白底问题）
    print(f"\n[3/3] 检查背景图")
    bg_dir = project_root / "frontend" / "public" / "backgrounds"
    if bg_dir.exists():
        for f in sorted(bg_dir.glob("*.png")):
            img = Image.open(str(f))
            w, h = img.size
            cx, cy = w // 2, h // 2
            center = img.getpixel((cx, cy))
            # 如果中心是浅色且 mode 为 RGB（无 Alpha），标记为可能需要处理
            if img.mode != "RGBA" and all(c > 200 for c in center[:3]):
                print(f"  [WARN] {f.name}: 中心偏白 {center}，可能需要处理")
            else:
                print(f"  [OK]  {f.name}: {img.mode} 中心={center}")

    print(f"\n{'=' * 50}")
    print("全部完成！请重启 Vite dev server 并硬刷新浏览器查看效果。")
    print("=" * 50)


if __name__ == "__main__":
    main()
