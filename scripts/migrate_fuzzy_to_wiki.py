#!/usr/bin/env python3
"""One-time migration: read FuzzyMemoryStore → wiki/synthesis/fuzzy-<id>.md"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


async def migrate(workspace: str = "~/.anima/workspace") -> int:
    from anima.memory.fuzzy.store import FuzzyMemoryStore
    from anima.memory.wiki.manager import WikiManager
    from anima.memory.wiki.models import WikiPage, PageType
    from anima.memory.manager import MemoryManager
    from anima.memory.config import MemoryConfig

    ws = Path(workspace).expanduser()
    fuzzy_db = str(ws / "fuzzy_memory.sqlite")

    print(f"Opening FuzzyMemoryStore at {fuzzy_db}...")
    fuzzy = FuzzyMemoryStore(fuzzy_db)
    fuzzy.open()

    print("Initializing WikiManager...")
    mgr = MemoryManager(config=MemoryConfig(workspace_dir=str(ws)))
    wiki = WikiManager(mgr)

    all_memories = fuzzy.search_fuzzy(limit=9999)
    print(f"Found {len(all_memories)} fuzzy memories to migrate")

    count = 0
    skipped = 0
    for m in all_memories:
        path = f"synthesis/fuzzy-{m.id}.md"
        if wiki.page_exists(path):
            skipped += 1
            continue
        wiki.write_page(
            WikiPage(
                title=f"模糊记忆: {m.text[:40]}",
                page_type=PageType.SYNTHESIS,
                path=path,
                content=m.text,
                tags=[m.granularity.value, "migrated-fuzzy"],
                metadata={
                    "confidence": m.confidence,
                    "session_id": m.session_id,
                    "migrated_from": "FuzzyMemoryStore",
                },
            )
        )
        count += 1

    fuzzy.close()
    print(f"Done: {count} migrated, {skipped} skipped")
    return count


if __name__ == "__main__":
    import asyncio

    ws = sys.argv[1] if len(sys.argv) > 1 else "~/.anima/workspace"
    asyncio.run(migrate(ws))
