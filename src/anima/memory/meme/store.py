"""Wiki-backed persistence for MemePool."""

from __future__ import annotations

from .models import Meme, MemeSource
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MemeStore:
    """Meme CRUD backed by WikiManager (wiki/memes/)."""

    def __init__(self, wiki: object) -> None:
        from ...memory.wiki.manager import WikiManager as _WikiManager
        from ...memory.wiki.models import WikiPage, PageType as _PageType
        self._wiki: _WikiManager = wiki
        self._WikiPage = _WikiPage
        self._PageType = _PageType

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    # ── CRUD ──────────────────────────────────────────────

    def insert(self, meme: Meme) -> str:
        self._wiki.write_page(self._meme_to_page(meme))
        return meme.id

    def update(self, meme: Meme) -> None:
        self._wiki.write_page(self._meme_to_page(meme))

    def get(self, meme_id: str) -> Optional[Meme]:
        page = self._wiki.read_page(f"memes/{meme_id}.md")
        return self._page_to_meme(page) if page else None

    def get_active(self, limit: int = 10) -> List[Meme]:
        all_pages = self._wiki.list_pages(self._PageType.MEME)
        memes = []
        for p in all_pages:
            page = self._wiki.read_page(p)
            if page:
                m = self._page_to_meme(page)
                if m and m.is_active:
                    memes.append(m)
        memes.sort(key=lambda m: m.current_score, reverse=True)
        return memes[:limit]

    def get_inactive(self, limit: int = 50) -> List[Meme]:
        all_pages = self._wiki.list_pages(self._PageType.MEME)
        memes = []
        for p in all_pages:
            page = self._wiki.read_page(p)
            if page:
                m = self._page_to_meme(page)
                if m and not m.is_active:
                    memes.append(m)
        memes.sort(key=lambda m: m.current_score, reverse=True)
        return memes[:limit]

    def update_score(self, meme_id: str, new_score: float) -> None:
        page = self._wiki.read_page(f"memes/{meme_id}.md")
        if page:
            page.metadata["current_score"] = new_score
            self._wiki.write_page(page)

    def increment_use(self, meme_id: str) -> None:
        page = self._wiki.read_page(f"memes/{meme_id}.md")
        if page:
            page.metadata["use_count"] = page.metadata.get("use_count", 0) + 1
            page.metadata["last_used_at"] = datetime.now().isoformat()
            self._wiki.write_page(page)

    def set_active(self, meme_id: str, active: bool) -> None:
        page = self._wiki.read_page(f"memes/{meme_id}.md")
        if page:
            page.metadata["is_active"] = active
            self._wiki.write_page(page)

    def delete(self, meme_id: str) -> None:
        path = self._wiki._wiki_dir / "memes" / f"{meme_id}.md"
        if path.exists():
            path.unlink()

    def count_active(self) -> int:
        return len(self.get_active(limit=9999))

    # ── MemePool compatibility layer ──────────────────────

    def list_active(self) -> List[Meme]:
        return self.get_active(limit=9999)

    def save(self, meme: Meme) -> str:
        return self.insert(meme)

    def discard(self, meme_id: str) -> None:
        self.set_active(meme_id, False)

    def list_discarded(self) -> List[Meme]:
        return self.get_inactive(limit=9999)

    def resurrect(self, meme_id: str) -> None:
        self.set_active(meme_id, True)

    # ── conversion helpers ─────────────────────────────────

    def _meme_to_page(self, meme: Meme) -> object:
        return self._WikiPage(
            title=meme.text[:50] if meme.text else "untitled",
            page_type=self._PageType.MEME,
            path=f"memes/{meme.id}.md",
            content=meme.text,
            tags=meme.tags.copy(),
            metadata={
                "id": meme.id,
                "context_hint": meme.context_hint,
                "source": meme.source.value,
                "base_score": meme.base_score,
                "current_score": meme.current_score,
                "use_count": meme.use_count,
                "last_used_at": meme.last_used_at.isoformat() if meme.last_used_at else None,
                "is_active": meme.is_active,
                "resurrection_count": meme.resurrection_count,
            },
        )

    def _page_to_meme(self, page: object) -> Optional[Meme]:
        md = page.metadata
        if not md.get("id"):
            return None
        return Meme(
            id=md.get("id", page.path.replace(".md", "").split("/")[-1]),
            text=page.content,
            context_hint=md.get("context_hint", ""),
            source=MemeSource(md.get("source", "ai")),
            tags=page.tags,
            base_score=md.get("base_score", 0.7),
            current_score=md.get("current_score", 0.7),
            use_count=md.get("use_count", 0),
            last_used_at=(
                datetime.fromisoformat(md["last_used_at"])
                if md.get("last_used_at") else None
            ),
            is_active=md.get("is_active", True),
            resurrection_count=md.get("resurrection_count", 0),
        )
