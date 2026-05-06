#!/usr/bin/env python3
"""
Auto-open browser for started services.
"""

import threading
import time
import webbrowser


def open_browser(urls: list[tuple[str, int]]):
    """
    Open multiple URLs in the browser with staggered delays.

    Args:
        urls: List of (url, delay_seconds) tuples.
    """
    def _open(url: str, delay: int):
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    for url, delay in urls:
        t = threading.Thread(target=_open, args=(url, delay), daemon=True)
        t.start()
