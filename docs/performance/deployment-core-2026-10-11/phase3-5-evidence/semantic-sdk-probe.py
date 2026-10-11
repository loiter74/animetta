import asyncio
import json
import sys
from pathlib import Path

from animetta.memory.v2.store import AtomStore


async def main():
    root = Path(sys.argv[1])
    root.mkdir(parents=True, exist_ok=True)
    store = AtomStore(str(root / "memory.sqlite"), enable_chroma=True)
    await store.initialize()
    store._chroma_collection.upsert(
        ids=["bounded-sdk-probe"], embeddings=[[1.0, 0.0, 0.0]],
        documents=["SDK persistence probe"],
    )
    first = store._chroma_collection.query(query_embeddings=[[1.0, 0.0, 0.0]], n_results=1)
    await store.close()
    reopened = AtomStore(str(root / "memory.sqlite"), enable_chroma=True)
    await reopened.initialize()
    second = reopened._chroma_collection.query(query_embeddings=[[1.0, 0.0, 0.0]], n_results=1)
    assert first["ids"] == second["ids"] == [["bounded-sdk-probe"]]
    await reopened.close()
    import importlib.metadata
    print(json.dumps({"status": "passed", "python": sys.version,
        "chromadb": importlib.metadata.version("chromadb"),
        "persistent_ids": second["ids"], "embedding_model_downloaded": False,
        "scope": "Real SDK and native storage with supplied embeddings; no language-quality parity claim"}))


asyncio.run(main())
