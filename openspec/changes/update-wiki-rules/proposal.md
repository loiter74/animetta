## Why

`WIKI_RULES.md` 未随架构重构更新：缺 `memes/` 目录、缺 `meme` 页面类型、命名规范还写"四个子目录"。同时该文件没有源码模板，只在 workspace 数据目录中存在。

## What Changes

- 更新 `memory_db/wiki/WIKI_RULES.md`：加 memes/ 目录、meme 类型、更新命名规范
- 在 `config/` 下创建 `wikirules.template.md` 作为源码模板
- `WikiManager._init_structure()` 首次初始化时从模板写入 WIKI_RULES.md

## Impact

- `memory_db/wiki/WIKI_RULES.md` → 内容更新
- `config/wikirules.template.md` → 新建源码模板
- `src/anima/memory/wiki/manager.py` → _init_structure 加规则文件初始化
