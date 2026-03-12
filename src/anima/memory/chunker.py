"""
Markdown 分块算法.

参考 OpenClaw 的 internal.ts:144-215 实现:
- 滑动窗口, 目标 ~400 token/块
- 80 token 重叠, 保留上下文连续性
- 按行边界分割, 记录起止行号
- SHA-256 去重
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .config import ChunkConfig


@dataclass
class RawChunk:
    """分块结果 (未关联文件路径)."""

    text: str
    start_line: int  # 1-based
    end_line: int  # 1-based, inclusive
    content_hash: str
    chunk_index: int


def chunk_markdown(
    content: str,
    config: ChunkConfig | None = None,
) -> list[RawChunk]:
    """
    将 Markdown 内容按滑动窗口分块.

    算法:
    1. 按行拆分
    2. 从当前位置累积行, 直到达到 target_chars
    3. 记录块的起止行号
    4. 回退 overlap_chars 个字符作为下一块的起点
    5. 对每块内容做 SHA-256 哈希

    Returns:
        按顺序排列的 RawChunk 列表
    """
    if config is None:
        config = ChunkConfig()

    lines = content.split("\n")
    if not lines or (len(lines) == 1 and not lines[0].strip()):
        return []

    target = config.target_chars
    overlap = config.overlap_chars

    chunks: list[RawChunk] = []
    chunk_idx = 0
    line_idx = 0  # 当前处理到的行 (0-based)

    while line_idx < len(lines):
        # 累积行直到达到目标大小
        buf_lines: list[str] = []
        buf_chars = 0
        start_line = line_idx  # 0-based

        while line_idx < len(lines) and buf_chars < target:
            line = lines[line_idx]
            buf_lines.append(line)
            buf_chars += len(line) + 1  # +1 for \n
            line_idx += 1

        if not buf_lines:
            break

        text = "\n".join(buf_lines)
        if not text.strip():
            continue

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        chunks.append(
            RawChunk(
                text=text,
                start_line=start_line + 1,  # 转 1-based
                end_line=start_line + len(buf_lines),  # 1-based, inclusive
                content_hash=content_hash,
                chunk_index=chunk_idx,
            )
        )
        chunk_idx += 1

        # 回退 overlap: 从当前位置往回找, 使下一块起点有重叠
        if line_idx < len(lines):
            overlap_chars_remaining = overlap
            backtrack = 0
            for i in range(len(buf_lines) - 1, -1, -1):
                line_len = len(buf_lines[i]) + 1
                if overlap_chars_remaining <= 0:
                    break
                overlap_chars_remaining -= line_len
                backtrack += 1
            # 回退行指针
            line_idx = max(start_line + 1, line_idx - backtrack)

    return chunks
