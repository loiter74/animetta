## 1. 删除死代码

- [x] 1.1 删除 `frontend/src/components/memory/MemoryDrillDown.vue`
- [x] 1.2 删除 `frontend/src/components/meme/` 整个目录（MemePanel/MemeAddForm/MemeHistory）
- [x] 1.3 删除 `frontend/src/stores/meme.ts`

## 2. 合并 Meme 功能到 MemoryPanel

- [x] 2.1 在 MemoryPanel 底部加快速添加梗输入框（text + send，emit `meme_add`）
- [x] 2.2 添加后自动刷新 wiki 页面列表

## 3. InteractivePanel 统一 tab

- [x] 3.1 移除 `InteractivePanel.vue` 中的 `meme` tab
- [x] 3.2 移除 MemePanel 的 import

## 4. 验证

- [x] 4.1 Frontend TypeScript 编译通过
- [x] 4.2 后端测试通过
