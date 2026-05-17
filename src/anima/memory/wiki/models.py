"""Wiki page data models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


class PageType(Enum):
    ENTITY = "entity"
    CONCEPT = "concept"
    SOURCE = "source"
    SYNTHESIS = "synthesis"
    MEME = "meme"


@dataclass
class WikiPage:
    """Wiki page with frontmatter + Markdown content."""

    title: str
    page_type: PageType
    path: str  # relative to wiki/, e.g. "entities/user.md"
    content: str  # Markdown body (without frontmatter)
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)  # [[wikilink]] targets
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    raw_source: Optional[str] = None  # link to raw/ source file
    metadata: Dict = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Render full Markdown with YAML frontmatter."""
        import yaml

        fm: Dict = {
            "type": self.page_type.value,
            "created": self.created_at.isoformat(),
            "updated": self.updated_at.isoformat(),
        }
        if self.tags:
            fm["tags"] = self.tags
        if self.links:
            fm["links"] = self.links
        if self.raw_source:
            fm["raw_source"] = self.raw_source
        # Merge custom metadata (e.g. id, review_status, is_active for MemeStore)
        if self.metadata:
            fm.update(self.metadata)

        yml = yaml.dump(fm, allow_unicode=True, default_flow_style=False)
        return f"---\n{yml}---\n\n{self.content}\n"

    @classmethod
    def from_markdown(cls, path: str, text: str) -> "WikiPage":
        """Parse a Markdown file with optional YAML frontmatter."""
        content = text
        fm: Dict = {}

        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                import yaml
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                except Exception:
                    fm = {}
                content = parts[2].strip()

        # title from first heading or filename
        title = Path(path).stem.replace("-", " ").replace("_", " ")
        first_line = content.split("\n", 1)[0] if content else ""
        if first_line.startswith("# "):
            title = first_line[2:].strip()

        # extract [[wikilinks]]
        parsed_links = re.findall(r"\[\[(.+?)\]\]", content)

        return cls(
            title=title,
            page_type=PageType(fm.get("type", "entity")),
            path=path,
            content=content,
            tags=fm.get("tags", []),
            links=parsed_links,
            created_at=_parse_dt(fm.get("created")),
            updated_at=_parse_dt(fm.get("updated")),
            raw_source=fm.get("raw_source"),
            metadata=fm,
        )


def _parse_dt(v) -> datetime:
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except Exception:
            logger.warning(f"[WikiModels] Invalid datetime string: {v}")
    return datetime.now()
