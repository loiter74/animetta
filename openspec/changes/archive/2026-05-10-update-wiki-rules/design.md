## Context

架构重构新增了 `memes/` 目录和 `PageType.MEME`，但 `WIKI_RULES.md` 未同步更新。该文件是 LLM 维护 wiki 的行为规范，需要保持准确。

## Goals / Non-Goals

**Goals:**
- 更新 WIKI_RULES.md：目录结构、页面类型、命名规范
- 创建源码模板确保规则不丢失

**Non-Goals:**
- 不改变 wiki 存储或处理逻辑

## Decisions

1. **模板放在 `config/`** — 与其他配置文件一致，不混入 `src/`
2. **首次写入，不覆盖** — `_init_structure` 只在文件不存在时写入，防止覆盖用户修改
