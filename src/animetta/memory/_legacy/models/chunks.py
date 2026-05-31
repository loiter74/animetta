"""
Markdown chunking algorithm.

Reference OpenClaw's internal.ts:144-215 implementation:
- Sliding window, target ~400 tokens/chunk
- 80 token overlap to preserve context continuity
- SHA-256 deduplication
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..config import ChunkConfig


@dataclass
class RawChunk:
    """Raw chunking result"""
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
    Chunk Markdown content using a sliding window.

    Algorithm:
    1. Split by lines
    2. Accumulate lines from current position until target_chars reached
    3. Record chunk start and end line numbers
    4. Roll back overlap_chars characters as start of next chunk
    5. Compute SHA-256 hash for each chunk

    Returns:
        List of RawChunk objects in order
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
    line_idx = 0  # Current processing line (0-based)

    while line_idx < len(lines):
        # Accumulate lines until target size reached
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
                start_line=start_line + 1,  # Convert to 1-based
                end_line=start_line + len(buf_lines),  # 1-based, inclusive
                content_hash=content_hash,
                chunk_index=chunk_idx,
            )
        )
        chunk_idx += 1

        # Roll back by overlap: search backward from current position so the next chunk starts with overlap
        if line_idx < len(lines):
            overlap_chars_remaining = overlap
            backtrack = 0
            for i in range(len(buf_lines) - 1, -1, -1):
                line_len = len(buf_lines[i]) + 1
                if overlap_chars_remaining <= 0:
                    break
                overlap_chars_remaining -= line_len
                backtrack += 1
            # Rewind line pointer
            line_idx = max(start_line + 1, line_idx - backtrack)

    return chunks
