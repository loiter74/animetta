"""Spectator client window capture for the vision perception agent.

Captures the host-side Minecraft spectator client window into a downscaled
JPEG frame. The capture is best-effort: any failure (missing window, missing
platform support, capture error) degrades to ``None`` so perception continues
with the environment agent only.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import hashlib
import io
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass(frozen=True, slots=True)
class CapturedFrame:
    """One downscaled JPEG frame plus capture metadata."""

    jpeg: bytes
    width: int
    height: int
    window_title: str
    captured_at_ms: int
    content_hash: str


def _enumerate_window_titles() -> list[str]:
    """Return titles of visible top-level windows (Windows only, best-effort)."""

    if sys.platform != "win32":
        return []
    try:
        user32 = ctypes.windll.user32
        titles: list[str] = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        def _callback(hwnd: int, _lparam: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            titles.append(buffer.value)
            return True

        user32.EnumWindows(_callback, 0)
        return titles
    except Exception as exc:  # pragma: no cover - platform dependent
        logger.debug("perception window enumeration failed: {}", exc)
        return []


def find_viewer_window(title_pattern: str) -> str | None:
    """Find the first visible window whose title matches ``title_pattern``."""

    try:
        pattern = re.compile(title_pattern)
    except re.error:
        pattern = re.compile(re.escape(title_pattern))
    for title in _enumerate_window_titles():
        if title and pattern.search(title):
            return title
    return None


class ViewerFrameCapture:
    """Capture the spectator client window region from the primary display."""

    def __init__(
        self,
        *,
        title_pattern: str = "(?i)minecraft",
        max_edge: int = 896,
        jpeg_quality: int = 72,
        enumerate_titles: Callable[[], list[str]] = _enumerate_window_titles,
    ) -> None:
        self._title_pattern = title_pattern
        self._max_edge = max_edge
        self._jpeg_quality = jpeg_quality
        self._enumerate_titles = enumerate_titles

    def _matching_title(self) -> str | None:
        try:
            pattern = re.compile(self._title_pattern)
        except re.error:
            pattern = re.compile(re.escape(self._title_pattern))
        for title in self._enumerate_titles():
            if title and pattern.search(title):
                return title
        return None

    def capture(self) -> CapturedFrame | None:
        """Grab the viewer window area; return ``None`` on any degradation."""

        title = self._matching_title()
        if title is None:
            return None
        rect = _window_rect_by_title(title)
        if rect is None:
            return None
        return self.capture_region(rect, window_title=title)

    def capture_region(
        self,
        rect: tuple[int, int, int, int],
        *,
        window_title: str = "",
    ) -> CapturedFrame | None:
        """Capture a screen rectangle; injectable for tests."""

        try:
            from PIL import Image, ImageGrab

            left, top, right, bottom = rect
            width = max(1, right - left)
            height = max(1, bottom - top)
            image = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
            image = image.convert("RGB")
            scale = min(1.0, self._max_edge / max(width, height))
            if scale < 1.0:
                image = image.resize(
                    (max(1, int(width * scale)), max(1, int(height * scale))),
                    Image.Resampling.LANCZOS,
                )
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=self._jpeg_quality)
            jpeg = buffer.getvalue()
            return CapturedFrame(
                jpeg=jpeg,
                width=image.width,
                height=image.height,
                window_title=window_title,
                captured_at_ms=int(time.time() * 1000),
                content_hash=hashlib.sha256(jpeg).hexdigest(),
            )
        except Exception as exc:
            logger.debug("perception frame capture failed: {}", exc)
            return None


def _window_rect_by_title(title: str) -> tuple[int, int, int, int] | None:
    """Return the screen rectangle of the first visible window titled ``title``."""

    if sys.platform != "win32":
        return None
    try:
        user32: Any = ctypes.windll.user32

        target: int | None = None

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        def _callback(hwnd: int, _lparam: int) -> bool:
            nonlocal target
            if target is not None or not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length != len(title):
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if buffer.value == title:
                target = hwnd
            return True

        user32.EnumWindows(_callback, 0)
        if target is None:
            return None
        rect = ctypes.wintypes.RECT()
        if not user32.GetWindowRect(target, ctypes.byref(rect)):
            return None
        if rect.right - rect.left < 200 or rect.bottom - rect.top < 150:
            return None
        return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception as exc:  # pragma: no cover - platform dependent
        logger.debug("perception window rect lookup failed: {}", exc)
        return None
