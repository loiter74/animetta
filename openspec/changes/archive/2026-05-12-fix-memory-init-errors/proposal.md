## Why

启动时两个 warning 导致内存系统降级：

1. `no such column: is_archived` — 新增列的索引创建早于迁移
2. `'MemorySystem' object has no attribute 'meme_pool'` — 变量声明在 try 块内

## What Changes

- `system.py`: `self.meme_pool = None` 移到 try 块外面
- `memory_entry_store.py`: 新索引创建用 try/except 包裹，不阻塞旧表启动

## Impact

- `src/anima/memory/system.py`: 移动 1 行
- `src/anima/memory/storage/memory_entry_store.py`: 包裹 1 条索引
