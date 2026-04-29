"""Wiki Manager - directory structure & file operations."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..manager import MemoryManager
from .models import PageType, WikiPage

logger = logging.getLogger(__name__)


class WikiManager:
    """
    Wiki-style memory manager.

    Directory layout inside workspace_dir::

        raw/               immutable conversation logs
        wiki/
          index.md         master table-of-contents
          log.md           append-only operation log
          entities/        people, characters, projects
          concepts/        preferences, interests, patterns
          sources/         per-day conversation summaries
          synthesis/       cross-source analysis

    The underlying SQLite + Chroma stores (via MemoryManager) are
    reused for search; only the file organisation and management
    logic are new.
    """

    PAGE_SUBDIRS = {
        PageType.ENTITY: "entities",
        PageType.CONCEPT: "concepts",
        PageType.SOURCE: "sources",
        PageType.SYNTHESIS: "synthesis",
    }

    def __init__(self, manager: MemoryManager):
        self._manager = manager
        self._ws = Path(manager.config.workspace_dir)
        self._raw_dir = self._ws / "raw"
        self._wiki_dir = self._ws / "wiki"
        self._init_structure()

    # ── properties ──────────────────────────────────────────

    @property
    def raw_dir(self) -> Path:
        return self._raw_dir

    @property
    def wiki_dir(self) -> Path:
        return self._wiki_dir

    @property
    def manager(self) -> MemoryManager:
        return self._manager

    # ── bootstrap ───────────────────────────────────────────

    def _init_structure(self) -> None:
        for d in (
            self._raw_dir,
            self._wiki_dir,
            self._wiki_dir / "entities",
            self._wiki_dir / "concepts",
            self._wiki_dir / "sources",
            self._wiki_dir / "synthesis",
        ):
            d.mkdir(parents=True, exist_ok=True)

        index = self._wiki_dir / "index.md"
        if not index.exists():
            index.write_text(
                "# Wiki Index\n\n"
                "## Entities\n\n## Concepts\n\n"
                "## Sources\n\n## Synthesis\n",
                encoding="utf-8",
            )

        log = self._wiki_dir / "log.md"
        if not log.exists():
            log.write_text(
                "# Wiki Operation Log\n\n"
                "| Date | Action | Target | Summary |\n"
                "|------|--------|--------|----------|\n",
                encoding="utf-8",
            )

    # ── raw writes (immutable) ──────────────────────────────

    def write_raw(self, date: datetime, content: str) -> None:
        """Append a conversation turn to the raw daily log."""
        path = self._raw_dir / f"{date.strftime('%Y-%m-%d')}.md"
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n## {date.strftime('%H:%M')}\n{content}\n")
        logger.debug(f"[Wiki] raw -> {path.name}")

    # ── wiki page CRUD ─────────────────────────────────────

    def read_page(self, rel_path: str) -> Optional[WikiPage]:
        full = self._wiki_dir / rel_path
        if not full.exists():
            return None
        return WikiPage.from_markdown(rel_path, full.read_text(encoding="utf-8"))

    def write_page(self, page: WikiPage) -> None:
        full = self._wiki_dir / page.path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(page.to_markdown(), encoding="utf-8")
        logger.debug(f"[Wiki] write -> {page.path}")
        # keep search index in sync
        try:
            self._manager._index_file(f"wiki/{page.path}", page.page_type.value)
        except Exception as exc:
            logger.warning(f"[Wiki] index failed for {page.path}: {exc}")

    def page_exists(self, rel_path: str) -> bool:
        return (self._wiki_dir / rel_path).exists()

    def list_pages(self, page_type: Optional[PageType] = None) -> List[str]:
        if page_type:
            subdir = self.PAGE_SUBDIRS.get(page_type, "")
            base = self._wiki_dir / subdir if subdir else self._wiki_dir
            if not base.exists():
                return []
            return [
                str(p.relative_to(self._wiki_dir)).replace("\\", "/")
                for p in sorted(base.glob("*.md"))
            ]
        return [
            str(p.relative_to(self._wiki_dir)).replace("\\", "/")
            for p in sorted(self._wiki_dir.rglob("*.md"))
            if p.parent != self._wiki_dir  # skip index.md, log.md
        ]

    # ── index / log ─────────────────────────────────────────

    def rebuild_index(self) -> None:
        sections: Dict[str, List[str]] = {
            "Entities": self.list_pages(PageType.ENTITY),
            "Concepts": self.list_pages(PageType.CONCEPT),
            "Sources": self.list_pages(PageType.SOURCE),
            "Synthesis": self.list_pages(PageType.SYNTHESIS),
        }
        lines = ["# Wiki Index\n"]
        for heading, pages in sections.items():
            lines.append(f"\n## {heading}\n")
            for p in sorted(pages):
                name = Path(p).stem.replace("-", " ")
                lines.append(f"- [[{name}]] `({p})`")
        (self._wiki_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def append_log(self, action: str, target: str, summary: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(self._wiki_dir / "log.md", "a", encoding="utf-8") as f:
            f.write(f"| {ts} | {action} | {target} | {summary} |\n")

    # ── link helpers ────────────────────────────────────────

    def extract_links(self, text: str) -> List[str]:
        return re.findall(r"\[\[(.+?)\]\]", text)

    def find_backlinks(self, page_name: str) -> List[str]:
        hits: List[str] = []
        for rel in self.list_pages():
            page = self.read_page(rel)
            if page and page_name in page.links:
                hits.append(rel)
        return hits

    # ── search (delegate) ───────────────────────────────────

    def search(self, query: str, max_results: int = 10):
        return self._manager.search(query, max_results=max_results)

    # ── legacy compat ───────────────────────────────────────

    def get(self, rel_path: str, **kw) -> str:
        return self._manager.get(rel_path, **kw)
