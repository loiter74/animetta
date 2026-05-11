## 1. Fix meme_pool init

- [x] 1.1 Move `self.meme_pool: Optional[MemePool] = None` before the outer try block in `system.py`

## 2. Fix new column migration

- [x] 2.1 Wrap `idx_mem_archived` CREATE INDEX in try/except in `memory_entry_store.py` ddl()
