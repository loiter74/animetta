## 1. 修复 ServicePool.init() 传入 model_manager

- [ ] 1.1 在 `ServicePool.init()` 中接收 `model_manager` 参数并传给 `ServiceContext`
- [ ] 1.2 确保 `__pool__` session 的模型 preload 函数被注册到 `ModelLoadingManager`

## 2. 修复 SessionManager.create_context() 传入 model_manager

- [ ] 2.1 将 `WebSocketServer.model_manager` 传递给 `SessionManager`
- [ ] 2.2 `create_context()` 创建 `ServiceContext` 时传入 `model_manager`

## 3. 验证

- [ ] 3.1 重启后端，检查日志确认模型在启动时就开始加载（非首次使用时）
- [ ] 3.2 检查无已注册模型时 warmup 静默跳过
