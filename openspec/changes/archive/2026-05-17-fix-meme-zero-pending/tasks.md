## 1. 诊断日志

- [x] 1.1 `MemePool.add_from_candidate()` 保存成功后增加 INFO 日志：meme.id + review_status
- [x] 1.2 `MemeStore.get_active()` 增加 DEBUG 日志：wiki 总页数 + active 数量
- [x] 1.3 `admin_handlers.on_meme_collect` 增加 INFO 日志：`list_active()` 原始返回数量

## 2. 修复

- [x] 2.1 诊断根因：`WikiPage.to_markdown()` 丢弃了 metadata dict，导致 MemeStore 的 id/is_active/review_status 无法持久化
- [x] 2.2 修复：`to_markdown()` 在序列化时将 `self.metadata` 合并到 YAML frontmatter

## 3. 验证

- [x] 3.1 直接测试：Before 0 active → After 2 active + 2 pending
