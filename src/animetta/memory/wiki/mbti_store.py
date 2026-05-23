"""
MBTIStore — reads/writes the MBTI personality profile from/to wiki concept pages.

Persists the current MBTI dimension scores and change history as a Markdown
wiki page at concepts/personality-mbti.md, using WikiPage metadata for
structured data and the content body for the human-readable profile.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..manager import MemoryManager as _MemoryManager
from ..wiki.manager import WikiManager
from ...persistence.protocols import PageType, WikiPage

logger = logging.getLogger(__name__)

# Wiki page path constant
MBTI_PAGE_PATH = "concepts/personality-mbti.md"


class MBTIStore:
    """Persistent storage for MBTI personality profile.

    Stores the current MBTI profile in a wiki concept page with:
    - Current dimension scores + confidence
    - Natural language description
    - Append-only change history table
    """

    def __init__(self, wiki: WikiManager):
        self._wiki = wiki

    # ── Public API ────────────────────────────────────────────

    def load_profile(self) -> Optional[Dict[str, Any]]:
        """Load the current MBTI profile from wiki.

        Returns:
            Dict with keys: type, dimensions, description, confidence, history
            None if the wiki page does not exist or is corrupted.
        """
        page = self._wiki.read_page(MBTI_PAGE_PATH)
        if not page:
            return None

        try:
            return self._parse_page(page)
        except Exception as e:
            logger.warning(f"[MBTIStore] Failed to parse wiki page: {e}")
            return None

    def save_profile(self, profile: Dict[str, Any]) -> None:
        """Save/update the MBTI profile to wiki.

        Appends a change history entry if dimensions changed from previous state.

        Args:
            profile: Dict with keys: type, dimensions (ei/sn/tf/jp), description, confidence
        """
        # Load existing to compute diff
        existing = self.load_profile()

        # Build change history
        history: List[Dict[str, Any]] = []
        if existing and "history" in existing:
            history = list(existing["history"])

        if existing and "dimensions" in existing:
            old_dims = existing["dimensions"]
            new_dims = profile.get("dimensions", {})
            if self._dimensions_changed(old_dims, new_dims):
                trigger = self._build_trigger(old_dims, new_dims)
                history.append({
                    "date": datetime.now().isoformat()[:10],
                    **{k: old_dims.get(k, 50) for k in ("ei", "sn", "tf", "jp")},
                    "delta": json_delta(old_dims, new_dims),
                    "trigger": trigger,
                })

        # Cap history to last 50 entries
        if len(history) > 50:
            history = history[-50:]

        # Build wiki page content
        dims = profile.get("dimensions", {})
        content_lines = [
            "# MBTI Personality Profile",
            "",
            "## Current State",
            f"- **Type**: {profile.get('type', 'N/A')}",
            f"- **Confidence**: {profile.get('confidence', 0.5):.2f}",
            "- **Dimensions**:",
            f"  - E/I: {dims.get('ei', 50)} (内向 {100-dims.get('ei', 50)}% / 外向 {dims.get('ei', 50)}%)",
            f"  - S/N: {dims.get('sn', 50)} (实感 {100-dims.get('sn', 50)}% / 直觉 {dims.get('sn', 50)}%)",
            f"  - T/F: {dims.get('tf', 50)} (共情 {100-dims.get('tf', 50)}% / 理性 {dims.get('tf', 50)}%)",
            f"  - J/P: {dims.get('jp', 50)} (随性 {100-dims.get('jp', 50)}% / 计划 {dims.get('jp', 50)}%)",
            "",
            "## Description",
            profile.get("description", ""),
            "",
        ]

        if history:
            content_lines.append("## Change History")
            content_lines.append("| Date | E/I | S/N | T/F | J/P | Δ | Trigger |")
            content_lines.append("|------|-----|-----|-----|-----|---|---------|")
            for entry in history:
                delta_str = entry.get("delta", "")
                content_lines.append(
                    f"| {entry.get('date', '')} "
                    f"| {entry.get('ei', '')} | {entry.get('sn', '')} "
                    f"| {entry.get('tf', '')} | {entry.get('jp', '')} "
                    f"| {delta_str} | {entry.get('trigger', '')} |"
                )

        content = "\n".join(content_lines)

        page = WikiPage(
            title="MBTI Personality Profile",
            page_type=PageType.CONCEPT,
            path=MBTI_PAGE_PATH,
            content=content,
            tags=["mbti", "personality"],
            links=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={
                "mbti_type": profile.get("type", ""),
                "mbti_ei": dims.get("ei", 50),
                "mbti_sn": dims.get("sn", 50),
                "mbti_tf": dims.get("tf", 50),
                "mbti_jp": dims.get("jp", 50),
                "mbti_confidence": profile.get("confidence", 0.5),
            },
        )

        self._wiki.write_page(page)
        logger.info(f"[MBTIStore] Saved profile: type={profile.get('type')}, dims=({dims.get('ei')},{dims.get('sn')},{dims.get('tf')},{dims.get('jp')})")

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the change history as a list of dicts."""
        existing = self.load_profile()
        if existing and "history" in existing:
            return list(existing["history"])
        return []

    def profile_exists(self) -> bool:
        """Check if a MBTI profile wiki page exists."""
        return self._wiki.page_exists(MBTI_PAGE_PATH)

    # ── Internal helpers ──────────────────────────────────────

    def _parse_page(self, page: WikiPage) -> Dict[str, Any]:
        """Parse a WikiPage into a structured MBTI profile dict."""
        meta = page.metadata or {}

        # Extract dimensions from metadata or content
        dims = {
            "ei": meta.get("mbti_ei", 50),
            "sn": meta.get("mbti_sn", 50),
            "tf": meta.get("mbti_tf", 50),
            "jp": meta.get("mbti_jp", 50),
        }

        # Parse change history from content
        history: List[Dict[str, Any]] = []
        for line in page.content.split("\n"):
            if line.startswith("|") and "|" in line[1:]:
                cells = [c.strip() for c in line.split("|")]
                # Skip header/separator rows
                if len(cells) >= 6 and cells[1].replace("-", "").strip():
                    try:
                        int(cells[1])  # only data rows with numeric date -> skip
                    except ValueError:
                        continue
                    entry = {
                        "date": cells[1],
                        "ei": _parse_int(cells[2]),
                        "sn": _parse_int(cells[3]),
                        "tf": _parse_int(cells[4]),
                        "jp": _parse_int(cells[5]),
                        "delta": cells[6] if len(cells) > 6 else "",
                        "trigger": cells[7] if len(cells) > 7 else "",
                    }
                    history.append(entry)

        return {
            "type": meta.get("mbti_type", ""),
            "dimensions": dims,
            "description": self._extract_description(page.content),
            "confidence": meta.get("mbti_confidence", 0.5),
            "history": history,
        }

    @staticmethod
    def _extract_description(content: str) -> str:
        """Extract the Description section from wiki page content."""
        in_desc = False
        desc_lines: List[str] = []
        for line in content.split("\n"):
            if line.strip() == "## Description":
                in_desc = True
                continue
            if in_desc:
                if line.startswith("## "):
                    break
                if line.strip():
                    desc_lines.append(line.strip())
        return " ".join(desc_lines)

    @staticmethod
    def _dimensions_changed(old: Dict[str, int], new: Dict[str, int]) -> bool:
        """Check if any dimension value changed."""
        for key in ("ei", "sn", "tf", "jp"):
            if old.get(key, 50) != new.get(key, 50):
                return True
        return False

    @staticmethod
    def _build_trigger(old: Dict[str, int], new: Dict[str, int]) -> str:
        """Build a trigger description from dimension changes."""
        changes: List[str] = []
        labels = {"ei": "E/I", "sn": "S/N", "tf": "T/F", "jp": "J/P"}
        for key in ("ei", "sn", "tf", "jp"):
            delta = new.get(key, 50) - old.get(key, 50)
            if delta != 0:
                changes.append(f"{labels[key]}{delta:+d}")
        return "维度调整: " + ", ".join(changes) if changes else "自动更新"


def json_delta(old: Dict[str, int], new: Dict[str, int]) -> str:
    """Format dimension changes as a compact string."""
    changes: List[str] = []
    for key in ("ei", "sn", "tf", "jp"):
        delta = new.get(key, 50) - old.get(key, 50)
        if delta != 0:
            changes.append(f"{key}={delta:+d}")
    return ", ".join(changes) if changes else "no change"


def _parse_int(val: Any) -> int:
    """Safely parse an integer value."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return 50
