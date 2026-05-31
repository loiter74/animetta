"""
Memory event handlers — wiki pages, memory organization.
"""

from typing import TYPE_CHECKING

from loguru import logger

from .base_handler import BaseSocketHandler

if TYPE_CHECKING:
    from socketio import AsyncServer

    from ..desktop import DesktopClientManager
    from ..live2d import Live2DManager
    from ..session import SessionManager


class MemoryHandlers(BaseSocketHandler):
    """Memory and wiki event handlers.

    Inherits shared infrastructure from BaseSocketHandler.
    """

    def __init__(
        self,
        sio: "AsyncServer",
        session_manager: "SessionManager",
        desktop_manager: "DesktopClientManager",
        live2d_manager: "Live2DManager",
    ):
        super().__init__(sio, session_manager, desktop_manager, live2d_manager)

    # ── Memory: Wiki Pages ─────────────────────────────────────────────

    async def on_get_wiki_pages(self, sid: str, data: dict) -> dict:
        """获取 wiki 页面列表"""
        try:
            # Try session-level memory_system
            ctx = self.session_manager.get_context(sid)
            if (
                ctx
                and ctx.memory_system
                and hasattr(ctx.memory_system, "_wiki_manager")
            ):
                wiki = ctx.memory_system._wiki_manager
                pages = []
                for rel in wiki.list_pages():
                    page = wiki.read_page(rel)
                    if page:
                        pages.append(
                            {
                                "path": page.path,
                                "title": page.title,
                                "page_type": page.page_type.value,
                                "content": page.content[:200],
                                "tags": page.tags,
                                "updated_at": page.updated_at.isoformat()
                                if page.updated_at
                                else "",
                            }
                        )
                logger.info(f"[{sid}] Wiki pages (from memory): {len(pages)}")
                return {"pages": pages}

            # Fallback: read wiki files directly from workspace
            from pathlib import Path

            workspace = Path("./memory_db")
            wiki_dir = workspace / "wiki"
            if not wiki_dir.exists():
                return {"pages": []}

            pages = []
            TYPE_MAP = {
                "entities": "entity",
                "concepts": "concept",
                "sources": "source",
                "synthesis": "synthesis",
                "memes": "meme",
            }
            for md_file in sorted(wiki_dir.rglob("*.md")):
                rel = str(md_file.relative_to(wiki_dir)).replace("\\", "/")
                content = md_file.read_text(encoding="utf-8")[:500]
                title = md_file.stem
                parent = md_file.parent.name if md_file.parent != wiki_dir else "source"
                pages.append(
                    {
                        "path": rel,
                        "title": title,
                        "page_type": TYPE_MAP.get(parent, parent),
                        "content": content,
                        "tags": [],
                        "updated_at": str(Path(md_file).stat().st_mtime),
                    }
                )
            logger.info(
                f"[{sid}] Wiki pages (from disk): {len(pages)} pages, "
                f"types={list(set(p['page_type'] for p in pages))}"
            )
            return {"pages": pages}
        except Exception as e:
            logger.error(f"[{sid}] get_wiki_pages failed: {e}")
            return {"pages": []}

    # ── Memory organization ────────────────────────────────────────────

    async def on_memory_organize(self, sid: str, data: dict) -> None:
        """Trigger memory organization."""
        logger.info(f"[{sid}] Received memory organization request")

        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx or not ctx.memory_system:
                await self.sio.emit(
                    "memory.organize.result",
                    {"type": "error", "message": "Memory system not initialized"},
                    to=sid,
                )
                return

            memory_system = ctx.memory_system
            if not memory_system._wiki_manager:
                await self.sio.emit(
                    "memory.organize.result",
                    {"type": "error", "message": "Wiki manager not initialized"},
                    to=sid,
                )
                return


            llm_client = None
            if ctx.llm_engine:
                llm_client = ctx.llm_engine

            organizer = WikiOrganizer(
                wiki=memory_system._wiki_manager,
                llm_client=llm_client,
            )

            async def progress_callback(text, pct):
                await self.sio.emit(
                    "memory.organize.progress",
                    {"text": text, "progress": pct},
                    to=sid,
                )

            result = await organizer.organize(progress_callback=progress_callback)

            await self.sio.emit(
                "memory.organize.result",
                {
                    "type": "success",
                    "merges": result.get("merges", 0),
                    "synthesis": result.get("synthesis", 0),
                    "updates": result.get("updates", 0),
                    "errors": result.get("errors", []),
                },
                to=sid,
            )

            logger.info(
                f"[{sid}] Memory organization complete: "
                f"merges={result.get('merges', 0)}, "
                f"synthesis={result.get('synthesis', 0)}, "
                f"updates={result.get('updates', 0)}"
            )

        except Exception as e:
            logger.error(f"[{sid}] Memory organization failed: {e}", exc_info=True)
            await self.sio.emit(
                "memory.organize.result",
                {"type": "error", "message": str(e)},
                to=sid,
            )
