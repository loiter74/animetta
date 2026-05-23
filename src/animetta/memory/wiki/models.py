"""Wiki page data models — re-exported from persistence.protocols for backward compatibility.

Original definitions (PageType, WikiPage, _parse_dt) live at:
    anima.persistence.protocols

This module is kept for backward compatibility. Internal memory modules and
external consumers can import from either location.
"""

from animetta import $$$

__all__ = ["WikiPage", "PageType"]
